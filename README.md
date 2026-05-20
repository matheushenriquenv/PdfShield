# PDFShield 🛡

Sistema SaaS completo para venda, proteção e rastreamento de PDFs.
**Stack:** FastAPI + Next.js + PostgreSQL + Docker

---

## Estrutura do projeto

```
pdfshield/
├── backend/
│   ├── app/
│   │   ├── main.py          ← API FastAPI (todos os endpoints)
│   │   ├── pdf_engine.py    ← Motor de fingerprint e marca d'água
│   │   ├── email_service.py ← Resend / SendGrid
│   │   └── payments.py      ← Stripe + Mercado Pago
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example         ← Copiar para .env
├── frontend/
│   ├── pages/
│   │   ├── index.tsx        ← Página de venda
│   │   ├── minha-conta.tsx  ← Dashboard do comprador
│   │   └── api/
│   │       ├── checkout.ts  ← Cria sessão Stripe
│   │       ├── pix.ts       ← Preferência Mercado Pago
│   │       └── purchase.ts  ← Detalhes da compra
│   ├── Dockerfile
│   ├── next.config.js
│   └── .env.example         ← Copiar para .env.local
├── scripts/
│   └── init.sql             ← Schema PostgreSQL (auto-executado)
├── docker-compose.yml       ← Sobe tudo com 1 comando
└── README.md
```

---

## Deploy em 5 minutos

### 1. Clonar e configurar variáveis

```bash
git clone <seu-repo> pdfshield && cd pdfshield

# Backend
cp backend/.env.example backend/.env
# Editar backend/.env com suas chaves

# Frontend
cp frontend/.env.example frontend/.env.local
# Editar frontend/.env.local com suas chaves
```

### 2. Subir tudo com Docker

```bash
docker-compose up -d --build
```

Isso inicia:
- **Backend** → http://localhost:8000 (Swagger: /docs)
- **Frontend** → http://localhost:3000
- **PostgreSQL** → localhost:5432

### 3. Fazer upload do seu PDF

```bash
curl -X POST http://localhost:8000/api/pdfs/upload \
  -F "file=@seu-curso.pdf"
# Retorna: {"pdf_id": "uuid-aqui", ...}
```

Copiar o `pdf_id` e colar no `NEXT_PUBLIC_DEFAULT_PDF_ID` do `.env.local`.

### 4. Configurar webhooks

**Stripe:**
1. Dashboard → Developers → Webhooks
2. Endpoint: `https://seudominio.com/api/webhook/stripe`
3. Eventos: `checkout.session.completed`
4. Copiar signing secret → `STRIPE_WEBHOOK_SECRET`

**Mercado Pago:**
1. Dashboard → Integrações → Notificações IPN
2. URL: `https://seudominio.com/api/webhook/mercadopago`
3. Tópicos: `payment`

### 5. Domínio e HTTPS (Railway ou VPS)

**Railway (mais simples):**
```bash
npm install -g @railway/cli
railway login && railway init
railway add postgresql
railway up
```

**VPS com Nginx + Let's Encrypt:**
```bash
# nginx.conf (simplificado)
server {
    listen 443 ssl;
    server_name seudominio.com;
    location /api { proxy_pass http://localhost:8000; }
    location /     { proxy_pass http://localhost:3000; }
}
```

---

## Fluxo completo de venda

```
1. Comprador acessa pdfshield.app
2. Preenche nome, e-mail, CPF → clica Comprar
3. Redirecionado para Stripe (Cartão/Boleto) ou MP (PIX)
4. Pagamento confirmado → webhook dispara
5. Backend gera PDF com fingerprint única (< 2 segundos)
6. E-mail enviado com link de download temporário (48h / 2 downloads)
7. Comprador clica → recebe PDF personalizado com seus dados
```

## Detectar vazamento

```bash
curl -X POST http://localhost:8000/api/pdfs/detect-leak \
  -F "file=@pdf_suspeito.pdf"
# Retorna: comprador identificado + método de detecção
```

---

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `STRIPE_SECRET_KEY` | Chave secreta do Stripe |
| `STRIPE_WEBHOOK_SECRET` | Signing secret do webhook Stripe |
| `MP_ACCESS_TOKEN` | Access Token do Mercado Pago |
| `RESEND_API_KEY` | API key do Resend (e-mails) |
| `EMAIL_FROM` | Remetente dos e-mails |
| `BASE_URL` | URL pública do site |
| `DATABASE_URL` | Connection string PostgreSQL |

---

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.12 + FastAPI |
| PDF | reportlab + pypdf |
| Frontend | Next.js 14 + TypeScript |
| Banco | PostgreSQL 16 |
| Pagamento | Stripe + Mercado Pago |
| E-mail | Resend ou SendGrid |
| Deploy | Docker + Railway/VPS |
