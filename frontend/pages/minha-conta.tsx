/**
 * PDFShield — Dashboard do Comprador
 * Acessado após o pagamento: /minha-conta?token=xxx
 * Mostra o PDF comprado, link de download e status de proteção
 */

import { useState, useEffect } from 'react'
import Head from 'next/head'
import { useRouter } from 'next/router'

interface Purchase {
  transaction_id: string
  filename:        string
  buyer_name:      string
  buyer_email:     string
  short_hash:      string
  downloads_used:  number
  max_downloads:   number
  expires_at:      string
  status:          'active' | 'expired' | 'leaked' | 'revoked'
  created_at:      string
  download_url:    string
}

export default function Dashboard() {
  const router    = useRouter()
  const { token } = router.query
  const [purchase, setPurchase] = useState<Purchase | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [copied,   setCopied]   = useState(false)

  useEffect(() => {
    if (!token) return
    fetch(`/api/purchase?token=${token}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => { setPurchase(data); setLoading(false) })
      .catch(() => { setError('Token inválido ou expirado.'); setLoading(false) })
  }, [token])

  const expiresIn = (iso: string) => {
    const diff = new Date(iso).getTime() - Date.now()
    if (diff < 0) return 'Expirado'
    const h = Math.floor(diff / 3600000)
    const m = Math.floor((diff % 3600000) / 60000)
    return h > 0 ? `${h}h ${m}min restantes` : `${m}min restantes`
  }

  const downloadsLeft = purchase
    ? purchase.max_downloads - purchase.downloads_used
    : 0

  return (
    <>
      <Head>
        <title>Minha compra — PDFShield</title>
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </Head>

      <style>{`
        :root {
          --ink:    #0D0D0D;
          --paper:  #F5F0E8;
          --accent: #C8473A;
          --green:  #2D9C6A;
          --muted:  #7A7068;
          --border: rgba(13,13,13,0.12);
          --serif:  'Playfair Display', Georgia, serif;
          --sans:   'DM Sans', system-ui, sans-serif;
          --mono:   'DM Mono', monospace;
        }
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body {
          background: var(--paper);
          color: var(--ink);
          font-family: var(--sans);
          font-weight: 300;
          min-height: 100vh;
        }

        .page-wrap {
          min-height: 100vh;
          display: flex; flex-direction: column;
          align-items: center; justify-content: center;
          padding: 40px 24px;
        }

        /* Header */
        .logo {
          font-family: var(--serif); font-size: 20px; font-weight: 700;
          margin-bottom: 48px; letter-spacing: -0.02em;
        }
        .logo span { color: var(--accent); }

        /* Card principal */
        .card {
          width: 100%; max-width: 560px;
          background: white;
          border: 1px solid var(--border);
        }
        .card-header {
          background: var(--ink);
          padding: 32px 36px;
          position: relative; overflow: hidden;
        }
        .card-header::before {
          content: '';
          position: absolute; bottom: -60px; right: -60px;
          width: 180px; height: 180px; border-radius: 50%;
          background: rgba(200,71,58,0.15);
        }
        .card-header-label {
          font-family: var(--mono); font-size: 10px; font-weight: 500;
          letter-spacing: 0.12em; text-transform: uppercase;
          color: rgba(245,240,232,0.4); margin-bottom: 10px;
        }
        .card-header-title {
          font-family: var(--serif); font-size: 26px; font-weight: 700;
          color: white; line-height: 1.15;
          position: relative; z-index: 1;
        }
        .card-header-sub {
          font-size: 13px; color: rgba(245,240,232,0.4);
          margin-top: 6px;
        }
        .card-body { padding: 32px 36px; }

        /* Hash fingerprint */
        .fingerprint-row {
          background: var(--paper);
          border: 1px solid var(--border);
          padding: 14px 16px;
          display: flex; align-items: center; justify-content: space-between;
          gap: 12px; margin-bottom: 24px;
        }
        .fingerprint-label {
          font-family: var(--mono); font-size: 10px;
          color: var(--muted); letter-spacing: 0.08em;
          text-transform: uppercase; flex-shrink: 0;
        }
        .fingerprint-value {
          font-family: var(--mono); font-size: 12px;
          color: var(--ink); letter-spacing: 0.03em;
          overflow: hidden; text-overflow: ellipsis;
          white-space: nowrap;
        }
        .copy-btn {
          flex-shrink: 0;
          background: none; border: none; cursor: pointer;
          font-family: var(--mono); font-size: 10px;
          color: var(--muted); padding: 4px 8px;
          border: 1px solid var(--border);
          transition: all 0.15s;
        }
        .copy-btn:hover { background: var(--paper); color: var(--ink); }
        .copy-btn.copied { color: var(--green); border-color: var(--green); }

        /* Info rows */
        .info-rows { display: flex; flex-direction: column; gap: 0; }
        .info-row {
          display: flex; justify-content: space-between;
          padding: 12px 0;
          border-bottom: 1px solid var(--border);
          font-size: 13px;
        }
        .info-row:last-child { border-bottom: none; }
        .info-key { color: var(--muted); }
        .info-val { font-weight: 500; text-align: right; }

        /* Download button */
        .download-section { margin-top: 28px; }
        .download-btn {
          width: 100%; padding: 15px;
          background: var(--ink); color: white;
          border: none; cursor: pointer;
          font-family: var(--sans); font-size: 14px; font-weight: 500;
          letter-spacing: 0.02em;
          display: flex; align-items: center; justify-content: center; gap: 10px;
          transition: background 0.2s;
        }
        .download-btn:hover:not(:disabled) { background: var(--accent); }
        .download-btn:disabled {
          opacity: 0.4; cursor: not-allowed;
        }
        .download-meta {
          display: flex; justify-content: space-between;
          margin-top: 10px;
          font-size: 11px; color: var(--muted);
        }

        /* Status badges */
        .badge {
          display: inline-flex; align-items: center; gap: 5px;
          padding: 3px 10px; font-size: 11px; font-weight: 500;
          font-family: var(--mono);
        }
        .badge-active   { background: rgba(45,156,106,0.1);  color: #1A7A4A; }
        .badge-expired  { background: rgba(122,112,104,0.1); color: var(--muted); }
        .badge-leaked   { background: rgba(200,71,58,0.1);   color: var(--accent); }
        .badge-revoked  { background: rgba(200,71,58,0.1);   color: var(--accent); }

        /* Progress bar downloads */
        .dl-bar {
          height: 3px; background: var(--border);
          margin-top: 6px; overflow: hidden;
        }
        .dl-bar-fill {
          height: 100%;
          background: var(--green);
          transition: width 0.5s ease;
        }

        /* Protection note */
        .protection-note {
          margin-top: 24px; padding: 16px;
          border: 1px solid var(--border);
          background: var(--paper);
          font-size: 12px; color: var(--muted);
          line-height: 1.6;
        }
        .protection-note strong { color: var(--ink); font-weight: 500; }

        /* States */
        .loading-state {
          display: flex; flex-direction: column;
          align-items: center; gap: 16px; padding: 60px;
        }
        .spinner {
          width: 36px; height: 36px; border-radius: 50%;
          border: 2px solid var(--border);
          border-top-color: var(--ink);
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .error-state {
          text-align: center; padding: 60px 36px;
        }
        .error-icon { font-size: 36px; margin-bottom: 16px; }
        .error-title {
          font-family: var(--serif); font-size: 22px; font-weight: 700;
          margin-bottom: 8px;
        }
        .error-desc { font-size: 13px; color: var(--muted); }

        /* Success flash */
        .success-banner {
          background: var(--green); color: white;
          padding: 12px 36px;
          font-size: 13px; font-weight: 500;
          display: flex; align-items: center; gap: 8px;
        }

        @media (max-width: 480px) {
          .card-header { padding: 24px; }
          .card-body   { padding: 24px; }
          .fingerprint-value { max-width: 120px; }
        }
      `}</style>

      <div className="page-wrap">
        <div className="logo">PDF<span>Shield</span></div>

        <div className="card">
          {loading ? (
            <div className="loading-state">
              <div className="spinner" />
              <span style={{ fontSize: 13, color: 'var(--muted)' }}>Verificando seu acesso...</span>
            </div>
          ) : error ? (
            <div className="error-state">
              <div className="error-icon">⚠</div>
              <div className="error-title">Link inválido</div>
              <div className="error-desc">{error}</div>
            </div>
          ) : purchase ? (
            <>
              {/* Flash de confirmação (só na primeira visita) */}
              <div className="success-banner">
                ✓ Pagamento confirmado — seu PDF está pronto
              </div>

              <div className="card-header">
                <div className="card-header-label">Seu produto</div>
                <div className="card-header-title">{purchase.filename.replace('.pdf', '')}</div>
                <div className="card-header-sub">Comprado em {new Date(purchase.created_at).toLocaleDateString('pt-BR')}</div>
              </div>

              <div className="card-body">
                {/* Fingerprint */}
                <div className="fingerprint-row">
                  <span className="fingerprint-label">Hash único</span>
                  <span className="fingerprint-value">{purchase.short_hash}…</span>
                  <button
                    className={`copy-btn${copied ? ' copied' : ''}`}
                    onClick={() => {
                      navigator.clipboard.writeText(purchase.short_hash)
                      setCopied(true)
                      setTimeout(() => setCopied(false), 2000)
                    }}
                  >
                    {copied ? '✓ Copiado' : 'Copiar'}
                  </button>
                </div>

                {/* Info */}
                <div className="info-rows">
                  <div className="info-row">
                    <span className="info-key">Comprador</span>
                    <span className="info-val">{purchase.buyer_name}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-key">E-mail registrado</span>
                    <span className="info-val">{purchase.buyer_email}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-key">Transação</span>
                    <span className="info-val" style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>
                      {purchase.transaction_id.slice(0, 20)}…
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-key">Status</span>
                    <span className={`badge badge-${purchase.status}`}>
                      {purchase.status === 'active' ? '● ativo'
                       : purchase.status === 'expired' ? '○ expirado'
                       : purchase.status === 'leaked'  ? '⚠ vazado'
                       : '✕ revogado'}
                    </span>
                  </div>
                </div>

                {/* Download */}
                <div className="download-section">
                  <button
                    className="download-btn"
                    disabled={downloadsLeft <= 0 || purchase.status !== 'active'}
                    onClick={() => {
                      window.location.href = purchase.download_url
                    }}
                  >
                    ↓ Baixar PDF personalizado
                    {downloadsLeft > 0 && ` (${downloadsLeft} restante${downloadsLeft > 1 ? 's' : ''})`}
                  </button>
                  <div className="download-meta">
                    <span>{purchase.downloads_used}/{purchase.max_downloads} downloads usados</span>
                    <span>{expiresIn(purchase.expires_at)}</span>
                  </div>
                  <div className="dl-bar">
                    <div
                      className="dl-bar-fill"
                      style={{ width: `${(purchase.downloads_used / purchase.max_downloads) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Nota de proteção */}
                <div className="protection-note">
                  <strong>Este PDF é único e personalizado para você.</strong>{' '}
                  Ele contém seu nome, e-mail{purchase.buyer_email ? '' : ' e CPF'} em marca d'água visível
                  e uma fingerprint digital invisível em todas as páginas.
                  Compartilhamento não autorizado é rastreável.
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </>
  )
}
