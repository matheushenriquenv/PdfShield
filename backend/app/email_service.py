"""
PDFShield — Serviço de E-mail
Provedores: Resend (padrão) ou SendGrid
Variáveis de ambiente:
  EMAIL_PROVIDER=resend | sendgrid
  RESEND_API_KEY=re_...
  SENDGRID_API_KEY=SG....
  EMAIL_FROM=noreply@seudominio.com
  EMAIL_FROM_NAME=PDFShield
  BASE_URL=https://pdfshield.app
"""
import os

EMAIL_PROVIDER  = os.getenv("EMAIL_PROVIDER",   "resend")
EMAIL_FROM      = os.getenv("EMAIL_FROM",        "noreply@pdfshield.app")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME",   "PDFShield")
RESEND_API_KEY  = os.getenv("RESEND_API_KEY",    "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
BASE_URL        = os.getenv("BASE_URL",          "https://pdfshield.app")


def _html(to_name, product_name, download_url, short_hash, expires_hours, max_dl):
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F5F0E8;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F0E8;padding:48px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#fff;border:1px solid rgba(13,13,13,0.1);">
  <tr><td style="background:#0D0D0D;padding:36px 48px;">
    <p style="margin:0 0 8px;font-family:monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:rgba(245,240,232,0.4);">Entrega imediata</p>
    <h1 style="margin:0;font-family:Georgia,serif;font-size:28px;font-weight:700;color:#F5F0E8;line-height:1.15;">Seu PDF está<br/>pronto para baixar.</h1>
  </td></tr>
  <tr><td style="padding:40px 48px;">
    <p style="margin:0 0 24px;font-family:sans-serif;font-size:15px;color:#0D0D0D;line-height:1.7;">Olá, <strong>{to_name}</strong>!</p>
    <p style="margin:0 0 32px;font-family:sans-serif;font-size:14px;color:#7A7068;line-height:1.75;">
      Seu pagamento foi confirmado. O PDF <strong style="color:#0D0D0D;">{product_name}</strong> foi gerado exclusivamente para você — com seus dados e uma fingerprint única em todas as páginas.
    </p>
    <table cellpadding="0" cellspacing="0" style="margin-bottom:32px;">
      <tr><td style="background:#0D0D0D;">
        <a href="{download_url}" style="display:inline-block;padding:16px 40px;font-family:sans-serif;font-size:14px;font-weight:500;color:#F5F0E8;text-decoration:none;letter-spacing:0.03em;">↓ Baixar meu PDF agora</a>
      </td></tr>
    </table>
    <p style="margin:0 0 8px;font-family:sans-serif;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;color:#7A7068;">Ou copie o link:</p>
    <div style="background:#F5F0E8;border:1px solid rgba(13,13,13,0.12);padding:12px 16px;margin-bottom:32px;word-break:break-all;">
      <a href="{download_url}" style="font-family:monospace;font-size:12px;color:#0D0D0D;text-decoration:none;">{download_url}</a>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid rgba(13,13,13,0.1);margin-bottom:32px;">
      <tr style="border-bottom:1px solid rgba(13,13,13,0.08);"><td style="padding:12px 16px;font-family:sans-serif;font-size:12px;color:#7A7068;">Válido por</td><td style="padding:12px 16px;font-family:sans-serif;font-size:12px;font-weight:500;color:#0D0D0D;text-align:right;">{expires_hours} horas</td></tr>
      <tr style="border-bottom:1px solid rgba(13,13,13,0.08);"><td style="padding:12px 16px;font-family:sans-serif;font-size:12px;color:#7A7068;">Downloads</td><td style="padding:12px 16px;font-family:sans-serif;font-size:12px;font-weight:500;color:#0D0D0D;text-align:right;">{max_dl}×</td></tr>
      <tr><td style="padding:12px 16px;font-family:sans-serif;font-size:12px;color:#7A7068;">Seu ID único</td><td style="padding:12px 16px;font-family:monospace;font-size:11px;color:#0D0D0D;text-align:right;">{short_hash}…</td></tr>
    </table>
    <div style="background:#FFF8F8;border-left:3px solid #C8473A;padding:16px 20px;margin-bottom:32px;">
      <p style="margin:0;font-family:sans-serif;font-size:12px;color:#7A7068;line-height:1.65;">
        <strong style="color:#0D0D0D;">Este PDF é exclusivo seu.</strong> Ele contém seus dados visíveis e uma fingerprint invisível em todas as páginas. Qualquer cópia distribuída pode ser rastreada até você.
      </p>
    </div>
    <p style="margin:0;font-family:sans-serif;font-size:13px;color:#7A7068;">Dúvidas? Responda este e-mail.</p>
  </td></tr>
  <tr><td style="background:#F5F0E8;padding:24px 48px;border-top:1px solid rgba(13,13,13,0.08);">
    <p style="margin:0;font-family:sans-serif;font-size:11px;color:#7A7068;line-height:1.6;">
      PDFShield · Produto digital · <a href="{BASE_URL}" style="color:#7A7068;">{BASE_URL}</a>
    </p>
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""


def _text(to_name, product_name, download_url, short_hash, expires_hours, max_dl):
    return f"""Olá, {to_name}!

Seu pagamento foi confirmado. O PDF "{product_name}" foi gerado exclusivamente para você.

LINK DE DOWNLOAD:
{download_url}

Válido por: {expires_hours} horas | Downloads: {max_dl}x | ID: {short_hash}…

ATENÇÃO: Este PDF contém seus dados e uma fingerprint invisível.
Qualquer cópia distribuída é rastreável até você.

PDFShield · {BASE_URL}"""


async def send_download_email(
    to_email: str,
    to_name: str,
    product_name: str,
    download_url: str,
    short_hash: str,
    expires_hours: int = 48,
    max_downloads: int = 2,
) -> dict:
    """Envia e-mail de entrega com link de download."""
    subject = f"✓ Seu PDF está pronto — {product_name}"
    html = _html(to_name, product_name, download_url, short_hash, expires_hours, max_downloads)
    text = _text(to_name, product_name, download_url, short_hash, expires_hours, max_downloads)

    if EMAIL_PROVIDER == "sendgrid":
        return await _sendgrid(to_email, to_name, subject, html, text)
    return await _resend(to_email, to_name, subject, html, text)


async def _resend(to_email, to_name, subject, html, text):
    try:
        import resend
    except ImportError:
        raise RuntimeError("pip install resend")
    resend.api_key = RESEND_API_KEY
    r = resend.Emails.send({
        "from":    f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
        "to":      [f"{to_name} <{to_email}>"],
        "subject": subject, "html": html, "text": text,
    })
    return {"provider": "resend", "id": r.get("id"), "status": "sent"}


async def _sendgrid(to_email, to_name, subject, html, text):
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, To
    except ImportError:
        raise RuntimeError("pip install sendgrid")
    msg = Mail(from_email=(EMAIL_FROM, EMAIL_FROM_NAME), to_emails=To(to_email, to_name),
               subject=subject, html_content=html, plain_text_content=text)
    r = SendGridAPIClient(SENDGRID_API_KEY).send(msg)
    return {"provider": "sendgrid", "status_code": r.status_code,
            "status": "sent" if r.status_code in (200, 202) else "failed"}
