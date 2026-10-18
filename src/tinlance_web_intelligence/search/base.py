"""Provider-neutral search contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    rank: int


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, *, limit: int = 10) -> list[SearchResult]: ...


class SearchProviderError(RuntimeError):
    """Provider configuration or response could not be used safely."""
