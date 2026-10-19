"""SQLite durable job repository with tenant scoping, idempotency, leases, and recovery."""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sqlite3
import threading
import time
import typing
import uuid

from tinlance_web_intelligence.jobs.model import (
    IdempotencyConflictError,
    Job,
    JobStatus,
    LeaseLostError,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('search', 'fetch', 'browser')),
    payload_json TEXT NOT NULL,
    payload_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
    ),
    result_json TEXT,
    error_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    available_at REAL NOT NULL,
    lease_owner TEXT,
    lease_until REAL,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    idempotency_key TEXT NOT NULL,
    UNIQUE (tenant_id, subject_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs(status, available_at, created_at);
CREATE INDEX IF NOT EXISTS jobs_tenant_idx ON jobs(tenant_id, subject_id, created_at);
"""

_ALLOWED_ERROR_CODE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-")


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


class SQLiteJobRepository:
    """Single-node durable queue; production multi-replica use is gated on W6 PostgreSQL."""

    def __init__(self, database_path: str, *, max_attempts: int = 3) -> None:
        if not database_path or "\x00" in database_path:
            raise ValueError("database path must be non-empty")
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        if database_path != ":memory:":
            pathlib.Path(database_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
        self._lock = threading.RLock()
        self._max_attempts = max_attempts
        self._connection = sqlite3.connect(
            database_path, timeout=5.0, check_same_thread=False, isolation_level=None
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if database_path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.executescript(_SCHEMA)
        self._migrate_browser_job_kind()

    def _migrate_browser_job_kind(self) -> None:
        """Transactionally rebuild a W3 schema to permit browser jobs."""
        row = self._connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='jobs'"
        ).fetchone()
        if row is None or "'browser'" in (row["sql"] or ""):
            return
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute("DROP INDEX IF EXISTS jobs_claim_idx")
                self._connection.execute("DROP INDEX IF EXISTS jobs_tenant_idx")
                self._connection.execute("ALTER TABLE jobs RENAME TO jobs_w3_migration")
                self._connection.execute(
                    """CREATE TABLE jobs (
                        job_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        subject_id TEXT NOT NULL,
                        kind TEXT NOT NULL CHECK (kind IN ('search', 'fetch', 'browser')),
                        payload_json TEXT NOT NULL,
                        payload_fingerprint TEXT NOT NULL,
                        status TEXT NOT NULL CHECK (
                            status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
                        ),
                        result_json TEXT,
                        error_code TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 3,
                        available_at REAL NOT NULL,
                        lease_owner TEXT,
                        lease_until REAL,
                        cancel_requested INTEGER NOT NULL DEFAULT 0,
                        idempotency_key TEXT NOT NULL,
                        UNIQUE (tenant_id, subject_id, idempotency_key)
                    )"""
                )
                self._connection.execute("INSERT INTO jobs SELECT * FROM jobs_w3_migration")
                self._connection.execute("DROP TABLE jobs_w3_migration")
                self._connection.execute(
                    "CREATE INDEX jobs_claim_idx ON jobs(status, available_at, created_at)"
                )
                self._connection.execute(
                    "CREATE INDEX jobs_tenant_idx ON jobs(tenant_id, subject_id, created_at)"
                )
                self._connection.commit()
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def create(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        kind: str,
        payload: dict[str, typing.Any],
        idempotency_key: str,
    ) -> Job:
        if kind not in {"search", "fetch", "browser"}:
            raise ValueError("unsupported job kind")
        if not tenant_id or not subject_id or not idempotency_key:
            raise ValueError("tenant, subject, and idempotency key are required")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        fingerprint = hashlib.sha256(f"{kind}\0{serialized}".encode()).hexdigest()
        now = _now()
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                existing = self._connection.execute(
                    "SELECT * FROM jobs WHERE tenant_id=? AND subject_id=? AND idempotency_key=?",
                    (tenant_id, subject_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    if existing["payload_fingerprint"] != fingerprint:
                        raise IdempotencyConflictError(
                            "idempotency key was reused for a different request"
                        )
                    self._connection.commit()
                    return self._to_job(existing)
                job_id = str(uuid.uuid4())
                self._connection.execute(
                    """INSERT INTO jobs (
                        job_id, tenant_id, subject_id, kind, payload_json, payload_fingerprint,
                        status, created_at, updated_at, attempts, max_attempts, available_at,
                        idempotency_key
                    ) VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?, 0, ?, ?, ?)""",
                    (
                        job_id,
                        tenant_id,
                        subject_id,
                        kind,
                        serialized,
                        fingerprint,
                        now,
                        now,
                        self._max_attempts,
                        time.time(),
                        idempotency_key,
                    ),
                )
                row = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                self._connection.commit()
                if row is None:
                    raise RuntimeError("created job could not be read back")
                return self._to_job(row)
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def get(
        self, job_id: str, *, tenant_id: str, subject_id: str | None = None
    ) -> Job | None:
        with self._lock:
            if subject_id is None:
                row = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=? AND tenant_id=?", (job_id, tenant_id)
                ).fetchone()
            else:
                row = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=? AND tenant_id=? AND subject_id=?",
                    (job_id, tenant_id, subject_id),
                ).fetchone()
        return self._to_job(row) if row is not None else None

    def claim_next(
        self,
        worker_id: str,
        *,
        lease_seconds: int = 60,
        allowed_kinds: tuple[str, ...] | None = None,
    ) -> Job | None:
        if not worker_id or not 5 <= lease_seconds <= 3600:
            raise ValueError("worker ID and a 5–3600 second lease are required")
        if allowed_kinds is not None and (
            not allowed_kinds
            or len(allowed_kinds) > 3
            or len(set(allowed_kinds)) != len(allowed_kinds)
            or any(kind not in {"search", "fetch", "browser"} for kind in allowed_kinds)
        ):
            raise ValueError("allowed_kinds must contain unique supported job kinds")
        now = time.time()
        timestamp = _now()
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute(
                    """UPDATE jobs SET status='cancelled', lease_owner=NULL,
                        lease_until=NULL, updated_at=?
                        WHERE status='running' AND lease_until < ? AND cancel_requested=1""",
                    (timestamp, now),
                )
                self._connection.execute(
                    """UPDATE jobs SET status='failed', error_code='lease_expired',
                        lease_owner=NULL, lease_until=NULL, updated_at=?
                        WHERE status='running' AND lease_until < ? AND attempts >= max_attempts""",
                    (timestamp, now),
                )
                self._connection.execute(
                    """UPDATE jobs SET status='queued', lease_owner=NULL, lease_until=NULL,
                        available_at=?, updated_at=?
                        WHERE status='running' AND lease_until < ? AND attempts < max_attempts""",
                    (now, timestamp, now),
                )
                query_all = (
                    """SELECT * FROM jobs
                       WHERE status='queued' AND available_at <= ?
                         AND cancel_requested=0
                       ORDER BY created_at, job_id LIMIT 1"""
                )
                query_by_kind = {
                    1: """SELECT * FROM jobs
                          WHERE status='queued' AND available_at <= ?
                            AND cancel_requested=0 AND kind IN (?)
                          ORDER BY created_at, job_id LIMIT 1""",
                    2: """SELECT * FROM jobs
                          WHERE status='queued' AND available_at <= ?
                            AND cancel_requested=0 AND kind IN (?, ?)
                          ORDER BY created_at, job_id LIMIT 1""",
                    3: """SELECT * FROM jobs
                          WHERE status='queued' AND available_at <= ?
                            AND cancel_requested=0 AND kind IN (?, ?, ?)
                          ORDER BY created_at, job_id LIMIT 1""",
                }
                if allowed_kinds is None:
                    query = query_all
                    params: tuple[object, ...] = (now,)
                else:
                    query = query_by_kind[len(allowed_kinds)]
                    params = (now, *allowed_kinds)
                row = self._connection.execute(query, params).fetchone()
                if row is None:
                    self._connection.commit()
                    return None
                job_id = row["job_id"]
                self._connection.execute(
                    """UPDATE jobs SET status='running', attempts=attempts+1,
                        lease_owner=?, lease_until=?, updated_at=?
                        WHERE job_id=? AND status='queued'""",
                    (worker_id, now + lease_seconds, timestamp, job_id),
                )
                claimed = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                self._connection.commit()
                return self._to_job(claimed) if claimed is not None else None
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def complete(
        self, job_id: str, worker_id: str, result: dict[str, typing.Any]
    ) -> Job:
        serialized = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._owned_running_job(job_id, worker_id)
                status = "cancelled" if row["cancel_requested"] else "succeeded"
                self._connection.execute(
                    """UPDATE jobs SET status=?, result_json=?, lease_owner=NULL,
                        lease_until=NULL, updated_at=? WHERE job_id=?""",
                    (status, None if status == "cancelled" else serialized, _now(), job_id),
                )
                updated = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                self._connection.commit()
                if updated is None:
                    raise RuntimeError("completed job could not be read back")
                return self._to_job(updated)
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def fail(
        self,
        job_id: str,
        worker_id: str,
        *,
        error_code: str,
        retryable: bool,
    ) -> Job:
        invalid_code = (
            not error_code
            or len(error_code) > 64
            or any(ch not in _ALLOWED_ERROR_CODE_CHARS for ch in error_code)
        )
        if invalid_code:
            error_code = "worker_error"
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._owned_running_job(job_id, worker_id)
                if row["cancel_requested"]:
                    status, available_at = "cancelled", row["available_at"]
                elif retryable and row["attempts"] < row["max_attempts"]:
                    status = "queued"
                    available_at = time.time() + min(60, 2 ** row["attempts"])
                else:
                    status, available_at = "failed", row["available_at"]
                self._connection.execute(
                    """UPDATE jobs SET status=?, error_code=?, available_at=?, lease_owner=NULL,
                        lease_until=NULL, updated_at=? WHERE job_id=?""",
                    (status, error_code, available_at, _now(), job_id),
                )
                updated = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                self._connection.commit()
                if updated is None:
                    raise RuntimeError("failed job could not be read back")
                return self._to_job(updated)
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def cancel(
        self, job_id: str, *, tenant_id: str, subject_id: str
    ) -> Job | None:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=? AND tenant_id=? AND subject_id=?",
                    (job_id, tenant_id, subject_id),
                ).fetchone()
                if row is None:
                    self._connection.commit()
                    return None
                status = row["status"]
                if status == "queued":
                    self._connection.execute(
                        "UPDATE jobs SET status='cancelled', updated_at=? WHERE job_id=?",
                        (_now(), job_id),
                    )
                elif status == "running":
                    self._connection.execute(
                        "UPDATE jobs SET cancel_requested=1, updated_at=? WHERE job_id=?",
                        (_now(), job_id),
                    )
                updated = self._connection.execute(
                    "SELECT * FROM jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                self._connection.commit()
                return self._to_job(updated) if updated is not None else None
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def metrics_snapshot(self) -> dict[str, float]:
        """Return low-cardinality queue counts and oldest queued-job age."""
        with self._lock:
            counts = self._connection.execute(
                "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
            ).fetchall()
            oldest = self._connection.execute(
                "SELECT MIN(created_at) AS created_at FROM jobs WHERE status='queued'"
            ).fetchone()
        snapshot = {
            f"jobs_{status}": 0.0
            for status in ("queued", "running", "succeeded", "failed", "cancelled")
        }
        for row in counts:
            snapshot[f"jobs_{row['status']}"] = float(row["count"])
        created_at = oldest["created_at"] if oldest is not None else None
        age_seconds = 0.0
        if isinstance(created_at, str):
            created = datetime.datetime.fromisoformat(created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=datetime.UTC)
            age_seconds = max(
                0.0, (datetime.datetime.now(datetime.UTC) - created).total_seconds()
            )
        snapshot["jobs_oldest_queued_age_seconds"] = age_seconds
        return snapshot

    def ping(self) -> bool:
        with self._lock:
            row = self._connection.execute("SELECT 1 AS ready").fetchone()
        return row is not None and row["ready"] == 1

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _owned_running_job(self, job_id: str, worker_id: str) -> sqlite3.Row:
        row = typing.cast(
            sqlite3.Row | None,
            self._connection.execute(
                "SELECT * FROM jobs WHERE job_id=? AND status='running' AND lease_owner=?",
                (job_id, worker_id),
            ).fetchone(),
        )
        if row is None:
            raise LeaseLostError("worker no longer owns the running job")
        return row

    @staticmethod
    def _to_job(row: sqlite3.Row) -> Job:
        result_value = json.loads(row["result_json"]) if row["result_json"] else None
        result = result_value if isinstance(result_value, dict) else None
        payload_value = json.loads(row["payload_json"])
        if not isinstance(payload_value, dict):
            raise RuntimeError("stored job payload is not an object")
        return Job(
            job_id=row["job_id"],
            tenant_id=row["tenant_id"],
            subject_id=row["subject_id"],
            kind=row["kind"],
            payload=payload_value,
            status=JobStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            result=result,
            error_code=row["error_code"],
            cancel_requested=bool(row["cancel_requested"]),
            idempotency_key=row["idempotency_key"],
        )
