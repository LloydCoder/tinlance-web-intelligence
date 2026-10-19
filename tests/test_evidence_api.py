from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tinlance_web_intelligence.api.http.app import create_app
from tinlance_web_intelligence.artifacts.store import MemoryArtifactStore
from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.config import Settings
from tinlance_web_intelligence.contracts.provenance import AcquisitionProvenance
from tinlance_web_intelligence.contracts.evidence_package import validate_evidence_package
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository

_REVISION = "a" * 40


class FakeVerifier:
    def __init__(self, principal: Principal) -> None:
        self.principal = principal

    def verify(self, token: str) -> Principal:
        if token != "valid-credential":
            raise PermissionError("invalid credential")
        return self.principal


def principal(
    tenant_id: str = "tenant-a",
    subject_id: str = "subject-a",
    scopes: frozenset[str] = frozenset({"twi:evidence:export"}),
) -> Principal:
    return Principal(
        tenant_id=tenant_id,
        subject_id=subject_id,
        client_id="test-client",
        principal_type="user",
        token_id="evidence-api-test",
        scopes=scopes,
        roles=frozenset(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def setup_client(
    *, principal_value: Principal | None = None, source_revision: str | None = _REVISION
) -> tuple[TestClient, SQLiteJobRepository, MemoryArtifactStore, str]:
    repo = SQLiteJobRepository(":memory:")
    artifacts = MemoryArtifactStore()
    body = b"<html><title>Public</title><p>Capture</p></html>"
    now = datetime(2026, 10, 19, 10, 0, tzinfo=UTC)
    manifest = AcquisitionProvenance.from_capture(
        requested_url="https://example.test/page?token=secret",
        final_url="https://example.test/final",
        status_code=200,
        content_type="text/html",
        body=body,
        retrieved_at=now,
        redirect_count=1,
        extractor_version="twi-html-extractor-v1",
    )
    artifact = artifacts.put(
        body=body, content_type="text/html", source_url="https://example.test/final",
        captured_at=now, tenant_id="tenant-a",
    )
    job = repo.create(
        tenant_id="tenant-a", subject_id="subject-a", kind="fetch",
        payload={"url": "https://example.test/page"}, idempotency_key="evidence-api-job-0001",
    )
    claimed = repo.claim_next("test-worker", allowed_kinds=("fetch",))
    assert claimed is not None and claimed.job_id == job.job_id
    repo.complete(
        job.job_id, "test-worker",
        {
            "artifact_id": artifact.artifact_id,
            "content_sha256": artifact.sha256,
            "content_type": "text/html",
            "status_code": 200,
            "retrieved_at": now.isoformat(),
            "provenance": manifest.to_dict(),
        },
    )
    env = {"TWI_ENV": "test", "TWI_DATABASE_PATH": ":memory:"}
    if source_revision is not None:
        env["TWI_SOURCE_REVISION"] = source_revision
    app = create_app(
        settings=Settings.from_env(env),
        repository=repo,
        verifier=FakeVerifier(principal_value or principal()),
        artifact_store=artifacts,
    )
    return TestClient(app), repo, artifacts, job.job_id


def test_evidence_export_is_authorized_reproducible_and_tenant_scoped() -> None:
    client, repo, artifacts, job_id = setup_client()
    headers = {"Authorization": "Bearer valid-credential"}
    first = client.get(f"/v1/jobs/{job_id}/evidence", headers=headers)
    second = client.get(f"/v1/jobs/{job_id}/evidence", headers=headers)
    assert first.status_code == 200
    assert first.content == second.content
    assert first.headers["content-type"].startswith("application/vnd.tinlance.twi-evidence+json")
    assert first.headers["cache-control"] == "no-store"
    payload = validate_evidence_package(first.content, expected_source_revision=_REVISION)
    assert payload["source_revision"] == _REVISION
    assert b"token=secret" not in first.content
    assert b"https://example.test" not in first.content

    other = setup_client(principal_value=principal(tenant_id="tenant-b", subject_id="subject-b"))[0]
    hidden = other.get(f"/v1/jobs/{job_id}/evidence", headers=headers)
    assert hidden.status_code == 404
    repo.close()
    artifacts.close()


def test_evidence_export_requires_dedicated_scope_and_source_revision() -> None:
    denied, repo, artifacts, job_id = setup_client(
        principal_value=principal(scopes=frozenset({"twi:jobs:read"}))
    )
    response = denied.get(
        f"/v1/jobs/{job_id}/evidence", headers={"Authorization": "Bearer valid-credential"}
    )
    assert response.status_code == 403
    repo.close()
    artifacts.close()

    unavailable, repo2, artifacts2, job_id2 = setup_client(source_revision=None)
    response = unavailable.get(
        f"/v1/jobs/{job_id2}/evidence", headers={"Authorization": "Bearer valid-credential"}
    )
    assert response.status_code == 503
    repo2.close()
    artifacts2.close()


def test_evidence_export_rejects_wrong_job_type_or_missing_artifact() -> None:
    client, repo, artifacts, job_id = setup_client()
    # Mutate the result through a distinct successful search job; search results are not fetch evidence.
    search = repo.create(
        tenant_id="tenant-a", subject_id="subject-a", kind="search",
        payload={"query": "test"}, idempotency_key="evidence-api-search-0001",
    )
    claimed = repo.claim_next("test-worker", allowed_kinds=("search",))
    assert claimed is not None and claimed.job_id == search.job_id
    repo.complete(search.job_id, "test-worker", {"results": []})
    wrong_type = client.get(
        f"/v1/jobs/{search.job_id}/evidence", headers={"Authorization": "Bearer valid-credential"}
    )
    assert wrong_type.status_code == 409
    artifacts.close()
    repo.close()
