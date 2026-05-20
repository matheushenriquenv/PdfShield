/**
 * PDFShield — Página de Venda
 * Design: editorial escuro, tipografia expressiva, micro-animações
 *
 * Instalar dependências:
 *   npx create-next-app@latest pdfshield-frontend --typescript --tailwind --app
 *   npm install @stripe/stripe-js framer-motion lucide-react
 */

import { useState, useEffect, useRef } from 'react'
import Head from 'next/head'
import { loadStripe } from '@stripe/stripe-js'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!)

// ── Tipos ──────────────────────────────────────────────────────────────────
interface Product {
  id: string
  name: string
  description: string
  price: number        // em centavos BRL
  pages: number
  topics: string[]
}

// ── Produto exemplo (em produção: buscar da API) ───────────────────────────
const PRODUCT: Product = {
  id:          'pdf-python-pro',
  name:        'Python do Zero ao Pro',
  description: 'O guia definitivo para dominar Python com projetos reais, APIs e automações. Mais de 300 páginas de conteúdo prático.',
  price:       9700,    // R$ 97,00
  pages:       312,
  topics: [
    'Fundamentos e estruturas de dados',
    'Funções, classes e POO',
    'APIs REST com FastAPI',
    'Web scraping e automação',
    'Banco de dados com PostgreSQL',
    'Deploy e boas práticas',
  ],
}

// ── Componente Principal ───────────────────────────────────────────────────
export default function SalePage() {
  const [step, setStep]         = useState<'landing' | 'checkout'>('landing')
  const [loading, setLoading]   = useState(false)
  const [scrollY, setScrollY]   = useState(0)
  const heroRef                 = useRef<HTMLDivElement>(null)

  // Parallax scroll
  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Reveal on scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => entries.forEach(e => {
        if (e.isIntersecting) e.target.classList.add('revealed')
      }),
      { threshold: 0.15 }
    )
    document.querySelectorAll('.reveal').forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  if (step === 'checkout') {
    return <CheckoutPage product={PRODUCT} onBack={() => setStep('landing')} />
  }

  return (
    <>
      <Head>
        <title>{PRODUCT.name} — PDFShield</title>
        <meta name="description" content={PRODUCT.description} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </Head>

      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
          --ink:       #0D0D0D;
          --paper:     #F5F0E8;
          --accent:    #C8473A;
          --accent2:   #1A3A5C;
          --muted:     #7A7068;
          --border:    rgba(13,13,13,0.12);
          --serif:     'Playfair Display', Georgia, serif;
          --sans:      'DM Sans', system-ui, sans-serif;
          --mono:      'DM Mono', monospace;
        }
        html { scroll-behavior: smooth; }
        body {
          background: var(--paper);
          color: var(--ink);
          font-family: var(--sans);
          font-weight: 300;
          line-height: 1.7;
          overflow-x: hidden;
        }

        /* Reveal animation */
        .reveal {
          opacity: 0;
          transform: translateY(32px);
          transition: opacity 0.7s ease, transform 0.7s ease;
        }
        .reveal.revealed { opacity: 1; transform: translateY(0); }
        .reveal-delay-1 { transition-delay: 0.1s; }
        .reveal-delay-2 { transition-delay: 0.2s; }
        .reveal-delay-3 { transition-delay: 0.3s; }
        .reveal-delay-4 { transition-delay: 0.4s; }

        /* Noise texture overlay */
        body::before {
          content: '';
          position: fixed; inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
          pointer-events: none; z-index: 9999; opacity: 0.4;
        }

        /* Navbar */
        .nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
          padding: 20px 40px;
          display: flex; align-items: center; justify-content: space-between;
          border-bottom: 1px solid transparent;
          transition: border-color 0.3s, background 0.3s, backdrop-filter 0.3s;
        }
        .nav.scrolled {
          border-color: var(--border);
          background: rgba(245,240,232,0.85);
          backdrop-filter: blur(12px);
        }
        .nav-logo {
          font-family: var(--serif);
          font-size: 18px;
          font-weight: 700;
          letter-spacing: -0.02em;
          color: var(--ink);
          text-decoration: none;
        }
        .nav-logo span { color: var(--accent); }
        .nav-cta {
          padding: 9px 22px;
          background: var(--ink);
          color: var(--paper);
          border: none; cursor: pointer;
          font-family: var(--sans); font-size: 13px; font-weight: 500;
          letter-spacing: 0.03em;
          transition: background 0.2s, transform 0.15s;
        }
        .nav-cta:hover { background: var(--accent); transform: translateY(-1px); }

        /* Hero */
        .hero {
          min-height: 100vh;
          display: grid;
          grid-template-columns: 1fr 1fr;
          align-items: center;
          padding: 120px 80px 80px;
          gap: 80px;
          position: relative;
          overflow: hidden;
        }
        .hero::after {
          content: '';
          position: absolute; right: -120px; top: -120px;
          width: 600px; height: 600px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(200,71,58,0.08) 0%, transparent 70%);
          pointer-events: none;
        }
        .hero-tag {
          display: inline-flex; align-items: center; gap: 8px;
          font-family: var(--mono); font-size: 11px; font-weight: 500;
          letter-spacing: 0.12em; text-transform: uppercase;
          color: var(--accent);
          border: 1px solid rgba(200,71,58,0.3);
          padding: 5px 12px; margin-bottom: 24px;
        }
        .hero-tag::before {
          content: '';
          width: 6px; height: 6px; border-radius: 50%;
          background: var(--accent);
          animation: pulse 2s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.7); }
        }
        .hero-title {
          font-family: var(--serif);
          font-size: clamp(42px, 5vw, 72px);
          font-weight: 900;
          line-height: 1.05;
          letter-spacing: -0.03em;
          color: var(--ink);
          margin-bottom: 24px;
        }
        .hero-title em {
          font-style: italic;
          color: var(--accent);
        }
        .hero-subtitle {
          font-size: 16px;
          color: var(--muted);
          line-height: 1.75;
          max-width: 420px;
          margin-bottom: 40px;
        }
        .hero-actions { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
        .btn-primary {
          padding: 16px 36px;
          background: var(--ink);
          color: var(--paper);
          border: none; cursor: pointer;
          font-family: var(--sans); font-size: 14px; font-weight: 500;
          letter-spacing: 0.02em;
          transition: all 0.2s;
          position: relative; overflow: hidden;
        }
        .btn-primary::after {
          content: '';
          position: absolute; inset: 0;
          background: var(--accent);
          transform: translateX(-100%);
          transition: transform 0.3s ease;
        }
        .btn-primary:hover::after { transform: translateX(0); }
        .btn-primary span { position: relative; z-index: 1; }
        .btn-secondary {
          font-size: 13px; color: var(--muted);
          background: none; border: none; cursor: pointer;
          text-decoration: underline; text-underline-offset: 3px;
          font-family: var(--sans);
          transition: color 0.2s;
        }
        .btn-secondary:hover { color: var(--ink); }

        /* PDF mockup */
        .hero-visual {
          position: relative;
          display: flex; justify-content: center; align-items: center;
        }
        .pdf-mockup {
          width: 300px;
          background: white;
          box-shadow: 0 40px 80px rgba(13,13,13,0.18), 0 8px 20px rgba(13,13,13,0.08);
          position: relative;
          transform: rotate(-2deg);
          transition: transform 0.4s ease;
        }
        .pdf-mockup:hover { transform: rotate(0deg) scale(1.02); }
        .pdf-cover {
          background: var(--accent2);
          padding: 40px 32px;
          color: white;
        }
        .pdf-cover-label {
          font-family: var(--mono); font-size: 10px; font-weight: 500;
          letter-spacing: 0.15em; text-transform: uppercase;
          opacity: 0.5; margin-bottom: 20px;
        }
        .pdf-cover-title {
          font-family: var(--serif); font-size: 22px; font-weight: 700;
          line-height: 1.2; margin-bottom: 8px;
        }
        .pdf-cover-sub { font-size: 12px; opacity: 0.6; }
        .pdf-body { padding: 20px 24px; }
        .pdf-line {
          height: 8px; border-radius: 2px;
          background: #F0EDE8; margin-bottom: 8px;
        }
        .pdf-wm {
          position: absolute; inset: 0; display: flex;
          align-items: center; justify-content: center;
          pointer-events: none;
        }
        .pdf-wm-text {
          font-family: var(--mono); font-size: 9px; font-weight: 500;
          color: rgba(200,71,58,0.25);
          transform: rotate(-35deg);
          white-space: nowrap; letter-spacing: 0.05em;
          line-height: 1.8;
          text-align: center;
        }
        .pdf-badge {
          position: absolute; top: -12px; right: -12px;
          background: var(--accent);
          color: white;
          width: 64px; height: 64px; border-radius: 50%;
          display: flex; flex-direction: column;
          align-items: center; justify-content: center;
          font-family: var(--serif); font-weight: 700;
          box-shadow: 0 4px 16px rgba(200,71,58,0.35);
          animation: float 3s ease-in-out infinite;
        }
        .pdf-badge .price { font-size: 20px; line-height: 1; }
        .pdf-badge .label { font-size: 9px; opacity: 0.8; }
        @keyframes float {
          0%,100% { transform: translateY(0); }
          50%      { transform: translateY(-6px); }
        }
        .pdf-shadow-stack {
          position: absolute; inset: 0;
          transform: rotate(4deg) translateY(8px);
          background: rgba(200,71,58,0.15);
          z-index: -1;
        }
        .pdf-shadow-stack2 {
          position: absolute; inset: 0;
          transform: rotate(7deg) translateY(14px);
          background: rgba(200,71,58,0.08);
          z-index: -2;
        }

        /* Stats */
        .stats {
          display: flex; gap: 40px; padding-top: 48px;
          border-top: 1px solid var(--border); margin-top: 48px;
        }
        .stat-value {
          font-family: var(--serif); font-size: 28px; font-weight: 700;
          color: var(--ink);
        }
        .stat-label { font-size: 12px; color: var(--muted); margin-top: 2px; }

        /* Section */
        .section { padding: 100px 80px; }
        .section-label {
          font-family: var(--mono); font-size: 11px;
          letter-spacing: 0.15em; text-transform: uppercase;
          color: var(--accent); margin-bottom: 16px;
        }
        .section-title {
          font-family: var(--serif);
          font-size: clamp(32px, 3.5vw, 52px);
          font-weight: 900; line-height: 1.1;
          letter-spacing: -0.025em;
          margin-bottom: 20px;
        }
        .section-sub {
          font-size: 16px; color: var(--muted); max-width: 520px; line-height: 1.75;
        }

        /* Tópicos */
        .topics-grid {
          display: grid; grid-template-columns: repeat(2, 1fr);
          gap: 1px; background: var(--border);
          border: 1px solid var(--border);
          margin-top: 48px;
        }
        .topic-item {
          background: var(--paper);
          padding: 28px 32px;
          display: flex; gap: 16px; align-items: flex-start;
          transition: background 0.2s;
        }
        .topic-item:hover { background: white; }
        .topic-num {
          font-family: var(--mono); font-size: 11px;
          color: var(--accent); padding-top: 2px; flex-shrink: 0;
        }
        .topic-text { font-size: 14px; font-weight: 400; line-height: 1.5; }

        /* Proteção strip */
        .protection-strip {
          background: var(--ink);
          padding: 80px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 80px; align-items: center;
        }
        .protection-strip .section-title { color: var(--paper); }
        .protection-strip .section-label { color: rgba(200,71,58,0.8); }
        .protection-strip .section-sub   { color: rgba(245,240,232,0.5); }
        .protection-items { display: flex; flex-direction: column; gap: 20px; }
        .protection-item {
          display: flex; gap: 16px; align-items: flex-start;
          padding: 20px 24px;
          border: 1px solid rgba(245,240,232,0.08);
          transition: border-color 0.2s;
        }
        .protection-item:hover { border-color: rgba(200,71,58,0.4); }
        .protection-icon {
          width: 36px; height: 36px; flex-shrink: 0;
          background: rgba(200,71,58,0.12);
          display: flex; align-items: center; justify-content: center;
          font-size: 16px;
        }
        .protection-title {
          font-size: 13px; font-weight: 500; color: var(--paper);
          margin-bottom: 4px;
        }
        .protection-desc { font-size: 12px; color: rgba(245,240,232,0.4); }

        /* Testimonials */
        .testimonials { padding: 100px 80px; background: white; }
        .testimonials-grid {
          display: grid; grid-template-columns: repeat(3, 1fr);
          gap: 1px; background: var(--border);
          border: 1px solid var(--border);
          margin-top: 48px;
        }
        .testimonial {
          background: white; padding: 36px;
          transition: background 0.2s;
        }
        .testimonial:hover { background: var(--paper); }
        .testimonial-quote {
          font-family: var(--serif); font-size: 17px; font-style: italic;
          line-height: 1.65; margin-bottom: 24px;
          color: var(--ink);
        }
        .testimonial-author { display: flex; align-items: center; gap: 12px; }
        .author-avatar {
          width: 36px; height: 36px; border-radius: 50%;
          background: var(--accent2);
          display: flex; align-items: center; justify-content: center;
          font-family: var(--serif); font-size: 14px; font-weight: 700;
          color: white;
        }
        .author-name { font-size: 13px; font-weight: 500; }
        .author-role { font-size: 11px; color: var(--muted); }

        /* CTA final */
        .cta-section {
          padding: 120px 80px;
          text-align: center;
          position: relative; overflow: hidden;
        }
        .cta-section::before {
          content: '';
          position: absolute; top: 50%; left: 50%;
          transform: translate(-50%,-50%);
          width: 800px; height: 800px;
          background: radial-gradient(circle, rgba(200,71,58,0.06) 0%, transparent 65%);
          pointer-events: none;
        }
        .cta-price-block {
          display: inline-flex; align-items: baseline; gap: 8px;
          margin: 32px 0 40px;
        }
        .cta-currency { font-family: var(--serif); font-size: 24px; color: var(--muted); }
        .cta-price {
          font-family: var(--serif); font-size: 80px; font-weight: 900;
          letter-spacing: -0.04em; color: var(--ink); line-height: 1;
        }
        .cta-guarantee {
          display: flex; align-items: center; justify-content: center;
          gap: 8px; margin-top: 20px;
          font-size: 12px; color: var(--muted);
        }
        .cta-guarantee::before {
          content: '✓'; color: #2D9C6A; font-weight: 700;
        }

        /* Footer */
        .footer {
          border-top: 1px solid var(--border);
          padding: 32px 80px;
          display: flex; align-items: center; justify-content: space-between;
          font-size: 12px; color: var(--muted);
        }
        .footer-shield {
          display: flex; align-items: center; gap: 6px;
        }
        .shield-badge {
          display: inline-flex; align-items: center; gap: 4px;
          padding: 3px 8px;
          border: 1px solid var(--border);
          font-family: var(--mono); font-size: 10px;
          color: var(--muted);
        }

        /* Scrolled nav */
        .nav-scrolled-class { border-color: var(--border) !important; }

        @media (max-width: 768px) {
          .hero { grid-template-columns: 1fr; padding: 100px 24px 60px; gap: 48px; }
          .hero-visual { order: -1; }
          .section { padding: 60px 24px; }
          .protection-strip { grid-template-columns: 1fr; padding: 60px 24px; }
          .testimonials { padding: 60px 24px; }
          .testimonials-grid { grid-template-columns: 1fr; }
          .topics-grid { grid-template-columns: 1fr; }
          .footer { flex-direction: column; gap: 12px; padding: 24px; }
          .stats { gap: 24px; }
          .cta-section { padding: 60px 24px; }
          .hero-title { font-size: 36px; }
        }
      `}</style>

      {/* Navbar */}
      <NavBar onBuy={() => setStep('checkout')} scrollY={scrollY} />

      {/* Hero */}
      <section className="hero" ref={heroRef}>
        <div>
          <div className="hero-tag">Produto digital protegido</div>
          <h1 className="hero-title reveal">
            Domine <em>Python</em> de verdade,<br />do zero ao deploy.
          </h1>
          <p className="hero-subtitle reveal reveal-delay-1">
            {PRODUCT.description}
          </p>
          <div className="hero-actions reveal reveal-delay-2">
            <button className="btn-primary" onClick={() => setStep('checkout')}>
              <span>Comprar agora — R$ {(PRODUCT.price / 100).toFixed(2).replace('.', ',')}</span>
            </button>
            <button className="btn-secondary" onClick={() =>
              document.getElementById('topicos')?.scrollIntoView({ behavior: 'smooth' })
            }>
              Ver conteúdo
            </button>
          </div>
          <div className="stats reveal reveal-delay-3">
            <div>
              <div className="stat-value">312</div>
              <div className="stat-label">páginas de conteúdo</div>
            </div>
            <div>
              <div className="stat-value">847</div>
              <div className="stat-label">cópias vendidas</div>
            </div>
            <div>
              <div className="stat-value">4.9★</div>
              <div className="stat-label">avaliação média</div>
            </div>
          </div>
        </div>

        <div className="hero-visual reveal reveal-delay-1">
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <div className="pdf-shadow-stack2" />
            <div className="pdf-shadow-stack" />
            <div className="pdf-mockup">
              <div className="pdf-cover">
                <div className="pdf-cover-label">Guia Completo · 2025</div>
                <div className="pdf-cover-title">Python do<br />Zero ao Pro</div>
                <div className="pdf-cover-sub">Projetos Reais · APIs · Deploy</div>
              </div>
              <div className="pdf-body">
                {[80, 95, 70, 88, 60, 78].map((w, i) => (
                  <div key={i} className="pdf-line" style={{ width: `${w}%` }} />
                ))}
                <div className="pdf-wm">
                  <div className="pdf-wm-text">
                    USO EXCLUSIVO DE NOME DO COMPRADOR<br />
                    email@comprador.com · TXN-00000<br />
                    PROIBIDA A DISTRIBUIÇÃO
                  </div>
                </div>
              </div>
            </div>
            <div className="pdf-badge">
              <span className="price">R$97</span>
              <span className="label">apenas</span>
            </div>
          </div>
        </div>
      </section>

      {/* Tópicos */}
      <section className="section" id="topicos">
        <div className="section-label">Conteúdo</div>
        <h2 className="section-title reveal">O que você vai aprender</h2>
        <p className="section-sub reveal reveal-delay-1">
          Um currículo estruturado do absoluto zero até aplicações prontas para produção.
        </p>
        <div className="topics-grid">
          {PRODUCT.topics.map((topic, i) => (
            <div className="topic-item reveal" key={i}
                 style={{ transitionDelay: `${i * 0.07}s` }}>
              <span className="topic-num">0{i + 1}</span>
              <span className="topic-text">{topic}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Proteção */}
      <section className="protection-strip">
        <div>
          <div className="section-label">Proteção</div>
          <h2 className="section-title reveal">Seu PDF. Sua identidade. Seu rastreio.</h2>
          <p className="section-sub reveal reveal-delay-1">
            Cada cópia vendida é personalizada com seus dados e rastreável. Se vazar, sabemos exatamente quem foi.
          </p>
        </div>
        <div className="protection-items">
          {[
            { icon: '◈', title: 'Marca d\'água visível', desc: 'Nome, e-mail e ID da transação em todas as páginas' },
            { icon: '◉', title: 'Fingerprint invisível', desc: 'Hash SHA-256 oculto em metadados e padrões de texto' },
            { icon: '⊕', title: 'Link de download único', desc: 'Expira em 24h com limite de downloads por compra' },
            { icon: '◎', title: 'Rastreamento de vazamento', desc: 'Upload do PDF suspeito → identifica o vazador instantaneamente' },
          ].map((item, i) => (
            <div className="protection-item reveal" key={i}
                 style={{ transitionDelay: `${i * 0.08}s` }}>
              <div className="protection-icon">{item.icon}</div>
              <div>
                <div className="protection-title">{item.title}</div>
                <div className="protection-desc">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Depoimentos */}
      <section className="testimonials">
        <div className="section-label">Depoimentos</div>
        <h2 className="section-title reveal">O que dizem os leitores</h2>
        <div className="testimonials-grid">
          {[
            {
              quote: '"Finalmente um guia que não para nos fundamentos. Consegui meu primeiro emprego como dev Python duas semanas depois de terminar."',
              name: 'Lucas F.', role: 'Dev Junior · São Paulo'
            },
            {
              quote: '"A parte de FastAPI vale o preço sozinha. Em dois dias já tinha minha primeira API rodando em produção."',
              name: 'Marina C.', role: 'Analista de Dados · Recife'
            },
            {
              quote: '"Comprei com medo de ser mais um PDF esquecido. Não foi. Li inteiro em uma semana e já apliquei no trabalho."',
              name: 'Rafael M.', role: 'Estudante de Engenharia · BH'
            },
          ].map((t, i) => (
            <div className="testimonial reveal" key={i}
                 style={{ transitionDelay: `${i * 0.1}s` }}>
              <div className="testimonial-quote">{t.quote}</div>
              <div className="testimonial-author">
                <div className="author-avatar">{t.name[0]}</div>
                <div>
                  <div className="author-name">{t.name}</div>
                  <div className="author-role">{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA final */}
      <section className="cta-section">
        <div className="section-label">Investimento</div>
        <h2 className="section-title reveal" style={{ maxWidth: 600, margin: '0 auto' }}>
          Pronto para dominar Python?
        </h2>
        <div className="cta-price-block reveal reveal-delay-1">
          <span className="cta-currency">R$</span>
          <span className="cta-price">97</span>
        </div>
        <button className="btn-primary reveal reveal-delay-2"
                onClick={() => setStep('checkout')}
                style={{ padding: '18px 48px', fontSize: '15px' }}>
          <span>Comprar agora com acesso imediato</span>
        </button>
        <div className="cta-guarantee reveal reveal-delay-3">
          Pagamento seguro · Link de download em segundos · PDF protegido com seus dados
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-shield">
          <span>© 2025 PDFShield</span>
          <span className="shield-badge">🔒 PROTEGIDO</span>
        </div>
        <div>Produto digital · Entrega imediata · Sem reembolso após download</div>
      </footer>
    </>
  )
}

// ── NavBar Component ───────────────────────────────────────────────────────
function NavBar({ onBuy, scrollY }: { onBuy: () => void; scrollY: number }) {
  return (
    <nav className={`nav${scrollY > 40 ? ' scrolled' : ''}`}>
      <a href="/" className="nav-logo">PDF<span>Shield</span></a>
      <button className="nav-cta" onClick={onBuy}>Comprar · R$97</button>
    </nav>
  )
}

// ── CheckoutPage Component ─────────────────────────────────────────────────
function CheckoutPage({ product, onBack }: { product: Product; onBack: () => void }) {
  const [form, setForm]       = useState({ name: '', email: '', cpf: '' })
  const [method, setMethod]   = useState<'stripe' | 'pix'>('stripe')
  const [errors, setErrors]   = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [step, setStep]       = useState<'form' | 'processing' | 'done'>('form')

  const validate = () => {
    const e: Record<string, string> = {}
    if (!form.name.trim())  e.name  = 'Informe seu nome completo'
    if (!form.email.trim()) e.email = 'Informe seu e-mail'
    else if (!/\S+@\S+\.\S+/.test(form.email)) e.email = 'E-mail inválido'
    return e
  }

  const handleSubmit = async () => {
    const e = validate()
    if (Object.keys(e).length) { setErrors(e); return }
    setLoading(true)
    setStep('processing')

    try {
      if (method === 'stripe') {
        // 1. Backend cria checkout session
        const res = await fetch('/api/checkout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pdf_id:     product.id,
            buyer_name: form.name,
            buyer_email: form.email,
            buyer_cpf:  form.cpf,
          }),
        })
        const data = await res.json()
        // 2. Redirecionar para Stripe Checkout
        window.location.href = data.checkout_url

      } else {
        // PIX via Mercado Pago
        const res = await fetch('/api/checkout/pix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pdf_id:     product.id,
            buyer_name: form.name,
            buyer_email: form.email,
            buyer_cpf:  form.cpf,
          }),
        })
        const data = await res.json()
        window.location.href = data.init_point  // página de PIX do Mercado Pago
      }
    } catch (err) {
      setStep('form')
      setErrors({ submit: 'Erro ao processar. Tente novamente.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{`
        .checkout-wrap {
          min-height: 100vh;
          display: grid;
          grid-template-columns: 1fr 420px;
          font-family: var(--sans);
        }
        .checkout-left {
          background: var(--ink);
          padding: 60px;
          display: flex; flex-direction: column; justify-content: center;
          position: relative; overflow: hidden;
        }
        .checkout-left::before {
          content: '';
          position: absolute; bottom: -200px; left: -200px;
          width: 500px; height: 500px; border-radius: 50%;
          background: radial-gradient(circle, rgba(200,71,58,0.12) 0%, transparent 65%);
        }
        .checkout-back {
          position: absolute; top: 32px; left: 40px;
          background: none; border: none; cursor: pointer;
          color: rgba(245,240,232,0.4);
          font-family: var(--sans); font-size: 13px;
          display: flex; align-items: center; gap: 6px;
          transition: color 0.2s;
        }
        .checkout-back:hover { color: var(--paper); }
        .checkout-product-name {
          font-family: var(--serif); font-size: 36px; font-weight: 900;
          color: var(--paper); line-height: 1.1; margin-bottom: 16px;
          position: relative; z-index: 1;
        }
        .checkout-product-desc {
          font-size: 14px; color: rgba(245,240,232,0.45);
          line-height: 1.7; max-width: 400px;
          position: relative; z-index: 1; margin-bottom: 40px;
        }
        .checkout-price-display {
          display: flex; align-items: baseline; gap: 6px;
          position: relative; z-index: 1;
        }
        .co-curr { font-family: var(--serif); font-size: 20px; color: rgba(245,240,232,0.4); }
        .co-price { font-family: var(--serif); font-size: 64px; font-weight: 900; color: var(--paper); line-height: 1; }
        .checkout-includes {
          margin-top: 40px; position: relative; z-index: 1;
          display: flex; flex-direction: column; gap: 10px;
        }
        .checkout-include-item {
          display: flex; gap: 10px; align-items: center;
          font-size: 13px; color: rgba(245,240,232,0.55);
        }
        .checkout-include-item::before {
          content: '✓'; color: #2D9C6A; flex-shrink: 0; font-weight: 700;
        }
        .checkout-right {
          background: var(--paper);
          padding: 60px 48px;
          display: flex; flex-direction: column; justify-content: center;
        }
        .checkout-title {
          font-family: var(--serif); font-size: 22px; font-weight: 700;
          margin-bottom: 28px; color: var(--ink);
        }
        .field { margin-bottom: 18px; }
        .field label {
          display: block; font-size: 11px; font-weight: 500;
          letter-spacing: 0.08em; text-transform: uppercase;
          color: var(--muted); margin-bottom: 6px;
        }
        .field input {
          width: 100%; padding: 12px 14px;
          border: 1px solid var(--border);
          background: white;
          font-family: var(--sans); font-size: 14px; color: var(--ink);
          outline: none;
          transition: border-color 0.2s;
        }
        .field input:focus { border-color: var(--ink); }
        .field input.error { border-color: var(--accent); }
        .field-error { font-size: 11px; color: var(--accent); margin-top: 4px; }
        .method-tabs {
          display: grid; grid-template-columns: 1fr 1fr;
          gap: 1px; background: var(--border);
          border: 1px solid var(--border);
          margin-bottom: 24px;
        }
        .method-tab {
          padding: 12px; background: white;
          border: none; cursor: pointer;
          font-family: var(--sans); font-size: 13px; font-weight: 500;
          color: var(--muted);
          transition: all 0.15s;
          display: flex; align-items: center; justify-content: center; gap: 6px;
        }
        .method-tab.active {
          background: var(--ink); color: var(--paper);
        }
        .submit-btn {
          width: 100%; padding: 15px;
          background: var(--ink); color: var(--paper);
          border: none; cursor: pointer;
          font-family: var(--sans); font-size: 14px; font-weight: 500;
          letter-spacing: 0.02em;
          transition: background 0.2s;
          margin-top: 8px;
          display: flex; align-items: center; justify-content: center; gap: 8px;
        }
        .submit-btn:hover:not(:disabled) { background: var(--accent); }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .submit-error {
          color: var(--accent); font-size: 12px;
          text-align: center; margin-top: 8px;
        }
        .security-badges {
          display: flex; gap: 16px; justify-content: center;
          margin-top: 20px; flex-wrap: wrap;
        }
        .sec-badge {
          font-size: 10px; color: var(--muted);
          display: flex; align-items: center; gap: 4px;
          border: 1px solid var(--border); padding: 4px 8px;
        }
        .processing-overlay {
          display: flex; flex-direction: column;
          align-items: center; justify-content: center;
          gap: 16px; text-align: center; padding: 40px 0;
        }
        .spinner {
          width: 40px; height: 40px; border-radius: 50%;
          border: 2px solid var(--border);
          border-top-color: var(--ink);
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (max-width: 768px) {
          .checkout-wrap { grid-template-columns: 1fr; }
          .checkout-left { padding: 80px 24px 40px; }
          .checkout-right { padding: 40px 24px; }
        }
      `}</style>

      <div className="checkout-wrap">
        {/* Esquerda: resumo do produto */}
        <div className="checkout-left">
          <button className="checkout-back" onClick={onBack}>← Voltar</button>
          <div className="checkout-product-name">
            Python do<br />Zero ao Pro
          </div>
          <p className="checkout-product-desc">
            Guia completo em PDF protegido. Acesso imediato após o pagamento.
          </p>
          <div className="checkout-price-display">
            <span className="co-curr">R$</span>
            <span className="co-price">97</span>
          </div>
          <div className="checkout-includes">
            {[
              '312 páginas de conteúdo prático',
              'PDF personalizado com seus dados',
              'Link de download com 2 acessos · 48h',
              'Atualizações gratuitas por 1 ano',
            ].map((item, i) => (
              <div className="checkout-include-item" key={i}>{item}</div>
            ))}
          </div>
        </div>

        {/* Direita: formulário */}
        <div className="checkout-right">
          {step === 'form' ? (
            <>
              <div className="checkout-title">Seus dados</div>

              <div className="method-tabs">
                <button
                  className={`method-tab${method === 'stripe' ? ' active' : ''}`}
                  onClick={() => setMethod('stripe')}
                >
                  💳 Cartão / Boleto
                </button>
                <button
                  className={`method-tab${method === 'pix' ? ' active' : ''}`}
                  onClick={() => setMethod('pix')}
                >
                  ⚡ PIX
                </button>
              </div>

              <div className="field">
                <label>Nome completo</label>
                <input
                  type="text"
                  placeholder="Carlos Mendes"
                  value={form.name}
                  className={errors.name ? 'error' : ''}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                />
                {errors.name && <div className="field-error">{errors.name}</div>}
              </div>

              <div className="field">
                <label>E-mail</label>
                <input
                  type="email"
                  placeholder="carlos@email.com"
                  value={form.email}
                  className={errors.email ? 'error' : ''}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                />
                {errors.email && <div className="field-error">{errors.email}</div>}
              </div>

              <div className="field">
                <label>CPF <span style={{ color: 'var(--muted)', textTransform: 'none', letterSpacing: 0 }}>(opcional — melhora o rastreamento)</span></label>
                <input
                  type="text"
                  placeholder="000.000.000-00"
                  value={form.cpf}
                  onChange={e => setForm(f => ({ ...f, cpf: e.target.value }))}
                />
              </div>

              <button
                className="submit-btn"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading
                  ? <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Processando...</>
                  : method === 'pix'
                    ? '⚡ Pagar com PIX — R$97'
                    : '💳 Ir para o pagamento — R$97'
                }
              </button>

              {errors.submit && <div className="submit-error">{errors.submit}</div>}

              <div className="security-badges">
                <span className="sec-badge">🔒 SSL</span>
                <span className="sec-badge">🛡 PDFShield</span>
                <span className="sec-badge">⚡ Entrega imediata</span>
              </div>
            </>
          ) : (
            <div className="processing-overlay">
              <div className="spinner" />
              <div style={{ fontFamily: 'var(--serif)', fontSize: 20, fontWeight: 700 }}>
                Redirecionando...
              </div>
              <div style={{ fontSize: 13, color: 'var(--muted)', maxWidth: 260 }}>
                Aguarde enquanto preparamos seu checkout seguro.
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
