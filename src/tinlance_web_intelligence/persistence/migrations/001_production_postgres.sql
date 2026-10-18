-- TWI production persistence schema. Applied idempotently by the PostgreSQL adapter.
CREATE TABLE IF NOT EXISTS twi_schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('search', 'fetch', 'browser')),
    payload_json JSONB NOT NULL,
    payload_fingerprint CHAR(64) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    result_json JSONB,
    error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    available_at DOUBLE PRECISION NOT NULL,
    lease_owner TEXT,
    lease_until DOUBLE PRECISION,
    cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
    idempotency_key TEXT NOT NULL,
    UNIQUE (tenant_id, subject_id, idempotency_key),
    CHECK ((status = 'running' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR status <> 'running')
);
CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs(status, available_at, created_at, job_id);
CREATE INDEX IF NOT EXISTS jobs_tenant_idx ON jobs(tenant_id, subject_id, created_at);
CREATE TABLE IF NOT EXISTS twi_source_evidence_outbox (
    event_id TEXT PRIMARY KEY,
    tenant_ref CHAR(64) NOT NULL CHECK (tenant_ref ~ '^[0-9a-f]{64}$'),
    subject_ref CHAR(64) NOT NULL CHECK (subject_ref ~ '^[0-9a-f]{64}$'),
    idempotency_key TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    status TEXT NOT NULL CHECK (status IN ('pending', 'delivering', 'delivered', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    available_at DOUBLE PRECISION NOT NULL,
    lease_owner TEXT,
    lease_until DOUBLE PRECISION,
    remote_evidence_id TEXT,
    last_error_code TEXT,
    request_id TEXT NOT NULL,
    traceparent TEXT,
    created_at DOUBLE PRECISION NOT NULL,
    updated_at DOUBLE PRECISION NOT NULL,
    delivered_at DOUBLE PRECISION,
    UNIQUE (tenant_ref, subject_ref, idempotency_key),
    CHECK ((status = 'delivering' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR status <> 'delivering')
);
CREATE INDEX IF NOT EXISTS twi_outbox_claim_idx ON twi_source_evidence_outbox(status, available_at, created_at);
CREATE INDEX IF NOT EXISTS twi_outbox_scope_idx ON twi_source_evidence_outbox(event_id, tenant_ref, subject_ref);
INSERT INTO twi_schema_migrations(version) VALUES (1) ON CONFLICT (version) DO NOTHING;
