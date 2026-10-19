"""Tenant-scoped customer evidence exports for successful fetch jobs."""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import Response

from tinlance_web_intelligence.artifacts.store import ArtifactStore
from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.contracts.evidence_package import (
    EvidencePackageError,
    build_evidence_package,
)
from tinlance_web_intelligence.jobs.model import JobStatus
from tinlance_web_intelligence.persistence.protocols import JobRepository

router = APIRouter(prefix="/v1/jobs", tags=["evidence"])
_JOB_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_MEDIA_TYPE = "application/vnd.tinlance.twi-evidence+json"


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


@router.get("/{job_id}/evidence")
def export_job_evidence(request: Request, job_id: str) -> Response:
    """Export the verified artifact and acquisition lineage for a caller-owned fetch job."""
    principal = _principal(request)
    if "twi:evidence:export" not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")
    if not _JOB_ID.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="job not found")

    repository: JobRepository = request.app.state.repository
    job = repository.get(job_id, tenant_id=principal.tenant_id, subject_id=principal.subject_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if (
        job.kind != "fetch"
        or job.status is not JobStatus.SUCCEEDED
        or not isinstance(job.result, dict)
    ):
        raise HTTPException(status_code=409, detail="job has no exportable fetch evidence")

    result: dict[str, Any] = job.result
    artifact_id = result.get("artifact_id")
    digest = result.get("content_sha256")
    content_type = result.get("content_type")
    provenance = result.get("provenance")
    if (
        not isinstance(artifact_id, str)
        or not isinstance(digest, str)
        or artifact_id != f"sha256:{digest}"
        or not isinstance(content_type, str)
        or not isinstance(provenance, dict)
    ):
        raise HTTPException(status_code=409, detail="fetch evidence metadata is incomplete")

    source_revision = getattr(request.app.state.settings, "source_revision", None)
    if not isinstance(source_revision, str) or not re.fullmatch(
        r"[0-9a-f]{40}", source_revision
    ):
        raise HTTPException(
            status_code=503, detail="evidence export source revision is unavailable"
        )
    artifacts: ArtifactStore = request.app.state.artifact_store
    try:
        body = artifacts.get(digest, tenant_id=principal.tenant_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=502, detail="stored evidence failed integrity verification"
        ) from exc
    if body is None:
        raise HTTPException(status_code=404, detail="evidence artifact not found")

    try:
        package = build_evidence_package(
            body=body,
            content_type=content_type,
            provenance=provenance,
            source_revision=source_revision,
        )
    except EvidencePackageError as exc:
        raise HTTPException(
            status_code=502, detail="stored evidence failed package validation"
        ) from exc

    response = Response(content=package, media_type=_MEDIA_TYPE)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="twi-evidence-{job_id}.json"'
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
