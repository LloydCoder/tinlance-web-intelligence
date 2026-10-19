from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tinlance_web_intelligence.persistence.postgres_jobs import PostgresJobRepository
from tinlance_web_intelligence.persistence.postgres_monitoring import (
    MonitoringLeaseLostError,
    MonitoringObservation,
    PostgresMonitoringRepository,
)


@pytest.fixture
def monitoring_repository() -> Iterator[PostgresMonitoringRepository]:
    dsn = os.environ.get("TWI_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip(
            "TWI_TEST_POSTGRES_DSN is required for PostgreSQL monitoring integration tests"
        )
    migrator = PostgresJobRepository(dsn, auto_migrate=True)
    migrator.close()
    repository = PostgresMonitoringRepository(dsn)
    try:
        yield repository
    finally:
        repository.close()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _observe(
    repository: PostgresMonitoringRepository,
    *,
    tenant_id: str,
    fingerprint: str,
    content: str,
    observed_at: datetime,
    status_code: int = 200,
    content_type: str = "text/html",
) -> MonitoringObservation:
    return repository.observe(
        tenant_id=tenant_id,
        source_fingerprint=fingerprint,
        content_sha256=_digest(content),
        status_code=status_code,
        content_type=content_type,
        observed_at=observed_at,
    )


def test_monitoring_baseline_change_and_idempotent_outbox_delivery(
    monitoring_repository: PostgresMonitoringRepository,
) -> None:
    tenant_id = f"w13-test-{uuid4().hex}"
    fingerprint = _digest("https://example.org/monitor")
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)

    baseline = _observe(
        monitoring_repository,
        tenant_id=tenant_id,
        fingerprint=fingerprint,
        content="version one",
        observed_at=now,
    )
    assert baseline.change_kind == "baseline"
    assert baseline.revision == 1
    assert baseline.event_id is None

    unchanged = _observe(
        monitoring_repository,
        tenant_id=tenant_id,
        fingerprint=fingerprint,
        content="version one",
        observed_at=now + timedelta(minutes=1),
    )
    assert unchanged.change_kind == "unchanged"
    assert unchanged.revision == 1

    changed = _observe(
        monitoring_repository,
        tenant_id=tenant_id,
        fingerprint=fingerprint,
        content="version two",
        observed_at=now + timedelta(minutes=2),
    )
    assert changed.change_kind == "content_changed"
    assert changed.revision == 2
    assert changed.event_id is not None
    assert changed.idempotency_key is not None

    replay = _observe(
        monitoring_repository,
        tenant_id=tenant_id,
        fingerprint=fingerprint,
        content="version two",
        observed_at=now + timedelta(minutes=2),
    )
    assert replay.change_kind == "unchanged"
    assert replay.event_id is None

    claimed = monitoring_repository.claim_pending_events(
        "w13-worker-a", now=now + timedelta(minutes=3)
    )
    event = next(item for item in claimed if item.event_id == changed.event_id)
    assert event.attempts == 1
    assert event.payload["change_kind"] == "content_changed"
    assert "source_url" not in event.payload
    assert "https://" not in json.dumps(event.payload)
    assert hashlib.sha256(
        json.dumps(event.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest() == event.payload_sha256

    assert monitoring_repository.retry_event(
        event.event_id,
        "w13-worker-a",
        error_code="delivery_timeout",
        delay_seconds=5,
        now=now + timedelta(minutes=3, seconds=1),
    ) == "pending"
    claimed_again = monitoring_repository.claim_pending_events(
        "w13-worker-b", now=now + timedelta(minutes=3, seconds=7)
    )
    event_again = next(item for item in claimed_again if item.event_id == changed.event_id)
    assert event_again.attempts == 2
    monitoring_repository.mark_delivered(
        event_again.event_id,
        "w13-worker-b",
        now=now + timedelta(minutes=3, seconds=8),
    )
    snapshot = monitoring_repository.metrics_snapshot(now=now + timedelta(minutes=3, seconds=9))
    assert snapshot["monitoring_events_delivered"] >= 1


def test_monitoring_is_tenant_scoped_and_rejects_out_of_order_updates(
    monitoring_repository: PostgresMonitoringRepository,
) -> None:
    tenant_a = f"w13-test-{uuid4().hex}"
    tenant_b = f"w13-test-{uuid4().hex}"
    fingerprint = _digest("https://example.org/shared-source")
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)

    for tenant in (tenant_a, tenant_b):
        assert _observe(
            monitoring_repository,
            tenant_id=tenant,
            fingerprint=fingerprint,
            content="baseline",
            observed_at=now,
        ).change_kind == "baseline"

    changed = _observe(
        monitoring_repository,
        tenant_id=tenant_a,
        fingerprint=fingerprint,
        content="new state",
        observed_at=now + timedelta(minutes=2),
    )
    assert changed.change_kind == "content_changed"

    out_of_order = _observe(
        monitoring_repository,
        tenant_id=tenant_a,
        fingerprint=fingerprint,
        content="stale baseline",
        observed_at=now + timedelta(minutes=1),
    )
    assert out_of_order.change_kind == "out_of_order"
    assert out_of_order.revision == 2

    tenant_b_unchanged = _observe(
        monitoring_repository,
        tenant_id=tenant_b,
        fingerprint=fingerprint,
        content="baseline",
        observed_at=now + timedelta(minutes=3),
    )
    assert tenant_b_unchanged.change_kind == "unchanged"
    assert tenant_b_unchanged.revision == 1


def test_expired_monitoring_lease_is_reclaimed_and_stale_worker_is_fenced(
    monitoring_repository: PostgresMonitoringRepository,
) -> None:
    tenant_id = f"w13-test-{uuid4().hex}"
    fingerprint = _digest("https://example.org/lease")
    now = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)
    _observe(
        monitoring_repository,
        tenant_id=tenant_id,
        fingerprint=fingerprint,
        content="first",
        observed_at=now,
    )
    changed = _observe(
        monitoring_repository,
        tenant_id=tenant_id,
        fingerprint=fingerprint,
        content="second",
        observed_at=now + timedelta(seconds=1),
    )
    assert changed.event_id is not None
    first = monitoring_repository.claim_pending_events(
        "w13-worker-old",
        lease_seconds=5,
        now=now + timedelta(seconds=2),
    )
    assert any(event.event_id == changed.event_id for event in first)
    second = monitoring_repository.claim_pending_events(
        "w13-worker-new",
        lease_seconds=30,
        now=now + timedelta(seconds=8),
    )
    reclaimed = next(event for event in second if event.event_id == changed.event_id)
    assert reclaimed.attempts == 2
    with pytest.raises(MonitoringLeaseLostError):
        monitoring_repository.mark_delivered(
            changed.event_id, "w13-worker-old", now=now + timedelta(seconds=9)
        )
    monitoring_repository.mark_delivered(
        changed.event_id, "w13-worker-new", now=now + timedelta(seconds=10)
    )
