-- Tenant-scoped monitors, durable run outcomes, and trace context propagation.
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check
    CHECK (kind IN ('search', 'fetch', 'browser', 'monitor'));
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS traceparent TEXT;

CREATE TABLE IF NOT EXISTS twi_monitors (
    monitor_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    target_url TEXT NOT NULL CHECK (length(target_url) BETWEEN 1 AND 4096),
    policy_json JSONB NOT NULL,
    request_fingerprint CHAR(64) NOT NULL
        CHECK (length(btrim(request_fingerprint)) = 64 AND request_fingerprint ~ '^[0-9a-f]{64}$'),
    status TEXT NOT NULL CHECK (status IN ('active', 'paused', 'deleted')),
    baseline_digest CHAR(64)
        CHECK (baseline_digest IS NULL OR (length(btrim(baseline_digest)) = 64 AND baseline_digest ~ '^[0-9a-f]{64}$')),
    baseline_observed_at TIMESTAMPTZ,
    baseline_version BIGINT NOT NULL DEFAULT 0 CHECK (baseline_version >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    idempotency_key TEXT NOT NULL,
    UNIQUE (tenant_id, subject_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS twi_monitors_scope_idx
    ON twi_monitors(tenant_id, subject_id, created_at DESC);

CREATE TABLE IF NOT EXISTS twi_monitor_run_results (
    monitor_id TEXT NOT NULL REFERENCES twi_monitors(monitor_id),
    job_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    previous_digest CHAR(64)
        CHECK (previous_digest IS NULL OR (length(btrim(previous_digest)) = 64 AND previous_digest ~ '^[0-9a-f]{64}$')),
    current_digest CHAR(64)
        CHECK (current_digest IS NULL OR (length(btrim(current_digest)) = 64 AND current_digest ~ '^[0-9a-f]{64}$')),
    changed BOOLEAN,
    observed_at TIMESTAMPTZ NOT NULL,
    changed_units INTEGER NOT NULL CHECK (changed_units BETWEEN 0 AND 10000),
    PRIMARY KEY (monitor_id, job_id)
);
CREATE INDEX IF NOT EXISTS twi_monitor_runs_time_idx
    ON twi_monitor_run_results(monitor_id, observed_at DESC);

INSERT INTO twi_schema_migrations(version) VALUES (2)
ON CONFLICT (version) DO NOTHING;
