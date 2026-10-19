from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from tinlance_web_intelligence.acquisition.fetcher import FetchError
from tinlance_web_intelligence.acquisition.models import AcquiredPage, ExtractedPage, FetchResult
from tinlance_web_intelligence.jobs.model import Job, JobStatus
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.jobs.worker import JobWorker
from tinlance_web_intelligence.monitors.service import MonitorService
from tinlance_web_intelligence.persistence.sqlite_monitors import SQLiteMonitorRepository
from tinlance_web_intelligence.search.base import SearchResult


class FakeSearchProvider:
    name = "fake"

    async def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        return [SearchResult("Example", "https://example.com/", query, self.name, 1)][:limit]


class SuccessfulAcquisition:
    async def acquire_page(self, url: str, *, tenant_id: str = "development") -> AcquiredPage:
        del tenant_id
        body = b"<html><title>Evidence</title></html>"
        digest = sha256(body).hexdigest()
        fetched = FetchResult(
            requested_url=url,
            final_url="https://example.com/final",
            status_code=200,
            content_type="text/html",
            body=body,
            retrieved_at=datetime(2026, 10, 19, tzinfo=UTC),
            headers={},
            redirect_count=1,
        )
        extracted = ExtractedPage(
            title="Evidence",
            description=None,
            canonical_url=None,
            text="Evidence",
            links=(),
        )
        return AcquiredPage(fetched, f"sha256:{digest}", digest, extracted)


class RetryableAcquisition:
    async def acquire_page(self, url: str, *, tenant_id: str = "development") -> None:
        del url, tenant_id
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

def test_worker_persists_validated_provenance_for_fetch_job() -> None:
    repository = SQLiteJobRepository(":memory:")
    requested_url = "https://example.com/requested?token=must-not-enter-manifest"
    job = create_job(repository, "fetch", {"url": requested_url})
    worker = JobWorker(
        repository,
        worker_id="worker-test",
        acquisition=cast(Any, SuccessfulAcquisition()),
    )
    try:
        assert worker.run_once()
        completed = repository.get(job.job_id, tenant_id="tenant-a", subject_id="subject-a")
        assert completed is not None and completed.status is JobStatus.SUCCEEDED
        assert completed.result is not None
        provenance = completed.result["provenance"]
        assert provenance["schema_version"] == "1.0.0"
        assert provenance["redirect_count"] == 1
        assert provenance["requested_url_sha256"] == sha256(requested_url.encode()).hexdigest()
        assert "token=must-not-enter-manifest" not in str(provenance)
        assert provenance["content_sha256"] == completed.result["content_sha256"]
    finally:
        repository.close()


def test_worker_executes_monitor_and_persists_bounded_change_result(tmp_path: Path) -> None:
    jobs = SQLiteJobRepository(":memory:")
    monitors = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = monitors.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.com/",
        policy={},
        idempotency_key="monitor-create-1",
    )
    service = MonitorService(
        repository=monitors,
        job_repository=jobs,
        acquisition=SuccessfulAcquisition(),
    )
    run = service.enqueue_run(
        tenant_id="tenant-a",
        subject_id="subject-a",
        monitor_id=monitor.monitor_id,
        idempotency_key="monitor-run-1",
        traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    )
    worker = JobWorker(
        jobs,
        worker_id="monitor-worker",
        monitor_service=service,
        allowed_kinds=("monitor",),
    )

    assert worker.run_once()
    completed = jobs.get(run.job_id, tenant_id="tenant-a", subject_id="subject-a")
    assert completed is not None and completed.status is JobStatus.SUCCEEDED
    assert completed.result is not None
    assert completed.result["outcome"] == "baseline_established"
    assert completed.result["artifact_id"].startswith("sha256:")
    assert "text" not in completed.result
    assert "url" not in completed.result
    updated = monitors.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert updated is not None and updated.baseline_version == 1
    jobs.close()
    monitors.close()


def test_failed_monitor_capture_does_not_advance_baseline(tmp_path: Path) -> None:
    jobs = SQLiteJobRepository(":memory:")
    monitors = SQLiteMonitorRepository(str(tmp_path / "monitors.sqlite3"))
    monitor = monitors.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        target_url="https://example.com/",
        policy={},
        idempotency_key="monitor-create-2",
    )
    service = MonitorService(
        repository=monitors,
        job_repository=jobs,
        acquisition=cast(Any, RetryableAcquisition()),
    )
    run = service.enqueue_run(
        tenant_id="tenant-a",
        subject_id="subject-a",
        monitor_id=monitor.monitor_id,
        idempotency_key="monitor-run-2",
    )
    worker = JobWorker(
        jobs,
        worker_id="monitor-worker",
        monitor_service=service,
        allowed_kinds=("monitor",),
    )

    assert worker.run_once()
    updated_job = jobs.get(run.job_id, tenant_id="tenant-a", subject_id="subject-a")
    assert updated_job is not None and updated_job.status is JobStatus.QUEUED
    assert updated_job.error_code == "upstream_failure"
    updated_monitor = monitors.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor.monitor_id
    )
    assert updated_monitor is not None and updated_monitor.baseline_version == 0
    jobs.close()
    monitors.close()

