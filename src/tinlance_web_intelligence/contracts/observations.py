"""Minimal source-backed observation contract; world-state semantics live elsewhere."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urlsplit


class ContractError(ValueError):
    """Raised for invalid external contract payloads."""


@dataclass(frozen=True, slots=True)
class SourceReference:
    url: str
    retrieved_at: datetime
    media_type: str | None = None
    content_sha256: str | None = None

    def validate(self) -> None:
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ContractError("source URL must be absolute HTTP(S)")
        if parsed.username or parsed.password:
            raise ContractError("source URL must not contain userinfo")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ContractError("retrieved_at must be timezone-aware")
        digest = self.content_sha256
        if digest is not None and (
            len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise ContractError("content_sha256 must be a lowercase SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    statement: str
    source: SourceReference
    observed_at: datetime
    extractor_version: str
    confidence: float | None = None

    def validate(self) -> None:
        required = (self.observation_id, self.statement, self.extractor_version)
        if any(not value.strip() for value in required):
            raise ContractError("observation_id, statement, and extractor_version must be non-empty")
        self.source.validate()
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ContractError("observed_at must be timezone-aware")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ContractError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.astimezone(UTC).isoformat()
        payload["source"]["retrieved_at"] = (
            self.source.retrieved_at.astimezone(UTC).isoformat()
        )
        return payload


def content_digest(content: bytes) -> str:
    """Return a stable SHA-256 digest for acquired bytes."""
    return sha256(content).hexdigest()
