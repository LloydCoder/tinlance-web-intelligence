"""Authenticated, tenant-scoped verification of research citations against TWI captures."""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from tinlance_web_intelligence.auth.principal import Principal
from tinlance_web_intelligence.jobs.model import Job
from tinlance_web_intelligence.research.verification import (
    CitationInput,
    CitationNotFoundError,
    CitationSourceError,
    ClaimInput,
    verify_research_report,
)

router = APIRouter(prefix="/v1/research", tags=["research"])


class CitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str = Field(min_length=1, max_length=64)
    quote: str = Field(min_length=8, max_length=350)


class ClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,64}$")
    statement: str = Field(min_length=1, max_length=500)
    citations: list[CitationRequest] = Field(min_length=1, max_length=4)


class VerifyResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ClaimRequest] = Field(min_length=1, max_length=20)


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


@router.post("/verify")
def verify_research(request: Request, body: VerifyResearchRequest) -> dict[str, Any]:
    principal = _principal(request)
    if "twi:research:verify" not in principal.scopes:
        raise HTTPException(status_code=403, detail="required scope is missing")

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

    claims = tuple(
        ClaimInput(
            claim_id=claim.claim_id,
            statement=claim.statement,
            citations=tuple(
                CitationInput(job_id=citation.job_id, quote=citation.quote)
                for citation in claim.citations
            ),
        )
        for claim in body.claims
    )
    try:
        return verify_research_report(claims, resolve_job=resolve_job)
    except CitationNotFoundError as exc:
        # Do not reveal whether a job exists outside the caller's tenant/subject scope.
        raise HTTPException(status_code=404, detail="citation job not found") from exc
    except CitationSourceError as exc:
        raise HTTPException(
            status_code=422, detail="citation does not reference valid source evidence"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="research report failed validation") from exc
