-- Durable tenant-scoped monitoring state and idempotent change-event outbox.
CREATE TABLE IF NOT EXISTS twi_monitoring_state (
    tenant_id TEXT NOT NULL CHECK (length(btrim(tenant_id)) BETWEEN 1 AND 256 AND tenant_id = btrim(tenant_id)),
    source_fingerprint CHAR(64) NOT NULL
        CHECK (length(btrim(source_fingerprint)) = 64 AND btrim(source_fingerprint) ~ '^[0-9a-f]{64}$'),
    content_sha256 CHAR(64) NOT NULL
        CHECK (length(btrim(content_sha256)) = 64 AND btrim(content_sha256) ~ '^[0-9a-f]{64}$'),
    status_code INTEGER NOT NULL CHECK (status_code BETWEEN 100 AND 599),
    content_type TEXT NOT NULL CHECK (length(content_type) BETWEEN 1 AND 255 AND content_type !~ '[[:cntrl:]]'),
    last_observed_at TIMESTAMPTZ NOT NULL,
    revision BIGINT NOT NULL DEFAULT 1 CHECK (revision >= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, source_fingerprint)
);

CREATE TABLE IF NOT EXISTS twi_monitoring_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL CHECK (length(btrim(tenant_id)) BETWEEN 1 AND 256 AND tenant_id = btrim(tenant_id)),
    source_fingerprint CHAR(64) NOT NULL
        CHECK (length(btrim(source_fingerprint)) = 64 AND btrim(source_fingerprint) ~ '^[0-9a-f]{64}$'),
    idempotency_key CHAR(64) NOT NULL
        CHECK (length(btrim(idempotency_key)) = 64 AND btrim(idempotency_key) ~ '^[0-9a-f]{64}$'),
    change_kind TEXT NOT NULL CHECK (
        change_kind IN ('content_changed', 'status_changed', 'content_type_changed', 'multiple_changes')
    ),
    previous_sha256 CHAR(64) NOT NULL
        CHECK (length(btrim(previous_sha256)) = 64 AND btrim(previous_sha256) ~ '^[0-9a-f]{64}$'),
    current_sha256 CHAR(64) NOT NULL
        CHECK (length(btrim(current_sha256)) = 64 AND btrim(current_sha256) ~ '^[0-9a-f]{64}$'),
    previous_status_code INTEGER NOT NULL CHECK (previous_status_code BETWEEN 100 AND 599),
    current_status_code INTEGER NOT NULL CHECK (current_status_code BETWEEN 100 AND 599),
    previous_content_type TEXT NOT NULL CHECK (length(previous_content_type) BETWEEN 1 AND 255),
    current_content_type TEXT NOT NULL CHECK (length(current_content_type) BETWEEN 1 AND 255),
    payload_json JSONB NOT NULL,
    payload_sha256 CHAR(64) NOT NULL
        CHECK (length(btrim(payload_sha256)) = 64 AND btrim(payload_sha256) ~ '^[0-9a-f]{64}$'),
    status TEXT NOT NULL CHECK (status IN ('pending', 'delivering', 'delivered', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    available_at DOUBLE PRECISION NOT NULL,
    lease_owner TEXT,
    lease_until DOUBLE PRECISION,
    last_error_code TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    UNIQUE (tenant_id, idempotency_key),
    CHECK ((status = 'delivering' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL) OR status <> 'delivering')
);

CREATE INDEX IF NOT EXISTS twi_monitoring_events_claim_idx
    ON twi_monitoring_events(status, available_at, created_at, event_id);
CREATE INDEX IF NOT EXISTS twi_monitoring_events_tenant_idx
    ON twi_monitoring_events(tenant_id, created_at DESC);

INSERT INTO twi_schema_migrations(version) VALUES (2)
ON CONFLICT (version) DO NOTHING;
