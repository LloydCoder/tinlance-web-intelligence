"""Source-grounded claim citation verification.

This module verifies that citations refer to successful TWI fetch/browser jobs and that
quoted excerpts occur in the captured text. It does not determine whether a claim is true.
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from tinlance_web_intelligence.contracts.observations import ContractError, SourceReference
from tinlance_web_intelligence.jobs.model import Job, JobStatus


class CitationSourceError(ValueError):
    """A citation does not reference successful acquisition evidence."""


class CitationNotFoundError(CitationSourceError):
    """A citation references no job visible to the authenticated principal."""


@dataclass(frozen=True, slots=True)
class CitationInput:
    job_id: str
    quote: str


@dataclass(frozen=True, slots=True)
class ClaimInput:
    claim_id: str
    statement: str
    citations: tuple[CitationInput, ...]


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise CitationSourceError("acquisition result has no retrieval timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CitationSourceError("acquisition result has an invalid retrieval timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CitationSourceError("acquisition timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _evidence_from_job(job: Job) -> dict[str, Any]:
    if job.status is not JobStatus.SUCCEEDED or job.kind not in {"fetch", "browser"}:
        raise CitationSourceError("citation must reference a successful fetch or browser job")
    result = job.result
    if not isinstance(result, dict):
        raise CitationSourceError("acquisition result is unavailable")
    source_url = result.get("source_url")
    text = result.get("text")
    content_sha256 = result.get("content_sha256")
    if not isinstance(source_url, str) or not isinstance(text, str) or not text.strip():
        raise CitationSourceError("acquisition result is missing source URL or captured text")
    if not isinstance(content_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", content_sha256):
        raise CitationSourceError("acquisition result has no valid content SHA-256")
    retrieved_at = _parse_timestamp(result.get("retrieved_at"))
    media_type_value = result.get("content_type")
    media_type = media_type_value if isinstance(media_type_value, str) else "text/plain"
    reference = SourceReference(
        url=source_url,
        retrieved_at=retrieved_at,
        media_type=media_type,
        content_sha256=content_sha256,
    )
    try:
        reference.validate()
    except ContractError as exc:
        raise CitationSourceError("acquisition result source reference is invalid") from exc
    return {
        "job_id": job.job_id,
        "source_url": source_url,
        "retrieved_at": retrieved_at.isoformat(),
        "media_type": media_type,
        "content_sha256": content_sha256,
        "text": text,
    }


def verify_research_report(
    claims: tuple[ClaimInput, ...],
    *,
    resolve_job: Callable[[str], Job | None],
) -> dict[str, Any]:
    """Verify citation provenance and exact excerpt matches against scoped TWI jobs."""
    if not claims:
        raise ValueError("at least one claim is required")
    if len(claims) > 50:
        raise ValueError("at most 50 claims are allowed")
    claim_ids = [claim.claim_id for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("claim_id values must be unique")

    evidence_by_job: dict[str, dict[str, Any]] = {}
    checked_claims: list[dict[str, Any]] = []
    canonical_claims: list[dict[str, Any]] = []

    for claim in claims:
        if not claim.citations:
            raise ValueError("every claim must contain at least one citation")
        if len(claim.citations) > 10:
            raise ValueError("at most 10 citations are allowed per claim")
        checked_citations: list[dict[str, Any]] = []
        matched_count = 0
        canonical_citations: list[dict[str, Any]] = []
        for citation in claim.citations:
            evidence = evidence_by_job.get(citation.job_id)
            if evidence is None:
                job = resolve_job(citation.job_id)
                if job is None:
                    raise CitationNotFoundError(
                        "citation job is not accessible to this principal"
                    )
                evidence = _evidence_from_job(job)
                evidence_by_job[citation.job_id] = evidence
            quote = _normalized_text(citation.quote)
            captured_text = _normalized_text(evidence["text"])
            matched = bool(quote) and quote in captured_text
            matched_count += int(matched)
            checked_citations.append({
                "job_id": citation.job_id,
                "quote": citation.quote,
                "quote_match": matched,
                "match_status": "matched" if matched else "quote_not_found",
                "source": {
                    "url": evidence["source_url"],
                    "retrieved_at": evidence["retrieved_at"],
                    "media_type": evidence["media_type"],
                    "content_sha256": evidence["content_sha256"],
                },
            })
            canonical_citations.append({
                "job_id": citation.job_id,
                "quote": quote,
                "quote_match": matched,
                "content_sha256": evidence["content_sha256"],
            })
        claim_status = (
            "all_citations_match_captured_text"
            if matched_count == len(claim.citations)
            else "citation_mismatch"
            if matched_count == 0
            else "partially_matched_citations"
        )
        checked_claims.append({
            "claim_id": claim.claim_id,
            "statement": claim.statement,
            "citation_status": claim_status,
            "citations": checked_citations,
        })
        canonical_claims.append({
            "claim_id": claim.claim_id,
            "statement": _normalized_text(claim.statement),
            "citations": canonical_citations,
        })

    digest_input = json.dumps(
        {"verifier_version": "twi-citation-verifier/1.0.0", "claims": canonical_claims},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    all_matched = all(
        claim["citation_status"] == "all_citations_match_captured_text"
        for claim in checked_claims
    )
    return {
        "verification_id": str(uuid.uuid4()),
        "verifier_version": "twi-citation-verifier/1.0.0",
        "verified_at": datetime.now(UTC).isoformat(),
        "report_sha256": sha256(digest_input).hexdigest(),
        "status": "all_citations_match_captured_text" if all_matched else "citation_mismatch",
        "factual_truth_assessed": False,
        "claims": checked_claims,
        "source_count": len(evidence_by_job),
        "claim_count": len(checked_claims),
        "citation_count": sum(len(claim["citations"]) for claim in checked_claims),
    }
