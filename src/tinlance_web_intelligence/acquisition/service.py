"""Composition of safe fetch, content-addressed artifacts, and deterministic extraction."""

from __future__ import annotations

import os

from tinlance_web_intelligence.acquisition.fetcher import SafeHTTPFetcher
from tinlance_web_intelligence.acquisition.models import AcquiredPage
from tinlance_web_intelligence.artifacts.store import ArtifactStore, MemoryArtifactStore
from tinlance_web_intelligence.extraction.html import extract_html


class UnsupportedMediaType(RuntimeError):
    """The current extractor cannot safely interpret the acquired representation."""


class WebAcquisitionService:
    def __init__(
        self,
        fetcher: SafeHTTPFetcher | None = None,
        artifacts: ArtifactStore | None = None,
    ) -> None:
        self._fetcher = fetcher or SafeHTTPFetcher()
        environment = os.environ.get("TWI_ENV", "development").lower()
        if environment in {"staging", "production"} and (
            artifacts is None or isinstance(artifacts, MemoryArtifactStore)
        ):
            raise RuntimeError("staging and production require a durable artifact store")
        self._artifacts = artifacts or MemoryArtifactStore()

    async def acquire_page(
        self, url: str, *, tenant_id: str = "development"
    ) -> AcquiredPage:
        fetched = await self._fetcher.fetch(url)
        if fetched.content_type not in {"text/html", "application/xhtml+xml"}:
            raise UnsupportedMediaType("only HTML and XHTML are supported in this workstream")
        try:
            html = fetched.body.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise UnsupportedMediaType("HTML response is not valid UTF-8") from exc
        artifact = self._artifacts.put(
            body=fetched.body,
            content_type=fetched.content_type,
            source_url=fetched.final_url,
            captured_at=fetched.retrieved_at,
            tenant_id=tenant_id,
        )
        extracted = extract_html(html, fetched.final_url)
        return AcquiredPage(fetched, artifact.artifact_id, artifact.sha256, extracted)
