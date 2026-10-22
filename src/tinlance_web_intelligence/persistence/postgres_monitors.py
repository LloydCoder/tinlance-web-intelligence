"""PostgreSQL-backed tenant-scoped monitor repository."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from psycopg import Connection
from psycopg.types.json import Jsonb

from tinlance_web_intelligence.persistence.postgres_pool import (
    acquire_pool,
    release_pool,
)

from tinlance_web_intelligence.monitors.model import (
    BaselineConflictError,
    IdempotencyConflictError,
    Monitor,
    MonitorRunResult,
    MonitorRunStatus,
    MonitorStatus,
    normalize_monitor_policy,
)


class PostgresMonitorRepository:
    """Multi-process monitor storage with transactional baseline compare-and-set."""

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 10) -> None:
        if not dsn or not dsn.strip() or dsn != dsn.strip():
            raise ValueError("PostgreSQL DSN must be non-empty and normalized")
        if not 1 <= min_size <= max_size <= 50:
            raise ValueError("invalid PostgreSQL pool configuration")
        self._pool = acquire_pool(dsn, min_size=min_size, max_size=max_size)
        try:
            self._verify_schema()
        except Exception:
            release_pool(self._pool)
            raise

    def _verify_schema(self) -> None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT to_regclass('twi_monitors') AS monitors, "
                "to_regclass('twi_monitor_run_results') AS runs"
            ).fetchone()
            version = conn.execute(
                "SELECT max(version) AS version FROM twi_schema_migrations"
            ).fetchone()
            if (
                row is None
                or row["monitors"] is None
                or row["runs"] is None
                or version is None
                or version["version"] < 3
            ):
                raise RuntimeError("PostgreSQL monitor schema is missing; run the migration job")

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
        normalized_policy = normalize_monitor_policy(policy)
        policy_json = json.dumps(
            normalized_policy, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        fingerprint = hashlib.sha256(f"{target_url}\0{policy_json}".encode()).hexdigest()
        monitor_id = str(uuid.uuid4())
        with self._pool.connection() as conn:
            row = conn.execute(
                """INSERT INTO twi_monitors (
                    monitor_id, tenant_id, subject_id, target_url, policy_json,
                    request_fingerprint, status, idempotency_key
                ) VALUES (%s, %s, %s, %s, %s, %s, 'active', %s)
                ON CONFLICT (tenant_id, subject_id, idempotency_key) DO NOTHING
                RETURNING *""",
                (
                    monitor_id,
                    tenant_id,
                    subject_id,
                    target_url,
                    Jsonb(normalized_policy),
                    fingerprint,
                    idempotency_key,
                ),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    """SELECT * FROM twi_monitors
                       WHERE tenant_id=%s AND subject_id=%s AND idempotency_key=%s""",
                    (tenant_id, subject_id, idempotency_key),
                ).fetchone()
                if row is None:
                    raise RuntimeError("idempotent monitor could not be resolved")
                if row["request_fingerprint"].strip() != fingerprint:
                    raise IdempotencyConflictError(
                        "idempotency key was reused for a different monitor request"
                    )
        return self._to_monitor(row)

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
        sql = "SELECT * FROM twi_monitors WHERE tenant_id=%s AND monitor_id=%s"
        params: tuple[Any, ...] = (tenant_id, monitor_id)
        if not administrative:
            sql += " AND subject_id=%s"
            params += (subject_id,)
        with self._pool.connection() as conn:
            row = conn.execute(sql, params).fetchone()
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
        with self._pool.connection() as conn:
            row = conn.execute(
                """UPDATE twi_monitors SET status=%s, updated_at=now()
                   WHERE tenant_id=%s AND subject_id=%s AND monitor_id=%s
                   RETURNING *""",
                (monitor_status.value, tenant_id, subject_id, monitor_id),
            ).fetchone()
        return self._to_monitor(row) if row is not None else None

    def redact(self, *, tenant_id: str, subject_id: str, monitor_id: str) -> Monitor | None:
        fingerprint = hashlib.sha256(b"twi-deleted-monitor-v1").hexdigest()
        with self._pool.connection() as conn:
            row = conn.execute(
                """UPDATE twi_monitors SET target_url='https://deleted.invalid/',
                       policy_json='{}', request_fingerprint=%s, status='deleted',
                       baseline_digest=NULL, baseline_observed_at=NULL,
                       baseline_version=baseline_version+1, updated_at=now()
                   WHERE tenant_id=%s AND subject_id=%s AND monitor_id=%s
                   RETURNING *""",
                (fingerprint, tenant_id, subject_id, monitor_id),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "DELETE FROM twi_monitor_run_results WHERE monitor_id=%s", (monitor_id,)
            )
        return self._to_monitor(row)

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
        with self._pool.connection() as conn:
            current = conn.execute(
                """SELECT status FROM twi_monitors
                   WHERE tenant_id=%s AND subject_id=%s AND monitor_id=%s FOR UPDATE""",
                (tenant_id, subject_id, monitor_id),
            ).fetchone()
            if current is None:
                raise KeyError("monitor not found")
            if current["status"] == MonitorStatus.DELETED.value:
                raise ValueError("deleted monitors cannot advance their baseline")
            self._write_run_result(conn, result)
            row = conn.execute(
                """UPDATE twi_monitors SET baseline_digest=%s, baseline_observed_at=%s,
                       baseline_version=baseline_version+1, updated_at=now()
                   WHERE tenant_id=%s AND subject_id=%s AND monitor_id=%s
                     AND baseline_version=%s
                   RETURNING *""",
                (
                    result.current_digest,
                    result.observed_at,
                    tenant_id,
                    subject_id,
                    monitor_id,
                    expected_baseline_version,
                ),
            ).fetchone()
            if row is None:
                raise BaselineConflictError("monitor baseline changed during capture")
        return self._to_monitor(row)

    def record_run_result(self, result: MonitorRunResult) -> None:
        with self._pool.connection() as conn:
            self._write_run_result(conn, result)

    @staticmethod
    def _write_run_result(
        conn: Connection[dict[str, Any]], result: MonitorRunResult
    ) -> None:
        conn.execute(
            """INSERT INTO twi_monitor_run_results (
                   monitor_id, job_id, status, previous_digest, current_digest,
                   changed, observed_at, changed_units
               ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (monitor_id, job_id) DO NOTHING""",
            (
                result.monitor_id,
                result.job_id,
                result.status.value,
                result.previous_digest,
                result.current_digest,
                result.changed,
                result.observed_at,
                result.changed_units,
            ),
        )

    def metrics_snapshot(self) -> dict[str, float]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT status, count(*) AS count FROM twi_monitors GROUP BY status"
            ).fetchall()
        return {f"monitors_{row['status']}": float(row["count"]) for row in rows}

    def ping(self) -> bool:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT 1 AS ok").fetchone()
            return bool(row is not None and row["ok"] == 1)

    def close(self) -> None:
        release_pool(self._pool)

    @staticmethod
    def _to_monitor(row: dict[str, Any]) -> Monitor:
        policy = row["policy_json"]
        if isinstance(policy, str):
            policy = json.loads(policy)
        if not isinstance(policy, dict):
            raise RuntimeError("stored monitor policy JSON has an invalid shape")
        return Monitor(
            monitor_id=row["monitor_id"],
            tenant_id=row["tenant_id"],
            subject_id=row["subject_id"],
            target_url=row["target_url"],
            policy=policy,
            status=MonitorStatus(row["status"]),
            baseline_digest=row["baseline_digest"].strip()
            if row["baseline_digest"] is not None
            else None,
            baseline_observed_at=row["baseline_observed_at"],
            baseline_version=int(row["baseline_version"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            idempotency_key=row["idempotency_key"],
        )
