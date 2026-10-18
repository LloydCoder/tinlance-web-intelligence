"""Brave Search API adapter; API keys are injected and never logged."""

from __future__ import annotations

import json
from urllib.parse import urlencode

from tinlance_web_intelligence.acquisition.fetcher import FetchError, SafeHTTPFetcher
from tinlance_web_intelligence.search.base import SearchProviderError, SearchResult
from tinlance_web_intelligence.security.url_validation import UnsafeURLError, validate_url


class BraveSearchProvider:
    name = "brave"
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, fetcher: SafeHTTPFetcher | None = None) -> None:
        if not api_key or not api_key.strip():
            raise SearchProviderError("Brave Search API key is required")
        self._api_key = api_key.strip()
        self._fetcher = fetcher or SafeHTTPFetcher()

    async def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        normalized_query = " ".join(query.split())
        if not normalized_query or len(normalized_query) > 400:
            raise SearchProviderError("query must contain 1 to 400 characters")
        if not 1 <= limit <= 20:
            raise SearchProviderError("limit must be between 1 and 20")
        url = f"{self.endpoint}?{urlencode({'q': normalized_query, 'count': limit})}"
        try:
            response = await self._fetcher.fetch(
                url,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self._api_key,
                },
            )
        except FetchError as exc:
            raise SearchProviderError("search provider request failed") from exc
        if response.content_type != "application/json":
            raise SearchProviderError("search provider returned an unexpected content type")
        try:
            payload = json.loads(response.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SearchProviderError("search provider returned invalid JSON") from exc
        raw_results = payload.get("web", {}).get("results", []) if isinstance(payload, dict) else []
        results: list[SearchResult] = []
        if not isinstance(raw_results, list):
            raise SearchProviderError("search provider results have an invalid shape")
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            target = item.get("url")
            snippet = item.get("description", "")
            if not isinstance(title, str) or not isinstance(target, str):
                continue
            try:
                safe_url = validate_url(target).normalized
            except (UnsafeURLError, ValueError):
                continue
            results.append(
                SearchResult(
                    title=title[:500],
                    url=safe_url,
                    snippet=snippet[:2000] if isinstance(snippet, str) else "",
                    provider=self.name,
                    rank=len(results) + 1,
                )
            )
            if len(results) >= limit:
                break
        return results
