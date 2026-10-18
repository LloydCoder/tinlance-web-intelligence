"""Tenant-scoped content-addressed artifact storage.

The memory implementation is for tests and development only. Production workers use
PostgresArtifactStore, whose reads are tenant-scoped and whose content hashes are verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    tenant_id: str
    sha256: str
    byte_size: int
    content_type: str
    source_url: str
    captured_at: datetime


class ArtifactStore(Protocol):
    def put(
        self, *, body: bytes, content_type: str, source_url: str,
        captured_at: datetime, tenant_id: str = "development"
    ) -> ArtifactRecord: ...

    def get(self, digest: str, *, tenant_id: str = "development") -> bytes | None: ...

    def count(self, *, tenant_id: str = "development") -> int: ...

    def close(self) -> None: ...


class MemoryArtifactStore:
    """Process-local store for tests and development; not durable or production-ready."""

    def __init__(self, *, max_bytes: int = 5_000_000) -> None:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self._max_bytes = max_bytes
        self._content: dict[tuple[str, str], bytes] = {}
        self._records: dict[tuple[str, str, str, str], ArtifactRecord] = {}

    def put(
        self, *, body: bytes, content_type: str, source_url: str,
        captured_at: datetime, tenant_id: str = "development"
    ) -> ArtifactRecord:
        if not tenant_id or len(tenant_id) > 256:
            raise ValueError("tenant_id must contain 1 to 256 characters")
        if len(body) > self._max_bytes:
            raise ValueError("artifact exceeds configured byte limit")
        if captured_at.tzinfo is None or captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        digest = sha256(body).hexdigest()
        key = (tenant_id, digest, source_url, captured_at.isoformat())
        record = self._records.get(key)
        if record is not None:
            return record
        record = ArtifactRecord(
            artifact_id=f"sha256:{digest}",
            tenant_id=tenant_id,
            sha256=digest,
            byte_size=len(body),
            content_type=content_type,
            source_url=source_url,
            captured_at=captured_at,
        )
        self._content.setdefault((tenant_id, digest), body)
        self._records[key] = record
        return record

    def get(self, digest: str, *, tenant_id: str = "development") -> bytes | None:
        return self._content.get((tenant_id, digest))

    def count(self, *, tenant_id: str = "development") -> int:
        """Return capture-record count for one tenant; bytes may be deduplicated."""
        return sum(1 for key in self._records if key[0] == tenant_id)

    def close(self) -> None:
        """Match the durable store lifecycle interface; no resource needs closing."""
