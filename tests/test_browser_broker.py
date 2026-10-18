from __future__ import annotations

from fastapi.testclient import TestClient

from apps.browser_broker.main import create_app
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository

BROKER_TOKEN = "test-browser-broker-token-with-sufficient-entropy-2026"


def _repository_with_jobs() -> SQLiteJobRepository:
    repository = SQLiteJobRepository(":memory:")
    repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind="search",
        payload={"query": "not for browser", "limit": 1},
        idempotency_key="search-job-idempotency-key",
    )
    repository.create(
        tenant_id="tenant-a",
        subject_id="subject-a",
        kind="browser",
        payload={"url": "https://example.com"},
        idempotency_key="browser-job-idempotency-key",
    )
    return repository


def test_browser_broker_requires_service_authentication() -> None:
    repository = _repository_with_jobs()
    try:
        client = TestClient(create_app(repository, BROKER_TOKEN))
        response = client.post("/internal/browser-jobs/claim", json={})
        assert response.status_code == 401
    finally:
        repository.close()


def test_browser_broker_claims_only_browser_jobs_and_binds_result_to_lease() -> None:
    repository = _repository_with_jobs()
    try:
        client = TestClient(create_app(repository, BROKER_TOKEN))
        headers = {"Authorization": f"Bearer {BROKER_TOKEN}"}
        claim_response = client.post("/internal/browser-jobs/claim", headers=headers, json={})
        assert claim_response.status_code == 200
        claim = claim_response.json()
        assert claim["payload"] == {"url": "https://example.com"}
        assert claim["attempts"] == 1
        job_id = claim["job_id"]
        lease_token = claim["lease_token"]
        assert isinstance(job_id, str)
        assert isinstance(lease_token, str) and len(lease_token) >= 32

        stale = client.post(
            f"/internal/browser-jobs/{job_id}/complete",
            headers=headers,
            json={"lease_token": "x" * 40, "result": {"title": "untrusted"}},
        )
        assert stale.status_code == 409

        completed = client.post(
            f"/internal/browser-jobs/{job_id}/complete",
            headers=headers,
            json={"lease_token": lease_token, "result": {"title": "captured"}},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "succeeded"

        no_more_jobs = client.post("/internal/browser-jobs/claim", headers=headers, json={})
        assert no_more_jobs.status_code == 204
    finally:
        repository.close()


def test_browser_broker_rejects_short_service_tokens() -> None:
    repository = SQLiteJobRepository(":memory:")
    try:
        try:
            create_app(repository, "short")
        except ValueError as exc:
            assert "at least 32" in str(exc)
        else:
            raise AssertionError("short broker token must be rejected")
    finally:
        repository.close()
