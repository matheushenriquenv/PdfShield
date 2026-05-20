"""
PDFShield — Integração de Pagamentos
Stripe: Checkout Session (Cartão + Boleto)
Mercado Pago: Preferência (PIX + Boleto + Cartão)

Variáveis de ambiente:
  STRIPE_SECRET_KEY=sk_live_...
  STRIPE_WEBHOOK_SECRET=whsec_...
  MP_ACCESS_TOKEN=APP_USR-...
  MP_WEBHOOK_SECRET=...
  BASE_URL=https://pdfshield.app
"""
import hashlib, hmac, os, json, time


BASE_URL = os.getenv("BASE_URL", "https://pdfshield.app")


# ── Stripe ────────────────────────────────────────────────────────────────

def stripe_create_checkout(
    pdf_id: str,
    pdf_name: str,
    price_brl_cents: int,
    buyer_name: str = "",
    buyer_email: str = "",
    buyer_cpf: str = "",
    success_url: str = "",
    cancel_url: str = "",
) -> dict:
    """Cria Checkout Session. Retorna {checkout_url, session_id}."""
    try:
        import stripe
    except ImportError:
        raise RuntimeError("pip install stripe")
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    session = stripe.checkout.Session.create(
        payment_method_types=["card", "boleto"],
        line_items=[{"price_data": {"currency": "brl", "unit_amount": price_brl_cents,
            "product_data": {"name": pdf_name,
                             "description": "Produto digital protegido por PDFShield"}},
            "quantity": 1}],
        mode="payment",
        customer_email=buyer_email or None,
        success_url=success_url or f"{BASE_URL}/minha-conta?token={{CHECKOUT_SESSION_ID}}",
        cancel_url=cancel_url or f"{BASE_URL}/?cancelado=1",
        metadata={"pdf_id": pdf_id, "buyer_name": buyer_name, "buyer_cpf": buyer_cpf},
        billing_address_collection="required",
        locale="pt-BR",
    )
    return {"checkout_url": session.url, "session_id": session.id}


def stripe_validate_webhook(payload: bytes, signature: str, secret: str) -> dict:
    """Valida e parseia evento Stripe sem SDK. Levanta ValueError se inválido."""
    parts = dict(p.split("=", 1) for p in signature.split(",") if "=" in p)
    ts, sig = parts.get("t", ""), parts.get("v1", "")
    signed = f"{ts}.{payload.decode('utf-8')}"
    expected = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Assinatura Stripe inválida.")
    if abs(time.time() - int(ts)) > 300:
        raise ValueError("Timestamp muito antigo.")
    return json.loads(payload)


# ── Mercado Pago ──────────────────────────────────────────────────────────

async def mp_create_preference(
    pdf_id: str,
    pdf_name: str,
    price_brl: float,
    buyer_name: str,
    buyer_email: str,
    buyer_cpf: str = "",
) -> dict:
    """Cria preferência MP. Retorna {init_point, preference_id}."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("pip install httpx")
    access_token = os.getenv("MP_ACCESS_TOKEN", "")
    cpf_clean = buyer_cpf.replace(".", "").replace("-", "") if buyer_cpf else ""
    payload = {
        "items": [{"id": pdf_id, "title": pdf_name,
                   "description": "Produto digital protegido por PDFShield",
                   "category_id": "digital_goods", "quantity": 1,
                   "currency_id": "BRL", "unit_price": price_brl}],
        "payer": {"name": buyer_name, "email": buyer_email,
                  **({"identification": {"type": "CPF", "number": cpf_clean}} if cpf_clean else {})},
        "payment_methods": {"installments": 12},
        "back_urls": {"success": f"{BASE_URL}/minha-conta",
                      "failure": f"{BASE_URL}/?erro=1",
                      "pending": f"{BASE_URL}/?aguardando=1"},
        "auto_return": "approved",
        "metadata": {"pdf_id": pdf_id, "buyer_name": buyer_name, "buyer_cpf": buyer_cpf},
        "notification_url": f"{BASE_URL}/api/webhook/mercadopago",
        "statement_descriptor": "PDFSHIELD",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.mercadopago.com/checkout/preferences",
            headers={"Authorization": f"Bearer {access_token}",
                     "Content-Type": "application/json"},
            json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
    return {"init_point": data["init_point"],
            "sandbox_point": data.get("sandbox_init_point"),
            "preference_id": data["id"]}


async def mp_get_payment(payment_id: str) -> dict:
    """Consulta pagamento na API do Mercado Pago."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("pip install httpx")
    token = os.getenv("MP_ACCESS_TOKEN", "")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://api.mercadopago.com/v1/payments/{payment_id}",
                             headers={"Authorization": f"Bearer {token}"}, timeout=10)
        r.raise_for_status()
        return r.json()


def mp_validate_signature(x_signature: str, x_request_id: str,
                           data_id: str, secret: str) -> bool:
    parts = dict(p.split("=", 1) for p in x_signature.split(",") if "=" in p)
    ts, v1 = parts.get("ts", ""), parts.get("v1", "")
    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)
