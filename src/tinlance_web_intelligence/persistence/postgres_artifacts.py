"""Tenant-scoped PostgreSQL artifact store for durable production capture."""
from __future__ import annotations

import re
from datetime import datetime
from hashlib import sha256
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from tinlance_web_intelligence.artifacts.store import ArtifactRecord

_DIGEST = re.compile(r"^[0-9a-f]{64}")


class PostgresArtifactStore:
    """Persist content and capture records with tenant-scoped reads and hash checks."""

    def __init__(self, dsn: str, *, max_bytes: int = 5_000_000) -> None:
        if not dsn or dsn != dsn.strip():
            raise ValueError("PostgreSQL DSN must be non-empty and normalized")
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self._max_bytes = max_bytes
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
            self._verify_schema()
        except Exception:
            self._pool.close()
            raise

    def _verify_schema(self) -> None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT to_regclass('twi_artifact_content') AS content, "
                "to_regclass('twi_artifact_records') AS records"
            ).fetchone()
            if row is None or row["content"] is None or row["records"] is None:
                raise RuntimeError("PostgreSQL artifact schema is missing; run the migration job")

    def put(
        self, *, body: bytes, content_type: str, source_url: str,
        captured_at: datetime, tenant_id: str = "development"
    ) -> ArtifactRecord:
        if not tenant_id or tenant_id != tenant_id.strip() or "\\x00" in tenant_id or len(tenant_id) > 256:
            raise ValueError("tenant_id must be normalized and contain 1 to 256 characters")
        if len(body) > self._max_bytes:
            raise ValueError("artifact exceeds configured byte limit")
        if not content_type or len(content_type) > 255:
            raise ValueError("content_type must contain 1 to 255 characters")
        if not source_url or len(source_url) > 4096:
            raise ValueError("source_url must contain 1 to 4096 characters")
        if captured_at.tzinfo is None or captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        digest = sha256(body).hexdigest()
        source_hash = sha256(source_url.encode("utf-8")).hexdigest()
        with self._pool.connection() as conn:
            stored = conn.execute(
                "INSERT INTO twi_artifact_content "
                "(tenant_id, sha256, body, byte_size) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, sha256) DO UPDATE "
                "SET byte_size = EXCLUDED.byte_size "
                "WHERE twi_artifact_content.body = EXCLUDED.body "
                "AND twi_artifact_content.byte_size = EXCLUDED.byte_size "
                "RETURNING sha256",
                (tenant_id, digest, body, len(body)),
            ).fetchone()
            if stored is None:
                raise RuntimeError("content-address collision or stored artifact integrity failure")
            row = conn.execute(
                "INSERT INTO twi_artifact_records "
                "(tenant_id, sha256, source_url_hash, source_url, captured_at, "
                "content_type, byte_size) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, sha256, source_url_hash, captured_at) DO NOTHING "
                "RETURNING tenant_id, sha256, byte_size, content_type, source_url, captured_at",
                (tenant_id, digest, source_hash, source_url, captured_at, content_type, len(body)),
            ).fetchone()
            if row is None:
                row = conn.execute(
                    "SELECT tenant_id, sha256, byte_size, content_type, source_url, captured_at "
                    "FROM twi_artifact_records WHERE tenant_id=%s AND sha256=%s "
                    "AND source_url_hash=%s AND captured_at=%s",
                    (tenant_id, digest, source_hash, captured_at),
                ).fetchone()
            if row is None:
                raise RuntimeError("artifact capture record could not be persisted")
            return ArtifactRecord(
                artifact_id=f"sha256:{digest}",
                tenant_id=row["tenant_id"],
                sha256=row["sha256"].strip(),
                byte_size=row["byte_size"],
                content_type=row["content_type"],
                source_url=row["source_url"],
                captured_at=row["captured_at"],
            )

    def get(self, digest: str, *, tenant_id: str = "development") -> bytes | None:
        if not _DIGEST.fullmatch(digest) or len(digest) != 64:
            raise ValueError("digest must be a lowercase SHA-256 hex string")
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT body, byte_size FROM twi_artifact_content "
                "WHERE tenant_id=%s AND sha256=%s",
                (tenant_id, digest),
            ).fetchone()
            if row is None:
                return None
            body = row["body"]
            if not isinstance(body, bytes) or len(body) != row["byte_size"]:
                raise RuntimeError("stored artifact has an invalid byte representation")
            if sha256(body).hexdigest() != digest:
                raise RuntimeError("stored artifact content failed SHA-256 integrity verification")
            return body

    def count(self, *, tenant_id: str = "development") -> int:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT count(*) AS count FROM twi_artifact_records WHERE tenant_id=%s",
                (tenant_id,),
            ).fetchone()
            return int(row["count"]) if row is not None else 0

    def count_expired(self, cutoff: datetime, *, tenant_id: str | None = None) -> int:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("cutoff must be timezone-aware")
        # RESTRICT on the capture FK makes concurrent writes fail closed rather than
        # allowing retention to cascade-delete a newly committed capture.
        with self._pool.connection() as conn:
            if tenant_id is None:
                row = conn.execute(
                    "SELECT count(*) AS count FROM twi_artifact_records WHERE captured_at < %s",
                    (cutoff,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT count(*) AS count FROM twi_artifact_records "
                    "WHERE captured_at < %s AND tenant_id=%s",
                    (cutoff, tenant_id),
                ).fetchone()
            return int(row["count"]) if row is not None else 0

    def prune_before(self, cutoff: datetime, *, tenant_id: str | None = None) -> int:
        """Delete expired capture records and only content no longer referenced."""
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("cutoff must be timezone-aware")
        with self._pool.connection() as conn:
            if tenant_id is None:
                result = conn.execute(
                    "DELETE FROM twi_artifact_records WHERE captured_at < %s",
                    (cutoff,),
                )
                conn.execute(
                    "DELETE FROM twi_artifact_content AS content WHERE NOT EXISTS "
                    "(SELECT 1 FROM twi_artifact_records AS record "
                    "WHERE record.tenant_id=content.tenant_id AND record.sha256=content.sha256)"
                )
            else:
                result = conn.execute(
                    "DELETE FROM twi_artifact_records WHERE captured_at < %s AND tenant_id=%s",
                    (cutoff, tenant_id),
                )
                conn.execute(
                    "DELETE FROM twi_artifact_content AS content WHERE content.tenant_id=%s "
                    "AND NOT EXISTS (SELECT 1 FROM twi_artifact_records AS record "
                    "WHERE record.tenant_id=content.tenant_id AND record.sha256=content.sha256)",
                    (tenant_id,),
                )
            return result.rowcount

    def close(self) -> None:
        self._pool.close()
