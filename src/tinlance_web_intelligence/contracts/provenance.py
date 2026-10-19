"""Acquisition provenance manifest; records collection facts, not source truth."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
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


    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> AcquisitionProvenance:
        """Parse a persisted manifest without coercing malformed values."""
        string_fields = (
            "requested_url_sha256",
            "final_url_sha256",
            "content_type",
            "content_sha256",
            "extractor_version",
            "schema_version",
            "retrieved_at",
        )
        if any(not isinstance(value.get(field), str) for field in string_fields):
            raise ProvenanceError("manifest contains missing or non-string fields")
        integer_fields = ("status_code", "byte_size", "redirect_count")
        if any(type(value.get(field)) is not int for field in integer_fields):
            raise ProvenanceError("manifest contains missing or non-integer fields")
        retrieved_at_raw = value.get("retrieved_at")
        if not isinstance(retrieved_at_raw, str):
            raise ProvenanceError("retrieved_at must be an ISO-8601 string")
        try:
            retrieved_at = datetime.fromisoformat(
                retrieved_at_raw.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ProvenanceError("retrieved_at must be a valid ISO-8601 timestamp") from exc
        manifest = cls(
            requested_url_sha256=value["requested_url_sha256"],  # type: ignore[arg-type]
            final_url_sha256=value["final_url_sha256"],  # type: ignore[arg-type]
            status_code=value["status_code"],  # type: ignore[arg-type]
            content_type=value["content_type"],  # type: ignore[arg-type]
            content_sha256=value["content_sha256"],  # type: ignore[arg-type]
            byte_size=value["byte_size"],  # type: ignore[arg-type]
            retrieved_at=retrieved_at,
            redirect_count=value["redirect_count"],  # type: ignore[arg-type]
            extractor_version=value["extractor_version"],  # type: ignore[arg-type]
            schema_version=value["schema_version"],  # type: ignore[arg-type]
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


class FreshnessStatus(StrEnum):
    """Freshness classification; it does not assess factual truth or authority."""

    FRESH = "fresh"
    STALE = "stale"
    FUTURE_DATED = "future_dated"


def assess_freshness(
    retrieved_at: datetime,
    *,
    now: datetime,
    max_age: timedelta,
    future_clock_skew: timedelta = timedelta(minutes=5),
) -> FreshnessStatus:
    """Classify evidence age against an explicit caller-owned freshness policy."""
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ProvenanceError("retrieved_at must be timezone-aware")
    if now.tzinfo is None or now.utcoffset() is None:
        raise ProvenanceError("now must be timezone-aware")
    if max_age <= timedelta(0):
        raise ProvenanceError("max_age must be positive")
    if future_clock_skew < timedelta(0):
        raise ProvenanceError("future_clock_skew must not be negative")
    age = now.astimezone(UTC) - retrieved_at.astimezone(UTC)
    if age < -future_clock_skew:
        return FreshnessStatus.FUTURE_DATED
    if age > max_age:
        return FreshnessStatus.STALE
    return FreshnessStatus.FRESH


def validate_evidence_pack(payload: Mapping[str, object]) -> None:
    """Validate the minimum durable fetch-result evidence pack and its hash linkage."""
    artifact_id = payload.get("artifact_id")
    content_sha256 = payload.get("content_sha256")
    raw_manifest = payload.get("provenance")
    if (
        not isinstance(artifact_id, str)
        or not artifact_id
        or artifact_id != artifact_id.strip()
        or len(artifact_id) > 256
    ):
        raise ProvenanceError("artifact_id must be normalized and contain 1 to 256 characters")
    if not isinstance(content_sha256, str) or _DIGEST.fullmatch(content_sha256) is None:
        raise ProvenanceError("evidence pack content_sha256 must be a lowercase SHA-256 digest")
    if not isinstance(raw_manifest, Mapping):
        raise ProvenanceError("evidence pack provenance manifest is missing")
    manifest = AcquisitionProvenance.from_dict(raw_manifest)
    if content_sha256 != manifest.content_sha256:
        raise ProvenanceError("evidence pack content digest does not match provenance")
    if payload.get("status_code") != manifest.status_code:
        raise ProvenanceError("evidence pack status_code does not match provenance")
    if payload.get("content_type") != manifest.content_type:
        raise ProvenanceError("evidence pack content_type does not match provenance")
    result_timestamp = payload.get("retrieved_at")
    if not isinstance(result_timestamp, str):
        raise ProvenanceError("evidence pack retrieved_at is missing")
    try:
        parsed_timestamp = datetime.fromisoformat(result_timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProvenanceError("evidence pack retrieved_at must be ISO-8601") from exc
    if parsed_timestamp.tzinfo is None or parsed_timestamp.utcoffset() is None:
        raise ProvenanceError("evidence pack retrieved_at must be timezone-aware")
    if parsed_timestamp.astimezone(UTC) != manifest.retrieved_at.astimezone(UTC):
        raise ProvenanceError("evidence pack retrieved_at does not match provenance")
