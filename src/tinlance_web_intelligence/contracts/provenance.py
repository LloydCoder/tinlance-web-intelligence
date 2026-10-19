"""Acquisition provenance manifest; records collection facts, not source truth."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import urlsplit


class ProvenanceError(ValueError):
    """Raised when an acquisition provenance manifest is incomplete or invalid."""


_DIGEST = re.compile(r"[0-9a-f]{64}")


def _url_fingerprint(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProvenanceError("source URL must be a normalized absolute HTTP(S) URL")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ProvenanceError("source URL must be a valid absolute HTTP(S) URL") from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProvenanceError("source URL must be absolute HTTP(S) without userinfo")
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AcquisitionProvenance:
    """Integrity and acquisition facts suitable for a durable job result.

    URL fingerprints are included instead of duplicating requested URLs, which may
    contain sensitive query parameters. This manifest does not assert that content
    is accurate, authoritative, safe, or true.
    """

    requested_url_sha256: str
    final_url_sha256: str
    status_code: int
    content_type: str
    content_sha256: str
    byte_size: int
    retrieved_at: datetime
    redirect_count: int
    extractor_version: str
    schema_version: str = "1.0.0"

    @classmethod
    def from_capture(
        cls,
        *,
        requested_url: str,
        final_url: str,
        status_code: int,
        content_type: str,
        body: bytes,
        retrieved_at: datetime,
        redirect_count: int,
        extractor_version: str,
    ) -> AcquisitionProvenance:
        """Build a manifest from the actual fetch result without retaining raw URLs."""
        manifest = cls(
            requested_url_sha256=_url_fingerprint(requested_url),
            final_url_sha256=_url_fingerprint(final_url),
            status_code=status_code,
            content_type=content_type,
            content_sha256=sha256(body).hexdigest(),
            byte_size=len(body),
            retrieved_at=retrieved_at,
            redirect_count=redirect_count,
            extractor_version=extractor_version,
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if not _DIGEST.fullmatch(self.requested_url_sha256):
            raise ProvenanceError("requested_url_sha256 must be a lowercase SHA-256 digest")
        if not _DIGEST.fullmatch(self.final_url_sha256):
            raise ProvenanceError("final_url_sha256 must be a lowercase SHA-256 digest")
        if not _DIGEST.fullmatch(self.content_sha256):
            raise ProvenanceError("content_sha256 must be a lowercase SHA-256 digest")
        if not 200 <= self.status_code <= 599:
            raise ProvenanceError("status_code must be between 200 and 599")
        if (
            not self.content_type
            or len(self.content_type) > 255
            or any(ord(character) < 32 or ord(character) == 127 for character in self.content_type)
        ):
            raise ProvenanceError("content_type must contain 1 to 255 printable characters")
        if self.byte_size < 0:
            raise ProvenanceError("byte_size must not be negative")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ProvenanceError("retrieved_at must be timezone-aware")
        if not 0 <= self.redirect_count <= 100:
            raise ProvenanceError("redirect_count must be between 0 and 100")
        if (
            not self.extractor_version
            or self.extractor_version != self.extractor_version.strip()
            or len(self.extractor_version) > 64
        ):
            raise ProvenanceError("extractor_version must be normalized and at most 64 characters")
        if self.schema_version != "1.0.0":
            raise ProvenanceError("unsupported acquisition provenance schema version")

    def to_dict(self) -> dict[str, str | int]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "requested_url_sha256": self.requested_url_sha256,
            "final_url_sha256": self.final_url_sha256,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "content_sha256": self.content_sha256,
            "byte_size": self.byte_size,
            "retrieved_at": self.retrieved_at.astimezone(UTC).isoformat(),
            "redirect_count": self.redirect_count,
            "extractor_version": self.extractor_version,
        }
