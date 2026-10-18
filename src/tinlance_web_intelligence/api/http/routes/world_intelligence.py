"""Governed export of source-grounded claims to the World Intelligence candidate-evidence outbox."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.integrations.world_intelligence.client import (
    redact_source_url,
    validate_traceparent,
)
from tinlance_web_intelligence.integrations.world_intelligence.outbox import (
    OutboxConflictError,
)
from tinlance_web_intelligence.jobs.model import Job
from tinlance_web_intelligence.research.verification import (
    CitationInput,
    CitationNotFoundError,
    CitationSourceError,
    ClaimInput,
    _normalized_text,
    verify_research_report,
)

router = APIRouter(prefix="/v1/integrations/world-intelligence", tags=["world-intelligence"])


class ExportSourceEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,64}$")
    statement: str = Field(min_length=1, max_length=500)
    job_id: str = Field(min_length=1, max_length=64)
    quote: str = Field(min_length=8, max_length=350)


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


def _scope(principal: Principal, required: str) -> None:
    if required not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")


def _request_id(request: Request) -> str:
    value = request.headers.get("X-Request-ID", "")
    return value if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value) else str(uuid.uuid4())


@router.post("/exports")
def export_source_evidence(
    request: Request, body: ExportSourceEvidenceRequest
) -> JSONResponse:
    principal = _principal(request)
    _scope(principal, "twi:observations:export")
    idempotency_key = request.headers.get("Idempotency-Key", "")
    traceparent = request.headers.get("traceparent")
    try:
        validate_traceparent(traceparent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid trace context") from exc

    repository = request.app.state.repository
    read_any = "twi:jobs:read:any" in principal.scopes

    def resolve_job(job_id: str) -> Job | None:
        return cast(
            Job | None,
            repository.get(
                job_id,
            tenant_id=principal.tenant_id,
                subject_id=None if read_any else principal.subject_id,
            ),
        )

    claim = ClaimInput(
        claim_id=body.claim_id,
        statement=body.statement,
        citations=(CitationInput(job_id=body.job_id, quote=body.quote),),
    )
    try:
        verification = verify_research_report((claim,), resolve_job=resolve_job)
    except CitationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="citation job not found") from exc
    except CitationSourceError as exc:
        raise HTTPException(
            status_code=422, detail="valid captured source evidence is required"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="source-evidence validation failed") from exc

    citation = verification["claims"][0]["citations"][0]
    if not citation["quote_match"]:
        raise HTTPException(status_code=422, detail="quote must match captured source text")
    source = citation["source"]
    quote = _normalized_text(body.quote)
    redacted_source_url = redact_source_url(source["url"])
    payload = {
        "schema_version": "1.0.0",
        "source_system": "tinlance-web-intelligence",
        "tenant_ref": hashlib.sha256(principal.tenant_id.encode("utf-8")).hexdigest(),
        "source_job_id": body.job_id,
        "claim_id": body.claim_id,
        "statement": _normalized_text(body.statement),
        "source_url": redacted_source_url,
        "source_url_redacted": redacted_source_url != source["url"],
        "retrieved_at": source["retrieved_at"],
        "media_type": source["media_type"][:128],
        "artifact_sha256": source["content_sha256"],
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "verifier_version": verification["verifier_version"],
        "report_sha256": verification["report_sha256"],
    }
    tenant_ref = payload["tenant_ref"]
    subject_ref = hashlib.sha256(principal.subject_id.encode("utf-8")).hexdigest()
    try:
        event, replayed = request.app.state.evidence_outbox.enqueue(
            tenant_ref=tenant_ref,
            subject_ref=subject_ref,
            idempotency_key=idempotency_key,
            payload=payload,
            request_id=_request_id(request),
            traceparent=traceparent,
        )
    except OutboxConflictError as exc:
        raise HTTPException(
            status_code=409, detail="idempotency key conflicts with another export"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="invalid idempotency key or export context"
        ) from exc
    return JSONResponse(
        status_code=200 if replayed else 202,
        content={
            "event_id": event.event_id,
            "status": event.status,
            "replayed": replayed,
            "report_sha256": verification["report_sha256"],
        },
    )


@router.get("/exports/{event_id}")
def read_export_status(event_id: str, request: Request) -> dict[str, Any]:
    principal = _principal(request)
    _scope(principal, "twi:observations:export:read")
    tenant_ref = hashlib.sha256(principal.tenant_id.encode("utf-8")).hexdigest()
    subject_ref = hashlib.sha256(principal.subject_id.encode("utf-8")).hexdigest()
    event = request.app.state.evidence_outbox.get(event_id, tenant_ref, subject_ref)
    if event is None:
        raise HTTPException(status_code=404, detail="export event not found")
    return {
        "event_id": event.event_id,
        "status": event.status,
        "attempts": event.attempts,
        "remote_evidence_id": event.remote_evidence_id,
    }
