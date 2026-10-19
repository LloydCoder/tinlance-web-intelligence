from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tinlance_web_intelligence.api.http.app import create_app
from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.persistence.sqlite_monitors import SQLiteMonitorRepository


class FakeVerifier:
    def __init__(self, scopes: frozenset[str], *, tenant_id: str = "tenant-a",
                 subject_id: str = "subject-a") -> None:
        self.principal = Principal(
            tenant_id=tenant_id,
            subject_id=subject_id,
            client_id="api-monitor-test",
            principal_type="user",
            token_id="monitor-test-jti",  # noqa: S106
            scopes=scopes,
            roles=frozenset(),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    def verify(self, token: str) -> Principal:
        if token != "valid-credential":  # noqa: S105
            raise PermissionError("invalid test credential")
        return self.principal


def client_for(
    scopes: frozenset[str] | None = None,
    *,
    tenant_id: str = "tenant-a",
    subject_id: str = "subject-a",
    jobs: SQLiteJobRepository | None = None,
    monitors: SQLiteMonitorRepository | None = None,
) -> tuple[TestClient, SQLiteJobRepository, SQLiteMonitorRepository]:
    jobs = jobs or SQLiteJobRepository(":memory:")
    monitors = monitors or SQLiteMonitorRepository(":memory:")
    app = create_app(
        settings=Settings.from_env({
            "TWI_ENV": "test",
            "TWI_DATABASE_PATH": ":memory:",
        }),
        repository=jobs,
        monitor_repository=monitors,
        verifier=FakeVerifier(
            scopes if scopes is not None else frozenset({
                "twi:monitors:read", "twi:monitors:read:any", "twi:monitors:write",
                "twi:monitors:delete", "twi:jobs:read",
            }),
            tenant_id=tenant_id,
            subject_id=subject_id,
        ),
    )
    return TestClient(app), jobs, monitors


def test_monitor_lifecycle_is_idempotent_scoped_and_redacts_urls() -> None:
    client, jobs, monitors = client_for()
    headers = {
        "Authorization": "Bearer valid-credential",
        "Idempotency-Key": "monitor-create-key-0001",
    }
    payload = {
        "target_url": "https://example.test/path?access_token=do-not-return",
        "policy": {"max_bytes": 2048},
    }

    created = client.post("/v1/monitors", json=payload, headers=headers)
    replay = client.post("/v1/monitors", json=payload, headers=headers)
    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["monitor_id"] == created.json()["monitor_id"]
    assert "access_token" not in created.text
    assert "example.test" not in created.text

    monitor_id = created.json()["monitor_id"]
    run_headers = {
        "Authorization": "Bearer valid-credential",
        "Idempotency-Key": "monitor-run-key-0001",
    }
    traceparent = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    run = client.post(
        f"/v1/monitors/{monitor_id}/runs",
        headers={**run_headers, "traceparent": traceparent},
    )
    assert run.status_code == 202
    assert run.headers["Location"].endswith(f"/runs/{run.json()['job_id']}")
    stored_job = jobs.get(
        run.json()["job_id"], tenant_id="tenant-a", subject_id="subject-a"
    )
    assert stored_job is not None and stored_job.traceparent == traceparent
    run_read = client.get(
        f"/v1/monitors/{monitor_id}/runs/{run.json()['job_id']}",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert run_read.status_code == 200
    assert run_read.json()["payload"]["monitor_id"] == monitor_id

    read = client.get(
        f"/v1/monitors/{monitor_id}",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert read.status_code == 200
    assert read.json()["status"] == "active"
    assert "target_url" not in read.json()

    paused = client.post(
        f"/v1/monitors/{monitor_id}/pause",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert paused.status_code == 200 and paused.json()["status"] == "paused"
    blocked = client.post(
        f"/v1/monitors/{monitor_id}/runs",
        headers={"Authorization": "Bearer valid-credential",
                 "Idempotency-Key": "monitor-run-key-0002"},
    )
    assert blocked.status_code == 409
    resumed = client.post(
        f"/v1/monitors/{monitor_id}/resume",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert resumed.status_code == 200 and resumed.json()["status"] == "active"
    deleted = client.delete(
        f"/v1/monitors/{monitor_id}",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert deleted.status_code == 200 and deleted.json()["status"] == "deleted"
    row = monitors.get(
        tenant_id="tenant-a", subject_id="subject-a", monitor_id=monitor_id
    )
    assert row is not None and row.target_url == "https://deleted.invalid/"
    assert row.baseline_digest is None
    hidden_run = client.get(
        f"/v1/monitors/{monitor_id}/runs/{run.json()['job_id']}",
        headers={"Authorization": "Bearer valid-credential"},
    )
    assert hidden_run.status_code == 404
    client.close()
    jobs.close()
    monitors.close()


def test_monitor_reads_hide_cross_tenant_and_cross_subject_records() -> None:
    owner, jobs, monitors = client_for()
    created = owner.post(
        "/v1/monitors",
        json={"target_url": "https://example.test/"},
        headers={"Authorization": "Bearer valid-credential",
                 "Idempotency-Key": "monitor-create-key-0002"},
    )
    assert created.status_code == 201
    monitor_id = created.json()["monitor_id"]
    cross_tenant, _, _ = client_for(
        tenant_id="tenant-b", subject_id="subject-a", jobs=jobs, monitors=monitors
    )
    cross_subject, _, _ = client_for(
        frozenset({"twi:monitors:read"}),
        tenant_id="tenant-a",
        subject_id="subject-b",
        jobs=jobs,
        monitors=monitors,
    )
    for client in (cross_tenant, cross_subject):
        response = client.get(
            f"/v1/monitors/{monitor_id}",
            headers={"Authorization": "Bearer valid-credential"},
        )
        assert response.status_code == 404
        client.close()
    owner.close()
    jobs.close()
    monitors.close()


def test_monitor_scope_and_safe_url_policy_are_enforced() -> None:
    no_write, jobs, monitors = client_for(frozenset({"twi:monitors:read"}))
    denied = no_write.post(
        "/v1/monitors",
        json={"target_url": "https://example.test/"},
        headers={"Authorization": "Bearer valid-credential",
                 "Idempotency-Key": "monitor-create-key-0003"},
    )
    assert denied.status_code == 403
    no_write.close()
    jobs.close()
    monitors.close()
    allowed, allowed_jobs, allowed_monitors = client_for()
    blocked = allowed.post(
        "/v1/monitors",
        json={"target_url": "http://127.0.0.1/private"},
        headers={"Authorization": "Bearer valid-credential",
                 "Idempotency-Key": "monitor-create-key-0004"},
    )
    assert blocked.status_code == 422
    allowed.close()
    allowed_jobs.close()
    allowed_monitors.close()
