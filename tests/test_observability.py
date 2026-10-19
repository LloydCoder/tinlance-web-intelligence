from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tinlance_web_intelligence.api.http.app import create_app
from tinlance_web_intelligence.config import ConfigurationError, Settings
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    SQLiteSourceEvidenceOutbox,
)
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository


def _client(metrics_token: str | None) -> tuple[TestClient, SQLiteJobRepository, SQLiteSourceEvidenceOutbox]:
    env = {"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}
    if metrics_token is not None:
        env["TWI_METRICS_TOKEN"] = metrics_token
    settings = Settings.from_env(env)
    repository = SQLiteJobRepository(":memory:")
    outbox = SQLiteSourceEvidenceOutbox(":memory:")
    app = create_app(settings=settings, repository=repository, evidence_outbox=outbox)
    return TestClient(app), repository, outbox


def test_metrics_endpoint_is_hidden_when_not_configured() -> None:
    client, repository, outbox = _client(None)
    try:
        with client:
            response = client.get("/internal/metrics")
        assert response.status_code == 404
    finally:
        repository.close()
        outbox.close()


def test_metrics_endpoint_requires_token_and_exports_safe_request_metrics() -> None:
    token = "metrics-test-token-" + ("x" * 32)
    client, repository, outbox = _client(token)
    try:
        with client:
            live = client.get("/health/live", headers={"X-Request-ID": "probe-123"})
            rejected = client.get("/internal/metrics")
            metrics = client.get(
                "/internal/metrics", headers={"Authorization": f"Bearer {token}"}
            )
        assert live.status_code == 200
        assert live.headers["X-Request-ID"] == "probe-123"
        assert rejected.status_code == 401
        assert metrics.status_code == 200
        assert "text/plain" in metrics.headers["content-type"]
        assert "twi_http_requests_total" in metrics.text
        assert 'route="/health/live"' in metrics.text
        assert token not in metrics.text
        assert "tenant_id" not in metrics.text
    finally:
        repository.close()
        outbox.close()


def test_metrics_endpoint_replaces_invalid_request_id() -> None:
    client, repository, outbox = _client("m" * 32)
    try:
        with client:
            response = client.get("/health/live", headers={"X-Request-ID": "invalid request id"})
        request_id = response.headers["X-Request-ID"]
        assert response.status_code == 200
        assert request_id != "invalid request id"
        assert len(request_id) == 32
        assert all(character in "0123456789abcdef" for character in request_id)
    finally:
        repository.close()
        outbox.close()


def test_metrics_token_must_be_long_and_unpadded() -> None:
    with pytest.raises(ConfigurationError, match="TWI_METRICS_TOKEN"):
        Settings.from_env({"TWI_METRICS_TOKEN": "short"})
