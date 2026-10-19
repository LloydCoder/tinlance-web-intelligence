"""Durable SQLite usage ledger and atomic quota reservations for development/tests.

Production deployments must use the PostgreSQL implementation. The ledger records
operation facts, not invoices, payment settlement, or authorization decisions.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal


class UsageConflictError(ValueError):
    """An idempotency key was reused with different usage semantics."""


class QuotaExceededError(ValueError):
    """The requested operation would exceed its configured hard quota."""


@dataclass(frozen=True, slots=True)
class UsageReservation:
    reservation_id: str
    tenant_id: str
    subject_id: str
    feature: str
    dimension: str
    period_start: str
    quantity: int
    status: Literal["reserved", "committed", "released"]
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class UsageEvent:
    event_id: str
    tenant_id: str
    subject_id: str
    feature: str
    dimension: str
    period_start: str
    quantity: int
    occurred_at: str
    schema_version: int
    reservation_id: str
    idempotency_key: str


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_key(value: str, label: str, maximum: int = 200) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or len(value) > maximum
    ):
        raise ValueError(f"{label} must be normalized and contain 1 to {maximum} characters")


class SQLiteUsageLedger:
    """Atomic, tenant-scoped usage accounting backed by SQLite transactions.

    SQLite serializes writers with BEGIN IMMEDIATE. Use PostgreSQL for multi-replica
    production workloads; this class is intentionally not a production backend.
    """

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
        self._connection.executescript("""
        CREATE TABLE IF NOT EXISTS twi_usage_reservations (
            reservation_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            feature TEXT NOT NULL,
            dimension TEXT NOT NULL,
            period_start TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            status TEXT NOT NULL CHECK(status IN ('reserved','committed','released')),
            idempotency_key TEXT NOT NULL,
            request_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(tenant_id, subject_id, idempotency_key)
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
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            occurred_at TEXT NOT NULL,
            schema_version INTEGER NOT NULL CHECK(schema_version = 1),
            reservation_id TEXT NOT NULL UNIQUE REFERENCES twi_usage_reservations(reservation_id),
            idempotency_key TEXT NOT NULL,
            UNIQUE(tenant_id, subject_id, idempotency_key)
        );
        CREATE INDEX IF NOT EXISTS twi_usage_events_scope_time_idx
            ON twi_usage_events(tenant_id, subject_id, occurred_at);
        CREATE TRIGGER IF NOT EXISTS twi_usage_events_no_update
            BEFORE UPDATE ON twi_usage_events
            BEGIN SELECT RAISE(ABORT, 'usage events are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS twi_usage_events_no_delete
            BEFORE DELETE ON twi_usage_events
            BEGIN SELECT RAISE(ABORT, 'usage events are append-only'); END;
        """)

    def reserve(
        self, *, tenant_id: str, subject_id: str, feature: str, dimension: str,
        period_start: str, quantity: int, limit: int, idempotency_key: str,
    ) -> UsageReservation:
        for value, label in (
            (tenant_id, "tenant_id"), (subject_id, "subject_id"), (feature, "feature"),
            (dimension, "dimension"), (period_start, "period_start"),
            (idempotency_key, "idempotency_key"),
        ):
            _validate_key(value, label)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("quantity must be a positive integer")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        # Idempotency describes the operation, not the policy snapshot or billing period.
        fingerprint = hashlib.sha256(json.dumps(
            [feature, dimension, quantity], separators=(",", ":"), ensure_ascii=True,
        ).encode()).hexdigest()
        now = _utc_now()
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                existing = self._connection.execute(
                    """SELECT * FROM twi_usage_reservations
                       WHERE tenant_id=? AND subject_id=? AND idempotency_key=?""",
                    (tenant_id, subject_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    if existing["request_fingerprint"] != fingerprint:
                        raise UsageConflictError(
                            "idempotency key reused with different quota request"
                        )
                    if existing["status"] == "released":
                        used = self._connection.execute(
                            """SELECT COALESCE(SUM(quantity), 0) AS quantity
                               FROM twi_usage_reservations
                               WHERE tenant_id=? AND dimension=? AND period_start=?
                                 AND status IN ('reserved','committed')""",
                            (tenant_id, dimension, period_start),
                        ).fetchone()["quantity"]
                        if used + quantity > limit:
                            raise QuotaExceededError("hard quota would be exceeded")
                        self._connection.execute(
                            """UPDATE twi_usage_reservations
                               SET period_start=?, status='reserved', updated_at=?
                               WHERE reservation_id=? AND status='released'""",
                            (period_start, now, existing["reservation_id"]),
                        )
                        existing = self._connection.execute(
                            "SELECT * FROM twi_usage_reservations WHERE reservation_id=?",
                            (existing["reservation_id"],),
                        ).fetchone()
                    self._connection.commit()
                    return self._to_reservation(existing)
                used = self._connection.execute(
                    """SELECT COALESCE(SUM(quantity), 0) AS quantity
                       FROM twi_usage_reservations
                       WHERE tenant_id=? AND dimension=? AND period_start=?
                         AND status IN ('reserved','committed')""",
                    (tenant_id, dimension, period_start),
                ).fetchone()["quantity"]
                if used + quantity > limit:
                    raise QuotaExceededError("hard quota would be exceeded")
                reservation_id = str(uuid.uuid4())
                self._connection.execute(
                    """INSERT INTO twi_usage_reservations
                       (reservation_id,tenant_id,subject_id,feature,dimension,period_start,
                        quantity,status,idempotency_key,request_fingerprint,created_at,updated_at)
                       VALUES (?,?,?,?,?,?,?,'reserved',?,?,?,?)""",
                    (reservation_id,tenant_id,subject_id,feature,dimension,period_start,
                     quantity,idempotency_key,fingerprint,now,now),
                )
                row = self._connection.execute(
                    "SELECT * FROM twi_usage_reservations WHERE reservation_id=?",
                    (reservation_id,),
                ).fetchone()
                self._connection.commit()
                return self._to_reservation(row)
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def commit(self, *, tenant_id: str, subject_id: str, reservation_id: str) -> UsageEvent:
        _validate_key(tenant_id, "tenant_id")
        _validate_key(subject_id, "subject_id")
        _validate_key(reservation_id, "reservation_id")
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                row = self._connection.execute(
                    """SELECT * FROM twi_usage_reservations
                       WHERE reservation_id=? AND tenant_id=? AND subject_id=?""",
                    (reservation_id, tenant_id, subject_id),
                ).fetchone()
                if row is None:
                    raise KeyError("usage reservation not found")
                existing = self._connection.execute(
                    "SELECT * FROM twi_usage_events WHERE reservation_id=?", (reservation_id,)
                ).fetchone()
                if existing is not None:
                    self._connection.commit()
                    return self._to_event(existing)
                if row["status"] != "reserved":
                    raise ValueError("only active reservations can be committed")
                event = UsageEvent(
                    event_id=str(uuid.uuid4()), tenant_id=tenant_id, subject_id=subject_id,
                    feature=row["feature"], dimension=row["dimension"],
                    period_start=row["period_start"], quantity=row["quantity"],
                    occurred_at=_utc_now(), schema_version=1, reservation_id=reservation_id,
                    idempotency_key=row["idempotency_key"],
                )
                self._connection.execute(
                    """INSERT INTO twi_usage_events
                       (event_id,tenant_id,subject_id,feature,dimension,period_start,quantity,
                        occurred_at,schema_version,reservation_id,idempotency_key)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (event.event_id,event.tenant_id,event.subject_id,event.feature,event.dimension,
                     event.period_start,event.quantity,event.occurred_at,event.schema_version,
                     event.reservation_id,event.idempotency_key),
                )
                self._connection.execute(
                    """UPDATE twi_usage_reservations SET status='committed', updated_at=?
                       WHERE reservation_id=? AND status='reserved'""",
                    (_utc_now(), reservation_id),
                )
                self._connection.commit()
                return event
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def release(self, *, tenant_id: str, subject_id: str, reservation_id: str) -> bool:
        """Release only an uncommitted reservation; committed usage is never erased."""
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = self._connection.execute(
                    """UPDATE twi_usage_reservations SET status='released', updated_at=?
                       WHERE reservation_id=? AND tenant_id=? AND subject_id=?
                         AND status='reserved'""",
                    (_utc_now(), reservation_id, tenant_id, subject_id),
                )
                self._connection.commit()
                return cursor.rowcount == 1
            except Exception:
                if self._connection.in_transaction:
                    self._connection.rollback()
                raise

    def usage_total(
        self, *, tenant_id: str, subject_id: str | None, dimension: str, period_start: str
    ) -> int:
        sql = (
            "SELECT COALESCE(SUM(quantity),0) AS quantity FROM twi_usage_events "
            "WHERE tenant_id=? AND dimension=? AND period_start=?"
        )
        parameters: list[str] = [tenant_id, dimension, period_start]
        if subject_id is not None:
            sql += " AND subject_id=?"
            parameters.append(subject_id)
        with self._lock:
            row = self._connection.execute(sql, parameters).fetchone()
        return int(row["quantity"])

    def list_events(
        self, *, tenant_id: str, subject_id: str | None, limit: int = 100,
        dimension: str | None = None, period_start: str | None = None,
        after: tuple[str, str] | None = None,
    ) -> list[UsageEvent]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 501:
            raise ValueError("limit must be between 1 and 501")
        sql = "SELECT * FROM twi_usage_events WHERE tenant_id=?"
        parameters: list[str | int] = [tenant_id]
        if subject_id is not None:
            sql += " AND subject_id=?"
            parameters.append(subject_id)
        if dimension is not None:
            sql += " AND dimension=?"
            parameters.append(dimension)
        if period_start is not None:
            sql += " AND period_start=?"
            parameters.append(period_start)
        if after is not None:
            sql += " AND (occurred_at > ? OR (occurred_at = ? AND event_id > ?))"
            parameters.extend((after[0], after[0], after[1]))
        sql += " ORDER BY occurred_at,event_id LIMIT ?"
        parameters.append(limit)
        with self._lock:
            rows = self._connection.execute(sql, parameters).fetchall()
        return [self._to_event(row) for row in rows]

    @staticmethod
    def _to_reservation(row: sqlite3.Row) -> UsageReservation:
        return UsageReservation(
            reservation_id=row["reservation_id"], tenant_id=row["tenant_id"],
            subject_id=row["subject_id"], feature=row["feature"], dimension=row["dimension"],
            period_start=row["period_start"], quantity=row["quantity"], status=row["status"],
            idempotency_key=row["idempotency_key"],
        )

    @staticmethod
    def _to_event(row: sqlite3.Row) -> UsageEvent:
        return UsageEvent(
            event_id=row["event_id"], tenant_id=row["tenant_id"], subject_id=row["subject_id"],
            feature=row["feature"], dimension=row["dimension"], period_start=row["period_start"],
            quantity=row["quantity"], occurred_at=row["occurred_at"],
            schema_version=row["schema_version"], reservation_id=row["reservation_id"],
            idempotency_key=row["idempotency_key"],
        )

    def close(self) -> None:
        with self._lock:
            self._connection.close()
