"""Deterministic, integrity-checked customer export packages for acquired evidence.

The package records acquisition lineage and bytes. It does not assert factual truth,
authority, or safety of the captured source.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from tinlance_web_intelligence.contracts.provenance import (
    AcquisitionProvenance,
    ProvenanceError,
)

_FORMAT = "application/vnd.tinlance.twi-evidence+json"
_SCHEMA_VERSION = "1.0.0"
_REVISION = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_KEYS = {
    "format",
    "schema_version",
    "export_id",
    "artifact_id",
    "content_sha256",
    "content_type",
    "byte_size",
    "source_revision",
    "provenance",
    "content_base64",
    "interpretation",
}


class EvidencePackageError(ValueError):
    """Raised when an evidence export cannot be built or verified."""


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise EvidencePackageError("evidence package is not canonical JSON") from exc


def build_evidence_package(
    *,
    body: bytes,
    content_type: str,
    provenance: Mapping[str, object],
    source_revision: str,
) -> bytes:
    """Build byte-stable JSON containing verified bytes and sanitized provenance facts."""
    if not isinstance(body, bytes):
        raise EvidencePackageError("artifact body must be bytes")
    if not isinstance(source_revision, str) or not _REVISION.fullmatch(source_revision):
        raise EvidencePackageError("source_revision must be a full lowercase Git commit SHA")
    try:
        manifest = AcquisitionProvenance.from_dict(provenance)
    except ProvenanceError as exc:
        raise EvidencePackageError("acquisition provenance is invalid") from exc
    digest = sha256(body).hexdigest()
    if digest != manifest.content_sha256 or len(body) != manifest.byte_size:
        raise EvidencePackageError("artifact bytes do not match acquisition provenance")
    if content_type != manifest.content_type:
        raise EvidencePackageError("content type does not match acquisition provenance")
    if len(body) > 20_000_000:
        raise EvidencePackageError("artifact exceeds the 20 MB evidence export limit")

    unsigned: dict[str, Any] = {
        "format": _FORMAT,
        "schema_version": _SCHEMA_VERSION,
        "artifact_id": f"sha256:{digest}",
        "content_sha256": digest,
        "content_type": content_type,
        "byte_size": len(body),
        "source_revision": source_revision,
        "provenance": manifest.to_dict(),
        "content_base64": base64.b64encode(body).decode("ascii"),
        "interpretation": {
            "provenance_kind": "acquisition_observation",
            "truth_assessment": "not_provided",
            "source_authority_assessment": "not_provided",
        },
    }
    export_id = "sha256:" + sha256(_canonical_json(unsigned)).hexdigest()
    return _canonical_json({**unsigned, "export_id": export_id})


def validate_evidence_package(
    package_bytes: bytes,
    *,
    expected_source_revision: str | None = None,
) -> dict[str, Any]:
    """Validate package schema invariants, canonical encoding, provenance, and content hash."""
    if not isinstance(package_bytes, bytes) or len(package_bytes) > 30_000_000:
        raise EvidencePackageError("evidence package must be bytes no larger than 30 MB")
    try:
        payload = json.loads(package_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EvidencePackageError("evidence package is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _REQUIRED_KEYS:
        raise EvidencePackageError("evidence package fields do not match schema version 1.0.0")
    if payload["format"] != _FORMAT or payload["schema_version"] != _SCHEMA_VERSION:
        raise EvidencePackageError("unsupported evidence package format or schema version")
    if not isinstance(payload["source_revision"], str) or not _REVISION.fullmatch(
        payload["source_revision"]
    ):
        raise EvidencePackageError("source_revision must be a full lowercase Git commit SHA")
    if (
        expected_source_revision is not None
        and payload["source_revision"] != expected_source_revision
    ):
        raise EvidencePackageError("evidence package source revision mismatch")
    if not isinstance(payload["content_sha256"], str) or not _DIGEST.fullmatch(
        payload["content_sha256"]
    ):
        raise EvidencePackageError("content_sha256 must be a lowercase SHA-256 digest")
    if not isinstance(payload["content_type"], str):
        raise EvidencePackageError("content_type must be a string")
    if type(payload["byte_size"]) is not int or payload["byte_size"] < 0:
        raise EvidencePackageError("byte_size must be a non-negative integer")
    if not isinstance(payload["artifact_id"], str) or payload["artifact_id"] != (
        "sha256:" + payload["content_sha256"]
    ):
        raise EvidencePackageError("artifact_id does not match content digest")
    if not isinstance(payload["content_base64"], str):
        raise EvidencePackageError("content_base64 must be a string")
    try:
        body = base64.b64decode(payload["content_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise EvidencePackageError("content_base64 is invalid") from exc
    if len(body) != payload["byte_size"] or sha256(body).hexdigest() != payload["content_sha256"]:
        raise EvidencePackageError(
            "exported artifact failed size or SHA-256 integrity verification"
        )
    try:
        manifest = AcquisitionProvenance.from_dict(payload["provenance"])
    except (ProvenanceError, TypeError) as exc:
        raise EvidencePackageError("acquisition provenance is invalid") from exc
    if (
        manifest.content_sha256 != payload["content_sha256"]
        or manifest.byte_size != payload["byte_size"]
        or manifest.content_type != payload["content_type"]
    ):
        raise EvidencePackageError("package fields do not match acquisition provenance")
    expected_interpretation = {
        "provenance_kind": "acquisition_observation",
        "truth_assessment": "not_provided",
        "source_authority_assessment": "not_provided",
    }
    if payload["interpretation"] != expected_interpretation:
        raise EvidencePackageError("evidence interpretation metadata is invalid")
    unsigned = {key: value for key, value in payload.items() if key != "export_id"}
    expected_export_id = "sha256:" + sha256(_canonical_json(unsigned)).hexdigest()
    if payload["export_id"] != expected_export_id:
        raise EvidencePackageError("export_id integrity check failed")
    if _canonical_json(payload) != package_bytes:
        raise EvidencePackageError("evidence package encoding is not canonical")
    return payload
