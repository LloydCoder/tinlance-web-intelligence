from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tinlance_web_intelligence.contracts.evidence_package import (
    EvidencePackageError,
    build_evidence_package,
    validate_evidence_package,
)
from tinlance_web_intelligence.contracts.provenance import AcquisitionProvenance

_REVISION = "a" * 40


def _fixture() -> tuple[bytes, dict[str, str | int]]:
    body = b"<html><title>Public page</title><p>Evidence</p></html>"
    manifest = AcquisitionProvenance.from_capture(
        requested_url="https://example.test/page?api_key=must-not-appear",
        final_url="https://example.test/final",
        status_code=200,
        content_type="text/html",
        body=body,
        retrieved_at=datetime(2026, 10, 19, 10, 0, tzinfo=UTC),
        redirect_count=1,
        extractor_version="twi-html-extractor-v1",
    )
    return body, manifest.to_dict()


def _build(body: bytes, manifest: dict[str, str | int]) -> bytes:
    return build_evidence_package(
        body=body,
        content_type="text/html",
        provenance=manifest,
        source_revision=_REVISION,
    )


def test_package_is_deterministic_and_round_trips_integrity() -> None:
    body, manifest = _fixture()
    first = _build(body, manifest)
    second = _build(body, manifest)
    assert first == second
    payload = validate_evidence_package(first, expected_source_revision=_REVISION)
    assert base64.b64decode(payload["content_base64"], validate=True) == body
    assert payload["content_sha256"] == sha256(body).hexdigest()
    assert payload["artifact_id"] == f"sha256:{sha256(body).hexdigest()}"
    assert payload["interpretation"]["truth_assessment"] == "not_provided"


def test_package_omits_raw_urls_and_sensitive_query_values() -> None:
    body, manifest = _fixture()
    exported = _build(body, manifest)
    assert b"api_key=must-not-appear" not in exported
    assert b"https://example.test" not in exported


def test_package_rejects_bytes_or_metadata_not_matching_provenance() -> None:
    body, manifest = _fixture()
    with pytest.raises(EvidencePackageError, match="do not match acquisition provenance"):
        _build(body + b"tampered", manifest)
    with pytest.raises(EvidencePackageError, match="content type"):
        build_evidence_package(
            body=body,
            content_type="application/json",
            provenance=manifest,
            source_revision=_REVISION,
        )


def test_validator_detects_content_tampering_and_revision_drift() -> None:
    body, manifest = _fixture()
    package = json.loads(_build(body, manifest))
    package["content_base64"] = base64.b64encode(b"tampered").decode("ascii")
    tampered = json.dumps(package, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(EvidencePackageError, match="integrity verification"):
        validate_evidence_package(tampered)
    with pytest.raises(EvidencePackageError, match="revision mismatch"):
        validate_evidence_package(_build(body, manifest), expected_source_revision="b" * 40)


def test_validator_rejects_modified_export_id_and_noncanonical_json() -> None:
    body, manifest = _fixture()
    package = json.loads(_build(body, manifest))
    package["export_id"] = "sha256:" + "0" * 64
    modified = json.dumps(package, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(EvidencePackageError, match="export_id integrity"):
        validate_evidence_package(modified)
    with pytest.raises(EvidencePackageError, match="canonical"):
        validate_evidence_package(json.dumps(json.loads(_build(body, manifest))).encode())


def test_package_rejects_invalid_source_revision_and_oversized_input() -> None:
    body, manifest = _fixture()
    with pytest.raises(EvidencePackageError, match="full lowercase Git"):
        build_evidence_package(
            body=body,
            content_type="text/html",
            provenance=manifest,
            source_revision="main",
        )
    with pytest.raises(EvidencePackageError, match="30 MB"):
        validate_evidence_package(b"x" * 30_000_001)


def test_export_matches_published_json_schema() -> None:
    body, manifest = _fixture()
    package = json.loads(_build(body, manifest))
    schema_path = (
        Path(__file__).resolve().parents[1] / "schemas" / "twi-evidence-package-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
        package
    )
