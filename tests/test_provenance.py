from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from tinlance_web_intelligence.contracts.provenance import (
    AcquisitionProvenance,
    ProvenanceError,
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
    changes: dict[str, object], message: str
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
