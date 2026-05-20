"""
PDFShield — API Backend
=======================
Rodar localmente:
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8000
  Swagger: http://localhost:8000/docs

Endpoints:
  POST /api/pdfs/upload          Upload do PDF base
  POST /api/pdfs/generate        Gera PDF protegido manualmente
  GET  /api/downloads/{token}    Download seguro com token
  POST /api/pdfs/detect-leak     Detecta vazamento em PDF suspeito
  POST /api/checkout/stripe      Cria Checkout Session Stripe
  POST /api/checkout/pix         Cria preferência Mercado Pago (PIX)
  POST /api/webhook/stripe       Webhook Stripe (pagamento confirmado)
  POST /api/webhook/mercadopago  Webhook Mercado Pago
  GET  /api/purchase             Detalhes da compra por token
  GET  /api/sales                Lista vendas (admin)
  GET  /api/sales/{txn_id}       Detalhes de uma venda (admin)
"""

import hashlib, hmac, io, json, os, secrets, time, uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.pdf_engine import BuyerInfo, generate_protected_pdf, extract_fingerprint
from app.email_service import send_download_email
from app.payments import (
    stripe_create_checkout, stripe_validate_webhook,
    mp_create_preference, mp_get_payment,
)

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="PDFShield API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000"),
                   os.getenv("BASE_URL", "https://pdfshield.app")],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

BASE_URL = os.getenv("BASE_URL", "https://pdfshield.app")

# ── Stores em memória (substituir por PostgreSQL em produção) ──────────────
# Em produção, cada dict representa uma tabela SQL.
# Ver ARCHITECTURE.md para o schema completo.
_pdfs:    dict[str, dict] = {}   # pdf_id → record
_sales:   dict[str, dict] = {}   # txn_id → record
_tokens:  dict[str, dict] = {}   # token  → record


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_pdf(pdf_id: str) -> dict:
    if pdf_id not in _pdfs:
        raise HTTPException(404, f"PDF '{pdf_id}' não encontrado.")
    return _pdfs[pdf_id]


def _new_token(txn_id: str, hours: int = 48, max_dl: int = 2) -> str:
    token = secrets.token_urlsafe(24)
    _tokens[token] = {
        "txn_id": txn_id,
        "expires": time.time() + hours * 3600,
        "downloads_left": max_dl,
    }
    return token


def _save_sale(txn_id, pdf_id, buyer: BuyerInfo, protected_bytes, unique_hash,
               token, expires_at, max_dl, provider=None, amount=None):
    _sales[txn_id] = {
        "transaction_id":  txn_id,
        "pdf_id":          pdf_id,
        "filename":        _pdfs.get(pdf_id, {}).get("filename", "documento.pdf"),
        "buyer":           {"name": buyer.name, "email": buyer.email, "cpf": buyer.cpf},
        "hash":            unique_hash,
        "short_hash":      buyer.short_hash(),
        "protected_pdf":   protected_bytes,
        "download_token":  token,
        "expires_at":      expires_at,
        "downloads_used":  0,
        "max_downloads":   max_dl,
        "payment_provider": provider,
        "amount_brl":      amount,
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "status":          "active",
    }


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "PDFShield API", "version": "1.0.0", "status": "ok"}


# 1. Upload PDF base ─────────────────────────────────────────────────────────
@app.post("/api/pdfs/upload", summary="Upload do PDF base")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Apenas arquivos .pdf são aceitos.")
    pdf_bytes = await file.read()
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise HTTPException(413, "Arquivo muito grande (máx 50 MB).")
    pdf_id = str(uuid.uuid4())
    _pdfs[pdf_id] = {
        "pdf_id": pdf_id, "filename": file.filename,
        "bytes": pdf_bytes, "size_bytes": len(pdf_bytes),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"pdf_id": pdf_id, "filename": file.filename,
            "size_kb": round(len(pdf_bytes) / 1024, 1)}


# 2. Gerar PDF protegido manualmente ────────────────────────────────────────
class GenerateRequest(BaseModel):
    pdf_id: str
    buyer_name: str
    buyer_email: str
    transaction_id: str
    buyer_cpf: Optional[str] = None
    watermark_opacity: float = 0.18
    expires_hours: int = 48
    max_downloads: int = 2
    send_email: bool = True


@app.post("/api/pdfs/generate", summary="Gera cópia protegida com fingerprint")
async def generate_pdf(req: GenerateRequest):
    pdf_record = _get_pdf(req.pdf_id)
    buyer = BuyerInfo(name=req.buyer_name, email=req.buyer_email,
                      transaction_id=req.transaction_id, cpf=req.buyer_cpf)
    protected_bytes, unique_hash = generate_protected_pdf(
        pdf_record["bytes"], buyer, req.watermark_opacity)
    token = _new_token(req.transaction_id, req.expires_hours, req.max_downloads)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=req.expires_hours)).isoformat()
    _save_sale(req.transaction_id, req.pdf_id, buyer, protected_bytes,
               unique_hash, token, expires_at, req.max_downloads)
    download_url = f"{BASE_URL}/api/downloads/{token}"
    if req.send_email:
        await send_download_email(
            to_email=buyer.email, to_name=buyer.name,
            product_name=pdf_record["filename"].replace(".pdf", ""),
            download_url=download_url,
            short_hash=buyer.short_hash(),
            expires_hours=req.expires_hours,
            max_downloads=req.max_downloads,
        )
    return {"transaction_id": req.transaction_id, "buyer_hash": unique_hash,
            "short_hash": buyer.short_hash(), "download_token": token,
            "download_url": download_url, "expires_at": expires_at}


# 3. Download seguro ─────────────────────────────────────────────────────────
@app.get("/api/downloads/{token}", summary="Download com token temporário")
async def download_pdf(token: str):
    td = _tokens.get(token)
    if not td:
        raise HTTPException(404, "Token inválido.")
    if time.time() > td["expires"]:
        del _tokens[token]
        raise HTTPException(410, "Link expirado.")
    if td["downloads_left"] <= 0:
        raise HTTPException(429, "Limite de downloads atingido.")
    sale = _sales.get(td["txn_id"])
    if not sale:
        raise HTTPException(404, "Venda não encontrada.")
    td["downloads_left"]   -= 1
    sale["downloads_used"] += 1
    filename = sale["filename"].replace(".pdf", f"_{sale['short_hash']}.pdf")
    return Response(
        content=sale["protected_pdf"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "X-Protected-By": "PDFShield", "Cache-Control": "no-store"},
    )


# 4. Detectar vazamento ──────────────────────────────────────────────────────
@app.post("/api/pdfs/detect-leak", summary="Analisa PDF suspeito")
async def detect_leak(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    result = extract_fingerprint(pdf_bytes)
    matched_buyer = None
    if result.get("found") and result.get("hash"):
        extracted = result["hash"]
        for txn_id, sale in _sales.items():
            sh = sale["hash"]
            if sh == extracted or sh.startswith(extracted) or extracted.startswith(sale["short_hash"]):
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
    return {**result, "buyer": matched_buyer}


# 5. Checkout Stripe ─────────────────────────────────────────────────────────
class CheckoutRequest(BaseModel):
    pdf_id: str
    buyer_name: str
    buyer_email: str
    buyer_cpf: Optional[str] = None


@app.post("/api/checkout/stripe")
async def checkout_stripe(req: CheckoutRequest):
    pdf_record = _get_pdf(req.pdf_id)
    # Buscar preço da config (em produção: da tabela products)
    price_cents = int(os.getenv("PRODUCT_PRICE_CENTS", "9700"))
    result = stripe_create_checkout(
        pdf_id=req.pdf_id,
        pdf_name=pdf_record["filename"].replace(".pdf", ""),
        price_brl_cents=price_cents,
        buyer_name=req.buyer_name,
        buyer_email=req.buyer_email,
        buyer_cpf=req.buyer_cpf or "",
    )
    return result


# 6. Checkout PIX (Mercado Pago) ─────────────────────────────────────────────
@app.post("/api/checkout/pix")
async def checkout_pix(req: CheckoutRequest):
    pdf_record = _get_pdf(req.pdf_id)
    price = float(os.getenv("PRODUCT_PRICE_BRL", "97.00"))
    result = await mp_create_preference(
        pdf_id=req.pdf_id,
        pdf_name=pdf_record["filename"].replace(".pdf", ""),
        price_brl=price,
        buyer_name=req.buyer_name,
        buyer_email=req.buyer_email,
        buyer_cpf=req.buyer_cpf or "",
    )
    return result


# 7. Webhook Stripe ──────────────────────────────────────────────────────────
@app.post("/api/webhook/stripe")
async def webhook_stripe(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    payload = await request.body()
    if secret and stripe_signature:
        try:
            event = stripe_validate_webhook(payload, stripe_signature, secret)
        except ValueError as e:
            raise HTTPException(400, str(e))
    else:
        event = json.loads(payload)

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        meta    = session.get("metadata", {})
        pdf_id  = meta.get("pdf_id")
        txn_id  = session.get("id")
        name    = meta.get("buyer_name") or session.get("customer_details", {}).get("name", "")
        email   = session.get("customer_details", {}).get("email", "")
        cpf     = meta.get("buyer_cpf", "")
        amount  = session.get("amount_total", 0) / 100

        if pdf_id and email and pdf_id in _pdfs:
            buyer = BuyerInfo(name=name, email=email, transaction_id=txn_id, cpf=cpf or None)
            protected_bytes, unique_hash = generate_protected_pdf(_pdfs[pdf_id]["bytes"], buyer)
            token = _new_token(txn_id, 48, 2)
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
            _save_sale(txn_id, pdf_id, buyer, protected_bytes, unique_hash,
                       token, expires_at, 2, "stripe", amount)
            download_url = f"{BASE_URL}/api/downloads/{token}"
            await send_download_email(
                to_email=email, to_name=name,
                product_name=_pdfs[pdf_id]["filename"].replace(".pdf", ""),
                download_url=download_url,
                short_hash=buyer.short_hash(),
            )

    return {"received": True}


# 8. Webhook Mercado Pago ────────────────────────────────────────────────────
@app.post("/api/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    body = await request.json()
    topic   = body.get("type") or body.get("topic", "")
    obj_id  = body.get("data", {}).get("id") or body.get("id")

    if topic == "payment" and obj_id:
        try:
            payment = await mp_get_payment(obj_id)
        except Exception:
            return {"received": True}

        if payment.get("status") == "approved":
            meta    = payment.get("metadata", {})
            pdf_id  = meta.get("pdf_id")
            txn_id  = f"MP-{obj_id}"
            name    = meta.get("buyer_name") or payment.get("payer", {}).get("first_name", "")
            email   = payment.get("payer", {}).get("email", "")
            cpf     = meta.get("buyer_cpf", "")
            amount  = payment.get("transaction_amount", 0)

            if pdf_id and email and pdf_id in _pdfs:
                buyer = BuyerInfo(name=name, email=email, transaction_id=txn_id, cpf=cpf or None)
                protected_bytes, unique_hash = generate_protected_pdf(_pdfs[pdf_id]["bytes"], buyer)
                token = _new_token(txn_id, 48, 2)
                expires_at = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
                _save_sale(txn_id, pdf_id, buyer, protected_bytes, unique_hash,
                           token, expires_at, 2, "mercadopago", amount)
                download_url = f"{BASE_URL}/api/downloads/{token}"
                await send_download_email(
                    to_email=email, to_name=name,
                    product_name=_pdfs[pdf_id]["filename"].replace(".pdf", ""),
                    download_url=download_url,
                    short_hash=buyer.short_hash(),
                )

    return {"received": True}


# 9. Detalhes da compra por token (frontend dashboard) ───────────────────────
@app.get("/api/purchase")
def get_purchase(token: str):
    td = _tokens.get(token)
    if not td:
        raise HTTPException(404, "Token inválido.")
    sale = _sales.get(td["txn_id"])
    if not sale:
        raise HTTPException(404, "Venda não encontrada.")
    return {
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
    }


# 10. Admin ──────────────────────────────────────────────────────────────────
@app.get("/api/sales")
def list_sales():
    sales = [{k: v for k, v in s.items() if k != "protected_pdf"}
             for s in _sales.values()]
    return {"total": len(sales), "sales": sales}


@app.get("/api/sales/{txn_id}")
def get_sale(txn_id: str):
    sale = _sales.get(txn_id)
    if not sale:
        raise HTTPException(404, "Venda não encontrada.")
    return {k: v for k, v in sale.items() if k != "protected_pdf"}
