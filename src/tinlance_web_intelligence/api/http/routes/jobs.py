"""Tenant-scoped durable job submission, inspection, and cancellation."""

from __future__ import annotations

import re
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.browser.policies import (
    BrowserPolicyError,
    normalize_browser_payload,
)
from tinlance_web_intelligence.jobs.model import IdempotencyConflictError, Job, JobStatus
from tinlance_web_intelligence.jobs.repository import SQLiteJobRepository
from tinlance_web_intelligence.security.url_validation import UnsafeURLError, validate_url

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])
_IDEMPOTENCY_PATTERN = re.compile(r"^[\x21-\x7e]+$")


class JobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    kind: Literal["search", "fetch", "browser"]
    payload: dict[str, Any] = Field(max_length=32)


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


def _require_scope(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")


def _public_job(job: Job) -> dict[str, Any]:
    return job.to_dict()


def _normalize_payload(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if kind == "search":
        if set(payload) - {"query", "limit"}:
            raise HTTPException(status_code=422, detail="unsupported search payload field")
        query = payload.get("query")
        limit = payload.get("limit", 10)
        if not isinstance(query, str) or not query.strip() or len(query) > 400:
            raise HTTPException(status_code=422, detail="query must contain 1 to 400 characters")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
            raise HTTPException(status_code=422, detail="limit must be an integer from 1 to 20")
        return {"query": " ".join(query.split()), "limit": limit}
    if kind == "browser":
        try:
            return normalize_browser_payload(payload)
        except BrowserPolicyError as exc:
            raise HTTPException(
                status_code=422,
                detail="browser request rejected by acquisition policy",
            ) from exc
    if set(payload) != {"url"}:
        raise HTTPException(status_code=422, detail="fetch payload must contain only url")
    url = payload.get("url")
    if not isinstance(url, str):
        raise HTTPException(status_code=422, detail="url must be a string")
    try:
        return {"url": validate_url(url).normalized}
    except UnsafeURLError as exc:
        raise HTTPException(status_code=422, detail="URL rejected by acquisition policy") from exc


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_job(
    request: Request,
    body: JobCreateRequest,
    idempotency_key: str = Header(
        ..., alias="Idempotency-Key", min_length=16, max_length=256
    ),
) -> dict[str, Any]:
    principal = _principal(request)
    required_scope = {
        "search": "twi:search",
        "fetch": "twi:fetch",
        "browser": "twi:browser",
    }[body.kind]
    _require_scope(principal, required_scope)
    if not _IDEMPOTENCY_PATTERN.fullmatch(idempotency_key):
        raise HTTPException(
            status_code=422,
            detail="Idempotency-Key contains unsupported characters",
        )
    payload = _normalize_payload(body.kind, body.payload)
    if body.kind == "browser" and not request.app.state.settings.browser_enabled:
        raise HTTPException(status_code=503, detail="browser acquisition is disabled")
    repository: SQLiteJobRepository = request.app.state.repository
    try:
        job = repository.create(
            tenant_id=principal.tenant_id,
            subject_id=principal.subject_id,
            kind=body.kind,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key conflicts with an existing request",
        ) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="job payload is not JSON-compatible") from exc
    return _public_job(job)


@router.get("/{job_id}")
def get_job(request: Request, job_id: str) -> dict[str, Any]:
    principal = _principal(request)
    read_any = "twi:jobs:read:any" in principal.scopes
    if not read_any and "twi:jobs:read" not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")
    repository: SQLiteJobRepository = request.app.state.repository
    job = repository.get(
        job_id,
        tenant_id=principal.tenant_id,
        subject_id=None if read_any else principal.subject_id,
    )
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return _public_job(job)


@router.post("/{job_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_job(request: Request, job_id: str) -> dict[str, Any]:
    principal = _principal(request)
    _require_scope(principal, "twi:jobs:cancel")
    repository: SQLiteJobRepository = request.app.state.repository
    job = repository.cancel(
        job_id, tenant_id=principal.tenant_id, subject_id=principal.subject_id
    )
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
        raise HTTPException(status_code=409, detail="terminal job cannot be cancelled")
    return _public_job(job)
