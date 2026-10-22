"""PostgreSQL transactional outbox with idempotency, leases, retries, and scope isolation."""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from importlib.resources import files
from typing import Any

from psycopg.types.json import Jsonb

from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    OutboxConflictError,
    OutboxEvent,
    OutboxLeaseLostError,
)
from tinlance_web_intelligence.persistence.postgres_pool import (
    acquire_pool,
    release_pool,
)


class PostgresSourceEvidenceOutbox:
    """Multi-replica-safe evidence outbox backed by PostgreSQL row-level locks."""

    def __init__(
        self, dsn: str, *, min_size: int = 1, max_size: int = 10,
        auto_migrate: bool = False
    ) -> None:
        if not dsn or dsn != dsn.strip():
            raise ValueError("PostgreSQL DSN must be non-empty and normalized")
        if not 1 <= min_size <= max_size <= 50:
            raise ValueError("invalid PostgreSQL pool configuration")
        self._pool = acquire_pool(dsn, min_size=min_size, max_size=max_size)
        try:
            if auto_migrate:
                self._apply_migrations()
            else:
                self._verify_schema()
        except Exception:
            release_pool(self._pool)
            raise

    def _apply_migrations(self) -> None:
        migrations = files("tinlance_web_intelligence.persistence.migrations")
        with self._pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(71020261018)")
            for name in (
                "001_production_postgres.sql",
                "002_monitors.sql",
                "003_commercial_usage.sql",
            ):
                migration = migrations.joinpath(name)
                if not migration.is_file():
                    raise RuntimeError(f"production PostgreSQL migration file is missing: {name}")
                conn.execute(migration.read_text(encoding="utf-8"), prepare=False)

    def _verify_schema(self) -> None:
        with self._pool.connection() as conn:
            tables = conn.execute(
                "SELECT to_regclass('jobs') AS jobs, "
                "to_regclass('twi_source_evidence_outbox') AS outbox, "
                "to_regclass('twi_schema_migrations') AS migrations"
            ).fetchone()
            if tables is None or any(
                tables[name] is None for name in ("jobs", "outbox", "migrations")
            ):
                raise RuntimeError("PostgreSQL schema is missing; run the migration job")
            version = conn.execute(
                "SELECT max(version) AS version FROM twi_schema_migrations"
            ).fetchone()
            if version is None or version["version"] < 3:
                raise RuntimeError("unsupported PostgreSQL schema version")

    @staticmethod
    def _row_to_event(row: dict[str, Any]) -> OutboxEvent:
        payload = row["payload_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise RuntimeError("stored outbox payload is not an object")
        return OutboxEvent(
            event_id=row["event_id"], tenant_ref=row["tenant_ref"],
            subject_ref=row["subject_ref"], idempotency_key=row["idempotency_key"],
            payload=payload, status=row["status"], attempts=int(row["attempts"]),
            lease_token=row["lease_owner"], request_id=row["request_id"],
            traceparent=row["traceparent"], remote_evidence_id=row["remote_evidence_id"],
        )

    @staticmethod
    def _canonical_payload(payload: dict[str, Any]) -> tuple[str, str]:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
        return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def enqueue(self, *, tenant_ref: str, subject_ref: str, idempotency_key: str,
                payload: dict[str, Any], request_id: str,
                traceparent: str | None) -> tuple[OutboxEvent, bool]:
        if not re.fullmatch(r"[0-9a-f]{64}", tenant_ref):
            raise ValueError("tenant_ref must be a pseudonymous SHA-256 reference")
        if not re.fullmatch(r"[0-9a-f]{64}", subject_ref):
            raise ValueError("subject_ref must be a pseudonymous SHA-256 reference")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{16,128}", idempotency_key):
            raise ValueError("invalid idempotency key")
        if not request_id or len(request_id) > 128:
            raise ValueError("invalid request_id")
        _encoded, payload_sha256 = self._canonical_payload(payload)
        event_id = str(uuid.uuid4())
        now = time.time()
        with self._pool.connection() as conn:
            row = conn.execute(
                """INSERT INTO twi_source_evidence_outbox (
                    event_id, tenant_ref, subject_ref, idempotency_key, payload_json,
                    payload_sha256, status, attempts, available_at, request_id, traceparent,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, 'pending', 0, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_ref, subject_ref, idempotency_key) DO NOTHING
                RETURNING *""",
                (event_id, tenant_ref, subject_ref, idempotency_key, Jsonb(payload),
                 payload_sha256, now, request_id, traceparent, now, now),
            ).fetchone()
            replayed = row is None
            if row is None:
                row = conn.execute(
                    """SELECT * FROM twi_source_evidence_outbox
                    WHERE tenant_ref=%s AND subject_ref=%s AND idempotency_key=%s""",
                    (tenant_ref, subject_ref, idempotency_key),
                ).fetchone()
                if row is None:
                    raise RuntimeError("idempotent outbox event could not be resolved")
                if row["payload_sha256"] != payload_sha256:
                    raise OutboxConflictError(
                        "idempotency key was used with another evidence payload"
                    )
            return self._row_to_event(row), replayed

    def claim_next(self, worker_id: str, *, lease_seconds: int = 60) -> OutboxEvent | None:
        if not worker_id or len(worker_id) > 128 or not 5 <= lease_seconds <= 300:
            raise ValueError("worker ID and a 5–300 second lease are required")
        now = time.time()
        with self._pool.connection() as conn:
            row = conn.execute(
                """SELECT * FROM twi_source_evidence_outbox
                WHERE (status='pending' AND available_at <= %s)
                   OR (status='delivering' AND lease_until <= %s)
                ORDER BY created_at, event_id LIMIT 1 FOR UPDATE SKIP LOCKED""",
                (now, now),
            ).fetchone()
            if row is None:
                return None
            token = f"{worker_id}:{uuid.uuid4()}"
            claimed = conn.execute(
                """UPDATE twi_source_evidence_outbox SET status='delivering',
                   attempts=attempts+1, lease_owner=%s, lease_until=%s, updated_at=%s,
                   last_error_code=NULL WHERE event_id=%s RETURNING *""",
                (token, now + lease_seconds, now, row["event_id"]),
            ).fetchone()
            return self._row_to_event(claimed) if claimed is not None else None

    def complete(self, event_id: str, lease_token: str,
                 remote_evidence_id: str) -> OutboxEvent:
        now = time.time()
        with self._pool.connection() as conn:
            row = conn.execute(
                """UPDATE twi_source_evidence_outbox SET status='delivered',
                   remote_evidence_id=%s, delivered_at=%s, lease_owner=NULL, lease_until=NULL,
                   updated_at=%s WHERE event_id=%s AND status='delivering' AND lease_until >= %s
                   AND lease_owner=%s RETURNING *""",
                (remote_evidence_id, now, now, event_id, now, lease_token),
            ).fetchone()
            if row is None:
                raise OutboxLeaseLostError("outbox lease was lost before completion")
            return self._row_to_event(row)

    def fail(self, event_id: str, lease_token: str, *, error_code: str,
             retryable: bool, max_attempts: int = 5) -> OutboxEvent:
        if not re.fullmatch(r"[a-z0-9_.-]{1,64}", error_code):
            raise ValueError("invalid error_code")
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")
        now = time.time()
        with self._pool.connection() as conn:
            row = conn.execute(
                """SELECT attempts FROM twi_source_evidence_outbox
                WHERE event_id=%s AND status='delivering' AND lease_owner=%s
                  AND lease_until >= %s FOR UPDATE""",
                (event_id, lease_token, now),
            ).fetchone()
            if row is None:
                raise OutboxLeaseLostError("outbox lease was lost before failure handling")
            attempts = int(row["attempts"])
            will_retry = retryable and attempts < max_attempts
            status = "pending" if will_retry else "failed"
            available_at = now + (min(2 ** min(attempts, 8), 300) if will_retry else 0)
            updated = conn.execute(
                """UPDATE twi_source_evidence_outbox SET status=%s, available_at=%s,
                   lease_owner=NULL, lease_until=NULL, last_error_code=%s, updated_at=%s
                   WHERE event_id=%s RETURNING *""",
                (status, available_at, error_code, now, event_id),
            ).fetchone()
            if updated is None:
                raise RuntimeError("failed outbox event could not be read back")
            return self._row_to_event(updated)

    def get(self, event_id: str, tenant_ref: str, subject_ref: str) -> OutboxEvent | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                """SELECT * FROM twi_source_evidence_outbox
                WHERE event_id=%s AND tenant_ref=%s AND subject_ref=%s""",
                (event_id, tenant_ref, subject_ref),
            ).fetchone()
        return self._row_to_event(row) if row is not None else None

    def metrics_snapshot(self) -> dict[str, float]:
        """Return low-cardinality outbox counts and oldest pending-event age."""
        with self._pool.connection() as conn:
            counts = conn.execute(
                "SELECT status, COUNT(*) AS count "
                "FROM twi_source_evidence_outbox GROUP BY status"
            ).fetchall()
            oldest = conn.execute(
                """SELECT GREATEST(
                       0, EXTRACT(EPOCH FROM clock_timestamp()) - MIN(created_at)
                   ) AS age_seconds
                   FROM twi_source_evidence_outbox WHERE status='pending'"""
            ).fetchone()
        snapshot = {
            f"outbox_{status}": 0.0
            for status in ("pending", "delivering", "delivered", "failed")
        }
        for row in counts:
            snapshot[f"outbox_{row['status']}"] = float(row["count"])
        age_seconds = oldest["age_seconds"] if oldest is not None else None
        snapshot["outbox_oldest_pending_age_seconds"] = float(age_seconds or 0.0)
        return snapshot

    def ping(self) -> bool:
        try:
            with self._pool.connection() as conn:
                row = conn.execute("SELECT 1 AS ready").fetchone()
            return row is not None and row["ready"] == 1
        except Exception:
            return False

    def close(self) -> None:
        if not getattr(self, "_pool_released", False):
            self._pool_released = True
            release_pool(self._pool)
