"""PostgreSQL-backed usage ledger with cross-process atomic quota reservations."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from tinlance_web_intelligence.commercial.usage_ledger import (
    QuotaExceededError,
    UsageConflictError,
    UsageEvent,
    UsageReservation,
    _validate_key,
)


def _now() -> datetime:
    return datetime.now(UTC)


class PostgresUsageLedger:
    """Durable multi-worker ledger; requires schema migration version 3."""

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 10) -> None:
        if not dsn or dsn != dsn.strip():
            raise ValueError("PostgreSQL DSN must be non-empty and normalized")
        if not 1 <= min_size <= max_size <= 50:
            raise ValueError("invalid PostgreSQL pool configuration")
        self._pool = ConnectionPool[Connection[dict[str, Any]]](
            conninfo=dsn, min_size=min_size, max_size=max_size,
            kwargs={"row_factory": dict_row, "connect_timeout": 5},
            timeout=10, open=True,
        )
        self._pool.wait(timeout=10)
        try:
            with self._pool.connection() as conn:
                row = conn.execute(
                    "SELECT to_regclass('twi_usage_reservations') AS reservations, "
                    "to_regclass('twi_usage_events') AS events"
                ).fetchone()
                version = conn.execute(
                    "SELECT max(version) AS version FROM twi_schema_migrations"
                ).fetchone()
                if (
                    row is None or row["reservations"] is None or row["events"] is None
                    or version is None or version["version"] < 3
                ):
                    raise RuntimeError("PostgreSQL usage schema missing; run migration job")
        except Exception:
            self._pool.close()
            raise

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
        with self._pool.connection() as conn:
            # Serialize all reservations for the same tenant quota bucket across replicas.
            bucket = json.dumps([tenant_id, dimension, period_start], separators=(",", ":"))
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (bucket,))
            existing = conn.execute(
                """SELECT * FROM twi_usage_reservations
                   WHERE tenant_id=%s AND subject_id=%s AND idempotency_key=%s""",
                (tenant_id, subject_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["request_fingerprint"].strip() != fingerprint:
                    raise UsageConflictError("idempotency key reused with different quota request")
                return self._to_reservation(existing)
            row = conn.execute(
                """SELECT COALESCE(SUM(quantity), 0) AS quantity
                   FROM twi_usage_reservations
                   WHERE tenant_id=%s AND dimension=%s AND period_start=%s
                     AND status IN ('reserved','committed')""",
                (tenant_id, dimension, period_start),
            ).fetchone()
            used = int(row["quantity"]) if row is not None else 0
            if used + quantity > limit:
                raise QuotaExceededError("hard quota would be exceeded")
            reservation_id = str(uuid.uuid4())
            row = conn.execute(
                """INSERT INTO twi_usage_reservations
                   (reservation_id,tenant_id,subject_id,feature,dimension,period_start,
                    quantity,status,idempotency_key,request_fingerprint,created_at,updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,'reserved',%s,%s,%s,%s)
                   RETURNING *""",
                (reservation_id,tenant_id,subject_id,feature,dimension,period_start,
                 quantity,idempotency_key,fingerprint,_now(),_now()),
            ).fetchone()
            if row is None:
                raise RuntimeError("usage reservation insert did not return a row")
            return self._to_reservation(row)

    def commit(self, *, tenant_id: str, subject_id: str, reservation_id: str) -> UsageEvent:
        for value, label in (
            (tenant_id, "tenant_id"), (subject_id, "subject_id"),
            (reservation_id, "reservation_id"),
        ):
            _validate_key(value, label)
        with self._pool.connection() as conn:
            row = conn.execute(
                """SELECT * FROM twi_usage_reservations
                   WHERE reservation_id=%s AND tenant_id=%s AND subject_id=%s FOR UPDATE""",
                (reservation_id, tenant_id, subject_id),
            ).fetchone()
            if row is None:
                raise KeyError("usage reservation not found")
            existing = conn.execute(
                "SELECT * FROM twi_usage_events WHERE reservation_id=%s", (reservation_id,)
            ).fetchone()
            if existing is not None:
                return self._to_event(existing)
            if row["status"] != "reserved":
                raise ValueError("only active reservations can be committed")
            event = conn.execute(
                """INSERT INTO twi_usage_events
                   (event_id,tenant_id,subject_id,feature,dimension,period_start,quantity,
                    occurred_at,schema_version,reservation_id,idempotency_key)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s)
                   RETURNING *""",
                (str(uuid.uuid4()),tenant_id,subject_id,row["feature"],row["dimension"],
                 row["period_start"],row["quantity"],_now(),reservation_id,row["idempotency_key"]),
            ).fetchone()
            conn.execute(
                """UPDATE twi_usage_reservations SET status='committed', updated_at=%s
                   WHERE reservation_id=%s AND status='reserved'""",
                (_now(), reservation_id),
            )
            if event is None:
                raise RuntimeError("usage event insert did not return a row")
            return self._to_event(event)

    def release(self, *, tenant_id: str, subject_id: str, reservation_id: str) -> bool:
        with self._pool.connection() as conn:
            row = conn.execute(
                """UPDATE twi_usage_reservations SET status='released', updated_at=%s
                   WHERE reservation_id=%s AND tenant_id=%s AND subject_id=%s AND status='reserved'
                   RETURNING reservation_id""",
                (_now(), reservation_id, tenant_id, subject_id),
            ).fetchone()
            return row is not None

    def usage_total(self, *, tenant_id: str, subject_id: str, dimension: str,
                    period_start: str) -> int:
        with self._pool.connection() as conn:
            row = conn.execute(
                """SELECT COALESCE(SUM(quantity),0) AS quantity FROM twi_usage_events
                   WHERE tenant_id=%s AND subject_id=%s AND dimension=%s AND period_start=%s""",
                (tenant_id, subject_id, dimension, period_start),
            ).fetchone()
        return int(row["quantity"]) if row is not None else 0

    def list_events(
        self, *, tenant_id: str, subject_id: str, limit: int = 100,
        dimension: str | None = None, period_start: str | None = None,
        after: tuple[str, str] | None = None,
    ) -> list[UsageEvent]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 501:
            raise ValueError("limit must be between 1 and 501")
        sql = "SELECT * FROM twi_usage_events WHERE tenant_id=%s AND subject_id=%s"
        parameters: list[Any] = [tenant_id, subject_id]
        if dimension is not None:
            sql += " AND dimension=%s"
            parameters.append(dimension)
        if period_start is not None:
            sql += " AND period_start=%s"
            parameters.append(period_start)
        if after is not None:
            sql += " AND (occurred_at > %s OR (occurred_at = %s AND event_id > %s))"
            parameters.extend((after[0], after[0], after[1]))
        sql += " ORDER BY occurred_at,event_id LIMIT %s"
        parameters.append(limit)
        with self._pool.connection() as conn:
            rows = conn.execute(sql, parameters).fetchall()
        return [self._to_event(row) for row in rows]

    @staticmethod
    def _to_reservation(row: dict[str, Any]) -> UsageReservation:
        return UsageReservation(
            reservation_id=row["reservation_id"], tenant_id=row["tenant_id"],
            subject_id=row["subject_id"], feature=row["feature"], dimension=row["dimension"],
            period_start=row["period_start"], quantity=int(row["quantity"]),
            status=row["status"], idempotency_key=row["idempotency_key"],
        )

    @staticmethod
    def _to_event(row: dict[str, Any]) -> UsageEvent:
        occurred_at = row["occurred_at"]
        return UsageEvent(
            event_id=row["event_id"], tenant_id=row["tenant_id"], subject_id=row["subject_id"],
            feature=row["feature"], dimension=row["dimension"], period_start=row["period_start"],
            quantity=int(row["quantity"]),
            occurred_at=(
                occurred_at.isoformat()
                if hasattr(occurred_at, "isoformat")
                else str(occurred_at)
            ),
            schema_version=int(row["schema_version"]), reservation_id=row["reservation_id"],
            idempotency_key=row["idempotency_key"],
        )

    def close(self) -> None:
        self._pool.close()
