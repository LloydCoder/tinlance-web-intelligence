"""Internal browser-job broker API; never expose this service on public ingress."""

from __future__ import annotations

import hmac
import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from tinlance_web_intelligence.jobs.model import LeaseLostError
from tinlance_web_intelligence.observability.tracing import validate_traceparent
from tinlance_web_intelligence.persistence.protocols import JobRepository


class CompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: str = Field(min_length=32, max_length=128)
    result: dict[str, Any]


class FailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease_token: str = Field(min_length=32, max_length=128)
    error_code: str = Field(min_length=1, max_length=64)
    retryable: bool = False


def create_app(repository: JobRepository, service_token: str) -> FastAPI:
    if len(service_token) < 32 or service_token != service_token.strip():
        raise ValueError("browser broker token must be at least 32 non-padded characters")

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.repository = repository

    @app.middleware("http")
    async def limit_internal_request_size(request: Request, call_next: Any) -> Response:
        if request.method == "POST":
            raw_length = request.headers.get("content-length")
            if raw_length is None:
                return JSONResponse(status_code=411, content={"detail": "content length required"})
            try:
                content_length = int(raw_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "invalid content length"})
            if content_length < 0 or content_length > 3_500_000:
                return JSONResponse(status_code=413, content={"detail": "request body too large"})
        response = await call_next(request)
        if not isinstance(response, Response):
            raise RuntimeError("internal middleware returned an invalid response")
        return response

    def authorize(request: Request) -> None:
        values = request.headers.getlist("authorization")
        expected = f"Bearer {service_token}"
        if len(values) != 1 or not hmac.compare_digest(values[0], expected):
            raise HTTPException(status_code=401, detail="service authentication required")

    @app.get("/health/ready")
    async def ready() -> dict[str, str]:
        if not repository.ping():
            raise HTTPException(status_code=503, detail="not ready")
        return {"status": "ready"}

    @app.post("/internal/browser-jobs/claim")
    async def claim(request: Request) -> Response:
        authorize(request)
        lease_token = secrets.token_urlsafe(32)
        job = repository.claim_next(
            lease_token,
            lease_seconds=90,
            allowed_kinds=("browser",),
        )
        if job is None:
            return Response(status_code=204)
        if job.kind != "browser":
            raise HTTPException(status_code=500, detail="invalid browser lease")
        body = {
            "job_id": job.job_id,
            "payload": job.payload,
            "lease_token": lease_token,
            "attempts": job.attempts,
            "traceparent": validate_traceparent(job.traceparent),
        }
        return JSONResponse(status_code=200, content=body)

    @app.post("/internal/browser-jobs/{job_id}/complete")
    async def complete(job_id: str, body: CompleteRequest, request: Request) -> dict[str, str]:
        authorize(request)
        try:
            job = repository.complete(job_id, body.lease_token, body.result)
        except LeaseLostError as exc:
            raise HTTPException(status_code=409, detail="browser job lease lost") from exc
        if job.kind != "browser":
            raise HTTPException(status_code=409, detail="job kind mismatch")
        return {"job_id": job.job_id, "status": job.status.value}

    @app.post("/internal/browser-jobs/{job_id}/fail")
    async def fail(job_id: str, body: FailRequest, request: Request) -> dict[str, str]:
        authorize(request)
        try:
            job = repository.fail(
                job_id,
                body.lease_token,
                error_code=body.error_code,
                retryable=body.retryable,
            )
        except LeaseLostError as exc:
            raise HTTPException(status_code=409, detail="browser job lease lost") from exc
        if job.kind != "browser":
            raise HTTPException(status_code=409, detail="job kind mismatch")
        return {"job_id": job.job_id, "status": job.status.value}

    return app
