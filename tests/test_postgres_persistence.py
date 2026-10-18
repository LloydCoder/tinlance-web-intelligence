"""PostgreSQL contract tests. CI supplies an ephemeral PostgreSQL service."""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256

import pytest

from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    OutboxConflictError,
    OutboxLeaseLostError,
)
from tinlance_web_intelligence.jobs.model import (
    IdempotencyConflictError,
    JobStatus,
    LeaseLostError,
)
from tinlance_web_intelligence.persistence.postgres_jobs import PostgresJobRepository
from tinlance_web_intelligence.persistence.postgres_outbox import PostgresSourceEvidenceOutbox

_DSN = os.environ.get("TWI_TEST_POSTGRES_DSN")
pytestmark = pytest.mark.skipif(not _DSN, reason="TWI_TEST_POSTGRES_DSN is not configured")


def test_postgres_jobs_are_idempotent_scoped_and_recoverable() -> None:
    assert _DSN is not None
    repository = PostgresJobRepository(_DSN, min_size=1, max_size=10, auto_migrate=True)
    tenant = f"tenant-{uuid.uuid4()}"
    subject = f"subject-{uuid.uuid4()}"
    try:
        created = repository.create(
            tenant_id=tenant, subject_id=subject, kind="fetch",
            payload={"url": "https://example.com/"}, idempotency_key="job-idempotency-key-0001",
        )
        replay = repository.create(
            tenant_id=tenant, subject_id=subject, kind="fetch",
            payload={"url": "https://example.com/"}, idempotency_key="job-idempotency-key-0001",
        )
        assert replay.job_id == created.job_id
        with pytest.raises(IdempotencyConflictError):
            repository.create(
                tenant_id=tenant, subject_id=subject, kind="fetch",
                payload={"url": "https://example.org/"}, idempotency_key="job-idempotency-key-0001",
            )
        assert repository.get(created.job_id, tenant_id="another-tenant") is None
        claimed = repository.claim_next("postgres-test-worker", allowed_kinds=("fetch",))
        assert claimed is not None and claimed.job_id == created.job_id
        completed = repository.complete(
            created.job_id, "postgres-test-worker", {"content_sha256": "a" * 64}
        )
        assert completed.status == JobStatus.SUCCEEDED
        assert repository.get(created.job_id, tenant_id=tenant, subject_id=subject) == completed

        queued = repository.create(
            tenant_id=tenant, subject_id=subject, kind="fetch",
            payload={"url": "https://example.net/"}, idempotency_key="cancel-queued-job-0001",
        )
        queued_cancelled = repository.cancel(
            queued.job_id, tenant_id=tenant, subject_id=subject
        )
        assert queued_cancelled is not None and queued_cancelled.status == JobStatus.CANCELLED

        running = repository.create(
            tenant_id=tenant, subject_id=subject, kind="fetch",
            payload={"url": "https://example.org/"}, idempotency_key="cancel-running-job-0001",
        )
        running_claim = repository.claim_next("cancel-worker", allowed_kinds=("fetch",))
        assert running_claim is not None and running_claim.job_id == running.job_id
        cancel_requested = repository.cancel(
            running.job_id, tenant_id=tenant, subject_id=subject
        )
        assert cancel_requested is not None and cancel_requested.cancel_requested
        completed_cancelled = repository.complete(
            running.job_id, "cancel-worker", {"should_not_be_persisted": True}
        )
        assert completed_cancelled.status == JobStatus.CANCELLED
        assert completed_cancelled.result is None

        retryable = repository.create(
            tenant_id=tenant, subject_id=subject, kind="fetch",
            payload={"url": "https://retry.example/"}, idempotency_key="retryable-job-0001",
        )
        retry_claim = repository.claim_next("retry-worker", allowed_kinds=("fetch",))
        assert retry_claim is not None and retry_claim.job_id == retryable.job_id
        retried = repository.fail(
            retryable.job_id, "retry-worker", error_code="temporary_error", retryable=True
        )
        assert retried.status == JobStatus.QUEUED and retried.error_code == "temporary_error"
        assert repository.ping()
    finally:
        repository.close()


def test_postgres_job_claims_are_unique_across_workers() -> None:
    assert _DSN is not None
    repository = PostgresJobRepository(_DSN, min_size=1, max_size=10, auto_migrate=True)
    namespace = uuid.uuid4().hex
    try:
        for index in range(8):
            repository.create(
                tenant_id=f"tenant-{namespace}-{index}",
                subject_id=f"subject-{namespace}-{index}",
                kind="fetch", payload={"url": "https://example.com/"},
                idempotency_key=f"parallel-job-{namespace}-{index}",
            )
        with ThreadPoolExecutor(max_workers=8) as executor:
            claimed = list(executor.map(
                lambda index: repository.claim_next(f"worker-{namespace}-{index}",
                                                    allowed_kinds=("fetch",)),
                range(8),
            ))
        assert all(job is not None for job in claimed)
        assert len({job.job_id for job in claimed if job is not None}) == 8
    finally:
        repository.close()


def test_postgres_outbox_enforces_idempotency_leases_and_scope() -> None:
    assert _DSN is not None
    outbox = PostgresSourceEvidenceOutbox(_DSN, min_size=1, max_size=10, auto_migrate=True)
    tenant_ref = sha256(uuid.uuid4().hex.encode()).hexdigest()
    subject_ref = hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest()
    key = f"outbox-key-{uuid.uuid4().hex}"
    payload = {"schema_version": "1.0.0", "statement": "Source-backed test evidence"}
    try:
        first, replayed = outbox.enqueue(
            tenant_ref=tenant_ref, subject_ref=subject_ref, idempotency_key=key,
            payload=payload, request_id="postgres-outbox-test", traceparent=None,
        )
        replay, was_replay = outbox.enqueue(
            tenant_ref=tenant_ref, subject_ref=subject_ref, idempotency_key=key,
            payload=payload, request_id="postgres-outbox-test", traceparent=None,
        )
        assert not replayed and was_replay and first.event_id == replay.event_id
        with pytest.raises(OutboxConflictError):
            outbox.enqueue(
                tenant_ref=tenant_ref, subject_ref=subject_ref, idempotency_key=key,
                payload={**payload, "statement": "conflicting payload"},
                request_id="postgres-outbox-test", traceparent=None,
            )
        claimed = outbox.claim_next("postgres-outbox-worker")
        assert claimed is not None and claimed.event_id == first.event_id
        assert claimed.lease_token is not None
        delivered = outbox.complete(claimed.event_id, claimed.lease_token, "wi-evidence-1")
        assert delivered.status == "delivered"
        assert outbox.get(first.event_id, tenant_ref, subject_ref) is not None
        assert outbox.get(first.event_id, hashlib.sha256(b"other").hexdigest(), subject_ref) is None
        assert outbox.ping()
    finally:
        outbox.close()


def test_postgres_expired_job_lease_rejects_stale_completion() -> None:
    assert _DSN is not None
    repository = PostgresJobRepository(_DSN, min_size=1, max_size=4, auto_migrate=True)
    namespace = uuid.uuid4().hex
    try:
        created = repository.create(
            tenant_id=f"tenant-expiry-{namespace}",
            subject_id=f"subject-expiry-{namespace}",
            kind="fetch", payload={"url": "https://example.com/"},
            idempotency_key=f"expiry-job-{namespace}",
        )
        claimed = repository.claim_next("stale-worker", lease_seconds=5,
                                        allowed_kinds=("fetch",))
        assert claimed is not None and claimed.job_id == created.job_id
        with repository._pool.connection() as conn:
            conn.execute(
                "UPDATE jobs SET lease_until=%s WHERE job_id=%s",
                (time.time() - 1, created.job_id),
            )
        with pytest.raises(LeaseLostError):
            repository.complete(created.job_id, "stale-worker", {"stale": True})
        reclaimed = repository.claim_next("fresh-worker", allowed_kinds=("fetch",))
        assert reclaimed is not None and reclaimed.job_id == created.job_id
    finally:
        repository.close()


def test_postgres_outbox_expired_lease_cannot_be_completed_by_stale_worker() -> None:
    assert _DSN is not None
    outbox = PostgresSourceEvidenceOutbox(_DSN, min_size=1, max_size=4, auto_migrate=True)
    tenant_ref = sha256(uuid.uuid4().hex.encode()).hexdigest()
    subject_ref = sha256(uuid.uuid4().hex.encode()).hexdigest()
    key = f"outbox-expiry-{uuid.uuid4().hex}"
    try:
        event, replayed = outbox.enqueue(
            tenant_ref=tenant_ref, subject_ref=subject_ref, idempotency_key=key,
            payload={"schema_version": "1.0.0"}, request_id="outbox-expiry-test",
            traceparent=None,
        )
        assert not replayed
        claimed = outbox.claim_next("stale-outbox-worker")
        assert claimed is not None and claimed.event_id == event.event_id
        assert claimed.lease_token is not None
        with outbox._pool.connection() as conn:
            conn.execute(
                "UPDATE twi_source_evidence_outbox SET lease_until=%s WHERE event_id=%s",
                (time.time() - 1, event.event_id),
            )
        with pytest.raises(OutboxLeaseLostError):
            outbox.complete(event.event_id, claimed.lease_token, "stale-evidence")
        reclaimed = outbox.claim_next("fresh-outbox-worker")
        assert reclaimed is not None and reclaimed.event_id == event.event_id
        assert reclaimed.lease_token is not None
        delivered = outbox.complete(reclaimed.event_id, reclaimed.lease_token, "fresh-evidence")
        assert delivered.status == "delivered"
    finally:
        outbox.close()
