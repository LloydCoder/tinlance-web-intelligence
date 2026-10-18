"""Durable SQLite outbox for verified source-evidence delivery to World Intelligence."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any


class OutboxConflictError(ValueError):
    """An idempotency key was reused with a different evidence payload."""


class OutboxLeaseLostError(RuntimeError):
    """A worker attempted to complete an event without owning its current lease."""


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    event_id: str
    tenant_ref: str
    subject_ref: str
    idempotency_key: str
    payload: dict[str, Any]
    status: str
    attempts: int
    lease_token: str | None
    request_id: str
    traceparent: str | None
    remote_evidence_id: str | None = None


class SQLiteSourceEvidenceOutbox:
    """Small single-node outbox; W6 promotes the same semantics to PostgreSQL."""

    def __init__(self, database_path: str) -> None:
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            database_path,
            timeout=5.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if database_path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS twi_source_evidence_outbox (
                event_id TEXT PRIMARY KEY,
                tenant_ref TEXT NOT NULL CHECK (length(tenant_ref) = 64),
                subject_ref TEXT NOT NULL CHECK (length(subject_ref) = 64),
                idempotency_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
                status TEXT NOT NULL CHECK (
                    status IN ('pending', 'delivering', 'delivered', 'failed')
                ),
                attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
                available_at REAL NOT NULL,
                lease_owner TEXT,
                lease_until REAL,
                remote_evidence_id TEXT,
                last_error_code TEXT,
                request_id TEXT NOT NULL,
                traceparent TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                delivered_at REAL,
                UNIQUE (tenant_ref, subject_ref, idempotency_key),
                CHECK (
                    (status = 'delivering' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL)
                    OR status <> 'delivering'
                )
            )
            """
        )

    @staticmethod
    def _canonical_payload(payload: dict[str, Any]) -> tuple[str, str]:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> OutboxEvent:
        return OutboxEvent(
            event_id=row["event_id"],
            tenant_ref=row["tenant_ref"],
            subject_ref=row["subject_ref"],
            idempotency_key=row["idempotency_key"],
            payload=json.loads(row["payload_json"]),
            status=row["status"],
            attempts=row["attempts"],
            lease_token=row["lease_owner"],
            request_id=row["request_id"],
            traceparent=row["traceparent"],
            remote_evidence_id=row["remote_evidence_id"],
        )

    def enqueue(
        self,
        *,
        tenant_ref: str,
        subject_ref: str,
        idempotency_key: str,
        payload: dict[str, Any],
        request_id: str,
        traceparent: str | None,
    ) -> tuple[OutboxEvent, bool]:
        if not re.fullmatch(r"[0-9a-f]{64}", tenant_ref):
            raise ValueError("tenant_ref must be a pseudonymous SHA-256 reference")
        if not re.fullmatch(r"[0-9a-f]{64}", subject_ref):
            raise ValueError("subject_ref must be a pseudonymous SHA-256 reference")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{16,128}", idempotency_key):
            raise ValueError("invalid idempotency key")
        if not request_id or len(request_id) > 128:
            raise ValueError("invalid request_id")
        payload_json, payload_sha256 = self._canonical_payload(payload)
        now = time.time()
        with self._lock:
            connection = self._connection
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    """
                    SELECT * FROM twi_source_evidence_outbox
                    WHERE tenant_ref = ? AND subject_ref = ? AND idempotency_key = ?
                    """,
                    (tenant_ref, subject_ref, idempotency_key),
                ).fetchone()
                if existing is not None:
                    if existing["payload_sha256"] != payload_sha256:
                        raise OutboxConflictError(
                            "idempotency key was used with another evidence payload"
                        )
                    event = self._row_to_event(existing)
                    connection.execute("COMMIT")
                    return event, True
                event_id = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO twi_source_evidence_outbox (
                        event_id, tenant_ref, subject_ref, idempotency_key, payload_json,
                        payload_sha256, status, attempts, available_at, request_id,
                        traceparent, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        tenant_ref,
                        subject_ref,
                        idempotency_key,
                        payload_json,
                        payload_sha256,
                        now,
                        request_id,
                        traceparent,
                        now,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM twi_source_evidence_outbox WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("outbox insert could not be read back")
                event = self._row_to_event(row)
                connection.execute("COMMIT")
                return event, False
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def claim_next(self, worker_id: str, *, lease_seconds: int = 60) -> OutboxEvent | None:
        if not worker_id or len(worker_id) > 128:
            raise ValueError("worker_id must be 1 to 128 characters")
        if not 5 <= lease_seconds <= 300:
            raise ValueError("lease_seconds must be between 5 and 300")
        now = time.time()
        with self._lock:
            connection = self._connection
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    """
                    SELECT event_id FROM twi_source_evidence_outbox
                    WHERE (status = 'pending' AND available_at <= ?)
                       OR (status = 'delivering' AND lease_until <= ?)
                    ORDER BY created_at, event_id
                    LIMIT 1
                    """,
                    (now, now),
                ).fetchone()
                if row is None:
                    connection.execute("COMMIT")
                    return None
                event_id = row["event_id"]
                lease_token = f"{worker_id}:{uuid.uuid4()}"
                connection.execute(
                    """
                    UPDATE twi_source_evidence_outbox
                    SET status = 'delivering', attempts = attempts + 1,
                        lease_owner = ?, lease_until = ?, updated_at = ?, last_error_code = NULL
                    WHERE event_id = ?
                    """,
                    (lease_token, now + lease_seconds, now, event_id),
                )
                claimed = connection.execute(
                    "SELECT * FROM twi_source_evidence_outbox WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                connection.execute("COMMIT")
                if claimed is None:
                    raise RuntimeError("claimed outbox event could not be read back")
                return self._row_to_event(claimed)
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise

    def complete(self, event_id: str, lease_token: str, remote_evidence_id: str) -> OutboxEvent:
        now = time.time()
        with self._lock:
            cursor = self._connection.execute(
                """
                UPDATE twi_source_evidence_outbox
                SET status = 'delivered', remote_evidence_id = ?, delivered_at = ?,
                    lease_owner = NULL, lease_until = NULL, updated_at = ?
                WHERE event_id = ? AND status = 'delivering' AND lease_owner = ?
                """,
                (remote_evidence_id, now, now, event_id, lease_token),
            )
            if cursor.rowcount != 1:
                raise OutboxLeaseLostError("outbox lease was lost before completion")
            row = self._connection.execute(
                "SELECT * FROM twi_source_evidence_outbox WHERE event_id = ?", (event_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError("completed outbox event could not be read back")
            return self._row_to_event(row)

    def fail(
        self,
        event_id: str,
        lease_token: str,
        *,
        error_code: str,
        retryable: bool,
        max_attempts: int = 5,
    ) -> OutboxEvent:
        if not re.fullmatch(r"[a-z0-9_.-]{1,64}", error_code):
            raise ValueError("invalid error_code")
        now = time.time()
        with self._lock:
            row = self._connection.execute(
                """
                SELECT attempts FROM twi_source_evidence_outbox
                WHERE event_id = ? AND status = 'delivering' AND lease_owner = ?
                """,
                (event_id, lease_token),
            ).fetchone()
            if row is None:
                raise OutboxLeaseLostError("outbox lease was lost before failure handling")
            attempts = int(row["attempts"])
            will_retry = retryable and attempts < max_attempts
            delay = min(2 ** min(attempts, 8), 300) if will_retry else 0
            status = "pending" if will_retry else "failed"
            self._connection.execute(
                """
                UPDATE twi_source_evidence_outbox
                SET status = ?, available_at = ?, lease_owner = NULL, lease_until = NULL,
                    last_error_code = ?, updated_at = ?
                WHERE event_id = ? AND status = 'delivering' AND lease_owner = ?
                """,
                (status, now + delay, error_code, now, event_id, lease_token),
            )
            updated = self._connection.execute(
                "SELECT * FROM twi_source_evidence_outbox WHERE event_id = ?", (event_id,)
            ).fetchone()
            if updated is None:
                raise RuntimeError("failed outbox event could not be read back")
            return self._row_to_event(updated)

    def get(self, event_id: str, tenant_ref: str, subject_ref: str) -> OutboxEvent | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM twi_source_evidence_outbox
                WHERE event_id = ? AND tenant_ref = ? AND subject_ref = ?
                """,
                (event_id, tenant_ref, subject_ref),
            ).fetchone()
        return self._row_to_event(row) if row is not None else None

    def ping(self) -> bool:
        try:
            with self._lock:
                row = self._connection.execute("SELECT 1 AS ready").fetchone()
            return row is not None and row["ready"] == 1
        except sqlite3.Error:
            return False

    def close(self) -> None:
        with self._lock:
            self._connection.close()
