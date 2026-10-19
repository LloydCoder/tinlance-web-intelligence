from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tinlance_web_intelligence.api.http.app import create_app
from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.commercial.entitlements import PlanEntitlements
from tinlance_web_intelligence.commercial.usage_ledger import SQLiteUsageLedger
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository

TEST_JTI = "usage-api-test"
TEST_CREDENTIAL = "valid-credential"


class FakeVerifier:
    def __init__(self, value: Principal) -> None:
        self.value = value

    def verify(self, token: str) -> Principal:
        if token != TEST_CREDENTIAL:
            raise PermissionError("invalid credential")
        return self.value


def make_principal(
    tenant: str = "tenant-a",
    subject: str = "subject-a",
    scopes: frozenset[str] = frozenset({"twi:usage:read"}),
) -> Principal:
    return Principal(
        tenant_id=tenant, subject_id=subject, client_id="test-client",
        principal_type="user", token_id=TEST_JTI, scopes=scopes, roles=frozenset(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def test_usage_endpoint_requires_scope_and_uses_verified_identity() -> None:
    jobs = SQLiteJobRepository(":memory:")
    usage = SQLiteUsageLedger(":memory:")
    reservation = usage.reserve(
        tenant_id="tenant-a", subject_id="subject-a", feature="fetch",
        dimension="requests_month", period_start="2026-10-01T00:00:00Z",
        quantity=2, limit=10, idempotency_key="usage-event-key-0001",
    )
    usage.commit(
        tenant_id="tenant-a", subject_id="subject-a",
        reservation_id=reservation.reservation_id,
    )
    app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=jobs, usage_ledger=usage,
        verifier=FakeVerifier(make_principal()),
    )
    client = TestClient(app)
    response = client.get(
        "/v1/usage?dimension=requests_month&period_start=2026-10-01T00:00:00Z",
        headers={"Authorization": f"Bearer {TEST_CREDENTIAL}"},
    )
    assert response.status_code == 200
    assert response.json()["used"] == 2
    assert len(response.json()["events"]) == 1
    assert "tenant_id" not in response.json()["events"][0]
    assert "subject_id" not in response.json()["events"][0]

    other_app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=jobs, usage_ledger=usage,
        verifier=FakeVerifier(make_principal(tenant="tenant-b", subject="subject-b")),
    )
    other = TestClient(other_app).get(
        "/v1/usage?dimension=requests_month&period_start=2026-10-01T00:00:00Z",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert other.status_code == 200
    assert other.json()["used"] == 0
    usage.close()
    jobs.close()


def test_usage_endpoint_fails_closed_without_read_scope() -> None:
    jobs = SQLiteJobRepository(":memory:")
    usage = SQLiteUsageLedger(":memory:")
    app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=jobs, usage_ledger=usage,
        verifier=FakeVerifier(make_principal(scopes=frozenset({"twi:search"}))),
    )
    response = TestClient(app).get(
        "/v1/usage?dimension=requests_month&period_start=2026-10-01T00:00:00Z",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert response.status_code == 403
    usage.close()
    jobs.close()



class FakeEntitlementResolver:
    def __init__(self, plan: PlanEntitlements | None) -> None:
        self.plan = plan

    def resolve(self, *, tenant_id: str, subject_id: str) -> PlanEntitlements | None:
        assert tenant_id and subject_id
        return self.plan


def test_usage_endpoint_returns_plan_quota_and_remaining_allowance() -> None:
    jobs = SQLiteJobRepository(":memory:")
    usage = SQLiteUsageLedger(":memory:")
    reservation = usage.reserve(
        tenant_id="tenant-a", subject_id="subject-a", feature="search",
        dimension="search_requests_month", period_start="2026-10-01T00:00:00Z",
        quantity=2, limit=5, idempotency_key="quota-view-event-0001",
    )
    usage.commit(
        tenant_id="tenant-a", subject_id="subject-a",
        reservation_id=reservation.reservation_id,
    )
    plan = PlanEntitlements(
        plan_id="customer-basic", version=3, features=frozenset({"search"}),
        limits={"search_requests_month": 5},
    )
    app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=jobs, usage_ledger=usage,
        verifier=FakeVerifier(make_principal()),
        entitlement_resolver=FakeEntitlementResolver(plan),
    )
    response = TestClient(app).get(
        "/v1/usage?dimension=search_requests_month&period_start=2026-10-01T00:00:00Z",
        headers={"Authorization": f"Bearer {TEST_CREDENTIAL}"},
    )
    assert response.status_code == 200
    assert response.json()["quota_limit"] == 5
    assert response.json()["remaining"] == 3
    assert response.json()["plan_id"] == "customer-basic"
    assert response.json()["plan_version"] == 3
    usage.close()
    jobs.close()



def test_usage_export_uses_stable_cursor_pagination() -> None:
    jobs = SQLiteJobRepository(":memory:")
    usage = SQLiteUsageLedger(":memory:")
    for index in range(3):
        reservation = usage.reserve(
            tenant_id="tenant-a", subject_id="subject-a", feature="search",
            dimension="search_requests_month", period_start="2026-10-01T00:00:00Z",
            quantity=1, limit=10, idempotency_key=f"cursor-event-key-{index:04d}",
        )
        usage.commit(
            tenant_id="tenant-a", subject_id="subject-a",
            reservation_id=reservation.reservation_id,
        )
    app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=jobs, usage_ledger=usage,
        verifier=FakeVerifier(make_principal()),
    )
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {TEST_CREDENTIAL}"}
    first = client.get(
        "/v1/usage",
        params={
            "dimension": "search_requests_month",
            "period_start": "2026-10-01T00:00:00Z",
            "limit": 2,
        },
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["has_more"] is True
    assert first.json()["next_cursor"]
    second = client.get(
        "/v1/usage",
        params={
            "dimension": "search_requests_month",
            "period_start": "2026-10-01T00:00:00Z",
            "limit": 2,
            "cursor": first.json()["next_cursor"],
        },
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["has_more"] is False
    assert second.json()["next_cursor"] is None
    ids = [event["event_id"] for event in first.json()["events"] + second.json()["events"]]
    assert len(ids) == len(set(ids)) == 3
    invalid = client.get(
        "/v1/usage",
        params={
            "dimension": "search_requests_month",
            "period_start": "2026-10-01T00:00:00Z",
            "cursor": "not-a-valid-cursor",
        },
        headers=headers,
    )
    assert invalid.status_code == 422
    usage.close()
    jobs.close()
