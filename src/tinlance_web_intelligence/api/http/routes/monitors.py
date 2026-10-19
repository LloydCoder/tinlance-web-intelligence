"""Tenant-scoped monitor definitions and durable run operations."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.jobs.model import IdempotencyConflictError
from tinlance_web_intelligence.monitors.model import Monitor
from tinlance_web_intelligence.monitors.service import MonitorService
from tinlance_web_intelligence.observability.tracing import extract_valid_traceparent
from tinlance_web_intelligence.persistence.protocols import JobRepository
from tinlance_web_intelligence.security.url_validation import UnsafeURLError, validate_url

router = APIRouter(prefix="/v1/monitors", tags=["monitors"])
_IDEMPOTENCY_PATTERN = re.compile(r"^[\x21-\x7e]+$")


class MonitorCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    target_url: str = Field(min_length=1, max_length=4096)
    policy: dict[str, Any] = Field(default_factory=dict, max_length=1)


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


def _require_scope(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")


def _service(request: Request) -> MonitorService:
    service = getattr(request.app.state, "monitor_service", None)
    if not isinstance(service, MonitorService):
        raise HTTPException(status_code=503, detail="monitor service is unavailable")
    return service


def _public_monitor(monitor: Monitor) -> dict[str, Any]:
    return {
        "monitor_id": monitor.monitor_id,
        "status": monitor.status.value,
        "baseline_digest": monitor.baseline_digest,
        "baseline_observed_at": (
            monitor.baseline_observed_at.isoformat()
            if monitor.baseline_observed_at is not None
            else None
        ),
        "baseline_version": monitor.baseline_version,
        "created_at": monitor.created_at.isoformat(),
        "updated_at": monitor.updated_at.isoformat(),
    }


def _visible_monitor(request: Request, monitor_id: str) -> tuple[Principal, Monitor]:
    principal = _principal(request)
    administrative = "twi:monitors:read:any" in principal.scopes
    if not administrative:
        _require_scope(principal, "twi:monitors:read")
    repository = request.app.state.monitor_repository
    monitor = repository.get(
        tenant_id=principal.tenant_id,
        subject_id=None if administrative else principal.subject_id,
        monitor_id=monitor_id,
        administrative=administrative,
    )
    if monitor is None:
        raise HTTPException(status_code=404, detail="monitor not found")
    return principal, monitor


def _idempotency_key(value: str) -> str:
    if not _IDEMPOTENCY_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=422,
            detail="Idempotency-Key contains unsupported characters",
        )
    return value


@router.post("", status_code=status.HTTP_201_CREATED)
def create_monitor(
    request: Request,
    body: MonitorCreateRequest,
    response: Response,
    idempotency_key: str = Header(
        ..., alias="Idempotency-Key", min_length=16, max_length=256
    ),
) -> dict[str, Any]:
    principal = _principal(request)
    _require_scope(principal, "twi:monitors:write")
    key = _idempotency_key(idempotency_key)
    if set(body.policy) - {"max_bytes"}:
        raise HTTPException(status_code=422, detail="unsupported monitor policy field")
    max_bytes = body.policy.get("max_bytes", request.app.state.settings.max_response_bytes)
    if (
        not isinstance(max_bytes, int)
        or isinstance(max_bytes, bool)
        or not 1 <= max_bytes <= request.app.state.settings.max_response_bytes
    ):
        raise HTTPException(
            status_code=422,
            detail="max_bytes must be a positive integer within the configured response limit",
        )
    try:
        target_url = validate_url(
            body.target_url,
            allowed_schemes=request.app.state.settings.allowed_schemes,
        ).normalized
    except UnsafeURLError as exc:
        raise HTTPException(status_code=422, detail="URL rejected by acquisition policy") from exc
    try:
        monitor = _service(request).create_monitor(
            tenant_id=principal.tenant_id,
            subject_id=principal.subject_id,
            target_url=target_url,
            policy={"max_bytes": max_bytes},
            idempotency_key=key,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key conflicts with an existing monitor",
        ) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="monitor request is invalid") from exc
    response.headers["Location"] = f"/v1/monitors/{monitor.monitor_id}"
    return _public_monitor(monitor)


@router.get("/{monitor_id}")
def get_monitor(request: Request, monitor_id: str) -> dict[str, Any]:
    _, monitor = _visible_monitor(request, monitor_id)
    return _public_monitor(monitor)


@router.post("/{monitor_id}/runs", status_code=status.HTTP_202_ACCEPTED)
def enqueue_monitor_run(
    request: Request,
    monitor_id: str,
    response: Response,
    idempotency_key: str = Header(
        ..., alias="Idempotency-Key", min_length=16, max_length=256
    ),
) -> dict[str, Any]:
    principal = _principal(request)
    _require_scope(principal, "twi:monitors:write")
    key = _idempotency_key(idempotency_key)
    try:
        job = _service(request).enqueue_run(
            tenant_id=principal.tenant_id,
            subject_id=principal.subject_id,
            monitor_id=monitor_id,
            idempotency_key=key,
            traceparent=extract_valid_traceparent(request.headers),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="monitor not found") from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key conflicts with an existing monitor run",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="monitor is not active") from exc
    response.headers["Location"] = f"/v1/monitors/{monitor_id}/runs/{job.job_id}"
    return job.to_dict()


@router.get("/{monitor_id}/runs/{job_id}")
def get_monitor_run(request: Request, monitor_id: str, job_id: str) -> dict[str, Any]:
    principal, _ = _visible_monitor(request, monitor_id)
    administrative = "twi:monitors:read:any" in principal.scopes
    repository: JobRepository = request.app.state.repository
    job = repository.get(
        job_id,
        tenant_id=principal.tenant_id,
        subject_id=None if administrative else principal.subject_id,
    )
    if job is None or job.kind != "monitor" or job.payload.get("monitor_id") != monitor_id:
        raise HTTPException(status_code=404, detail="monitor run not found")
    return job.to_dict()


@router.post("/{monitor_id}/pause")
def pause_monitor(request: Request, monitor_id: str) -> dict[str, Any]:
    principal = _principal(request)
    _require_scope(principal, "twi:monitors:write")
    try:
        monitor = _service(request).pause(
            tenant_id=principal.tenant_id,
            subject_id=principal.subject_id,
            monitor_id=monitor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="monitor not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="deleted monitor cannot be changed") from exc
    return _public_monitor(monitor)


@router.post("/{monitor_id}/resume")
def resume_monitor(request: Request, monitor_id: str) -> dict[str, Any]:
    principal = _principal(request)
    _require_scope(principal, "twi:monitors:write")
    try:
        monitor = _service(request).resume(
            tenant_id=principal.tenant_id,
            subject_id=principal.subject_id,
            monitor_id=monitor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="monitor not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="deleted monitor cannot be changed") from exc
    return _public_monitor(monitor)


@router.delete("/{monitor_id}")
def delete_monitor(request: Request, monitor_id: str) -> dict[str, Any]:
    principal = _principal(request)
    _require_scope(principal, "twi:monitors:delete")
    try:
        monitor = _service(request).delete(
            tenant_id=principal.tenant_id,
            subject_id=principal.subject_id,
            monitor_id=monitor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="monitor not found") from exc
    return _public_monitor(monitor)
