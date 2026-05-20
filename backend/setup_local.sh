#!/bin/bash
# PDFShield — Setup Local Automático
# Roda em Mac e Linux (Ubuntu/Debian)
# Uso: bash setup_local.sh

set -e

GREEN='\033[0;32m'
AMBER='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${AMBER}⚠${NC}  $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║    PDFShield — Setup Local               ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ── 1. Python 3.8+ ────────────────────────────────────────────────────────
echo "  Verificando Python..."
if ! command -v python3 &>/dev/null; then
  fail "Python 3 não encontrado."
  echo "  Instale em: https://python.org/downloads"
  exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Python $PY_VERSION encontrado"

# ── 2. pip ─────────────────────────────────────────────────────────────────
if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
  warn "pip não encontrado. Tentando instalar..."
  python3 -m ensurepip --upgrade 2>/dev/null || true
fi
ok "pip disponível"

# ── 3. Instalar dependências essenciais ────────────────────────────────────
echo ""
echo "  Instalando dependências..."
pip3 install reportlab pypdf --quiet --break-system-packages 2>/dev/null || \
pip3 install reportlab pypdf --quiet 2>/dev/null || \
pip  install reportlab pypdf --quiet 2>/dev/null
ok "reportlab + pypdf instalados"

# ── 4. Instalar FastAPI (opcional, para produção) ─────────────────────────
echo ""
echo "  Instalando FastAPI + uvicorn (para produção)..."
pip3 install fastapi uvicorn python-multipart stripe httpx resend pydantic --quiet \
  --break-system-packages 2>/dev/null || \
pip3 install fastapi uvicorn python-multipart stripe httpx resend pydantic --quiet 2>/dev/null || \
  warn "FastAPI não instalado (ok — server_local.py não precisa)"

# ── 5. Verificar arquivo do servidor ──────────────────────────────────────
echo ""
echo "  Verificando arquivos..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/server_local.py" ]; then
  fail "server_local.py não encontrado em $SCRIPT_DIR"
  exit 1
fi
ok "server_local.py encontrado"

if [ ! -f "$SCRIPT_DIR/app/pdf_engine.py" ]; then
  fail "app/pdf_engine.py não encontrado"
  exit 1
fi
ok "app/pdf_engine.py encontrado"

# ── 6. Teste rápido do motor ───────────────────────────────────────────────
echo ""
echo "  Testando motor de PDF..."
python3 -c "
import sys; sys.path.insert(0, '.')
from app.pdf_engine import BuyerInfo, generate_protected_pdf, extract_fingerprint
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rc
import io
buf = io.BytesIO()
c = rc.Canvas(buf, pagesize=A4)
c.setFont('Helvetica-Bold', 16); c.drawCentredString(297, 741, 'Teste')
c.showPage(); c.save(); buf.seek(0)
buyer = BuyerInfo('Teste','t@t.com','TXN-0')
pdf, h = generate_protected_pdf(buf.read(), buyer)
r = extract_fingerprint(pdf)
assert r['found'] and r['hash'] == h
print('OK')
" 2>&1
ok "Motor de PDF funcionando"

# ── 7. Criar .env se não existir ──────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ]; then
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  warn ".env criado a partir do .env.example — preencha as chaves antes do deploy"
fi

# ── 8. Iniciar servidor ────────────────────────────────────────────────────
echo ""
echo "  ══════════════════════════════════════════"
ok "Tudo pronto! Iniciando o servidor..."
echo "  ══════════════════════════════════════════"
echo ""

cd "$SCRIPT_DIR"
python3 server_local.py
