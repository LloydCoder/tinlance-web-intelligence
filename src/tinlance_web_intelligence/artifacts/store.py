"""Content-addressed artifact store interface and local in-memory implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    sha256: str
    byte_size: int
    content_type: str
    source_url: str
    captured_at: datetime


class MemoryArtifactStore:
    """Process-local store for tests and development; not durable or production-ready."""

    def __init__(self) -> None:
        self._content: dict[str, bytes] = {}
        self._records: dict[tuple[str, str, str], ArtifactRecord] = {}

    def put(
        self, *, body: bytes, content_type: str, source_url: str, captured_at: datetime
    ) -> ArtifactRecord:
        digest = sha256(body).hexdigest()
        key = (digest, source_url, captured_at.isoformat())
        record = self._records.get(key)
        if record is not None:
            return record
        record = ArtifactRecord(
            artifact_id=f"sha256:{digest}",
            sha256=digest,
            byte_size=len(body),
            content_type=content_type,
            source_url=source_url,
            captured_at=captured_at,
        )
        self._content.setdefault(digest, body)
        self._records[key] = record
        return record

    def get(self, digest: str) -> bytes | None:
        return self._content.get(digest)

    def count(self) -> int:
        """Return capture-record count; identical bytes may have multiple source records."""
        return len(self._records)
