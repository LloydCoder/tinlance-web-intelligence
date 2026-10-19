from __future__ import annotations

import sqlite3

import pytest

from tinlance_web_intelligence.commercial.usage_ledger import (
    QuotaExceededError,
    SQLiteUsageLedger,
    UsageConflictError,
    UsageReservation,
)


def ledger() -> SQLiteUsageLedger:
    return SQLiteUsageLedger(":memory:")


def reserve(
    store: SQLiteUsageLedger, *, key: str, quantity: int = 1, limit: int = 2
) -> UsageReservation:
    return store.reserve(
        tenant_id="tenant-a", subject_id="subject-a", feature="fetch",
        dimension="requests_month", period_start="2026-10-01T00:00:00Z",
        quantity=quantity, limit=limit, idempotency_key=key,
    )


def test_reservation_is_idempotent_and_conflicts_on_changed_request() -> None:
    store = ledger()
    first = reserve(store, key="same")
    assert reserve(store, key="same") == first
    with pytest.raises(UsageConflictError):
        reserve(store, key="same", quantity=2)


def test_quota_reservation_is_atomic_and_released_on_failed_submission() -> None:
    store = ledger()
    first = reserve(store, key="one", quantity=2)
    with pytest.raises(QuotaExceededError):
        reserve(store, key="two", quantity=1)
    assert store.release(
        tenant_id="tenant-a", subject_id="subject-a", reservation_id=first.reservation_id
    )
    assert reserve(store, key="two", quantity=1).status == "reserved"


def test_commit_creates_one_immutable_usage_fact_and_is_idempotent() -> None:
    store = ledger()
    reservation = reserve(store, key="operation")
    event = store.commit(
        tenant_id="tenant-a", subject_id="subject-a",
        reservation_id=reservation.reservation_id,
    )
    assert store.commit(
        tenant_id="tenant-a", subject_id="subject-a",
        reservation_id=reservation.reservation_id,
    ) == event
    assert store.usage_total(
        tenant_id="tenant-a", subject_id="subject-a",
        dimension="requests_month", period_start="2026-10-01T00:00:00Z",
    ) == 1
    with pytest.raises(sqlite3.IntegrityError):
        store._connection.execute(
            "UPDATE twi_usage_events SET quantity=99 WHERE event_id=?", (event.event_id,)
        )


def test_tenant_and_subject_scope_isolation() -> None:
    store = ledger()
    reservation = reserve(store, key="private")
    with pytest.raises(KeyError):
        store.commit(
            tenant_id="tenant-b", subject_id="subject-a",
            reservation_id=reservation.reservation_id,
        )
    assert store.list_events(tenant_id="tenant-b", subject_id="subject-a") == []


def test_released_reservation_is_reactivated_on_same_idempotent_retry() -> None:
    store = ledger()
    first = reserve(store, key="retry")
    assert store.release(
        tenant_id="tenant-a", subject_id="subject-a", reservation_id=first.reservation_id
    )
    retried = reserve(store, key="retry")
    assert retried.reservation_id == first.reservation_id
    assert retried.status == "reserved"
    event = store.commit(
        tenant_id="tenant-a", subject_id="subject-a", reservation_id=retried.reservation_id
    )
    assert event.quantity == 1


def test_released_reservation_cannot_be_committed() -> None:
    store = ledger()
    reservation = reserve(store, key="released")
    assert store.release(
        tenant_id="tenant-a", subject_id="subject-a", reservation_id=reservation.reservation_id
    )
    with pytest.raises(ValueError, match="only active reservations"):
        store.commit(
            tenant_id="tenant-a", subject_id="subject-a",
            reservation_id=reservation.reservation_id,
        )


def test_bad_limit_and_quantity_fail_closed() -> None:
    store = ledger()
    with pytest.raises(ValueError):
        reserve(store, key="bool", quantity=True)
    with pytest.raises(ValueError):
        reserve(store, key="negative", limit=-1)
