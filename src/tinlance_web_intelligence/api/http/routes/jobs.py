"""Tenant-scoped durable job submission, inspection, and cancellation."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.commercial.entitlements import evaluate_feature
from tinlance_web_intelligence.commercial.usage_ledger import (
    QuotaExceededError,
    UsageConflictError,
)
from tinlance_web_intelligence.browser.policies import (
    BrowserPolicyError,
    normalize_browser_payload,
)
from tinlance_web_intelligence.jobs.model import IdempotencyConflictError, Job, JobStatus
from tinlance_web_intelligence.observability.tracing import extract_valid_traceparent
from tinlance_web_intelligence.persistence.protocols import JobRepository
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
    repository: JobRepository = request.app.state.repository
    usage_ledger = request.app.state.usage_ledger
    reservation_id: str | None = None
    resolver = request.app.state.entitlement_resolver
    if resolver is not None:
        try:
            plan = resolver.resolve(
                tenant_id=principal.tenant_id, subject_id=principal.subject_id
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail="commercial entitlement state unavailable"
            ) from exc
        feature_decision = evaluate_feature(plan, feature=body.kind)
        if not feature_decision.allowed:
            if feature_decision.reason == "unknown_plan":
                raise HTTPException(
                    status_code=503, detail="commercial entitlement state unavailable"
                )
            raise HTTPException(
                status_code=403, detail="feature is not included in the current plan"
            )
        dimension = f"{body.kind}_requests_month"
        limit = plan.limits.get(dimension) if plan is not None else None
        if limit is None:
            raise HTTPException(
                status_code=503, detail="quota dimension is not configured for this plan"
            )
        now = datetime.now(UTC)
        period_start = datetime(now.year, now.month, 1, tzinfo=UTC).isoformat().replace(
            "+00:00", "Z"
        )
        usage_key = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        try:
            reservation = usage_ledger.reserve(
                tenant_id=principal.tenant_id,
                subject_id=principal.subject_id,
                feature=body.kind,
                dimension=dimension,
                period_start=period_start,
                quantity=1,
                limit=limit,
                idempotency_key=usage_key,
            )
        except QuotaExceededError as exc:
            raise HTTPException(status_code=429, detail="plan quota exceeded") from exc
        except UsageConflictError as exc:
            raise HTTPException(
                status_code=409, detail="usage idempotency key conflicts with another operation"
            ) from exc
        reservation_id = reservation.reservation_id

    try:
        job = repository.create(
            tenant_id=principal.tenant_id,
            subject_id=principal.subject_id,
            kind=body.kind,
            payload=payload,
            idempotency_key=idempotency_key,
            traceparent=extract_valid_traceparent(request.headers),
        )
    except IdempotencyConflictError as exc:
        if reservation_id is not None:
            usage_ledger.release(
                tenant_id=principal.tenant_id, subject_id=principal.subject_id,
                reservation_id=reservation_id,
            )
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key conflicts with an existing request",
        ) from exc
    except (TypeError, ValueError) as exc:
        if reservation_id is not None:
            usage_ledger.release(
                tenant_id=principal.tenant_id, subject_id=principal.subject_id,
                reservation_id=reservation_id,
            )
        raise HTTPException(status_code=422, detail="job payload is not JSON-compatible") from exc
    except Exception:
        if reservation_id is not None:
            usage_ledger.release(
                tenant_id=principal.tenant_id, subject_id=principal.subject_id,
                reservation_id=reservation_id,
            )
        raise

    if reservation_id is not None:
        try:
            usage_ledger.commit(
                tenant_id=principal.tenant_id, subject_id=principal.subject_id,
                reservation_id=reservation_id,
            )
        except Exception as exc:
            # The job and reservation are durable. Retrying with the same idempotency key
            # safely replays the job and completes the usage commit.
            raise HTTPException(
                status_code=503,
                detail=(
                    "job accepted; usage accounting is pending recovery, "
                    "retry the same idempotency key"
                ),
            ) from exc
    return _public_job(job)


@router.get("/{job_id}")
def get_job(request: Request, job_id: str) -> dict[str, Any]:
    principal = _principal(request)
    read_any = "twi:jobs:read:any" in principal.scopes
    if not read_any and "twi:jobs:read" not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")
    repository: JobRepository = request.app.state.repository
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
    repository: JobRepository = request.app.state.repository
    job = repository.cancel(
        job_id, tenant_id=principal.tenant_id, subject_id=principal.subject_id
    )
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
        raise HTTPException(status_code=409, detail="terminal job cannot be cancelled")
    return _public_job(job)
