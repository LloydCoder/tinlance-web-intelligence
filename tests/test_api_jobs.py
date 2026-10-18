from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tinlance_web_intelligence.api.http.app import create_app
from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.config import ConfigurationError, Settings
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository


class FakeVerifier:
    def __init__(self, principal: Principal) -> None:
        self.principal = principal

    def verify(self, token: str) -> Principal:
        if token != "valid-test-token":
            raise PermissionError("invalid test token")
        return self.principal


def principal(
    tenant_id: str = "tenant-a",
    subject_id: str = "subject-a",
    scopes: frozenset[str] = frozenset(
        {"twi:search", "twi:fetch", "twi:jobs:read", "twi:jobs:cancel"}
    ),
) -> Principal:
    return Principal(
        tenant_id=tenant_id,
        subject_id=subject_id,
        client_id="test-client",
        principal_type="user",
        token_id="token-test-01",
        scopes=scopes,
        roles=frozenset(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def client_for(
    *,
    principal_value: Principal | None = None,
    repository: SQLiteJobRepository | None = None,
) -> tuple[TestClient, SQLiteJobRepository]:
    repo = repository or SQLiteJobRepository(":memory:")
    app = create_app(
        settings=Settings.from_env({"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}),
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
        "Authorization": "Bearer valid-test-token",
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
        headers={"Authorization": "Bearer valid-test-token"},
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
            "Authorization": "Bearer valid-test-token",
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
        headers={"Authorization": "Bearer valid-test-token"},
    )
    assert response.status_code == 404
    repository.close()


def test_scope_and_url_policy_are_enforced_before_queueing() -> None:
    no_scope, repo = client_for(principal_value=principal(scopes=frozenset({"twi:jobs:read"})))
    denied = no_scope.post(
        "/v1/jobs",
        json={"kind": "search", "payload": {"query": "example"}},
        headers={
            "Authorization": "Bearer valid-test-token",
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
            "Authorization": "Bearer valid-test-token",
            "Idempotency-Key": "request-key-000002",
        },
    )
    assert blocked.status_code == 422
    oversized = fetch_client.post(
        "/v1/jobs",
        content=b"x" * 70_000,
        headers={
            "Authorization": "Bearer valid-test-token",
            "Idempotency-Key": "request-key-000003",
            "Content-Type": "application/json",
        },
    )
    assert oversized.status_code == 413
    fetch_repo.close()


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
