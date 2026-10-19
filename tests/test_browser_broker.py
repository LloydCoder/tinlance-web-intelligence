from __future__ import annotations

import os
import secrets
import uuid

import pytest
from fastapi.testclient import TestClient

from tinlance_web_intelligence.browser.broker_api import create_app
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.persistence.postgres_jobs import PostgresJobRepository

BROKER_TOKEN = secrets.token_urlsafe(32)
_POSTGRES_DSN = os.environ.get("TWI_TEST_POSTGRES_DSN")


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
        traceparent="00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
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
        assert claim["traceparent"] == "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
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
        with pytest.raises(ValueError, match="at least 32"):
            create_app(repository, "short")
    finally:
        repository.close()


@pytest.mark.skipif(_POSTGRES_DSN is None, reason="TWI_TEST_POSTGRES_DSN is not configured")
def test_browser_broker_uses_shared_postgres_job_queue() -> None:
    assert _POSTGRES_DSN is not None
    repository = PostgresJobRepository(_POSTGRES_DSN, min_size=1, max_size=10, auto_migrate=True)
    namespace = uuid.uuid4().hex
    try:
        created = repository.create(
            tenant_id=f"tenant-{namespace}",
            subject_id=f"subject-{namespace}",
            kind="browser",
            payload={"url": "https://example.com"},
            idempotency_key=f"browser-broker-{namespace}",
        )
        client = TestClient(create_app(repository, BROKER_TOKEN))
        headers = {"Authorization": f"Bearer {BROKER_TOKEN}"}
        claim_response = client.post("/internal/browser-jobs/claim", headers=headers, json={})
        assert claim_response.status_code == 200
        claim = claim_response.json()
        assert claim["job_id"] == created.job_id
        assert claim["payload"] == {"url": "https://example.com"}

        completed = client.post(
            f"/internal/browser-jobs/{created.job_id}/complete",
            headers=headers,
            json={"lease_token": claim["lease_token"], "result": {"title": "captured"}},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "succeeded"
        persisted = repository.get(
            created.job_id, tenant_id=f"tenant-{namespace}", subject_id=f"subject-{namespace}"
        )
        assert persisted is not None
        assert persisted.status.value == "succeeded"
    finally:
        repository.close()
