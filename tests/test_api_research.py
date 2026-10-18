from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi.testclient import TestClient

from tinlance_web_intelligence.api.http.app import create_app
from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository


class FakeVerifier:
    def __init__(self, principal: Principal) -> None:
        self.principal = principal

    def verify(self, supplied: str) -> Principal:
        if supplied != "valid-credential":
            raise PermissionError("invalid test credential")
        return self.principal


def _principal(
    *,
    tenant_id: str = "tenant-a",
    subject_id: str = "subject-a",
    scopes: frozenset[str] = frozenset({"twi:research:verify"}),
) -> Principal:
    return Principal(
        tenant_id=tenant_id,
        subject_id=subject_id,
        client_id="research-test-client",
        principal_type="user",
        token_id="research-test-jti",
        scopes=scopes,
        roles=frozenset(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def _client(
    repository: SQLiteJobRepository,
    principal: Principal | None = None,
) -> TestClient:
    app = create_app(
        settings=Settings.from_env(
            {"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}
        ),
        repository=repository,
        verifier=FakeVerifier(principal or _principal()),
    )
    return TestClient(app)


def _completed_fetch(repository: SQLiteJobRepository) -> str:
    created = repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind="fetch",
        payload={"url": "https://example.com/"},
        idempotency_key="research-fetch-job-0001",
    )
    claimed = repository.claim_next("research-test-worker", allowed_kinds=("fetch",))
    assert claimed is not None and claimed.job_id == created.job_id
    text = "The company launched its new product in October 2026."
    repository.complete(
        created.job_id,
        "research-test-worker",
        {
            "source_url": "https://example.com/news",
            "retrieved_at": "2026-10-18T12:00:00+00:00",
            "content_type": "text/html",
            "content_sha256": sha256(b"raw-html-artifact").hexdigest(),
            "title": "Company news",
            "text": text,
        },
    )
    return created.job_id


def test_research_verification_matches_quotes_to_successful_source_capture() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        job_id = _completed_fetch(repository)
        client = _client(repository)
        response = client.post(
            "/v1/research/verify",
            headers={"Authorization": "Bearer valid-credential"},
            json={
                "claims": [
                    {
                        "claim_id": "product-launch",
                        "statement": "The company launched a new product in October 2026.",
                        "citations": [
                            {
                                "job_id": job_id,
                                "quote": "launched its new product in October 2026",
                            }
                        ],
                    }
                ]
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "all_citations_match_captured_text"
        assert payload["factual_truth_assessed"] is False
        assert payload["source_count"] == 1
        assert payload["claims"][0]["citations"][0]["quote_match"] is True
        assert payload["claims"][0]["citations"][0]["source"]["url"] == "https://example.com/news"
        assert len(payload["report_sha256"]) == 64
    finally:
        repository.close()


def test_research_verification_marks_unmatched_quote_without_claiming_truth() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        job_id = _completed_fetch(repository)
        response = _client(repository).post(
            "/v1/research/verify",
            headers={"Authorization": "Bearer valid-credential"},
            json={
                "claims": [
                    {
                        "claim_id": "unsupported",
                        "statement": "A different event happened.",
                        "citations": [{"job_id": job_id, "quote": "this text does not exist"}],
                    }
                ]
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "citation_mismatch"
        assert payload["factual_truth_assessed"] is False
        assert payload["claims"][0]["citation_status"] == "citation_mismatch"
        assert payload["claims"][0]["citations"][0]["quote_match"] is False
    finally:
        repository.close()


def test_research_verification_is_tenant_and_subject_scoped() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        job_id = _completed_fetch(repository)
        client = _client(repository, _principal(tenant_id="tenant-b", subject_id="subject-b"))
        response = client.post(
            "/v1/research/verify",
            headers={"Authorization": "Bearer valid-credential"},
            json={
                "claims": [
                    {
                        "claim_id": "cross-tenant",
                        "statement": "A claim.",
                        "citations": [{"job_id": job_id, "quote": "launched its new product"}],
                    }
                ]
            },
        )
        assert response.status_code == 404
    finally:
        repository.close()


def test_research_verification_requires_scope_and_successful_fetch_or_browser_job() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        search_job = repository.create(
            tenant_id="tenant-a",
            subject_id="subject-a",
            kind="search",
            payload={"query": "example", "limit": 1},
            idempotency_key="research-search-job-0001",
        )
        client = _client(repository)
        wrong_kind = client.post(
            "/v1/research/verify",
            headers={"Authorization": "Bearer valid-credential"},
            json={
                "claims": [
                    {
                        "claim_id": "search-result",
                        "statement": "A claim.",
                        "citations": [{"job_id": search_job.job_id, "quote": "search result text"}],
                    }
                ]
            },
        )
        assert wrong_kind.status_code == 422

        no_scope = _client(repository, _principal(scopes=frozenset({"twi:jobs:read"})))
        denied = no_scope.post(
            "/v1/research/verify",
            headers={"Authorization": "Bearer valid-credential"},
            json={
                "claims": [
                    {
                        "claim_id": "denied",
                        "statement": "A claim.",
                        "citations": [{"job_id": search_job.job_id, "quote": "search result text"}],
                    }
                ]
            },
        )
        assert denied.status_code == 403
    finally:
        repository.close()


def test_research_verification_requires_bearer_auth_and_rejects_extra_fields() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        client = _client(repository)
        unauthenticated = client.post(
            "/v1/research/verify",
            json={"claims": [{"claim_id": "x", "statement": "claim", "citations": []}]},
        )
        assert unauthenticated.status_code == 401
        invalid = client.post(
            "/v1/research/verify",
            headers={"Authorization": "Bearer valid-credential"},
            json={"claims": [], "tenant_id": "attacker-controlled"},
        )
        assert invalid.status_code == 422
    finally:
        repository.close()
