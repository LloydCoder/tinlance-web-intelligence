"""PostgreSQL job repository with transactional idempotency and SKIP LOCKED leases."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from importlib.resources import files
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from tinlance_web_intelligence.jobs.model import (
    IdempotencyConflictError,
    Job,
    JobStatus,
    LeaseLostError,
)


def _iso(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class PostgresJobRepository:
    """Multi-worker PostgreSQL queue. Claiming is atomic across independent processes."""

    def __init__(self, dsn: str, *, max_attempts: int = 3,
                 min_size: int = 1, max_size: int = 10, auto_migrate: bool = False) -> None:
        if not dsn or not dsn.strip() or dsn != dsn.strip():
            raise ValueError("PostgreSQL DSN must be non-empty and normalized")
        if not 1 <= max_attempts <= 10 or not 1 <= min_size <= max_size <= 50:
            raise ValueError("invalid PostgreSQL pool or retry configuration")
        self._max_attempts = max_attempts
        self._pool = ConnectionPool(
            conninfo=dsn, min_size=min_size, max_size=max_size,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
            timeout=10, open=True,
        )
        self._pool.wait(timeout=10)
        if auto_migrate:
            self._apply_migrations()
        else:
            self._verify_schema()

    def _apply_migrations(self) -> None:
        migration = files("tinlance_web_intelligence.persistence.migrations").joinpath("001_production_postgres.sql")
        if not migration.is_file():
            self._pool.close()
            raise RuntimeError("production PostgreSQL migration file is missing")
        sql = migration.read_text(encoding="utf-8")
        with self._pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(71020261018)")
            conn.execute(sql, prepare=False)

    def _verify_schema(self) -> None:
        with self._pool.connection() as conn:
            tables = conn.execute(
                "SELECT to_regclass('jobs') AS jobs, "
                "to_regclass('twi_source_evidence_outbox') AS outbox, "
                "to_regclass('twi_schema_migrations') AS migrations"
            ).fetchone()
            if tables is None or any(tables[name] is None for name in ("jobs", "outbox", "migrations")):
                raise RuntimeError("PostgreSQL schema is missing; run the migration job")
            version = conn.execute(
                "SELECT max(version) AS version FROM twi_schema_migrations"
            ).fetchone()
            if version is None or version["version"] != 1:
                raise RuntimeError("unsupported PostgreSQL schema version")

    @staticmethod
    def _to_job(row: dict[str, Any]) -> Job:
        payload = row["payload_json"]
        result = row["result_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(result, str):
            result = json.loads(result)
        if not isinstance(payload, dict) or (result is not None and not isinstance(result, dict)):
            raise RuntimeError("stored job JSON has an invalid shape")
        return Job(
            job_id=row["job_id"], tenant_id=row["tenant_id"], subject_id=row["subject_id"],
            kind=row["kind"], payload=payload, status=JobStatus(row["status"]),
            created_at=_iso(row["created_at"]), updated_at=_iso(row["updated_at"]),
            attempts=int(row["attempts"]), max_attempts=int(row["max_attempts"]),
            result=result, error_code=row["error_code"],
            cancel_requested=bool(row["cancel_requested"]),
            idempotency_key=row["idempotency_key"],
        )

    def create(self, *, tenant_id: str, subject_id: str, kind: str,
               payload: dict[str, Any], idempotency_key: str) -> Job:
        if kind not in {"search", "fetch", "browser"}:
            raise ValueError("unsupported job kind")
        if not tenant_id or not subject_id or not idempotency_key:
            raise ValueError("tenant, subject, and idempotency key are required")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        fingerprint = hashlib.sha256(f"{kind}\0{serialized}".encode()).hexdigest()
        job_id = str(uuid.uuid4())
        with self._pool.connection() as conn:
            row = conn.execute(
                """INSERT INTO jobs (
                    job_id, tenant_id, subject_id, kind, payload_json, payload_fingerprint,
                    status, created_at, updated_at, attempts, max_attempts, available_at,
                    idempotency_key
                ) VALUES (%s, %s, %s, %s, %s, %s, 'queued', now(), now(), 0, %s, %s, %s)
                ON CONFLICT (tenant_id, subject_id, idempotency_key) DO NOTHING
                RETURNING *""",
                (job_id, tenant_id, subject_id, kind, Jsonb(payload), fingerprint,
                 self._max_attempts, time.time(), idempotency_key),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    """SELECT * FROM jobs
                    WHERE tenant_id=%s AND subject_id=%s AND idempotency_key=%s""",
                    (tenant_id, subject_id, idempotency_key),
                ).fetchone()
                if row is None:
                    raise RuntimeError("idempotent job could not be resolved")
                if row["payload_fingerprint"] != fingerprint:
                    raise IdempotencyConflictError(
                        "idempotency key was reused for a different request"
                    )
            return self._to_job(row)

    def get(self, job_id: str, *, tenant_id: str,
            subject_id: str | None = None) -> Job | None:
        sql = "SELECT * FROM jobs WHERE job_id=%s AND tenant_id=%s"
        params: tuple[Any, ...] = (job_id, tenant_id)
        if subject_id is not None:
            sql += " AND subject_id=%s"
            params += (subject_id,)
        with self._pool.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        return self._to_job(row) if row is not None else None

    def claim_next(self, worker_id: str, *, lease_seconds: int = 60,
                   allowed_kinds: tuple[str, ...] | None = None) -> Job | None:
        if not worker_id or len(worker_id) > 128 or not 5 <= lease_seconds <= 3600:
            raise ValueError("worker ID and a 5–3600 second lease are required")
        if allowed_kinds is not None and (
            not allowed_kinds or len(allowed_kinds) > 3
            or len(set(allowed_kinds)) != len(allowed_kinds)
            or any(kind not in {"search", "fetch", "browser"} for kind in allowed_kinds)
        ):
            raise ValueError("allowed_kinds must contain unique supported job kinds")
        now = time.time()
        with self._pool.connection() as conn:
            conn.execute(
                """UPDATE jobs SET status='cancelled', lease_owner=NULL, lease_until=NULL,
                   updated_at=now() WHERE status='running' AND lease_until < %s
                   AND cancel_requested=TRUE""", (now,)
            )
            conn.execute(
                """UPDATE jobs SET status='failed', error_code='lease_expired',
                   lease_owner=NULL, lease_until=NULL, updated_at=now()
                   WHERE status='running' AND lease_until < %s AND attempts >= max_attempts""",
                (now,),
            )
            conn.execute(
                """UPDATE jobs SET status='queued', lease_owner=NULL, lease_until=NULL,
                   available_at=%s, updated_at=now()
                   WHERE status='running' AND lease_until < %s AND attempts < max_attempts""",
                (now, now),
            )
            if allowed_kinds is None:
                row = conn.execute(
                    """SELECT * FROM jobs WHERE status='queued' AND available_at <= %s
                       AND cancel_requested=FALSE ORDER BY created_at, job_id LIMIT 1
                       FOR UPDATE SKIP LOCKED""", (now,)
                ).fetchone()
            else:
                row = conn.execute(
                    """SELECT * FROM jobs WHERE status='queued' AND available_at <= %s
                       AND cancel_requested=FALSE AND kind = ANY(%s)
                       ORDER BY created_at, job_id LIMIT 1 FOR UPDATE SKIP LOCKED""",
                    (now, list(allowed_kinds)),
                ).fetchone()
            if row is None:
                return None
            lease_until = now + lease_seconds
            claimed = conn.execute(
                """UPDATE jobs SET status='running', attempts=attempts+1, lease_owner=%s,
                   lease_until=%s, updated_at=now() WHERE job_id=%s RETURNING *""",
                (worker_id, lease_until, row["job_id"]),
            ).fetchone()
            return self._to_job(claimed) if claimed is not None else None

    def _owned_running_job(self, conn: Any, job_id: str, worker_id: str) -> dict[str, Any]:
        row = conn.execute(
            """SELECT * FROM jobs WHERE job_id=%s AND status='running' AND lease_owner=%s
               AND lease_until >= %s FOR UPDATE""",
            (job_id, worker_id, time.time()),
        ).fetchone()
        if row is None:
            raise LeaseLostError("worker no longer owns the running job")
        return row

    def complete(self, job_id: str, worker_id: str, result: dict[str, Any]) -> Job:
        json.dumps(result, allow_nan=False)
        with self._pool.connection() as conn:
            row = self._owned_running_job(conn, job_id, worker_id)
            status = "cancelled" if row["cancel_requested"] else "succeeded"
            updated = conn.execute(
                """UPDATE jobs SET status=%s, result_json=%s, lease_owner=NULL,
                   lease_until=NULL, updated_at=now() WHERE job_id=%s RETURNING *""",
                (status, None if status == "cancelled" else Jsonb(result), job_id),
            ).fetchone()
            if updated is None:
                raise RuntimeError("completed job could not be read back")
            return self._to_job(updated)

    def fail(self, job_id: str, worker_id: str, *, error_code: str, retryable: bool) -> Job:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not error_code or len(error_code) > 64 or any(ch not in allowed for ch in error_code):
            error_code = "worker_error"
        with self._pool.connection() as conn:
            row = self._owned_running_job(conn, job_id, worker_id)
            if row["cancel_requested"]:
                status, available_at = "cancelled", row["available_at"]
            elif retryable and row["attempts"] < row["max_attempts"]:
                status, available_at = "queued", time.time() + min(60, 2 ** row["attempts"])
            else:
                status, available_at = "failed", row["available_at"]
            updated = conn.execute(
                """UPDATE jobs SET status=%s, error_code=%s, available_at=%s,
                   lease_owner=NULL, lease_until=NULL, updated_at=now()
                   WHERE job_id=%s RETURNING *""",
                (status, error_code, available_at, job_id),
            ).fetchone()
            if updated is None:
                raise RuntimeError("failed job could not be read back")
            return self._to_job(updated)

    def cancel(self, job_id: str, *, tenant_id: str, subject_id: str) -> Job | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                """SELECT * FROM jobs WHERE job_id=%s AND tenant_id=%s AND subject_id=%s
                   FOR UPDATE""", (job_id, tenant_id, subject_id)
            ).fetchone()
            if row is None:
                return None
            if row["status"] == "queued":
                updated = conn.execute(
                    "UPDATE jobs SET status='cancelled', updated_at=now() WHERE job_id=%s RETURNING *",
                    (job_id,),
                ).fetchone()
            elif row["status"] == "running":
                updated = conn.execute(
                    "UPDATE jobs SET cancel_requested=TRUE, updated_at=now() WHERE job_id=%s RETURNING *",
                    (job_id,),
                ).fetchone()
            else:
                updated = row
            return self._to_job(updated) if updated is not None else None

    def ping(self) -> bool:
        try:
            with self._pool.connection() as conn:
                row = conn.execute("SELECT 1 AS ready").fetchone()
            return row is not None and row["ready"] == 1
        except Exception:
            return False

    def close(self) -> None:
        self._pool.close()
