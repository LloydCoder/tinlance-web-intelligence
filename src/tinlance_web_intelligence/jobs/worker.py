"""Lease-based worker that executes only explicitly supported acquisition job types."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from tinlance_web_intelligence.acquisition.fetcher import FetchError, SafeHTTPFetcher
from tinlance_web_intelligence.browser.service import BrowserCaptureError, BrowserService
from tinlance_web_intelligence.acquisition.service import (
    UnsupportedMediaType,
    WebAcquisitionService,
)
from tinlance_web_intelligence.jobs.model import Job, LeaseLostError
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.search.base import SearchProvider, SearchProviderError


class JobWorker:
    def __init__(
        self,
        repository: SQLiteJobRepository,
        *,
        worker_id: str,
        acquisition: WebAcquisitionService | None = None,
        search_provider: SearchProvider | None = None,
        browser_service: BrowserService | None = None,
        allowed_kinds: tuple[str, ...] = ("search", "fetch"),
        lease_seconds: int = 180,
    ) -> None:
        self.repository = repository
        self.worker_id = worker_id
        self.allowed_kinds = allowed_kinds
        self.acquisition = acquisition or WebAcquisitionService(SafeHTTPFetcher())
        self.search_provider = search_provider
        self.browser_service = browser_service
        self.lease_seconds = lease_seconds

    def run_once(self) -> bool:
        job = self.repository.claim_next(self.worker_id, lease_seconds=self.lease_seconds, allowed_kinds=self.allowed_kinds)
        if job is None:
            return False
        try:
            result = self._execute(job)
        except BrowserCaptureError as exc:
            self._fail(job, exc.error_code, exc.retryable)
        except FetchError as exc:
            self._fail(job, "upstream_failure", bool(getattr(exc, "retryable", False)))
        except SearchProviderError as exc:
            self._fail(job, "search_provider_failure", bool(getattr(exc, "retryable", False)))
        except UnsupportedMediaType:
            self._fail(job, "unsupported_media_type", False)
        except Exception:
            self._fail(job, "worker_error", False)
        else:
            try:
                self.repository.complete(job.job_id, self.worker_id, result)
            except LeaseLostError:
                # Another worker reclaimed an expired lease; stale workers must not overwrite it.
                return True
        return True

    def _execute(self, job: Job) -> dict[str, Any]:
        if job.kind == "browser":
            if self.browser_service is None:
                raise BrowserCaptureError("browser_not_configured")
            return asyncio.run(
                self.browser_service.capture(
                    url=job.payload["url"],
                    wait_until=job.payload["wait_until"],
                    timeout_ms=job.payload["timeout_ms"],
                    include_screenshot=job.payload["include_screenshot"],
                )
            )
        if job.kind == "search":
            if self.search_provider is None:
                raise SearchProviderError("search provider is not configured")
            query = job.payload["query"]
            limit = job.payload["limit"]
            results = asyncio.run(self.search_provider.search(query, limit=limit))
            return {
                "provider": self.search_provider.name,
                "results": [asdict(item) for item in results],
            }
        if job.kind == "fetch":
            page = asyncio.run(self.acquisition.acquire_page(job.payload["url"]))
            return {
                "source_url": page.fetch.final_url,
                "retrieved_at": page.fetch.retrieved_at.isoformat(),
                "status_code": page.fetch.status_code,
                "content_type": page.fetch.content_type,
                "artifact_id": page.artifact_id,
                "content_sha256": page.content_sha256,
                "title": page.extracted.title,
                "description": page.extracted.description,
                "canonical_url": page.extracted.canonical_url,
                "text": page.extracted.text,
                "links": list(page.extracted.links[:100]),
            }
        raise ValueError("unsupported job kind")

    def _fail(self, job: Job, error_code: str, retryable: bool) -> None:
        try:
            self.repository.fail(
                job.job_id,
                self.worker_id,
                error_code=error_code,
                retryable=retryable,
            )
        except LeaseLostError:
            return
