"""SQLite monitor persistence for local development and tests."""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import sqlite3
import threading
import uuid

from tinlance_web_intelligence.monitors.model import (
    BaselineConflictError,
    IdempotencyConflictError,
    Monitor,
    MonitorRunResult,
    MonitorRunStatus,
    MonitorStatus,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS monitors (
    monitor_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    target_url TEXT NOT NULL CHECK(length(target_url) BETWEEN 1 AND 4096),
    policy_json TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active', 'paused', 'deleted')),
    baseline_digest TEXT,
    baseline_observed_at TEXT,
    baseline_version INTEGER NOT NULL DEFAULT 0 CHECK(baseline_version >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    UNIQUE(tenant_id, subject_id, idempotency_key),
    CHECK(baseline_digest IS NULL OR (
        length(baseline_digest) = 64 AND baseline_digest NOT GLOB '*[^0-9a-f]*'
    ))
);
CREATE INDEX IF NOT EXISTS monitors_scope_idx ON monitors(tenant_id, subject_id, created_at);
CREATE TABLE IF NOT EXISTS monitor_run_results (
    monitor_id TEXT NOT NULL REFERENCES monitors(monitor_id),
    job_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('succeeded', 'failed')),
    previous_digest TEXT,
    current_digest TEXT,
    changed INTEGER,
    observed_at TEXT NOT NULL,
    changed_units INTEGER NOT NULL CHECK(changed_units BETWEEN 0 AND 10000),
    PRIMARY KEY(monitor_id, job_id)
);
"""


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _dt(value: str | None) -> datetime.datetime | None:
    return datetime.datetime.fromisoformat(value) if value is not None else None


class SQLiteMonitorRepository:
    """Transactional single-process monitor repository."""

    def __init__(self, database_path: str) -> None:
        if not database_path or "\x00" in database_path:
            raise ValueError("database path must be non-empty")
        if database_path != ":memory:":
            pathlib.Path(database_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
        self._lock = threading.RLock()
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

    def create(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        target_url: str,
        policy: dict[str, object],
        idempotency_key: str,
    ) -> Monitor:
        if not tenant_id or not subject_id or not idempotency_key:
            raise ValueError("tenant, subject, and idempotency key are required")
        if not target_url or len(target_url) > 4096 or "\x00" in target_url:
            raise ValueError("target URL must be between 1 and 4096 characters")
        policy_json = json.dumps(policy, sort_keys=True, separators=(",", ":"), allow_nan=False)
        fingerprint = hashlib.sha256(f"{target_url}\0{policy_json}".encode()).hexdigest()
        now = _now()
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    """SELECT * FROM monitors
                       WHERE tenant_id=? AND subject_id=? AND idempotency_key=?""",
                    (tenant_id, subject_id, idempotency_key),
                ).fetchone()
                if row is not None:
                    if row["request_fingerprint"] != fingerprint:
                        raise IdempotencyConflictError(
                            "idempotency key was reused for a different monitor request"
                        )
                    self._connection.commit()
                    return self._to_monitor(row)
                monitor_id = str(uuid.uuid4())
                self._connection.execute(
                    """INSERT INTO monitors (
                        monitor_id, tenant_id, subject_id, target_url, policy_json,
                        request_fingerprint, status, created_at, updated_at, idempotency_key
                    ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
                    (
                        monitor_id,
                        tenant_id,
                        subject_id,
                        target_url,
                        policy_json,
                        fingerprint,
                        now.isoformat(),
                        now.isoformat(),
                        idempotency_key,
                    ),
                )
                row = self._connection.execute(
                    "SELECT * FROM monitors WHERE monitor_id=?", (monitor_id,)
                ).fetchone()
                self._connection.commit()
                return self._to_monitor(row)
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def get(
        self,
        *,
        tenant_id: str,
        subject_id: str | None,
        monitor_id: str,
        administrative: bool = False,
    ) -> Monitor | None:
        if not tenant_id or (subject_id is None and not administrative):
            return None
        with self._lock:
            if administrative:
                row = self._connection.execute(
                    "SELECT * FROM monitors WHERE tenant_id=? AND monitor_id=?",
                    (tenant_id, monitor_id),
                ).fetchone()
            else:
                row = self._connection.execute(
                    "SELECT * FROM monitors WHERE tenant_id=? AND subject_id=? AND monitor_id=?",
                    (tenant_id, subject_id, monitor_id),
                ).fetchone()
        return self._to_monitor(row) if row is not None else None

    def set_status(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        monitor_id: str,
        status: str,
    ) -> Monitor | None:
        try:
            monitor_status = MonitorStatus(status)
        except ValueError as exc:
            raise ValueError("invalid monitor status") from exc
        with self._lock:
            cursor = self._connection.execute(
                """UPDATE monitors SET status=?, updated_at=?
                   WHERE tenant_id=? AND subject_id=? AND monitor_id=?""",
                (monitor_status.value, _now().isoformat(), tenant_id, subject_id, monitor_id),
            )
        return self.get(
            tenant_id=tenant_id, subject_id=subject_id, monitor_id=monitor_id
        ) if cursor.rowcount else None

    def commit_successful_run(
        self,
        *,
        tenant_id: str,
        subject_id: str,
        monitor_id: str,
        expected_baseline_version: int,
        result: MonitorRunResult,
    ) -> Monitor:
        if result.status is not MonitorRunStatus.SUCCEEDED:
            raise ValueError("only successful runs may advance a monitor baseline")
        if result.monitor_id != monitor_id:
            raise ValueError("run result monitor does not match the target monitor")
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    "SELECT * FROM monitors WHERE tenant_id=? AND subject_id=? AND monitor_id=?",
                    (tenant_id, subject_id, monitor_id),
                ).fetchone()
                if row is None:
                    raise KeyError("monitor not found")
                if row["baseline_version"] != expected_baseline_version:
                    raise BaselineConflictError("monitor baseline changed during capture")
                if row["status"] == MonitorStatus.DELETED.value:
                    raise ValueError("deleted monitors cannot advance their baseline")
                self._write_run_result(result)
                self._connection.execute(
                    """UPDATE monitors SET baseline_digest=?, baseline_observed_at=?,
                       baseline_version=baseline_version+1, updated_at=?
                       WHERE monitor_id=?""",
                    (
                        result.current_digest,
                        result.observed_at.isoformat(),
                        _now().isoformat(),
                        monitor_id,
                    ),
                )
                updated = self._connection.execute(
                    "SELECT * FROM monitors WHERE monitor_id=?", (monitor_id,)
                ).fetchone()
                self._connection.commit()
                return self._to_monitor(updated)
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def record_run_result(self, result: MonitorRunResult) -> None:
        with self._lock:
            self._write_run_result(result)

    def _write_run_result(self, result: MonitorRunResult) -> None:
        self._connection.execute(
            """INSERT INTO monitor_run_results (
               monitor_id, job_id, status, previous_digest, current_digest,
               changed, observed_at, changed_units
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(monitor_id, job_id) DO NOTHING""",
            (
                result.monitor_id,
                result.job_id,
                result.status.value,
                result.previous_digest,
                result.current_digest,
                None if result.changed is None else int(result.changed),
                result.observed_at.isoformat(),
                result.changed_units,
            ),
        )

    def metrics_snapshot(self) -> dict[str, float]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT status, count(*) AS count FROM monitors GROUP BY status"
            ).fetchall()
        return {f"monitors_{row['status']}": float(row["count"]) for row in rows}

    def ping(self) -> bool:
        with self._lock:
            return bool(self._connection.execute("SELECT 1").fetchone()[0] == 1)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @staticmethod
    def _to_monitor(row: sqlite3.Row) -> Monitor:
        return Monitor(
            monitor_id=row["monitor_id"],
            tenant_id=row["tenant_id"],
            subject_id=row["subject_id"],
            target_url=row["target_url"],
            policy=json.loads(row["policy_json"]),
            status=MonitorStatus(row["status"]),
            baseline_digest=row["baseline_digest"],
            baseline_observed_at=_dt(row["baseline_observed_at"]),
            baseline_version=row["baseline_version"],
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.datetime.fromisoformat(row["updated_at"]),
            idempotency_key=row["idempotency_key"],
        )
