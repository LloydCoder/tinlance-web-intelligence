"""Tenant-scoped content-addressed artifact storage.

The memory implementation is for tests and development only. Production workers use
PostgresArtifactStore, whose reads are tenant-scoped and whose content hashes are verified.
"""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol
from urllib.parse import urlsplit


_DIGEST_HEX = frozenset("0123456789abcdef")


def validate_artifact_digest(digest: str) -> None:
    """Reject malformed digests rather than treating them as absent artifacts."""
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in _DIGEST_HEX for character in digest)
    ):
        raise ValueError("artifact digest must be a lowercase SHA-256 hex digest")


def validate_artifact_metadata(content_type: str, source_url: str) -> None:
    """Validate non-network metadata shared by memory and durable artifact stores."""
    if (
        not isinstance(content_type, str)
        or not content_type
        or len(content_type) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in content_type)
    ):
        raise ValueError("content_type must contain 1 to 255 printable characters")
    if (
        not isinstance(source_url, str)
        or not source_url
        or source_url != source_url.strip()
        or len(source_url) > 4096
        or any(ord(character) < 32 or ord(character) == 127 for character in source_url)
    ):
        raise ValueError("source_url must contain 1 to 4096 normalized characters")
    try:
        parsed = urlsplit(source_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("source_url must be a valid absolute HTTP(S) URL") from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ValueError("source_url must be absolute HTTP(S) without userinfo or fragment")


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

    def count_expired(self, cutoff: datetime, *, tenant_id: str | None = None) -> int: ...

    def prune_before(self, cutoff: datetime, *, tenant_id: str | None = None) -> int: ...

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
        if (
            not tenant_id
            or tenant_id != tenant_id.strip()
            or "\x00" in tenant_id
            or len(tenant_id) > 256
        ):
            raise ValueError("tenant_id must be normalized and contain 1 to 256 characters")
        validate_artifact_metadata(content_type, source_url)
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
        validate_artifact_digest(digest)
        return self._content.get((tenant_id, digest))

    def count(self, *, tenant_id: str = "development") -> int:
        """Return capture-record count for one tenant; bytes may be deduplicated."""
        return sum(1 for key in self._records if key[0] == tenant_id)

    def count_expired(self, cutoff: datetime, *, tenant_id: str | None = None) -> int:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("cutoff must be timezone-aware")
        return sum(
            1 for record in self._records.values()
            if record.captured_at < cutoff and (tenant_id is None or record.tenant_id == tenant_id)
        )

    def prune_before(self, cutoff: datetime, *, tenant_id: str | None = None) -> int:
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("cutoff must be timezone-aware")
        expired = [
            key for key, record in self._records.items()
            if record.captured_at < cutoff and (tenant_id is None or record.tenant_id == tenant_id)
        ]
        for key in expired:
            del self._records[key]
        retained_content = {(record.tenant_id, record.sha256) for record in self._records.values()}
        for content_key in list(self._content):
            if (
                (tenant_id is None or content_key[0] == tenant_id)
                and content_key not in retained_content
            ):
                del self._content[content_key]
        return len(expired)

    def close(self) -> None:
        """Match the durable store lifecycle interface; no resource needs closing."""
