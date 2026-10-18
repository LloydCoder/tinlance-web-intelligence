from __future__ import annotations

from typing import Any, cast

from tinlance_web_intelligence.acquisition.fetcher import FetchError
from tinlance_web_intelligence.jobs.model import Job, JobStatus
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.jobs.worker import JobWorker
from tinlance_web_intelligence.search.base import SearchResult


class FakeSearchProvider:
    name = "fake"

    async def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        return [SearchResult("Example", "https://example.com/", query, self.name, 1)][:limit]


class RetryableAcquisition:
    async def acquire_page(self, url: str) -> None:
        del url
        raise FetchError("temporary upstream failure", retryable=True)


def create_job(
    repository: SQLiteJobRepository, kind: str, payload: dict[str, Any]
) -> Job:
    return repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind=kind,
        payload=payload,
        idempotency_key=f"request-key-{kind}-0001",
    )


def test_worker_completes_search_job() -> None:
    repository = SQLiteJobRepository(":memory:")
    job = create_job(repository, "search", {"query": "example", "limit": 5})
    worker = JobWorker(repository, worker_id="worker-test", search_provider=FakeSearchProvider())
    assert worker.run_once()
    completed = repository.get(job.job_id, tenant_id="tenant-a", subject_id="subject-a")
    assert completed is not None and completed.status is JobStatus.SUCCEEDED
    assert completed.result is not None
    assert completed.result["provider"] == "fake"
    assert completed.result["results"][0]["url"] == "https://example.com/"
    repository.close()


def test_worker_requeues_retryable_fetch_failure() -> None:
    repository = SQLiteJobRepository(":memory:")
    job = create_job(repository, "fetch", {"url": "https://example.com/"})
    worker = JobWorker(
        repository,
        worker_id="worker-test",
        acquisition=cast(Any, RetryableAcquisition()),
    )
    assert worker.run_once()
    updated = repository.get(job.job_id, tenant_id="tenant-a", subject_id="subject-a")
    assert updated is not None
    assert updated.status is JobStatus.QUEUED
    assert updated.error_code == "upstream_failure"
    assert updated.attempts == 1
    repository.close()


def test_worker_fails_closed_without_search_provider() -> None:
    repository = SQLiteJobRepository(":memory:")
    job = create_job(repository, "search", {"query": "example", "limit": 5})
    worker = JobWorker(repository, worker_id="worker-test")
    assert worker.run_once()
    updated = repository.get(job.job_id, tenant_id="tenant-a", subject_id="subject-a")
    assert updated is not None and updated.status is JobStatus.FAILED
    assert updated.error_code == "search_provider_failure"
    repository.close()
