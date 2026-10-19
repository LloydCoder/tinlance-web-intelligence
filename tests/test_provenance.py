from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import pytest

from tinlance_web_intelligence.contracts.provenance import (
    AcquisitionProvenance,
    FreshnessStatus,
    ProvenanceError,
    assess_freshness,
    validate_evidence_pack,
)


def _manifest() -> AcquisitionProvenance:
    return AcquisitionProvenance.from_capture(
        requested_url="https://example.com/path?token=not-retained",
        final_url="https://example.com/final",
        status_code=200,
        content_type="text/html",
        body=b"<html>evidence</html>",
        retrieved_at=datetime(2026, 10, 19, 7, 0, tzinfo=UTC),
        redirect_count=1,
        extractor_version="twi-html-extractor-v1",
    )


def test_manifest_records_hashes_and_collection_facts_without_raw_url() -> None:
    manifest = _manifest()
    payload = manifest.to_dict()
    assert payload["schema_version"] == "1.0.0"
    assert payload["requested_url_sha256"] == sha256(
        b"https://example.com/path?token=not-retained"
    ).hexdigest()
    assert payload["content_sha256"] == sha256(b"<html>evidence</html>").hexdigest()
    assert payload["byte_size"] == len(b"<html>evidence</html>")
    assert payload["redirect_count"] == 1
    assert "token=not-retained" not in str(payload)
    assert "accurate" not in str(payload)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"content_sha256": "a" * 64 + "x"}, "content_sha256"),
        ({"status_code": 199}, "status_code"),
        ({"redirect_count": -1}, "redirect_count"),
        ({"extractor_version": " "}, "extractor_version"),
        ({"retrieved_at": datetime(2026, 10, 19)}, "timezone-aware"),
    ],
)
def test_manifest_rejects_invalid_collection_facts(
    changes: dict[str, Any], message: str
) -> None:
    manifest = replace(_manifest(), **changes)
    with pytest.raises(ProvenanceError, match=message):
        manifest.validate()


def test_manifest_rejects_credentials_in_source_url() -> None:
    with pytest.raises(ProvenanceError, match="without userinfo"):
        AcquisitionProvenance.from_capture(
            requested_url="https://user:password@example.com/",
            final_url="https://example.com/",
            status_code=200,
            content_type="text/html",
            body=b"content",
            retrieved_at=datetime(2026, 10, 19, tzinfo=UTC),
            redirect_count=0,
            extractor_version="twi-html-extractor-v1",
        )


def test_freshness_policy_boundaries_and_clock_skew() -> None:
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    assert assess_freshness(
        now - timedelta(hours=1), now=now, max_age=timedelta(hours=1)
    ) is FreshnessStatus.FRESH
    assert assess_freshness(
        now - timedelta(hours=1, seconds=1), now=now, max_age=timedelta(hours=1)
    ) is FreshnessStatus.STALE
    assert assess_freshness(
        now + timedelta(minutes=6), now=now, max_age=timedelta(hours=1)
    ) is FreshnessStatus.FUTURE_DATED
    assert assess_freshness(
        now + timedelta(minutes=2), now=now, max_age=timedelta(hours=1)
    ) is FreshnessStatus.FRESH


def test_freshness_policy_rejects_naive_timestamps_and_invalid_age() -> None:
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    with pytest.raises(ProvenanceError, match="timezone-aware"):
        assess_freshness(datetime(2026, 10, 19), now=now, max_age=timedelta(hours=1))
    with pytest.raises(ProvenanceError, match="max_age must be positive"):
        assess_freshness(now, now=now, max_age=timedelta(0))


def test_evidence_pack_requires_consistent_artifact_provenance() -> None:
    manifest = _manifest()
    serialized = manifest.to_dict()
    pack: dict[str, object] = {
        "artifact_id": f"sha256:{manifest.content_sha256}",
        "content_sha256": manifest.content_sha256,
        "status_code": manifest.status_code,
        "content_type": manifest.content_type,
        "retrieved_at": manifest.retrieved_at.isoformat(),
        "provenance": serialized,
    }
    validate_evidence_pack(pack)
    pack["content_sha256"] = "a" * 64
    with pytest.raises(ProvenanceError, match="does not match provenance"):
        validate_evidence_pack(pack)


def test_evidence_pack_rejects_missing_provenance() -> None:
    with pytest.raises(ProvenanceError, match="manifest is missing"):
        validate_evidence_pack({"artifact_id": "sha256:" + "a" * 64})
