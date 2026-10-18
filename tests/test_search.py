import asyncio
import json
from typing import Any, cast

import pytest

from tinlance_web_intelligence.acquisition.fetcher import SafeHTTPFetcher
from tinlance_web_intelligence.acquisition.models import FetchResult
from tinlance_web_intelligence.search.base import SearchProviderError
from tinlance_web_intelligence.search.brave import BraveSearchProvider
from tinlance_web_intelligence.search.registry import SearchRegistry


class FakeFetcher:
    def __init__(self, body: bytes, content_type: str = "application/json") -> None:
        self.body = body
        self.content_type = content_type
        self.headers: dict[str, str] = {}

    async def fetch(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResult:
        self.headers = headers or {}
        from datetime import UTC, datetime
        return FetchResult(url, url, 200, self.content_type, self.body, datetime.now(UTC), {})


def test_brave_adapter_normalizes_results_and_discards_unsafe_urls() -> None:
    body = json.dumps({"web": {"results": [
        {"title": "Safe", "url": "https://example.com/", "description": "summary"},
        {"title": "Unsafe", "url": "http://127.0.0.1/admin", "description": "bad"},
    ]}}).encode()
    fake = FakeFetcher(body)
    provider = BraveSearchProvider("test-key", cast(Any, fake))
    results = asyncio.run(provider.search("example", limit=5))
    assert len(results) == 1
    assert results[0].url == "https://example.com/"
    assert results[0].rank == 1
    assert fake.headers["X-Subscription-Token"] == "test-key"


def test_provider_requires_key_and_bounds_query() -> None:
    with pytest.raises(SearchProviderError):
        BraveSearchProvider("")
    provider = BraveSearchProvider("key", cast(Any, FakeFetcher(b'{"web":{"results":[]}}')))
    with pytest.raises(SearchProviderError):
        asyncio.run(provider.search(" "))


def test_registry_rejects_duplicate_provider_names() -> None:
    provider = BraveSearchProvider("key", cast(Any, FakeFetcher(b'{"web":{"results":[]}}')))
    registry = SearchRegistry()
    registry.register(provider)
    with pytest.raises(SearchProviderError):
        registry.register(provider)
