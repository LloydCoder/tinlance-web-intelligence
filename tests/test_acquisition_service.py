import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from tinlance_web_intelligence.acquisition.models import FetchResult
from tinlance_web_intelligence.acquisition.service import WebAcquisitionService
from tinlance_web_intelligence.artifacts.store import MemoryArtifactStore


class FakeFetcher:
    async def fetch(self, url: str) -> FetchResult:
        body = b"<html><title>Example</title><p>Source-backed text.</p></html>"
        return FetchResult(
            requested_url=url,
            final_url="https://example.com/article",
            status_code=200,
            content_type="text/html",
            body=body,
            retrieved_at=datetime.now(UTC),
            headers={},
        )


def test_acquisition_service_records_artifact_and_extracts_text() -> None:
    store = MemoryArtifactStore()
    service = WebAcquisitionService(cast(Any, FakeFetcher()), store)
    result = asyncio.run(service.acquire_page("https://example.com/article"))
    assert result.extracted.title == "Example"
    assert "Source-backed text." in result.extracted.text
    assert result.artifact_id == f"sha256:{result.content_sha256}"
    assert store.get(result.content_sha256) is not None


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_non_dev_requires_explicit_durable_artifact_store(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setenv("TWI_ENV", environment)
    with pytest.raises(RuntimeError, match="durable artifact store"):
        WebAcquisitionService(cast(Any, FakeFetcher()))
    with pytest.raises(RuntimeError, match="durable artifact store"):
        WebAcquisitionService(
            cast(Any, FakeFetcher()), MemoryArtifactStore()
        )
