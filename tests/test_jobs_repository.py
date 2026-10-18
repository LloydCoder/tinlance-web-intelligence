from __future__ import annotations

import time
from pathlib import Path

import pytest

from tinlance_web_intelligence.jobs.model import (
    IdempotencyConflictError,
    Job,
    JobStatus,
    LeaseLostError,
)
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository


def create_job(
    repository: SQLiteJobRepository, key: str = "request-key-000001"
) -> Job:
    return repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind="search",
        payload={"query": "example", "limit": 5},
        idempotency_key=key,
    )


def test_idempotency_is_scoped_and_persisted(tmp_path: Path) -> None:
    path = str(tmp_path / "jobs.sqlite3")
    repository = SQLiteJobRepository(path)
    first = create_job(repository)
    replay = create_job(repository)
    assert first.job_id == replay.job_id
    with pytest.raises(IdempotencyConflictError):
        repository.create(
            tenant_id="tenant-a",
            subject_id="subject-a",
            kind="search",
            payload={"query": "different", "limit": 5},
            idempotency_key="request-key-000001",
        )
    assert repository.get(first.job_id, tenant_id="tenant-b") is None
    repository.close()
    reopened = SQLiteJobRepository(path)
    assert reopened.get(first.job_id, tenant_id="tenant-a", subject_id="subject-a") is not None
    reopened.close()


def test_claim_and_complete_enforce_lease_owner() -> None:
    repository = SQLiteJobRepository(":memory:")
    created = create_job(repository)
    claimed = repository.claim_next("worker-a")
    assert claimed is not None
    assert claimed.job_id == created.job_id
    assert claimed.status is JobStatus.RUNNING
    assert claimed.attempts == 1
    with pytest.raises(LeaseLostError):
        repository.complete(created.job_id, "worker-b", {"unexpected": True})
    completed = repository.complete(created.job_id, "worker-a", {"count": 1})
    assert completed.status is JobStatus.SUCCEEDED
    assert completed.result == {"count": 1}
    assert repository.claim_next("worker-a") is None
    repository.close()


def test_expired_lease_is_recovered_without_stale_worker_overwrite() -> None:
    repository = SQLiteJobRepository(":memory:")
    created = create_job(repository)
    first = repository.claim_next("worker-a", lease_seconds=5)
    assert first is not None
    with repository._lock:
        repository._connection.execute(
            "UPDATE jobs SET lease_until=? WHERE job_id=?", (time.time() - 1, created.job_id)
        )
    second = repository.claim_next("worker-b", lease_seconds=5)
    assert second is not None
    assert second.job_id == created.job_id
    assert second.attempts == 2
    with pytest.raises(LeaseLostError):
        repository.complete(created.job_id, "worker-a", {"stale": True})
    repository.close()


def test_running_cancel_is_observed_at_completion() -> None:
    repository = SQLiteJobRepository(":memory:")
    created = create_job(repository)
    claimed = repository.claim_next("worker-a")
    assert claimed is not None
    requested = repository.cancel(
        created.job_id, tenant_id="tenant-a", subject_id="subject-a"
    )
    assert requested is not None and requested.cancel_requested
    finished = repository.complete(created.job_id, "worker-a", {"should": "not persist"})
    assert finished.status is JobStatus.CANCELLED
    assert finished.result is None
    repository.close()
