"""Explicit search-provider registration with no silent provider substitution."""

from __future__ import annotations

from tinlance_web_intelligence.search.base import SearchProvider, SearchProviderError


class SearchRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, SearchProvider] = {}

    def register(self, provider: SearchProvider) -> None:
        name = provider.name.strip().lower()
        if not name or name in self._providers:
            raise SearchProviderError("provider name must be unique and non-empty")
        self._providers[name] = provider

    def get(self, name: str) -> SearchProvider:
        try:
            return self._providers[name.lower()]
        except KeyError as exc:
            raise SearchProviderError("search provider is not configured") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))
