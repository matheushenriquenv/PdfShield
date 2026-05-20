-- PDFShield — Schema PostgreSQL
-- Executado automaticamente no primeiro docker-compose up

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- PDFs base (uploads do admin)
CREATE TABLE IF NOT EXISTS pdfs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename      TEXT NOT NULL,
    s3_key        TEXT NOT NULL UNIQUE,
    size_bytes    INTEGER NOT NULL,
    page_count    INTEGER,
    is_active     BOOLEAN DEFAULT true,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Vendas e PDFs protegidos
CREATE TABLE IF NOT EXISTS sales (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id   TEXT NOT NULL UNIQUE,
    pdf_id           UUID REFERENCES pdfs(id),
    buyer_name       TEXT NOT NULL,
    buyer_email      TEXT NOT NULL,
    buyer_cpf        TEXT,
    buyer_hash       CHAR(64) NOT NULL,
    short_hash       CHAR(16) NOT NULL,
    protected_s3_key TEXT,
    payment_provider TEXT,
    amount_brl       NUMERIC(10,2),
    status           TEXT DEFAULT 'active',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sales_hash  ON sales(buyer_hash);
CREATE INDEX IF NOT EXISTS idx_sales_email ON sales(buyer_email);

-- Tokens de download temporários
CREATE TABLE IF NOT EXISTS download_tokens (
    token          TEXT PRIMARY KEY,
    sale_id        UUID REFERENCES sales(id),
    expires_at     TIMESTAMPTZ NOT NULL,
    downloads_used INTEGER DEFAULT 0,
    max_downloads  INTEGER DEFAULT 2,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Logs de acesso
CREATE TABLE IF NOT EXISTS access_logs (
    id         BIGSERIAL PRIMARY KEY,
    sale_id    UUID REFERENCES sales(id),
    event      TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Incidentes de vazamento
CREATE TABLE IF NOT EXISTS leak_incidents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id          UUID REFERENCES sales(id),
    detection_method TEXT NOT NULL,
    extracted_hash   TEXT,
    reported_url     TEXT,
    resolved         BOOLEAN DEFAULT false,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
