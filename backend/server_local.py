#!/usr/bin/env python3
"""
PDFShield — Servidor Local de Teste
====================================
Roda com APENAS Python 3.8+ + reportlab + pypdf instalados.
NÃO precisa de FastAPI, uvicorn, PostgreSQL ou Docker.

Como rodar:
  pip install reportlab pypdf
  python server_local.py

Acesse:
  Painel de testes:  http://localhost:8000
  API (Swagger):     http://localhost:8000/docs
  Todos os endpoints disponíveis em http://localhost:8000

Funcionalidades disponíveis localmente:
  ✓ Upload de PDF base
  ✓ Geração de PDF protegido com marca d'água + fingerprint
  ✓ Download do PDF gerado
  ✓ Detecção de vazamento (upload de PDF suspeito)
  ✓ Listar vendas
  ✓ Simulação de webhook (sem chave real)
  ✗ Envio de e-mail (simulado, mostra o conteúdo no terminal)
  ✗ Pagamento real (simulado via endpoint /api/test/simular-pagamento)
"""

import cgi
import hashlib
import io
import json
import mimetypes
import os
import re
import secrets
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Adicionar o diretório atual ao path para importar app/
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.pdf_engine import BuyerInfo, generate_protected_pdf, extract_fingerprint
    from app.email_service import _html as email_html, _text as email_text
    ENGINE_OK = True
    print("✓ Motor de PDF carregado")
except ImportError as e:
    print(f"✗ Erro ao importar motor: {e}")
    print("  Execute: pip install reportlab pypdf")
    ENGINE_OK = False

# ── Stores em memória ──────────────────────────────────────────────────────
_pdfs:   dict[str, dict] = {}
_sales:  dict[str, dict] = {}
_tokens: dict[str, dict] = {}
_logs:   list[dict]      = []

BASE_URL = "http://localhost:8000"


def _log(event: str, detail: str = ""):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "event": event,
        "detail": detail,
    }
    _logs.insert(0, entry)
    if len(_logs) > 50:
        _logs.pop()
    print(f"  [{entry['time']}] {event}" + (f" — {detail}" if detail else ""))


def _new_token(txn_id: str, hours: int = 48, max_dl: int = 2) -> str:
    token = secrets.token_urlsafe(16)
    _tokens[token] = {
        "txn_id":         txn_id,
        "expires":        time.time() + hours * 3600,
        "downloads_left": max_dl,
    }
    return token


# ── Handler HTTP ────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silenciar logs padrão do servidor

    def _send(self, status: int, body, content_type="application/json"):
        if isinstance(body, (dict, list)):
            data = json.dumps(body, ensure_ascii=False, indent=2).encode()
        elif isinstance(body, str):
            data = body.encode()
        else:
            data = body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(200, b"")

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        qs     = parse_qs(parsed.query)

        # ── Painel de testes HTML ──────────────────────────────────────────
        if path in ("", "/"):
            self._send(200, self._painel_html(), "text/html; charset=utf-8")

        # ── Docs (lista de endpoints) ──────────────────────────────────────
        elif path == "/docs":
            self._send(200, self._docs_html(), "text/html; charset=utf-8")

        # ── Health ──────────────────────────────────────────────────────────
        elif path == "/api" or path == "/api/health":
            self._send(200, {
                "service": "PDFShield API (local)",
                "version": "1.0.0",
                "status":  "ok",
                "engine":  ENGINE_OK,
                "pdfs_uploaded": len(_pdfs),
                "sales":         len(_sales),
            })

        # ── Listar vendas ───────────────────────────────────────────────────
        elif path == "/api/sales":
            sales = [{k: v for k, v in s.items() if k != "protected_pdf"}
                     for s in _sales.values()]
            self._send(200, {"total": len(sales), "sales": sales})

        # ── Detalhes de uma venda ───────────────────────────────────────────
        elif path.startswith("/api/sales/"):
            txn_id = path[len("/api/sales/"):]
            sale = _sales.get(txn_id)
            if not sale:
                self._send(404, {"error": "Venda não encontrada."})
            else:
                self._send(200, {k: v for k, v in sale.items() if k != "protected_pdf"})

        # ── Download seguro ────────────────────────────────────────────────
        elif path.startswith("/api/downloads/"):
            token = path[len("/api/downloads/"):]
            td = _tokens.get(token)
            if not td:
                self._send(404, {"error": "Token inválido."})
                return
            if time.time() > td["expires"]:
                self._send(410, {"error": "Link expirado."})
                return
            if td["downloads_left"] <= 0:
                self._send(429, {"error": "Limite de downloads atingido."})
                return
            sale = _sales.get(td["txn_id"])
            if not sale:
                self._send(404, {"error": "Venda não encontrada."})
                return
            td["downloads_left"]   -= 1
            sale["downloads_used"] += 1
            filename = sale["filename"].replace(".pdf", f"_{sale['short_hash']}.pdf")
            pdf_bytes = sale["protected_pdf"]
            _log("DOWNLOAD", f"{sale['buyer']['name']} — {filename}")
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(pdf_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(pdf_bytes)

        # ── Detalhes da compra por token ───────────────────────────────────
        elif path == "/api/purchase":
            token = qs.get("token", [None])[0]
            td = _tokens.get(token) if token else None
            if not td:
                self._send(404, {"error": "Token inválido."})
                return
            sale = _sales.get(td["txn_id"])
            if not sale:
                self._send(404, {"error": "Venda não encontrada."})
                return
            self._send(200, {
                "transaction_id": sale["transaction_id"],
                "filename":       sale["filename"],
                "buyer_name":     sale["buyer"]["name"],
                "buyer_email":    sale["buyer"]["email"],
                "short_hash":     sale["short_hash"],
                "downloads_used": sale["downloads_used"],
                "max_downloads":  sale["max_downloads"],
                "expires_at":     sale["expires_at"],
                "status":         sale["status"],
                "created_at":     sale["created_at"],
                "download_url":   f"{BASE_URL}/api/downloads/{token}",
            })

        # ── Logs ───────────────────────────────────────────────────────────
        elif path == "/api/logs":
            self._send(200, {"logs": _logs})

        else:
            self._send(404, {"error": f"Endpoint não encontrado: {path}"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")

        # Lê o corpo
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length else b""

        ct = self.headers.get("Content-Type", "")

        # ── Upload de PDF base ─────────────────────────────────────────────
        if path == "/api/pdfs/upload":
            if "multipart/form-data" not in ct:
                self._send(400, {"error": "Envie como multipart/form-data"})
                return
            # Parsear multipart
            boundary = ct.split("boundary=")[-1].encode()
            parts    = raw_body.split(b"--" + boundary)
            pdf_bytes, filename = None, "documento.pdf"
            for part in parts:
                if b'filename="' in part:
                    fn_match = re.search(rb'filename="([^"]+)"', part)
                    if fn_match:
                        filename = fn_match.group(1).decode()
                    header_end = part.find(b"\r\n\r\n")
                    if header_end != -1:
                        pdf_bytes = part[header_end + 4:].rstrip(b"\r\n")
            if not pdf_bytes:
                self._send(400, {"error": "Nenhum arquivo encontrado."})
                return
            if not filename.lower().endswith(".pdf"):
                self._send(400, {"error": "Apenas .pdf aceito."})
                return
            pdf_id = str(uuid.uuid4())
            _pdfs[pdf_id] = {
                "pdf_id":      pdf_id,
                "filename":    filename,
                "bytes":       pdf_bytes,
                "size_bytes":  len(pdf_bytes),
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            _log("UPLOAD", f"{filename} ({round(len(pdf_bytes)/1024,1)} KB) → {pdf_id[:8]}…")
            self._send(200, {
                "pdf_id":   pdf_id,
                "filename": filename,
                "size_kb":  round(len(pdf_bytes) / 1024, 1),
                "message":  "Upload realizado com sucesso.",
            })

        # ── Gerar PDF protegido ────────────────────────────────────────────
        elif path == "/api/pdfs/generate":
            try:
                body = json.loads(raw_body)
            except Exception:
                self._send(400, {"error": "JSON inválido."}); return
            pdf_id = body.get("pdf_id", "")
            if pdf_id not in _pdfs:
                self._send(404, {"error": f"pdf_id '{pdf_id}' não encontrado."}); return
            if not ENGINE_OK:
                self._send(500, {"error": "Motor PDF não disponível. pip install reportlab pypdf"}); return
            buyer = BuyerInfo(
                name=body.get("buyer_name", "Comprador"),
                email=body.get("buyer_email", "email@exemplo.com"),
                transaction_id=body.get("transaction_id", str(uuid.uuid4())[:8]),
                cpf=body.get("buyer_cpf"),
            )
            pdf_bytes, uhash = generate_protected_pdf(
                _pdfs[pdf_id]["bytes"], buyer,
                watermark_opacity=body.get("watermark_opacity", 0.18),
            )
            txn_id     = buyer.transaction_id
            token      = _new_token(txn_id,
                                     body.get("expires_hours", 48),
                                     body.get("max_downloads", 2))
            expires_at = (datetime.now(timezone.utc) +
                          timedelta(hours=body.get("expires_hours", 48))).isoformat()
            _sales[txn_id] = {
                "transaction_id":  txn_id,
                "pdf_id":          pdf_id,
                "filename":        _pdfs[pdf_id]["filename"],
                "buyer":           {"name": buyer.name, "email": buyer.email, "cpf": buyer.cpf},
                "hash":            uhash,
                "short_hash":      buyer.short_hash(),
                "protected_pdf":   pdf_bytes,
                "download_token":  token,
                "expires_at":      expires_at,
                "downloads_used":  0,
                "max_downloads":   body.get("max_downloads", 2),
                "created_at":      datetime.now(timezone.utc).isoformat(),
                "status":          "active",
            }
            _log("PDF GERADO", f"{buyer.name} — {_pdfs[pdf_id]['filename']} ({round(len(pdf_bytes)/1024,1)} KB)")
            # Simular e-mail
            self._print_email(buyer, _pdfs[pdf_id]["filename"], token,
                              body.get("expires_hours", 48),
                              body.get("max_downloads", 2))
            self._send(200, {
                "transaction_id": txn_id,
                "buyer_hash":     uhash,
                "short_hash":     buyer.short_hash(),
                "download_token": token,
                "download_url":   f"{BASE_URL}/api/downloads/{token}",
                "expires_at":     expires_at,
                "pdf_size_kb":    round(len(pdf_bytes) / 1024, 1),
            })

        # ── Detectar vazamento ─────────────────────────────────────────────
        elif path == "/api/pdfs/detect-leak":
            if "multipart/form-data" not in ct:
                self._send(400, {"error": "Envie como multipart/form-data"}); return
            boundary  = ct.split("boundary=")[-1].encode()
            parts     = raw_body.split(b"--" + boundary)
            pdf_bytes = None
            for part in parts:
                if b'filename="' in part:
                    header_end = part.find(b"\r\n\r\n")
                    if header_end != -1:
                        pdf_bytes = part[header_end + 4:].rstrip(b"\r\n")
            if not pdf_bytes:
                self._send(400, {"error": "Nenhum arquivo encontrado."}); return
            if not ENGINE_OK:
                self._send(500, {"error": "Motor PDF não disponível."}); return
            result = extract_fingerprint(pdf_bytes)
            matched_buyer = None
            if result.get("found") and result.get("hash"):
                extracted = result["hash"]
                for txn_id, sale in _sales.items():
                    sh = sale["hash"]
                    if sh == extracted or sh.startswith(extracted) or \
                       extracted.startswith(sale["short_hash"]):
                        matched_buyer = {
                            "transaction_id": txn_id,
                            "name":  sale["buyer"]["name"],
                            "email": sale["buyer"]["email"],
                            "cpf":   sale["buyer"]["cpf"],
                            "hash":  sale["hash"],
                            "purchased_at": sale["created_at"],
                        }
                        sale["status"] = "leaked"
                        break
            _log("DETECTOR", f"found={result.get('found')} método={result.get('method')}")
            self._send(200, {**result, "buyer": matched_buyer})

        # ── Simular pagamento (sem Stripe real) ────────────────────────────
        elif path == "/api/test/simular-pagamento":
            try:
                body = json.loads(raw_body)
            except Exception:
                self._send(400, {"error": "JSON inválido."}); return
            pdf_id = body.get("pdf_id", list(_pdfs.keys())[0] if _pdfs else "")
            if pdf_id not in _pdfs:
                self._send(404, {"error": "Faça upload de um PDF primeiro."}); return
            buyer = BuyerInfo(
                name=body.get("buyer_name", "Comprador Teste"),
                email=body.get("buyer_email", "comprador@teste.com"),
                transaction_id=f"TEST-{secrets.token_urlsafe(6).upper()}",
                cpf=body.get("buyer_cpf"),
            )
            pdf_bytes, uhash = generate_protected_pdf(_pdfs[pdf_id]["bytes"], buyer)
            token      = _new_token(buyer.transaction_id, 48, 2)
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
            _sales[buyer.transaction_id] = {
                "transaction_id":  buyer.transaction_id,
                "pdf_id":          pdf_id,
                "filename":        _pdfs[pdf_id]["filename"],
                "buyer":           {"name": buyer.name, "email": buyer.email, "cpf": buyer.cpf},
                "hash":            uhash,
                "short_hash":      buyer.short_hash(),
                "protected_pdf":   pdf_bytes,
                "download_token":  token,
                "expires_at":      expires_at,
                "downloads_used":  0,
                "max_downloads":   2,
                "created_at":      datetime.now(timezone.utc).isoformat(),
                "status":          "active",
                "payment_provider": "simulado",
                "amount_brl":      97.00,
            }
            _log("PAGAMENTO SIMULADO", f"{buyer.name} — TXN: {buyer.transaction_id}")
            self._print_email(buyer, _pdfs[pdf_id]["filename"], token, 48, 2)
            self._send(200, {
                "message":        "Pagamento simulado com sucesso!",
                "transaction_id": buyer.transaction_id,
                "buyer_hash":     uhash,
                "short_hash":     buyer.short_hash(),
                "download_url":   f"{BASE_URL}/api/downloads/{token}",
                "expires_at":     expires_at,
            })

        else:
            self._send(404, {"error": f"Endpoint não encontrado: {path}"})

    # ── Helpers ────────────────────────────────────────────────────────────

    def _print_email(self, buyer: "BuyerInfo", filename: str,
                     token: str, hours: int, max_dl: int):
        """Simula o envio de e-mail — imprime no terminal."""
        url = f"{BASE_URL}/api/downloads/{token}"
        print()
        print("  " + "─" * 52)
        print("  📧 E-MAIL SIMULADO (seria enviado por Resend/SendGrid)")
        print("  " + "─" * 52)
        print(f"  Para:     {buyer.name} <{buyer.email}>")
        print(f"  Assunto:  ✓ Seu PDF está pronto — {filename.replace('.pdf','')}")
        print(f"  Link:     {url}")
        print(f"  Válido:   {hours}h · {max_dl} downloads")
        print(f"  Hash:     {buyer.short_hash()}…")
        print("  " + "─" * 52)
        print()

    def _painel_html(self) -> str:
        """Painel de testes visual — abre no browser."""
        pdfs_opts = "".join(
            f'<option value="{pid}">{rec["filename"]} ({round(rec["size_bytes"]/1024,1)} KB)</option>'
            for pid, rec in _pdfs.items()
        )
        pdfs_opts = pdfs_opts or '<option value="">— faça upload primeiro —</option>'
        sales_rows = ""
        for s in list(_sales.values())[-5:]:
            sales_rows += f"""<tr>
              <td>{s['buyer']['name']}</td>
              <td style="font-family:monospace;font-size:11px">{s['short_hash']}…</td>
              <td><span class="tag tag-{s['status']}">{s['status']}</span></td>
              <td><a href="/api/downloads/{s['download_token']}" target="_blank">baixar</a></td>
            </tr>"""
        logs_html = ""
        for l in _logs[:8]:
            logs_html += f'<div class="log-item"><span class="log-time">{l["time"]}</span> <strong>{l["event"]}</strong>{" — "+l["detail"] if l["detail"] else ""}</div>'

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>PDFShield — Teste Local</title>
<style>
  :root{{--ink:#0D0D0D;--bg:#F5F0E8;--surface:#fff;--border:rgba(0,0,0,0.1);
    --flame:#FF4D2E;--green:#16a34a;--amber:#b45309;--red:#dc2626;
    --mono:'JetBrains Mono',monospace;--sans:system-ui,sans-serif}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);font-family:var(--sans);color:var(--ink);font-size:14px}}
  header{{background:var(--ink);color:white;padding:16px 32px;display:flex;align-items:center;justify-content:space-between}}
  .logo{{font-size:18px;font-weight:700}}.logo em{{color:var(--flame);font-style:normal}}
  .local-badge{{background:rgba(255,255,255,0.15);padding:4px 10px;font-size:11px;font-family:var(--mono);border-radius:4px}}
  .wrap{{max-width:960px;margin:0 auto;padding:24px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden}}
  .card-head{{padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:13px;display:flex;align-items:center;justify-content:space-between}}
  .card-body{{padding:16px}}
  label{{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#666;margin-bottom:5px;margin-top:10px}}
  label:first-child{{margin-top:0}}
  input,select,textarea{{width:100%;padding:8px 12px;border:1px solid var(--border);border-radius:4px;font-family:var(--sans);font-size:13px;background:var(--bg)}}
  input:focus,select:focus{{outline:none;border-color:var(--flame)}}
  .btn{{width:100%;padding:10px;background:var(--ink);color:white;border:none;cursor:pointer;font-size:13px;font-weight:600;border-radius:4px;margin-top:12px;transition:background .15s}}
  .btn:hover{{background:var(--flame)}}
  .btn-sm{{padding:5px 12px;font-size:11px;background:var(--ink);color:white;border:none;cursor:pointer;border-radius:4px;transition:background .15s;width:auto;margin:0}}
  .btn-sm:hover{{background:var(--flame)}}
  .result{{margin-top:10px;padding:10px 12px;background:#f0f0e8;border:1px solid var(--border);border-radius:4px;font-family:var(--mono);font-size:11px;white-space:pre-wrap;word-break:break-all;min-height:40px;color:#333;display:none}}
  .result.show{{display:block}}
  .result.ok{{background:#f0fdf4;border-color:#86efac;color:#166534}}
  .result.err{{background:#fef2f2;border-color:#fca5a5;color:#991b1b}}
  table{{width:100%;border-collapse:collapse;font-size:12px}}
  th{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#888}}
  td{{padding:7px 8px;border-bottom:1px solid var(--border)}}
  .tag{{padding:2px 7px;border-radius:3px;font-size:10px;font-weight:600;font-family:var(--mono)}}
  .tag-active{{background:#dcfce7;color:#166534}}
  .tag-leaked{{background:#fee2e2;color:#991b1b}}
  .tag-revoked{{background:#fee2e2;color:#991b1b}}
  .tag-simulado{{background:#dbeafe;color:#1e40af}}
  a{{color:var(--flame);text-decoration:none}}a:hover{{text-decoration:underline}}
  .log-item{{padding:5px 0;border-bottom:1px solid var(--border);font-size:12px;line-height:1.4}}
  .log-time{{font-family:var(--mono);font-size:10px;color:#888}}
  .status-bar{{display:flex;gap:12px;margin-bottom:16px;font-size:12px}}
  .status-pill{{padding:5px 12px;border-radius:20px;font-weight:600}}
  .s-ok{{background:#dcfce7;color:#166534}}.s-warn{{background:#fef9c3;color:#854d0e}}
  .full{{grid-column:1/-1}}
  .endpoint-tag{{font-size:10px;font-family:var(--mono);background:#f0f0e8;padding:2px 6px;border-radius:3px;color:#555}}
  @media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header>
  <div class="logo">PDF<em>Shield</em></div>
  <div class="local-badge">MODO LOCAL · localhost:8000</div>
</header>
<div class="wrap">

<div class="status-bar">
  <span class="status-pill {'s-ok' if ENGINE_OK else 's-warn'}">{'✓ Motor PDF ativo' if ENGINE_OK else '✗ Instale reportlab + pypdf'}</span>
  <span class="status-pill s-ok">✓ Servidor rodando</span>
  <span class="status-pill {'s-ok' if _pdfs else 's-warn'}">{len(_pdfs)} PDF(s) carregado(s)</span>
  <span class="status-pill {'s-ok' if _sales else 's-warn'}">{len(_sales)} venda(s)</span>
</div>

<div class="grid">

  <!-- Upload PDF -->
  <div class="card">
    <div class="card-head">1. Upload do PDF base <span class="endpoint-tag">POST /api/pdfs/upload</span></div>
    <div class="card-body">
      <label>Arquivo PDF</label>
      <input type="file" id="upload-file" accept=".pdf"/>
      <button class="btn" onclick="uploadPDF()">Enviar PDF</button>
      <div class="result" id="upload-result"></div>
    </div>
  </div>

  <!-- Simular pagamento -->
  <div class="card">
    <div class="card-head">2. Simular pagamento <span class="endpoint-tag">POST /api/test/simular-pagamento</span></div>
    <div class="card-body">
      <label>PDF base</label>
      <select id="sim-pdf">{pdfs_opts}</select>
      <label>Nome do comprador</label>
      <input type="text" id="sim-name" value="Carlos Mendes" placeholder="Nome completo"/>
      <label>E-mail</label>
      <input type="email" id="sim-email" value="carlos@email.com" placeholder="email@exemplo.com"/>
      <label>CPF (opcional)</label>
      <input type="text" id="sim-cpf" placeholder="000.000.000-00"/>
      <button class="btn" onclick="simularPagamento()">Simular pagamento</button>
      <div class="result" id="sim-result"></div>
    </div>
  </div>

  <!-- Gerar PDF protegido manualmente -->
  <div class="card">
    <div class="card-head">3. Gerar PDF protegido <span class="endpoint-tag">POST /api/pdfs/generate</span></div>
    <div class="card-body">
      <label>pdf_id (cole o retornado no passo 1)</label>
      <input type="text" id="gen-pdf-id" placeholder="uuid do pdf"/>
      <label>Nome</label>
      <input type="text" id="gen-name" value="Ana Souza"/>
      <label>E-mail</label>
      <input type="email" id="gen-email" value="ana@email.com"/>
      <label>ID da transação</label>
      <input type="text" id="gen-txn" value="TXN-001"/>
      <button class="btn" onclick="gerarPDF()">Gerar PDF protegido</button>
      <div class="result" id="gen-result"></div>
    </div>
  </div>

  <!-- Detector de vazamento -->
  <div class="card">
    <div class="card-head">4. Detectar vazamento <span class="endpoint-tag">POST /api/pdfs/detect-leak</span></div>
    <div class="card-body">
      <p style="font-size:12px;color:#666;margin-bottom:10px">Faça download de um PDF gerado acima, depois suba ele aqui para verificar se o sistema consegue identificar o comprador.</p>
      <label>PDF suspeito</label>
      <input type="file" id="leak-file" accept=".pdf"/>
      <button class="btn" onclick="detectarVazamento()">Analisar PDF</button>
      <div class="result" id="leak-result"></div>
    </div>
  </div>

  <!-- Vendas -->
  <div class="card full">
    <div class="card-head">
      Vendas registradas
      <button class="btn-sm" onclick="reloadPage()">atualizar</button>
    </div>
    <div class="card-body" style="padding:0">
      <table>
        <thead><tr><th>Comprador</th><th>Hash</th><th>Status</th><th>Download</th></tr></thead>
        <tbody id="sales-tbody">{sales_rows if sales_rows else '<tr><td colspan="4" style="text-align:center;color:#888;padding:16px">Nenhuma venda ainda</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <!-- Logs -->
  <div class="card full">
    <div class="card-head">
      Log de atividade
      <button class="btn-sm" onclick="reloadPage()">atualizar</button>
    </div>
    <div class="card-body">
      {logs_html if logs_html else '<div style="color:#888;font-size:12px">Nenhuma atividade ainda</div>'}
    </div>
  </div>

</div>
</div>

<script>
const BASE = 'http://localhost:8000'

function showResult(id, data, ok) {{
  const el = document.getElementById(id)
  el.className = 'result show ' + (ok ? 'ok' : 'err')
  el.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
}}

async function uploadPDF() {{
  const file = document.getElementById('upload-file').files[0]
  if(!file) {{ showResult('upload-result', 'Selecione um arquivo PDF primeiro.', false); return }}
  const fd = new FormData(); fd.append('file', file)
  try {{
    const r = await fetch(BASE+'/api/pdfs/upload', {{method:'POST',body:fd}})
    const data = await r.json()
    showResult('upload-result', data, r.ok)
    if(r.ok) {{
      document.getElementById('gen-pdf-id').value = data.pdf_id
      const sel = document.getElementById('sim-pdf')
      const opt = document.createElement('option')
      opt.value = data.pdf_id
      opt.textContent = data.filename + ' (' + data.size_kb + ' KB)'
      sel.innerHTML = ''
      sel.appendChild(opt)
      setTimeout(reloadPage, 500)
    }}
  }} catch(e) {{ showResult('upload-result', 'Erro: ' + e.message, false) }}
}}

async function simularPagamento() {{
  const body = {{
    pdf_id: document.getElementById('sim-pdf').value,
    buyer_name: document.getElementById('sim-name').value,
    buyer_email: document.getElementById('sim-email').value,
    buyer_cpf: document.getElementById('sim-cpf').value || null,
  }}
  if(!body.pdf_id) {{ showResult('sim-result','Faça upload de um PDF primeiro.',false); return }}
  try {{
    const r = await fetch(BASE+'/api/test/simular-pagamento', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}})
    const data = await r.json()
    showResult('sim-result', data, r.ok)
    if(r.ok) setTimeout(reloadPage, 500)
  }} catch(e) {{ showResult('sim-result','Erro: '+e.message,false) }}
}}

async function gerarPDF() {{
  const body = {{
    pdf_id: document.getElementById('gen-pdf-id').value,
    buyer_name: document.getElementById('gen-name').value,
    buyer_email: document.getElementById('gen-email').value,
    transaction_id: document.getElementById('gen-txn').value,
  }}
  try {{
    const r = await fetch(BASE+'/api/pdfs/generate', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}})
    const data = await r.json()
    showResult('gen-result', data, r.ok)
    if(r.ok) setTimeout(reloadPage, 500)
  }} catch(e) {{ showResult('gen-result','Erro: '+e.message,false) }}
}}

async function detectarVazamento() {{
  const file = document.getElementById('leak-file').files[0]
  if(!file) {{ showResult('leak-result','Selecione um PDF para analisar.',false); return }}
  const fd = new FormData(); fd.append('file', file)
  try {{
    const r = await fetch(BASE+'/api/pdfs/detect-leak', {{method:'POST',body:fd}})
    const data = await r.json()
    showResult('leak-result', data, r.ok && data.found)
  }} catch(e) {{ showResult('leak-result','Erro: '+e.message,false) }}
}}

function reloadPage() {{ window.location.reload() }}
</script>
</body></html>"""

    def _docs_html(self) -> str:
        return """<!DOCTYPE html><html><head><meta charset=UTF-8><title>PDFShield API Docs</title>
<style>body{font-family:system-ui;max-width:800px;margin:40px auto;padding:0 20px;background:#F5F0E8}
h1{font-size:24px;margin-bottom:8px}h2{font-size:14px;font-weight:600;margin:20px 0 4px}
.ep{background:white;border:1px solid rgba(0,0,0,.1);border-radius:6px;padding:12px 16px;margin-bottom:8px}
.method{font-size:11px;font-weight:700;padding:2px 6px;border-radius:3px;font-family:monospace}
.get{background:#dbeafe;color:#1e40af}.post{background:#dcfce7;color:#166534}
.path{font-family:monospace;font-size:13px;margin-left:8px}
.desc{font-size:12px;color:#666;margin-top:4px}</style></head><body>
<h1>PDFShield API — Local</h1><p style="font-size:13px;color:#666">Servidor rodando em http://localhost:8000</p>
<h2>Endpoints disponíveis</h2>
<div class=ep><span class="method get">GET</span><span class=path>/</span><div class=desc>Painel de testes (abrir no browser)</div></div>
<div class=ep><span class="method get">GET</span><span class=path>/api</span><div class=desc>Health check — status do servidor</div></div>
<div class=ep><span class="method post">POST</span><span class=path>/api/pdfs/upload</span><div class=desc>Upload de PDF base (multipart/form-data, campo: file)</div></div>
<div class=ep><span class="method post">POST</span><span class=path>/api/pdfs/generate</span><div class=desc>Gerar PDF protegido com fingerprint (JSON)</div></div>
<div class=ep><span class="method post">POST</span><span class=path>/api/pdfs/detect-leak</span><div class=desc>Detectar fingerprint em PDF suspeito (multipart)</div></div>
<div class=ep><span class="method get">GET</span><span class=path>/api/downloads/{token}</span><div class=desc>Download do PDF protegido via token</div></div>
<div class=ep><span class="method get">GET</span><span class=path>/api/purchase?token=...</span><div class=desc>Detalhes da compra por token</div></div>
<div class=ep><span class="method get">GET</span><span class=path>/api/sales</span><div class=desc>Listar todas as vendas</div></div>
<div class=ep><span class="method post">POST</span><span class=path>/api/test/simular-pagamento</span><div class=desc>Simular pagamento aprovado (sem Stripe/MP real)</div></div>
<div class=ep><span class="method get">GET</span><span class=path>/api/logs</span><div class=desc>Logs de atividade recente</div></div>
</body></html>"""


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 8000))

    if not ENGINE_OK:
        print()
        print("  ERRO: Motor de PDF não disponível.")
        print("  Execute antes: pip install reportlab pypdf")
        print()
        sys.exit(1)

    server = HTTPServer(("localhost", PORT), Handler)

    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║      PDFShield — Servidor Local          ║")
    print("  ╠══════════════════════════════════════════╣")
    print(f"  ║  Painel de testes:  http://localhost:{PORT}  ║")
    print(f"  ║  Documentação:      http://localhost:{PORT}/docs ║")
    print(f"  ║  Health:            http://localhost:{PORT}/api  ║")
    print("  ╠══════════════════════════════════════════╣")
    print("  ║  CTRL+C para parar                       ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Servidor encerrado.")
