-- Commercial usage facts and quota reservations. Payment/invoice authority remains external.
CREATE TABLE IF NOT EXISTS twi_usage_reservations (
    reservation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    feature TEXT NOT NULL,
    dimension TEXT NOT NULL,
    period_start TEXT NOT NULL,
    quantity BIGINT NOT NULL CHECK (quantity > 0),
    status TEXT NOT NULL CHECK (status IN ('reserved', 'committed', 'released')),
    idempotency_key TEXT NOT NULL,
    request_fingerprint CHAR(64) NOT NULL
        CHECK (length(btrim(request_fingerprint)) = 64 AND request_fingerprint ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, subject_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS twi_usage_reservation_quota_idx
    ON twi_usage_reservations(tenant_id, dimension, period_start, status);

CREATE TABLE IF NOT EXISTS twi_usage_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    feature TEXT NOT NULL,
    dimension TEXT NOT NULL,
    period_start TEXT NOT NULL,
    quantity BIGINT NOT NULL CHECK (quantity > 0),
    occurred_at TIMESTAMPTZ NOT NULL,
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    reservation_id TEXT NOT NULL UNIQUE REFERENCES twi_usage_reservations(reservation_id),
    idempotency_key TEXT NOT NULL,
    UNIQUE (tenant_id, subject_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS twi_usage_events_scope_time_idx
    ON twi_usage_events(tenant_id, subject_id, occurred_at);

CREATE OR REPLACE FUNCTION twi_reject_usage_event_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'usage events are append-only';
END;
$$;
DROP TRIGGER IF EXISTS twi_usage_events_no_update ON twi_usage_events;
CREATE TRIGGER twi_usage_events_no_update BEFORE UPDATE ON twi_usage_events
    FOR EACH ROW EXECUTE FUNCTION twi_reject_usage_event_mutation();
DROP TRIGGER IF EXISTS twi_usage_events_no_delete ON twi_usage_events;
CREATE TRIGGER twi_usage_events_no_delete BEFORE DELETE ON twi_usage_events
    FOR EACH ROW EXECUTE FUNCTION twi_reject_usage_event_mutation();

INSERT INTO twi_schema_migrations(version) VALUES (3)
ON CONFLICT (version) DO NOTHING;
