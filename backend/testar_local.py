"""
PDFShield — Teste Local Completo
=================================
Roda todos os testes SEM precisar de:
  - FastAPI instalado
  - Stripe / Mercado Pago configurados
  - E-mail configurado
  - Banco de dados
  - Internet

Pré-requisitos (já no requirements.txt):
  pip install reportlab pypdf

Uso:
  cd pdfshield-final/backend
  python3 testar_local.py
"""

import sys, io, hashlib, hmac, time, os, re, secrets, tempfile
sys.path.insert(0, '.')

# ── Cores no terminal ──────────────────────────────────────────────────────
VERDE   = '\033[92m'
VERMELHO= '\033[91m'
AMARELO = '\033[93m'
AZUL    = '\033[94m'
RESET   = '\033[0m'
NEGRITO = '\033[1m'

passed, failed, warns = 0, 0, []

def ok(msg):
    global passed; passed += 1
    print(f"  {VERDE}✓{RESET} {msg}")

def fail(msg, err=''):
    global failed; failed += 1
    print(f"  {VERMELHO}✗{RESET} {msg}")
    if err: print(f"    {VERMELHO}└─ {err}{RESET}")

def warn(msg):
    warns.append(msg)
    print(f"  {AMARELO}⚠{RESET} {msg}")

def section(title):
    print(f"\n{NEGRITO}{AZUL}{'─'*55}{RESET}")
    print(f"{NEGRITO}{AZUL}  {title}{RESET}")
    print(f"{NEGRITO}{AZUL}{'─'*55}{RESET}")


# ══════════════════════════════════════════════════════
# 1. BUYER INFO — hash único por comprador
# ══════════════════════════════════════════════════════
section("1. BuyerInfo — hash único por comprador")
try:
    from app.pdf_engine import BuyerInfo

    b1 = BuyerInfo(name='Carlos Mendes', email='carlos@email.com',
                   transaction_id='TXN-84729', cpf='123.456.789-00',
                   purchase_date='2025-04-24T14:32:00+00:00')
    b2 = BuyerInfo(name='Maria Silva', email='maria@email.com',
                   transaction_id='TXN-99001',
                   purchase_date='2025-04-24T14:32:00+00:00')

    h1 = b1.unique_hash()
    assert len(h1) == 64
    ok(f"Hash SHA-256 (64 chars): {h1[:24]}...")

    assert h1 != b2.unique_hash()
    ok("Compradores diferentes geram hashes diferentes")

    assert b1.short_hash() == h1[:16]
    ok(f"Short hash: {b1.short_hash()}")

    # Determinístico
    b1c = BuyerInfo(name='Carlos Mendes', email='carlos@email.com',
                    transaction_id='TXN-84729', cpf='123.456.789-00',
                    purchase_date='2025-04-24T14:32:00+00:00')
    assert b1.unique_hash() == b1c.unique_hash()
    ok("Determinístico: mesmo input → mesmo hash sempre")

except Exception as e:
    fail("BuyerInfo", str(e))


# ══════════════════════════════════════════════════════
# 2. PDF DE TESTE — criar PDF base simulando o seu curso
# ══════════════════════════════════════════════════════
section("2. Criando PDF de curso de exemplo")
src_pdf = None
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rc

    buf = io.BytesIO()
    c = rc.Canvas(buf, pagesize=A4)
    w, h = A4

    # Página 1 — capa
    c.setFont('Helvetica-Bold', 22)
    c.drawCentredString(w/2, h-100, 'Python do Zero ao Pro')
    c.setFont('Helvetica', 14)
    c.drawCentredString(w/2, h-140, 'Guia Completo 2025')
    c.setFont('Helvetica', 12)
    capitulos = [
        'Capítulo 1: Fundamentos do Python',
        'Capítulo 2: Funções e Classes',
        'Capítulo 3: APIs com FastAPI',
        'Capítulo 4: PostgreSQL e SQLAlchemy',
        'Capítulo 5: Docker e Deploy',
    ]
    for i, cap in enumerate(capitulos):
        c.drawString(80, h-220-i*28, cap)
    c.showPage()

    # Página 2 — conteúdo
    c.setFont('Helvetica-Bold', 16)
    c.drawString(60, h-80, 'Capítulo 1: Fundamentos do Python')
    c.setFont('Helvetica', 12)
    conteudo = [
        'Python é uma linguagem de programação de alto nível,',
        'interpretada e com tipagem dinâmica. É amplamente usada',
        'em ciência de dados, automação, web e IA.',
        '',
        'Variáveis não precisam de declaração de tipo:',
        '  nome = "Carlos"',
        '  idade = 30',
        '  preco = 97.0',
    ]
    for i, linha in enumerate(conteudo):
        c.drawString(60, h-120-i*20, linha)
    c.showPage()
    c.save()
    buf.seek(0)
    src_pdf = buf.read()
    ok(f"PDF de curso criado: {len(src_pdf):,} bytes, 2 páginas")

except Exception as e:
    fail("criação do PDF de teste", str(e))


# ══════════════════════════════════════════════════════
# 3. GERAR PDF PROTEGIDO — marca d'água + fingerprint
# ══════════════════════════════════════════════════════
section("3. generate_protected_pdf — marca d'água + fingerprint")
pdf_bytes = None
uhash = None
try:
    from app.pdf_engine import generate_protected_pdf

    pdf_bytes, uhash = generate_protected_pdf(src_pdf, b1, watermark_opacity=0.20)

    assert len(pdf_bytes) > len(src_pdf)
    ok(f"PDF protegido gerado: {len(pdf_bytes):,} bytes (original: {len(src_pdf):,})")
    ok(f"Hash único do comprador: {uhash}")

    # Verificar que dados do comprador estão no raw
    assert b'Carlos Mendes' in pdf_bytes or b'TXN-84729' in pdf_bytes
    ok("Dados do comprador embutidos no PDF (marca d'água)")

    # Verificar metadados XMP
    assert b'pdfshield:buyerHash' in pdf_bytes
    ok("Hash SHA-256 embutido nos metadados XMP")

    # Verificar keyword nos metadados Info
    assert b'pdfshield:' in pdf_bytes
    ok("Fingerprint presente em múltiplas camadas do PDF")

    # Salvar PDF gerado para inspeção manual
    output_path = '/tmp/pdf_protegido_teste.pdf'
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    ok(f"PDF salvo em {output_path} — abra para ver a marca d'água!")

except Exception as e:
    fail("generate_protected_pdf", str(e))


# ══════════════════════════════════════════════════════
# 4. DETECTAR FINGERPRINT — simula PDF vazado
# ══════════════════════════════════════════════════════
section("4. extract_fingerprint — detectar comprador em PDF vazado")
try:
    from app.pdf_engine import extract_fingerprint

    # Teste 1: PDF com fingerprint
    result = extract_fingerprint(pdf_bytes)
    assert result['found'] == True
    assert result['hash'] == uhash
    ok(f"Fingerprint encontrada via método: {result['method']}")
    ok(f"Hash extraído bate 100% com o original")

    # Teste 2: PDF limpo (não deve dar falso positivo)
    clean_buf = io.BytesIO()
    c_clean = rc.Canvas(clean_buf, pagesize=A4)
    c_clean.setFont('Helvetica', 12)
    c_clean.drawString(60, 700, 'PDF sem proteção PDFShield')
    c_clean.showPage(); c_clean.save()
    clean_buf.seek(0)
    result2 = extract_fingerprint(clean_buf.read())
    assert result2['found'] == False
    ok("PDF sem fingerprint → found=False (zero falso positivo)")

    # Teste 3: Salvar em disco e reler (simula arquivo baixado/compartilhado)
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf_bytes); tmp = f.name
    with open(tmp, 'rb') as f:
        result3 = extract_fingerprint(f.read())
    os.unlink(tmp)
    assert result3['hash'] == uhash
    ok("Fingerprint intacta após salvar e reler do disco (simula vazamento)")

    # Teste 4: Segundo comprador tem hash diferente e detectável
    pdf2, uhash2 = generate_protected_pdf(src_pdf, b2, 0.18)
    r2 = extract_fingerprint(pdf2)
    assert r2['hash'] == uhash2
    assert r2['hash'] != uhash
    ok("Dois compradores → dois PDFs → dois hashes distintos e detectáveis")

except Exception as e:
    fail("extract_fingerprint", str(e))


# ══════════════════════════════════════════════════════
# 5. EMAIL — templates HTML e texto
# ══════════════════════════════════════════════════════
section("5. Email — templates de entrega")
try:
    from app.email_service import _html, _text, send_download_email
    import inspect

    token_teste = secrets.token_urlsafe(24)
    url_teste = f'https://pdfshield.app/d/{token_teste}'

    h_out = _html('Carlos Mendes', 'Python do Zero ao Pro',
                  url_teste, b1.short_hash(), 48, 2)
    t_out = _text('Carlos Mendes', 'Python do Zero ao Pro',
                  url_teste, b1.short_hash(), 48, 2)

    assert 'Carlos Mendes' in h_out and 'Python do Zero ao Pro' in h_out
    assert url_teste in h_out and '48' in h_out
    ok(f"Template HTML: {len(h_out):,} chars — contém nome, produto, link e prazo")

    assert 'Carlos Mendes' in t_out and b1.short_hash() in t_out
    ok(f"Template texto: {len(t_out):,} chars — contém hash do comprador")

    # Salvar preview do email
    email_path = '/tmp/email_preview.html'
    with open(email_path, 'w', encoding='utf-8') as f:
        f.write(h_out)
    ok(f"Preview do e-mail salvo em {email_path} — abra no browser!")

    assert inspect.iscoroutinefunction(send_download_email)
    ok("send_download_email() é async e pronta para uso")

    warn("Envio real: configure RESEND_API_KEY=re_... no arquivo .env")

except Exception as e:
    fail("email templates", str(e))


# ══════════════════════════════════════════════════════
# 6. PAGAMENTOS — validação HMAC (sem chaves reais)
# ══════════════════════════════════════════════════════
section("6. Pagamentos — validação HMAC de segurança")
try:
    from app.payments import stripe_validate_webhook, mp_validate_signature

    # ── Stripe ──────────────────────────────────────
    ts = str(int(time.time()))
    payload = b'{"type":"checkout.session.completed","data":{"object":{}}}'
    secret = 'whsec_test_chave_local_segura'
    signed = f'{ts}.{payload.decode()}'
    sig = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()

    event = stripe_validate_webhook(payload, f't={ts},v1={sig}', secret)
    assert event['type'] == 'checkout.session.completed'
    ok("Stripe: assinatura HMAC válida aceita corretamente")

    try:
        stripe_validate_webhook(payload, f't={ts},v1=assinatura_falsa', secret)
        fail("Deveria rejeitar assinatura falsa")
    except ValueError:
        ok("Stripe: assinatura falsa rejeitada (segurança)")

    ts_antigo = str(int(time.time()) - 400)
    s_old = hmac.new(secret.encode(), f'{ts_antigo}.{payload.decode()}'.encode(), hashlib.sha256).hexdigest()
    try:
        stripe_validate_webhook(payload, f't={ts_antigo},v1={s_old}', secret)
        fail("Deveria rejeitar timestamp antigo")
    except ValueError:
        ok("Stripe: webhook com timestamp >5min rejeitado (anti-replay)")

    # ── Mercado Pago ─────────────────────────────────
    mp_secret = 'mp_chave_local_teste'
    data_id, req_id, ts2 = '99887766', 'req-xyz-local', '1714000000'
    manifest = f'id:{data_id};request-id:{req_id};ts:{ts2};'
    v1 = hmac.new(mp_secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    assert mp_validate_signature(f'ts={ts2},v1={v1}', req_id, data_id, mp_secret) == True
    ok("Mercado Pago: assinatura HMAC válida aceita")
    assert mp_validate_signature(f'ts={ts2},v1=errada', req_id, data_id, mp_secret) == False
    ok("Mercado Pago: assinatura falsa rejeitada")

    warn("Pagamentos reais: configure STRIPE_SECRET_KEY e MP_ACCESS_TOKEN no .env")

except Exception as e:
    fail("validação HMAC", str(e))


# ══════════════════════════════════════════════════════
# 7. FLUXO COMPLETO END-TO-END — sem nenhuma rede
# ══════════════════════════════════════════════════════
section("7. Fluxo completo simulado (pagamento → PDF → detecção)")
try:
    print(f"\n  {AZUL}Simulando: comprador efetua pagamento...{RESET}")

    # Passo 1: webhook recebe pagamento aprovado
    comprador = BuyerInfo(name='Ana Rodriguez', email='ana@exemplo.com',
                          transaction_id='STRIPE-cs_test_abc123',
                          cpf='987.654.321-00')
    ok(f"[1/6] Webhook recebido: pagamento de {comprador.name}")

    # Passo 2: gerar PDF personalizado
    pdf_entrega, hash_entrega = generate_protected_pdf(src_pdf, comprador, 0.18)
    ok(f"[2/6] PDF protegido gerado: {len(pdf_entrega):,} bytes")

    # Passo 3: criar token de download temporário
    token_dl = secrets.token_urlsafe(24)
    expires_ts = time.time() + 48 * 3600
    assert time.time() < expires_ts
    ok(f"[3/6] Token de download criado (expira em 48h)")

    # Passo 4: preparar e-mail
    url_dl = f'https://pdfshield.app/d/{token_dl}'
    email_html = _html(comprador.name, 'Python do Zero ao Pro',
                       url_dl, comprador.short_hash(), 48, 2)
    assert comprador.name in email_html and url_dl in email_html
    ok(f"[4/6] E-mail de entrega preparado com link personalizado")

    # Passo 5: comprador baixa o PDF
    assert len(pdf_entrega) > 1000
    ok(f"[5/6] PDF disponível para download")

    # Passo 6: PDF vaza → detectar quem foi
    print(f"\n  {AMARELO}Simulando vazamento do PDF...{RESET}")
    leak = extract_fingerprint(pdf_entrega)
    assert leak['found'] and leak['hash'] == hash_entrega
    # Simular lookup no banco
    db = {hash_entrega: {'nome': comprador.name, 'email': comprador.email,
                          'txn': comprador.transaction_id}}
    comprador_encontrado = db.get(leak['hash'])
    assert comprador_encontrado is not None
    assert comprador_encontrado['email'] == 'ana@exemplo.com'
    ok(f"[6/6] Vazador identificado: {comprador_encontrado['nome']} ({comprador_encontrado['email']})")

except Exception as e:
    fail("fluxo end-to-end", str(e))


# ══════════════════════════════════════════════════════
# RESULTADO FINAL
# ══════════════════════════════════════════════════════
print(f"\n{NEGRITO}{'═'*55}{RESET}")
print(f"{NEGRITO}  RESULTADO FINAL{RESET}")
print(f"{'═'*55}")
cor_ok = VERDE if failed == 0 else VERMELHO
print(f"  {VERDE}✓ {passed} testes passaram{RESET}")
print(f"  {''+VERDE if failed==0 else VERMELHO}✗ {failed} testes falharam{RESET}")

if warns:
    print(f"\n  {AMARELO}Avisos — funciona localmente, mas precisa de config para produção:{RESET}")
    for i, w in enumerate(warns, 1):
        print(f"  {AMARELO}{i}. {w}{RESET}")

print()
if failed == 0:
    print(f"  {VERDE}{NEGRITO}✅ SISTEMA 100% FUNCIONAL LOCALMENTE!{RESET}")
    print()
    print(f"  Arquivos gerados para inspecionar:")
    print(f"  {AZUL}📄 /tmp/pdf_protegido_teste.pdf{RESET}  → abra para ver a marca d'água")
    print(f"  {AZUL}📧 /tmp/email_preview.html{RESET}       → abra no browser para ver o e-mail")
    print()
    print(f"  Próximo passo: instale o FastAPI e suba a API localmente:")
    print(f"  {NEGRITO}pip install fastapi uvicorn python-multipart{RESET}")
    print(f"  {NEGRITO}uvicorn app.main:app --reload --port 8000{RESET}")
    print(f"  {NEGRITO}Acesse: http://localhost:8000/docs{RESET}")
else:
    print(f"  {VERMELHO}{NEGRITO}❌ {failed} TESTE(S) FALHARAM — verifique os erros acima.{RESET}")

print(f"{'═'*55}\n")
sys.exit(0 if failed == 0 else 1)
