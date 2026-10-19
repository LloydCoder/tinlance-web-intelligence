"""Tenant-scoped durable change detection and retryable monitoring-event outbox."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ERROR_CODE = re.compile(r"^[a-z0-9_]{1,64}$")


class MonitoringLeaseLostError(RuntimeError):
    """Raised when a worker attempts to acknowledge an event after losing its lease."""


@dataclass(frozen=True, slots=True)
class MonitoringObservation:
    """Sanitized result of recording one source observation."""

    change_kind: str
    revision: int
    event_id: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class MonitoringEvent:
    """Claimed outbox event; payload contains fingerprints and metadata, never page content."""

    event_id: str
    tenant_id: str
    source_fingerprint: str
    idempotency_key: str
    payload: dict[str, Any]
    payload_sha256: str
    attempts: int


def _validate_tenant_id(tenant_id: str) -> None:
    if (
        not isinstance(tenant_id, str)
        or not tenant_id
        or tenant_id != tenant_id.strip()
        or "\x00" in tenant_id
        or len(tenant_id) > 256
    ):
        raise ValueError("tenant_id must be normalized and contain 1 to 256 characters")


def _validate_digest(value: str, field: str) -> None:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _validate_content_type(content_type: str) -> None:
    if (
        not isinstance(content_type, str)
        or not content_type
        or len(content_type) > 255
        or content_type != content_type.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in content_type)
    ):
        raise ValueError("content_type must contain 1 to 255 normalized printable characters")


def _validate_observed_at(observed_at: datetime) -> datetime:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    return observed_at.astimezone(UTC)


class PostgresMonitoringRepository:
    """Persist source state and change events with tenant isolation and retry-safe leases."""

    def __init__(self, dsn: str) -> None:
        if not dsn or dsn != dsn.strip():
            raise ValueError("PostgreSQL DSN must be non-empty and normalized")
        self._pool = ConnectionPool[Connection[dict[str, Any]]](
            conninfo=dsn,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
            timeout=10,
            open=True,
        )
        self._pool.wait(timeout=10)
        try:
            with self._pool.connection() as conn:
                row = conn.execute(
                    "SELECT to_regclass('twi_monitoring_state') AS state, "
                    "to_regclass('twi_monitoring_events') AS events"
                ).fetchone()
                if row is None or row["state"] is None or row["events"] is None:
                    raise RuntimeError("monitoring schema is missing; run the migration job")
        except Exception:
            self._pool.close()
            raise

    @staticmethod
    def _classify(previous: Mapping[str, Any], current: Mapping[str, Any]) -> str:
        changes = []
        if previous["content_sha256"].strip() != current["content_sha256"]:
            changes.append("content")
        if previous["status_code"] != current["status_code"]:
            changes.append("status")
        if previous["content_type"] != current["content_type"]:
            changes.append("content_type")
        if len(changes) > 1:
            return "multiple_changes"
        if changes == ["content"]:
            return "content_changed"
        if changes == ["status"]:
            return "status_changed"
        if changes == ["content_type"]:
            return "content_type_changed"
        return "unchanged"

    def observe(
        self,
        *,
        tenant_id: str,
        source_fingerprint: str,
        content_sha256: str,
        status_code: int,
        content_type: str,
        observed_at: datetime,
    ) -> MonitoringObservation:
        """Persist an observation; older observations cannot overwrite newer state."""
        _validate_tenant_id(tenant_id)
        _validate_digest(source_fingerprint, "source_fingerprint")
        _validate_digest(content_sha256, "content_sha256")
        if type(status_code) is not int or not 100 <= status_code <= 599:
            raise ValueError("status_code must be an integer between 100 and 599")
        _validate_content_type(content_type)
        timestamp = _validate_observed_at(observed_at)
        current: dict[str, Any] = {
            "content_sha256": content_sha256,
            "status_code": status_code,
            "content_type": content_type,
        }
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT content_sha256, status_code, content_type, last_observed_at, revision "
                "FROM twi_monitoring_state WHERE tenant_id=%s AND source_fingerprint=%s FOR UPDATE",
                (tenant_id, source_fingerprint),
            ).fetchone()
            if row is None:
                inserted = conn.execute(
                    "INSERT INTO twi_monitoring_state "
                    "(tenant_id, source_fingerprint, content_sha256, status_code, content_type, "
                    "last_observed_at) VALUES (%s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (tenant_id, source_fingerprint) DO NOTHING RETURNING revision",
                    (
                        tenant_id,
                        source_fingerprint,
                        content_sha256,
                        status_code,
                        content_type,
                        timestamp,
                    ),
                ).fetchone()
                if inserted is not None:
                    return MonitoringObservation("baseline", int(inserted["revision"]))
                row = conn.execute(
                    "SELECT content_sha256, status_code, content_type, last_observed_at, revision "
                    "FROM twi_monitoring_state WHERE tenant_id=%s AND source_fingerprint=%s FOR UPDATE",
                    (tenant_id, source_fingerprint),
                ).fetchone()
                if row is None:
                    raise RuntimeError("monitoring state insert raced but state row is missing")
            previous = {
                "content_sha256": row["content_sha256"].strip(),
                "status_code": row["status_code"],
                "content_type": row["content_type"],
            }
            previous_at = row["last_observed_at"]
            if timestamp <= previous_at:
                if self._classify(previous, current) == "unchanged":
                    return MonitoringObservation("unchanged", int(row["revision"]))
                return MonitoringObservation("out_of_order", int(row["revision"]))
            change_kind = self._classify(previous, current)
            if change_kind == "unchanged":
                conn.execute(
                    "UPDATE twi_monitoring_state SET last_observed_at=%s, updated_at=now() "
                    "WHERE tenant_id=%s AND source_fingerprint=%s",
                    (timestamp, tenant_id, source_fingerprint),
                )
                return MonitoringObservation("unchanged", int(row["revision"]))
            event_basis = {
                "tenant_id": tenant_id,
                "source_fingerprint": source_fingerprint,
                "previous": previous,
                "current": current,
                "observed_at": timestamp.isoformat(),
            }
            idempotency_key = hashlib.sha256(
                json.dumps(event_basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            event_id = f"monitoring-change-{idempotency_key}"
            payload: dict[str, Any] = {
                "schema_version": "1.0.0",
                "source_fingerprint": source_fingerprint,
                "change_kind": change_kind,
                "previous_sha256": previous["content_sha256"],
                "current_sha256": content_sha256,
                "previous_status_code": previous["status_code"],
                "current_status_code": status_code,
                "previous_content_type": previous["content_type"],
                "current_content_type": content_type,
                "observed_at": timestamp.isoformat(),
            }
            payload_bytes = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
            payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
            conn.execute(
                "INSERT INTO twi_monitoring_events "
                "(event_id, tenant_id, source_fingerprint, idempotency_key, change_kind, "
                "previous_sha256, current_sha256, previous_status_code, current_status_code, "
                "previous_content_type, current_content_type, payload_json, payload_sha256, "
                "status, available_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s) "
                "ON CONFLICT (tenant_id, idempotency_key) DO NOTHING",
                (
                    event_id,
                    tenant_id,
                    source_fingerprint,
                    idempotency_key,
                    change_kind,
                    previous["content_sha256"],
                    content_sha256,
                    previous["status_code"],
                    status_code,
                    previous["content_type"],
                    content_type,
                    Jsonb(payload),
                    payload_sha256,
                    timestamp.timestamp(),
                ),
            )
            revision = int(row["revision"]) + 1
            conn.execute(
                "UPDATE twi_monitoring_state SET content_sha256=%s, status_code=%s, "
                "content_type=%s, last_observed_at=%s, revision=%s, updated_at=now() "
                "WHERE tenant_id=%s AND source_fingerprint=%s",
                (
                    content_sha256,
                    status_code,
                    content_type,
                    timestamp,
                    revision,
                    tenant_id,
                    source_fingerprint,
                ),
            )
            return MonitoringObservation(change_kind, revision, event_id, idempotency_key)

    def claim_pending_events(
        self,
        worker_id: str,
        *,
        limit: int = 10,
        lease_seconds: int = 60,
        max_attempts: int = 5,
        now: datetime | None = None,
    ) -> tuple[MonitoringEvent, ...]:
        """Claim pending events with SKIP LOCKED so parallel workers do not double-deliver."""
        if not worker_id or worker_id != worker_id.strip() or len(worker_id) > 128:
            raise ValueError("worker_id must be normalized and contain 1 to 128 characters")
        if not 1 <= limit <= 100 or not 5 <= lease_seconds <= 3600 or not 1 <= max_attempts <= 20:
            raise ValueError("invalid monitoring claim limits")
        current = _validate_observed_at(now or datetime.now(UTC))
        with self._pool.connection() as conn:
            rows = conn.execute(
                "WITH candidates AS ("
                " SELECT event_id FROM twi_monitoring_events "
                " WHERE ((status='pending' AND available_at <= %s) "
                " OR (status='delivering' AND lease_until < %s)) AND attempts < %s "
                " ORDER BY created_at, event_id LIMIT %s FOR UPDATE SKIP LOCKED"
                ") UPDATE twi_monitoring_events AS event SET status='delivering', "
                " attempts=event.attempts+1, lease_owner=%s, lease_until=%s, updated_at=%s "
                "FROM candidates WHERE event.event_id=candidates.event_id "
                "RETURNING event.event_id, event.tenant_id, event.source_fingerprint, "
                "event.idempotency_key, event.payload_json, event.payload_sha256, event.attempts",
                (
                    current.timestamp(),
                    current.timestamp(),
                    max_attempts,
                    limit,
                    worker_id,
                    current.timestamp() + lease_seconds,
                    current,
                ),
            ).fetchall()
        events = []
        for row in rows:
            payload = row["payload_json"]
            if not isinstance(payload, dict):
                raise RuntimeError("monitoring event payload has an invalid shape")
            canonical = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
            digest = hashlib.sha256(canonical).hexdigest()
            if digest != row["payload_sha256"].strip():
                raise RuntimeError("monitoring event payload failed SHA-256 integrity verification")
            events.append(
                MonitoringEvent(
                    event_id=row["event_id"],
                    tenant_id=row["tenant_id"],
                    source_fingerprint=row["source_fingerprint"].strip(),
                    idempotency_key=row["idempotency_key"].strip(),
                    payload=payload,
                    payload_sha256=digest,
                    attempts=int(row["attempts"]),
                )
            )
        return tuple(events)

    def mark_delivered(self, event_id: str, worker_id: str, *, now: datetime | None = None) -> None:
        current = _validate_observed_at(now or datetime.now(UTC))
        with self._pool.connection() as conn:
            result = conn.execute(
                "UPDATE twi_monitoring_events SET status='delivered', lease_owner=NULL, "
                "lease_until=NULL, delivered_at=%s, updated_at=%s "
                "WHERE event_id=%s AND status='delivering' AND lease_owner=%s "
                "AND lease_until >= %s",
                (current, current, event_id, worker_id, current.timestamp()),
            )
            if result.rowcount != 1:
                raise MonitoringLeaseLostError("monitoring event lease is no longer owned")

    def retry_event(
        self,
        event_id: str,
        worker_id: str,
        *,
        error_code: str,
        delay_seconds: int = 30,
        max_attempts: int = 5,
        now: datetime | None = None,
    ) -> str:
        """Release a lease with bounded backoff; terminal failures remain inspectable."""
        if not isinstance(error_code, str) or _ERROR_CODE.fullmatch(error_code) is None:
            raise ValueError("error_code must be a normalized low-cardinality code")
        if not 0 <= delay_seconds <= 86400 or not 1 <= max_attempts <= 20:
            raise ValueError("invalid retry policy")
        current = _validate_observed_at(now or datetime.now(UTC))
        with self._pool.connection() as conn:
            row = conn.execute(
                "UPDATE twi_monitoring_events SET "
                "status=CASE WHEN attempts >= %s THEN 'failed' ELSE 'pending' END, "
                "available_at=%s, lease_owner=NULL, lease_until=NULL, last_error_code=%s, "
                "updated_at=%s WHERE event_id=%s AND status='delivering' AND lease_owner=%s "
                "AND lease_until >= %s RETURNING status",
                (
                    max_attempts,
                    current.timestamp() + delay_seconds,
                    error_code,
                    current,
                    event_id,
                    worker_id,
                    current.timestamp(),
                ),
            ).fetchone()
            if row is None:
                raise MonitoringLeaseLostError("monitoring event lease is no longer owned")
            return str(row["status"])

    def metrics_snapshot(self, *, now: datetime | None = None) -> dict[str, float]:
        """Return low-cardinality monitoring backlog metrics without tenant/source labels."""
        current = _validate_observed_at(now or datetime.now(UTC))
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM twi_monitoring_events GROUP BY status"
            ).fetchall()
            oldest = conn.execute(
                "SELECT GREATEST(0, %s - MIN(available_at)) AS age_seconds "
                "FROM twi_monitoring_events WHERE status='pending'",
                (current.timestamp(),),
            ).fetchone()
        result = {
            f"monitoring_events_{status}": 0.0
            for status in ("pending", "delivering", "delivered", "failed")
        }
        for row in rows:
            result[f"monitoring_events_{row['status']}"] = float(row["count"])
        age = oldest["age_seconds"] if oldest is not None else None
        result["monitoring_events_oldest_pending_age_seconds"] = float(age or 0.0)
        return result

    def close(self) -> None:
        self._pool.close()
