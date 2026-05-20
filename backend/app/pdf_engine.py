"""
PDFShield — Motor de Fingerprint & Marca d'Água
Dependências: reportlab, pypdf
"""
import hashlib, io, re
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DecodedStreamObject


@dataclass
class BuyerInfo:
    name: str
    email: str
    transaction_id: str
    cpf: Optional[str] = None
    purchase_date: Optional[str] = None

    def __post_init__(self):
        if not self.purchase_date:
            self.purchase_date = datetime.now(timezone.utc).isoformat()

    def unique_hash(self) -> str:
        payload = f"{self.email}|{self.transaction_id}|{self.purchase_date}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def short_hash(self) -> str:
        return self.unique_hash()[:16]


# ── Marca d'água visível ──────────────────────────────────────────────────

def _watermark_overlay(w: float, h: float, buyer: BuyerInfo, opacity: float) -> bytes:
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(w, h))

    # Diagonal central
    c.saveState()
    c.setFillColor(colors.red)
    c.setFillAlpha(opacity)
    c.setFont("Helvetica-Bold", 13)
    c.translate(w / 2, h / 2)
    c.rotate(35)
    lines = [
        f"USO EXCLUSIVO DE {buyer.name.upper()}",
        f"{buyer.email}",
        f"TRANSAÇÃO: {buyer.transaction_id}  •  {buyer.short_hash()}",
        "PROIBIDA A DISTRIBUIÇÃO",
    ]
    lh = 18
    sy = (len(lines) - 1) * lh / 2
    for i, line in enumerate(lines):
        c.drawCentredString(0, sy - i * lh, line)
    c.restoreState()

    # Rodapé
    c.saveState()
    c.setFillColor(colors.darkgrey)
    c.setFillAlpha(0.45)
    c.setFont("Helvetica", 7)
    footer = (
        f"Documento protegido · {buyer.name} · {buyer.email}"
        + (f" · CPF: {buyer.cpf}" if buyer.cpf else "")
        + f" · {buyer.purchase_date[:10]} · ID: {buyer.short_hash()}"
    )
    c.drawCentredString(w / 2, 8 * mm, footer)
    c.restoreState()

    c.save()
    buf.seek(0)
    return buf.read()


# ── Fingerprint invisível: caracteres ZWC ────────────────────────────────

_ZW = {"0": "\u200B", "1": "\u2060", "S": "\uFEFF"}

def _hash_to_zwc(hex_hash: str, bits: int = 64) -> str:
    binary = bin(int(hex_hash[:bits // 4], 16))[2:].zfill(bits)
    groups = [binary[i:i+8] for i in range(0, bits, 8)]
    return "".join("".join(_ZW[b] for b in g) + _ZW["S"] for g in groups)


# ── XMP metadata com hash ──────────────────────────────────────────────────

def _xmp_block(buyer: BuyerInfo) -> bytes:
    h = buyer.unique_hash()
    now = datetime.now(timezone.utc).isoformat()
    return f"""<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
    <rdf:Description rdf:about=''
      xmlns:pdfshield='https://pdfshield.app/ns/1.0/'>
      <pdfshield:buyerEmail>{buyer.email}</pdfshield:buyerEmail>
      <pdfshield:transactionId>{buyer.transaction_id}</pdfshield:transactionId>
      <pdfshield:buyerHash>{h}</pdfshield:buyerHash>
      <pdfshield:fingerprint>{buyer.short_hash()}</pdfshield:fingerprint>
      <pdfshield:protectedAt>{now}</pdfshield:protectedAt>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>""".encode("utf-8")


# ── Gerar PDF protegido ────────────────────────────────────────────────────

def generate_protected_pdf(
    source_pdf_bytes: bytes,
    buyer: BuyerInfo,
    watermark_opacity: float = 0.18,
) -> tuple[bytes, str]:
    """Retorna (pdf_bytes, unique_hash)."""
    unique_hash = buyer.unique_hash()
    reader = PdfReader(io.BytesIO(source_pdf_bytes))
    writer = PdfWriter()

    for page in reader.pages:
        pw = float(page.mediabox.width)
        ph = float(page.mediabox.height)
        wm_bytes = _watermark_overlay(pw, ph, buyer, watermark_opacity)
        wm_page = PdfReader(io.BytesIO(wm_bytes)).pages[0]
        page.merge_page(wm_page)
        writer.add_page(page)

    # Metadados Info
    writer.add_metadata({
        "/Author":   buyer.name,
        "/Subject":  f"Protected · {buyer.transaction_id}",
        "/Keywords": f"pdfshield:{unique_hash}",
        "/Creator":  "PDFShield v1.0",
        "/Producer": f"pdfshield:{buyer.short_hash()}",
    })

    # XMP
    xmp_obj = DecodedStreamObject()
    xmp_obj.set_data(_xmp_block(buyer))
    xmp_obj.update({
        NameObject("/Type"):    NameObject("/Metadata"),
        NameObject("/Subtype"): NameObject("/XML"),
    })
    xmp_ref = writer._add_object(xmp_obj)
    writer._root_object[NameObject("/Metadata")] = xmp_ref

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue(), unique_hash


# ── Detectar fingerprint em PDF vazado ────────────────────────────────────

def extract_fingerprint(pdf_bytes: bytes) -> dict:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    meta = {k: str(v) for k, v in (reader.metadata or {}).items()}

    # Estratégia 1: /Keywords
    m = re.search(r"pdfshield:([0-9a-f]{64})", meta.get("/Keywords", ""), re.I)
    if m:
        return {"found": True, "method": "metadata_keywords",
                "hash": m.group(1), "meta": meta}

    # Estratégia 2: XMP raw bytes
    m = re.search(rb"pdfshield:buyerHash>([0-9a-f]{64})<", pdf_bytes, re.I)
    if m:
        return {"found": True, "method": "xmp_metadata",
                "hash": m.group(1).decode(), "meta": meta}

    # Estratégia 3: fingerprint curto
    m = re.search(rb"pdfshield:fingerprint>([0-9a-f]{16})<", pdf_bytes, re.I)
    if m:
        return {"found": True, "method": "xmp_fingerprint",
                "hash": m.group(1).decode(), "meta": meta}

    # Estratégia 4: ZWC
    zwc_chars = set(_ZW.values())
    total = sum(
        sum(1 for ch in (p.extract_text() or "") if ch in zwc_chars)
        for p in reader.pages
    )
    if total > 10:
        return {"found": True, "method": "zwc_pattern",
                "hash": None, "zwc_bits": total, "meta": meta}

    return {"found": False, "method": "none", "meta": meta}
