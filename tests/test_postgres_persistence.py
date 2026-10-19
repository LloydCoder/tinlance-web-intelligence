"""PostgreSQL contract tests. CI supplies an ephemeral PostgreSQL service."""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from psycopg.errors import RaiseException

from tinlance_web_intelligence.commercial.usage_ledger import (
    QuotaExceededError,
    UsageConflictError,
)
from tinlance_web_intelligence.persistence.postgres_usage_ledger import PostgresUsageLedger

from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    OutboxConflictError,
    OutboxLeaseLostError,
)
from tinlance_web_intelligence.jobs.model import (
    IdempotencyConflictError,
    JobStatus,
    LeaseLostError,
)
from tinlance_web_intelligence.persistence.postgres_artifacts import PostgresArtifactStore
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
        metrics = repository.metrics_snapshot()
        assert metrics["jobs_succeeded"] >= 1
        assert metrics["jobs_oldest_queued_age_seconds"] >= 0

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
        cutoff = datetime.now(UTC) + timedelta(days=1)
        assert repository.count_expired_results(cutoff, tenant_id=tenant) >= 3
        assert repository.redact_expired_results(cutoff, tenant_id=tenant) >= 3
        redacted = repository.get(created.job_id, tenant_id=tenant, subject_id=subject)
        assert redacted is not None and redacted.status is JobStatus.SUCCEEDED
        assert redacted.payload == {
            "retention_redacted": True,
            "reason": "retention_expired",
        }
        assert redacted.result is None
        assert repository.count_expired_results(cutoff, tenant_id=tenant) == 0
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
        metrics = outbox.metrics_snapshot()
        assert metrics["outbox_pending"] >= 1
        assert metrics["outbox_oldest_pending_age_seconds"] >= 0
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


def test_postgres_artifacts_are_durable_deduplicated_and_tenant_scoped() -> None:
    assert _DSN is not None
    migration = PostgresJobRepository(_DSN, auto_migrate=True)
    store = PostgresArtifactStore(_DSN, max_bytes=1024)
    tenant = f"artifact-tenant-{uuid.uuid4().hex}"
    other_tenant = f"artifact-other-{uuid.uuid4().hex}"
    now = datetime.now(UTC)
    try:
        first = store.put(
            body=b"durable source bytes", content_type="text/html",
            source_url="https://one.example/", captured_at=now, tenant_id=tenant,
        )
        second = store.put(
            body=b"durable source bytes", content_type="text/html",
            source_url="https://two.example/", captured_at=now, tenant_id=tenant,
        )
        other = store.put(
            body=b"durable source bytes", content_type="text/html",
            source_url="https://one.example/", captured_at=now, tenant_id=other_tenant,
        )
        old = store.put(
            body=b"durable source bytes", content_type="text/html",
            source_url="https://one.example/", captured_at=now - timedelta(days=45),
            tenant_id=tenant,
        )
        assert first.sha256 == second.sha256 == other.sha256 == old.sha256
        assert store.get(first.sha256, tenant_id=tenant) == b"durable source bytes"
        assert store.get(first.sha256, tenant_id=other_tenant) == b"durable source bytes"
        assert store.count(tenant_id=tenant) == 3
        assert store.count(tenant_id=other_tenant) == 1
        cutoff = now - timedelta(days=30)
        assert store.count_expired(cutoff, tenant_id=tenant) == 1
        assert store.prune_before(cutoff, tenant_id=tenant) == 1
        assert store.count(tenant_id=tenant) == 2
        assert store.get(first.sha256, tenant_id=tenant) == b"durable source bytes"
        assert store.get(first.sha256, tenant_id="unrelated-tenant") is None
        with pytest.raises(ValueError):
            store.get("invalid-digest", tenant_id=tenant)
    finally:
        store.close()
        migration.close()



def test_postgres_usage_ledger_is_idempotent_scoped_and_append_only() -> None:
    assert _DSN is not None
    migration = PostgresJobRepository(_DSN, auto_migrate=True)
    migration.close()
    ledger = PostgresUsageLedger(_DSN, min_size=1, max_size=8)
    namespace = uuid.uuid4().hex
    tenant, subject = f"usage-tenant-{namespace}", f"usage-subject-{namespace}"
    period = "2026-10-01T00:00:00Z"
    try:
        reservation = ledger.reserve(
            tenant_id=tenant, subject_id=subject, feature="fetch",
            dimension="requests_month", period_start=period, quantity=2, limit=2,
            idempotency_key=f"usage-key-{namespace}",
        )
        replay = ledger.reserve(
            tenant_id=tenant, subject_id=subject, feature="fetch",
            dimension="requests_month", period_start=period, quantity=2, limit=2,
            idempotency_key=f"usage-key-{namespace}",
        )
        assert replay.reservation_id == reservation.reservation_id
        with pytest.raises(UsageConflictError):
            ledger.reserve(
                tenant_id=tenant, subject_id=subject, feature="fetch",
                dimension="requests_month", period_start=period, quantity=1, limit=2,
                idempotency_key=f"usage-key-{namespace}",
            )
        with pytest.raises(QuotaExceededError):
            ledger.reserve(
                tenant_id=tenant, subject_id=subject, feature="fetch",
                dimension="requests_month", period_start=period, quantity=1, limit=2,
                idempotency_key=f"over-quota-{namespace}",
            )
        event = ledger.commit(
            tenant_id=tenant, subject_id=subject, reservation_id=reservation.reservation_id
        )
        assert ledger.commit(
            tenant_id=tenant, subject_id=subject, reservation_id=reservation.reservation_id
        ) == event
        assert ledger.usage_total(
            tenant_id=tenant, subject_id=subject,
            dimension="requests_month", period_start=period,
        ) == 2
        assert ledger.list_events(tenant_id=tenant, subject_id=subject) == [event]
        assert ledger.list_events(tenant_id=f"other-{namespace}", subject_id=subject) == []
        with ledger._pool.connection() as conn:
            with pytest.raises(RaiseException, match="append-only"):
                conn.execute(
                    "UPDATE twi_usage_events SET quantity=9 WHERE event_id=%s", (event.event_id,)
                )
    finally:
        ledger.close()


def test_postgres_usage_quota_reservations_serialize_concurrent_requests() -> None:
    assert _DSN is not None
    migration = PostgresJobRepository(_DSN, auto_migrate=True)
    migration.close()
    ledger = PostgresUsageLedger(_DSN, min_size=1, max_size=10)
    namespace = uuid.uuid4().hex
    tenant, subject = f"quota-tenant-{namespace}", f"quota-subject-{namespace}"
    period = "2026-10-01T00:00:00Z"

    def reserve(index: int) -> bool:
        try:
            ledger.reserve(
                tenant_id=tenant, subject_id=subject, feature="fetch",
                dimension="requests_month", period_start=period, quantity=1, limit=1,
                idempotency_key=f"concurrent-{namespace}-{index}",
            )
            return True
        except QuotaExceededError:
            return False

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(reserve, range(8)))
        assert sum(results) == 1
    finally:
        ledger.close()
