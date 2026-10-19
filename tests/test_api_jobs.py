from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tinlance_web_intelligence.api.http.app import create_app
from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.commercial.entitlements import PlanEntitlements
from tinlance_web_intelligence.commercial.usage_ledger import SQLiteUsageLedger, UsageEvent
from tinlance_web_intelligence.config import ConfigurationError, Settings
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository

TEST_JTI = "jti-test-01"


class FakeVerifier:
    def __init__(self, principal: Principal) -> None:
        self.principal = principal

    def verify(self, supplied: str) -> Principal:
        if supplied != "valid-credential":
            raise PermissionError("invalid test credential")
        return self.principal


def principal(
    tenant_id: str = "tenant-a",
    subject_id: str = "subject-a",
    scopes: frozenset[str] = frozenset(
        {"twi:search", "twi:fetch", "twi:browser", "twi:jobs:read", "twi:jobs:cancel"}
    ),
) -> Principal:
    return Principal(
        tenant_id=tenant_id,
        subject_id=subject_id,
        client_id="test-client",
        principal_type="user",
        token_id=TEST_JTI,
        scopes=scopes,
        roles=frozenset(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def client_for(
    *,
    principal_value: Principal | None = None,
    repository: SQLiteJobRepository | None = None,
    browser_enabled: bool = False,
) -> tuple[TestClient, SQLiteJobRepository]:
    repo = repository or SQLiteJobRepository(":memory:")
    app = create_app(
        settings=Settings.from_env({
            "TWI_ENV": "test",
            "TWI_DATABASE_PATH": ":memory:",
            "TWI_BROWSER_ENABLED": "true" if browser_enabled else "false",
        }),
        repository=repo,
        verifier=FakeVerifier(principal_value or principal()),
    )
    return TestClient(app), repo


def test_health_is_public_but_jobs_require_bearer_token() -> None:
    client, repo = client_for()
    assert client.get("/health/live").status_code == 200
    assert client.post(
        "/v1/jobs",
        json={"kind": "search", "payload": {"query": "example"}},
        headers={"Idempotency-Key": "request-key-000001"},
    ).status_code == 401
    repo.close()


def test_job_create_replay_read_and_idempotency_conflict() -> None:
    client, repo = client_for()
    headers = {
        "Authorization": "Bearer valid-credential",
        "Idempotency-Key": "request-key-000001",
    }
    payload = {"kind": "search", "payload": {"query": "  example   query ", "limit": 5}}
    first = client.post("/v1/jobs", json=payload, headers=headers)
    replay = client.post("/v1/jobs", json=payload, headers=headers)
    assert first.status_code == 202
    assert replay.status_code == 202
    assert first.json()["job_id"] == replay.json()["job_id"]
    assert first.json()["payload"]["query"] == "example query"
    read = client.get(
        f"/v1/jobs/{first.json()['job_id']}",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert read.status_code == 200
    conflict = client.post(
        "/v1/jobs",
        json={"kind": "search", "payload": {"query": "different", "limit": 5}},
        headers=headers,
    )
    assert conflict.status_code == 409
    repo.close()


def test_tenant_and_subject_scoping_prevents_job_disclosure() -> None:
    repository = SQLiteJobRepository(":memory:")
    owner_client, _ = client_for(repository=repository)
    created = owner_client.post(
        "/v1/jobs",
        json={"kind": "search", "payload": {"query": "example"}},
        headers={
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "request-key-000001",
        },
    )
    assert created.status_code == 202
    other_client, _ = client_for(
        principal_value=principal(tenant_id="tenant-b", subject_id="subject-b"),
        repository=repository,
    )
    response = other_client.get(
        f"/v1/jobs/{created.json()['job_id']}",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert response.status_code == 404
    repository.close()


def test_scope_and_url_policy_are_enforced_before_queueing() -> None:
    no_scope, repo = client_for(principal_value=principal(scopes=frozenset({"twi:jobs:read"})))
    denied = no_scope.post(
        "/v1/jobs",
        json={"kind": "search", "payload": {"query": "example"}},
        headers={
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "request-key-000001",
        },
    )
    assert denied.status_code == 403
    repo.close()
    fetch_client, fetch_repo = client_for(
        principal_value=principal(scopes=frozenset({"twi:fetch"}))
    )
    blocked = fetch_client.post(
        "/v1/jobs",
        json={"kind": "fetch", "payload": {"url": "http://127.0.0.1/"}},
        headers={
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "request-key-000002",
        },
    )
    assert blocked.status_code == 422
    oversized = fetch_client.post(
        "/v1/jobs",
        content=b"x" * 70_000,
        headers={
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "request-key-000003",
            "Content-Type": "application/json",
        },
    )
    assert oversized.status_code == 413
    fetch_repo.close()



def test_browser_job_is_scope_gated_bounded_and_disabled_by_default() -> None:
    client, repo = client_for(browser_enabled=True)
    headers = {
        "Authorization": "Bearer valid-credential",
        "Idempotency-Key": "browser-request-0001",
    }
    response = client.post(
        "/v1/jobs",
        json={"kind": "browser", "payload": {
            "url": "https://example.com", "wait_until": "load",
            "timeout_ms": 10000, "include_screenshot": True,
        }},
        headers=headers,
    )
    assert response.status_code == 202
    assert response.json()["payload"] == {
        "url": "https://example.com/", "wait_until": "load",
        "timeout_ms": 10000, "include_screenshot": True,
    }
    invalid = client.post(
        "/v1/jobs",
        json={"kind": "browser", "payload": {
            "url": "https://example.com", "timeout_ms": 999999,
        }},
        headers={"Authorization": "Bearer valid-credential",
                 "Idempotency-Key": "browser-request-0002"},
    )
    assert invalid.status_code == 422
    repo.close()
    denied, denied_repo = client_for(
        principal_value=principal(scopes=frozenset({"twi:search"})),
        browser_enabled=True,
    )
    forbidden = denied.post(
        "/v1/jobs", json={"kind": "browser", "payload": {"url": "https://example.com"}},
        headers={"Authorization": "Bearer valid-credential",
                 "Idempotency-Key": "browser-request-0003"},
    )
    assert forbidden.status_code == 403
    denied_repo.close()
    disabled, disabled_repo = client_for()
    unavailable = disabled.post(
        "/v1/jobs", json={"kind": "browser", "payload": {"url": "https://example.com"}},
        headers={"Authorization": "Bearer valid-credential",
                 "Idempotency-Key": "browser-request-0004"},
    )
    assert unavailable.status_code == 503
    disabled_repo.close()


def test_production_fails_closed_without_platform_identity_configuration() -> None:
    try:
        settings = Settings.from_env({"TWI_ENV": "production"})
    except ConfigurationError:
        return
    try:
        create_app(settings=settings)
    except ConfigurationError:
        return
    raise AssertionError("production app unexpectedly started without a trusted verifier")



class FakeEntitlementResolver:
    def __init__(self, plan: PlanEntitlements | None) -> None:
        self.plan = plan

    def resolve(self, *, tenant_id: str, subject_id: str) -> PlanEntitlements | None:
        assert tenant_id and subject_id
        return self.plan


def test_job_submission_enforces_atomic_monthly_quota_and_idempotent_usage() -> None:
    repository = SQLiteJobRepository(":memory:")
    usage = SQLiteUsageLedger(":memory:")
    plan = PlanEntitlements(
        plan_id="test-basic", version=1, features=frozenset({"search"}),
        limits={"search_requests_month": 1},
    )
    app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=repository, usage_ledger=usage,
        verifier=FakeVerifier(principal()),
        entitlement_resolver=FakeEntitlementResolver(plan),
    )
    client = TestClient(app)
    headers = {
        "Authorization": "Bearer valid-credential",
        "Idempotency-Key": "quota-request-key-0001",
    }
    payload = {"kind": "search", "payload": {"query": "first operation"}}
    first = client.post("/v1/jobs", json=payload, headers=headers)
    replay = client.post("/v1/jobs", json=payload, headers=headers)
    assert first.status_code == replay.status_code == 202
    assert first.json()["job_id"] == replay.json()["job_id"]
    period = usage.list_events(
        tenant_id="tenant-a", subject_id="subject-a",
        dimension="search_requests_month",
        period_start=datetime.now(UTC).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ).isoformat().replace("+00:00", "Z"),
    )[0].period_start
    assert usage.usage_total(
        tenant_id="tenant-a", subject_id="subject-a",
        dimension="search_requests_month", period_start=period,
    ) == 1
    exceeded = client.post(
        "/v1/jobs",
        json={"kind": "search", "payload": {"query": "second operation"}},
        headers={
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "quota-request-key-0002",
        },
    )
    assert exceeded.status_code == 429
    usage.close()
    repository.close()


def test_job_submission_fails_closed_for_unknown_plan_or_missing_quota() -> None:
    repository = SQLiteJobRepository(":memory:")
    usage = SQLiteUsageLedger(":memory:")
    app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=repository, usage_ledger=usage,
        verifier=FakeVerifier(principal()),
        entitlement_resolver=FakeEntitlementResolver(None),
    )
    response = TestClient(app).post(
        "/v1/jobs", json={"kind": "search", "payload": {"query": "no plan"}},
        headers={
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "unknown-plan-key-0001",
        },
    )
    assert response.status_code == 503
    missing_quota_app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=repository, usage_ledger=usage,
        verifier=FakeVerifier(principal()),
        entitlement_resolver=FakeEntitlementResolver(
            PlanEntitlements(
                plan_id="incomplete", version=1, features=frozenset({"search"}), limits={}
            )
        ),
    )
    missing_quota = TestClient(missing_quota_app).post(
        "/v1/jobs", json={"kind": "search", "payload": {"query": "no quota"}},
        headers={
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "missing-quota-key-0001",
        },
    )
    assert missing_quota.status_code == 503
    usage.close()
    repository.close()


def test_production_requires_entitlement_resolver_even_with_platform_verifier() -> None:
    settings = Settings.from_env(
        {
            "TWI_ENV": "production",
            "TWI_IDENTITY_ISSUER": "https://identity.example.test",
            "TWI_IDENTITY_AUDIENCE": "twi",
            "TWI_IDENTITY_JWKS_URL": "https://identity.example.test/.well-known/jwks.json",
        },
        require_database=False,
    )
    with pytest.raises(ConfigurationError, match="entitlement resolver"):
        create_app(settings=settings, verifier=FakeVerifier(principal()))



class FailOnceSQLiteUsageLedger(SQLiteUsageLedger):
    def __init__(self) -> None:
        super().__init__(":memory:")
        self.fail_next_commit = True

    def commit(self, *, tenant_id: str, subject_id: str, reservation_id: str) -> UsageEvent:
        if self.fail_next_commit:
            self.fail_next_commit = False
            raise RuntimeError("simulated transient accounting failure")
        return super().commit(
            tenant_id=tenant_id, subject_id=subject_id, reservation_id=reservation_id
        )


def test_job_usage_commit_recovers_on_same_idempotency_key() -> None:
    repository = SQLiteJobRepository(":memory:")
    usage = FailOnceSQLiteUsageLedger()
    plan = PlanEntitlements(
        plan_id="test-basic", version=1, features=frozenset({"search"}),
        limits={"search_requests_month": 1},
    )
    client = TestClient(create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
        repository=repository, usage_ledger=usage,
        verifier=FakeVerifier(principal()),
        entitlement_resolver=FakeEntitlementResolver(plan),
    ))
    headers = {
        "Authorization": "Bearer valid-credential",
        "Idempotency-Key": "recovery-request-key-0001",
    }
    payload = {"kind": "search", "payload": {"query": "recover accounting"}}
    first = client.post("/v1/jobs", json=payload, headers=headers)
    assert first.status_code == 503
    replay = client.post("/v1/jobs", json=payload, headers=headers)
    assert replay.status_code == 202
    assert usage.usage_total(
        tenant_id="tenant-a", subject_id="subject-a",
        dimension="search_requests_month",
        period_start=usage.list_events(
            tenant_id="tenant-a", subject_id="subject-a",
            dimension="search_requests_month",
        )[0].period_start,
    ) == 1
    usage.close()
    repository.close()
