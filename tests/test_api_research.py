from __future__ import annotations

import uuid
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
        token_id=uuid.uuid4().hex,
        scopes=scopes,
        roles=frozenset(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def _client(
    repository: SQLiteJobRepository,
    principal: Principal | None = None,
) -> TestClient:
    verifier = FakeVerifier(principal or _principal())
    app = create_app(
        settings=Settings.from_env(
            {"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}
        ),
        repository=repository,
        verifier=verifier,
    )
    app.state.test_verifier = verifier
    return TestClient(app)


def _completed_fetch(
    repository: SQLiteJobRepository,
    *,
    source_url: str = "https://example.com/news",
) -> str:
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
            "source_url": source_url,
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


def test_world_intelligence_export_is_verified_idempotent_and_subject_scoped() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        job_id = _completed_fetch(
            repository,
            source_url="https://example.com/news?topic=product&access_token=secret-value",
        )
        scopes = frozenset({
            "twi:research:verify",
            "twi:observations:export",
            "twi:observations:export:read",
        })
        client = _client(repository, _principal(scopes=scopes))
        request_body = {
            "claim_id": "product-launch",
            "statement": "The company launched a new product in October 2026.",
            "job_id": job_id,
            "quote": "launched its new product in October 2026",
        }
        headers = {
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "wi-export-idempotency-0001",
            "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
        }
        first = client.post(
            "/v1/integrations/world-intelligence/exports",
            headers=headers,
            json=request_body,
        )
        assert first.status_code == 202
        payload = first.json()
        assert payload["status"] == "pending"
        assert payload["replayed"] is False

        replay = client.post(
            "/v1/integrations/world-intelligence/exports",
            headers=headers,
            json=request_body,
        )
        assert replay.status_code == 200
        assert replay.json()["event_id"] == payload["event_id"]
        assert replay.json()["replayed"] is True

        status = client.get(
            f"/v1/integrations/world-intelligence/exports/{payload['event_id']}",
            headers={"Authorization": "Bearer valid-credential"},
        )
        assert status.status_code == 200
        assert status.json()["status"] == "pending"

        event = client.app.state.evidence_outbox.get(
            payload["event_id"],
            sha256(b"tenant-a").hexdigest(),
            sha256(b"subject-a").hexdigest(),
        )
        assert event is not None
        assert event.payload["source_url_redacted"] is True
        assert "secret-value" not in event.payload["source_url"]
        assert event.payload["tenant_ref"] == sha256(b"tenant-a").hexdigest()

        client.app.state.test_verifier.principal = _principal(
            subject_id="subject-b",
            scopes=frozenset({"twi:observations:export:read"}),
        )
        hidden = client.get(
            f"/v1/integrations/world-intelligence/exports/{payload['event_id']}",
            headers={"Authorization": "Bearer valid-credential"},
        )
        assert hidden.status_code == 404
    finally:
        repository.close()


def test_world_intelligence_export_rejects_unmatched_quote_and_conflicting_key() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        job_id = _completed_fetch(repository)
        scopes = frozenset({"twi:observations:export", "twi:observations:export:read"})
        client = _client(repository, _principal(scopes=scopes))
        headers = {
            "Authorization": "Bearer valid-credential",
            "Idempotency-Key": "wi-export-idempotency-0002",
        }
        unmatched = client.post(
            "/v1/integrations/world-intelligence/exports",
            headers=headers,
            json={
                "claim_id": "unsupported",
                "statement": "A claim that is not quoted.",
                "job_id": job_id,
                "quote": "a quote absent from captured text",
            },
        )
        assert unmatched.status_code == 422

        body = {
            "claim_id": "product-launch",
            "statement": "The company launched a new product in October 2026.",
            "job_id": job_id,
            "quote": "launched its new product in October 2026",
        }
        first = client.post(
            "/v1/integrations/world-intelligence/exports",
            headers=headers,
            json=body,
        )
        assert first.status_code == 202
        changed = {**body, "statement": "A different statement."}
        conflict = client.post(
            "/v1/integrations/world-intelligence/exports",
            headers=headers,
            json=changed,
        )
        assert conflict.status_code == 409
    finally:
        repository.close()
