"""Durable, payload-free inbox for verified provider billing events."""
from __future__ import annotations

import pathlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from tinlance_web_intelligence.commercial.billing_events import VerifiedBillingEvent
from tinlance_web_intelligence.commercial.usage_ledger import _validate_key
from tinlance_web_intelligence.persistence.postgres_pool import (
    acquire_pool,
    release_pool,
)


class BillingEventReceiptConflict(ValueError):
    """A provider reused an event ID with different verified payload bytes."""


@dataclass(frozen=True, slots=True)
class BillingEventReceipt:
    provider_key: str
    event_id: str
    event_type: str
    occurred_at: str
    payload_sha256: str
    status: Literal["received", "processed", "failed", "ignored"]
    attempts: int
    last_error_code: str | None


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _receipt(row: Any) -> BillingEventReceipt:
    occurred_at = row["occurred_at"]
    return BillingEventReceipt(
        provider_key=row["provider_key"],
        event_id=row["event_id"],
        event_type=row["event_type"],
        occurred_at=(
            occurred_at.isoformat()
            if hasattr(occurred_at, "isoformat")
            else str(occurred_at)
        ),
        payload_sha256=row["payload_sha256"].strip(),
        status=row["status"],
        attempts=int(row["attempts"]),
        last_error_code=row["last_error_code"],
    )


class SQLiteBillingEventInbox:
    """Single-node/dev inbox. Use PostgreSQL for deployed multi-replica operation."""

    def __init__(self, database_path: str) -> None:
        if not database_path or "\x00" in database_path:
            raise ValueError("database path must be non-empty")
        if database_path != ":memory:":
            pathlib.Path(database_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
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
        CREATE TABLE IF NOT EXISTS twi_billing_event_receipts (
            provider_key TEXT NOT NULL,
            event_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL CHECK(length(payload_sha256)=64),
            status TEXT NOT NULL CHECK(status IN ('received','processed','failed','ignored')),
            attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts >= 0),
            last_error_code TEXT,
            PRIMARY KEY(provider_key,event_id)
        );
        CREATE INDEX IF NOT EXISTS twi_billing_event_receipts_status_idx
            ON twi_billing_event_receipts(status, received_at);
        """)

    def record(
        self, *, provider_key: str, event: VerifiedBillingEvent
    ) -> tuple[BillingEventReceipt, bool]:
        _validate_key(provider_key, "provider_key")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._connection.execute(
                """SELECT * FROM twi_billing_event_receipts
                   WHERE provider_key=? AND event_id=?""",
                (provider_key, event.event_id),
            ).fetchone()
            if row is not None:
                if row["payload_sha256"] != event.payload_sha256:
                    raise BillingEventReceiptConflict(
                        "provider event ID was reused with different payload bytes"
                    )
                self._connection.commit()
                return _receipt(row), True
            self._connection.execute(
                """INSERT INTO twi_billing_event_receipts
                   (provider_key,event_id,event_type,occurred_at,received_at,payload_sha256,status)
                   VALUES (?,?,?,?,?,?,'received')""",
                (provider_key,event.event_id,event.event_type,event.occurred_at,_now(),
                 event.payload_sha256),
            )
            row = self._connection.execute(
                """SELECT * FROM twi_billing_event_receipts
                   WHERE provider_key=? AND event_id=?""",
                (provider_key, event.event_id),
            ).fetchone()
            if row is None:
                raise RuntimeError("billing receipt could not be read after insert")
            self._connection.commit()
            return _receipt(row), False
        except Exception:
            if self._connection.in_transaction:
                self._connection.rollback()
            raise

    def mark_processed(self, *, provider_key: str, event_id: str) -> BillingEventReceipt:
        return self._transition(provider_key=provider_key, event_id=event_id, status="processed")

    def mark_ignored(self, *, provider_key: str, event_id: str) -> BillingEventReceipt:
        return self._transition(provider_key=provider_key, event_id=event_id, status="ignored")

    def mark_failed(
        self, *, provider_key: str, event_id: str, error_code: str
    ) -> BillingEventReceipt:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not error_code or len(error_code) > 64 or any(ch not in allowed for ch in error_code):
            error_code = "billing_event_error"
        return self._transition(
            provider_key=provider_key, event_id=event_id, status="failed",
            error_code=error_code,
        )

    def _transition(
        self, *, provider_key: str, event_id: str,
        status: Literal["processed", "failed", "ignored"], error_code: str | None = None,
    ) -> BillingEventReceipt:
        _validate_key(provider_key, "provider_key")
        _validate_key(event_id, "event_id")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._connection.execute(
                """UPDATE twi_billing_event_receipts SET status=?, attempts=attempts+1,
                       last_error_code=? WHERE provider_key=? AND event_id=?
                       AND status IN ('received','failed') RETURNING *""",
                (status, error_code, provider_key, event_id),
            ).fetchone()
            if row is None:
                row = self._connection.execute(
                    """SELECT * FROM twi_billing_event_receipts
                       WHERE provider_key=? AND event_id=?""",
                    (provider_key, event_id),
                ).fetchone()
                if row is None:
                    raise KeyError("billing event receipt not found")
                if row["status"] != status:
                    raise ValueError("billing event receipt cannot make this state transition")
            self._connection.commit()
            return _receipt(row)
        except Exception:
            if self._connection.in_transaction:
                self._connection.rollback()
            raise

    def get(self, *, provider_key: str, event_id: str) -> BillingEventReceipt | None:
        with self._connection:
            row = self._connection.execute(
                """SELECT * FROM twi_billing_event_receipts
                   WHERE provider_key=? AND event_id=?""",
                (provider_key, event_id),
            ).fetchone()
        return _receipt(row) if row is not None else None

    def close(self) -> None:
        self._connection.close()


class PostgresBillingEventInbox:
    """Multi-worker durable receipt inbox; schema migration version 3 is required."""

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 10) -> None:
        if not dsn or dsn != dsn.strip():
            raise ValueError("PostgreSQL DSN must be non-empty and normalized")
        if not 1 <= min_size <= max_size <= 50:
            raise ValueError("invalid PostgreSQL pool configuration")
        self._pool = acquire_pool(dsn, min_size=min_size, max_size=max_size)
        try:
            with self._pool.connection() as conn:
                row = conn.execute(
                    "SELECT to_regclass('twi_billing_event_receipts') AS receipts"
                ).fetchone()
                version = conn.execute(
                    "SELECT max(version) AS version FROM twi_schema_migrations"
                ).fetchone()
                if (
                    row is None or row["receipts"] is None
                    or version is None or version["version"] < 3
                ):
                    raise RuntimeError("billing receipt schema missing; run migration job")
        except Exception:
            release_pool(self._pool)
            raise

    def record(
        self, *, provider_key: str, event: VerifiedBillingEvent
    ) -> tuple[BillingEventReceipt, bool]:
        _validate_key(provider_key, "provider_key")
        with self._pool.connection() as conn:
            row = conn.execute(
                """INSERT INTO twi_billing_event_receipts
                   (provider_key,event_id,event_type,occurred_at,payload_sha256,status)
                   VALUES (%s,%s,%s,%s,%s,'received')
                   ON CONFLICT (provider_key,event_id) DO NOTHING RETURNING *""",
                (
                    provider_key, event.event_id, event.event_type,
                    event.occurred_at, event.payload_sha256,
                ),
            ).fetchone()
            if row is not None:
                return _receipt(row), False
            row = conn.execute(
                """SELECT * FROM twi_billing_event_receipts
                   WHERE provider_key=%s AND event_id=%s FOR UPDATE""",
                (provider_key,event.event_id),
            ).fetchone()
            if row is None:
                raise RuntimeError("billing receipt idempotency lookup returned no row")
            if row["payload_sha256"].strip() != event.payload_sha256:
                raise BillingEventReceiptConflict(
                    "provider event ID was reused with different payload bytes"
                )
            return _receipt(row), True

    def mark_processed(self, *, provider_key: str, event_id: str) -> BillingEventReceipt:
        return self._transition(provider_key=provider_key, event_id=event_id, status="processed")

    def mark_ignored(self, *, provider_key: str, event_id: str) -> BillingEventReceipt:
        return self._transition(provider_key=provider_key, event_id=event_id, status="ignored")

    def mark_failed(
        self, *, provider_key: str, event_id: str, error_code: str
    ) -> BillingEventReceipt:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not error_code or len(error_code) > 64 or any(ch not in allowed for ch in error_code):
            error_code = "billing_event_error"
        return self._transition(
            provider_key=provider_key, event_id=event_id, status="failed",
            error_code=error_code,
        )

    def _transition(
        self, *, provider_key: str, event_id: str,
        status: Literal["processed", "failed", "ignored"], error_code: str | None = None,
    ) -> BillingEventReceipt:
        with self._pool.connection() as conn:
            row = conn.execute(
                """UPDATE twi_billing_event_receipts SET status=%s, attempts=attempts+1,
                       last_error_code=%s WHERE provider_key=%s AND event_id=%s
                       AND status IN ('received','failed') RETURNING *""",
                (status,error_code,provider_key,event_id),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    """SELECT * FROM twi_billing_event_receipts
                       WHERE provider_key=%s AND event_id=%s""",
                    (provider_key,event_id),
                ).fetchone()
                if row is None:
                    raise KeyError("billing event receipt not found")
                if row["status"] != status:
                    raise ValueError("billing event receipt cannot make this state transition")
            return _receipt(row)

    def get(self, *, provider_key: str, event_id: str) -> BillingEventReceipt | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                """SELECT * FROM twi_billing_event_receipts
                   WHERE provider_key=%s AND event_id=%s""",
                (provider_key,event_id),
            ).fetchone()
        return _receipt(row) if row is not None else None

    def close(self) -> None:
        if not getattr(self, "_pool_released", False):
            self._pool_released = True
            release_pool(self._pool)
