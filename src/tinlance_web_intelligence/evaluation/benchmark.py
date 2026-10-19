"""Offline, deterministic evaluation of retrieval and evidence-quality observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit, urlunsplit

from tinlance_web_intelligence.contracts.provenance import (
    FreshnessStatus,
    ProvenanceError,
    assess_freshness,
)


class BenchmarkError(ValueError):
    """Raised when benchmark datasets or result observations violate the contract."""


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    expected_urls: tuple[str, ...]
    expected_domains: tuple[str, ...]
    expected_phrases: tuple[str, ...]
    max_age_seconds: int
    expected_failure_mode: str | None
    challenge_class: str
    support_status: str
    expected_completion_status: str
    evidence_mode: str
    max_duplicate_retrievals: int


@dataclass(frozen=True, slots=True)
class Evidence:
    url: str
    retrieved_at: datetime
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class Claim:
    text: str
    citations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CaseObservation:
    case_id: str
    retrieved: tuple[Evidence, ...]
    claims: tuple[Claim, ...]
    failure_mode: str | None
    completion_status: str
    latency_ms: int
    resource_bytes: int
    request_count: int
    retry_count: int
    evidence_mode: str


_STOP_WORDS = frozenset(
    {
        "about", "after", "also", "and", "are", "for", "from", "into", "its",
        "not", "of", "our", "that", "the", "their", "then", "this", "through",
        "to", "was", "were", "with", "you", "your",
    }
)
_TOKEN = re.compile(r"[a-z0-9_]{3,}")
_SCHEMA_VERSION = "1.1.0"
_REPORT_SCHEMA_VERSION = "1.1.0"
_ALLOWED_COMPLETION = frozenset({"completed", "failed", "unsupported"})
_ALLOWED_SUPPORT = frozenset({"supported", "unsupported"})
_ALLOWED_EVIDENCE_MODES = frozenset({"synthetic", "live"})
_MAX_LATENCY_MS = 600_000
_MAX_RESOURCE_BYTES = 100_000_000
_MAX_REQUEST_COUNT = 10_000
_MAX_RETRY_COUNT = 100
_MAX_DUPLICATES = 10_000
_ALLOWED_CHALLENGE_CLASSES = frozenset({
    "baseline_retrieval", "stale_evidence", "unsupported_claim", "redirect_ssrf",
    "tenant_scope_denial", "capture_failure", "javascript_heavy", "pagination_dedup",
    "conflicting_sources", "transient_recovery", "anti_bot_challenge",
    "unsupported_content_type",
})


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise BenchmarkError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise BenchmarkError(f"{field} must be an array")
    return cast(list[object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise BenchmarkError(f"{field} must be a non-empty normalized string")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) > 5_000_000:
        raise BenchmarkError(f"{field} must be text no larger than five million characters")
    return value


def _string_list(value: object, field: str) -> tuple[str, ...]:
    items = tuple(_string(item, f"{field}[]") for item in _list(value, field))
    if not items or len(set(items)) != len(items):
        raise BenchmarkError(f"{field} must contain unique non-empty values")
    return items


def _timestamp(value: object, field: str) -> datetime:
    raw = _string(value, field)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BenchmarkError(f"{field} must be timezone-aware")
    return parsed.astimezone(UTC)


def _url(value: object, field: str) -> str:
    raw = _string(value, field)
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise BenchmarkError(f"{field} contains control characters")
    try:
        parsed = urlsplit(raw)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise BenchmarkError(f"{field} must be a valid HTTP(S) URL") from exc
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise BenchmarkError(f"{field} must be an absolute HTTP(S) URL without userinfo")
    netloc = parsed.netloc.lower()
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, ""))


def _domain(value: object, field: str) -> str:
    domain = _string(value, field).lower().rstrip(".")
    if not domain or "/" in domain or ":" in domain or "@" in domain:
        raise BenchmarkError(f"{field} must be a hostname without a port")
    return domain


def load_dataset(raw: bytes) -> tuple[str, tuple[BenchmarkCase, ...]]:
    """Load and strictly validate a versioned benchmark dataset."""
    try:
        payload = _mapping(json.loads(raw), "dataset")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError("dataset must be valid UTF-8 JSON") from exc
    if payload.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkError("unsupported dataset schema_version")
    if set(payload) != {"schema_version", "dataset_id", "description", "cases"}:
        raise BenchmarkError("dataset fields do not match schema version 1.1.0")
    dataset_id = _string(payload.get("dataset_id"), "dataset_id")
    cases: list[BenchmarkCase] = []
    seen: set[str] = set()
    for index, item in enumerate(_list(payload.get("cases"), "cases")):
        row = _mapping(item, f"cases[{index}]")
        case_id = _string(row.get("case_id"), f"cases[{index}].case_id")
        if case_id in seen:
            raise BenchmarkError(f"duplicate benchmark case_id: {case_id}")
        seen.add(case_id)
        max_age = row.get("max_age_seconds")
        if type(max_age) is not int or max_age <= 0:
            raise BenchmarkError(f"cases[{index}].max_age_seconds must be a positive integer")
        failure_mode = row.get("expected_failure_mode")
        if failure_mode is not None:
            failure_mode = _string(failure_mode, f"cases[{index}].expected_failure_mode")
        challenge_class = _string(row.get("challenge_class"), f"cases[{index}].challenge_class")
        support_status = _string(row.get("support_status"), f"cases[{index}].support_status")
        completion_status = _string(
            row.get("expected_completion_status"), f"cases[{index}].expected_completion_status"
        )
        evidence_mode = _string(row.get("evidence_mode"), f"cases[{index}].evidence_mode")
        max_duplicates = row.get("max_duplicate_retrievals", 0)
        if support_status not in _ALLOWED_SUPPORT:
            raise BenchmarkError(f"cases[{index}].support_status is invalid")
        if completion_status not in _ALLOWED_COMPLETION:
            raise BenchmarkError(f"cases[{index}].expected_completion_status is invalid")
        if evidence_mode not in _ALLOWED_EVIDENCE_MODES:
            raise BenchmarkError(f"cases[{index}].evidence_mode is invalid")
        if type(max_duplicates) is not int or not 0 <= max_duplicates <= _MAX_DUPLICATES:
            raise BenchmarkError(f"cases[{index}].max_duplicate_retrievals is invalid")
        if set(row) != {
            "case_id", "expected_urls", "expected_domains", "expected_phrases",
            "max_age_seconds", "expected_failure_mode", "challenge_class", "support_status",
            "expected_completion_status", "evidence_mode", "max_duplicate_retrievals",
        }:
            raise BenchmarkError(f"cases[{index}] fields do not match schema version 1.1.0")
        challenge_class = _string(row.get("challenge_class"), f"cases[{index}].challenge_class")
        if challenge_class not in _ALLOWED_CHALLENGE_CLASSES:
            raise BenchmarkError(f"cases[{index}].challenge_class is invalid")
        cases.append(
            BenchmarkCase(
                case_id=case_id,
                expected_urls=tuple(
                    _url(url, f"cases[{index}].expected_urls[]")
                    for url in _string_list(
                        row.get("expected_urls"), f"cases[{index}].expected_urls"
                    )
                ),
                expected_domains=tuple(
                    _domain(domain, f"cases[{index}].expected_domains[]")
                    for domain in _string_list(
                        row.get("expected_domains"), f"cases[{index}].expected_domains"
                    )
                ),
                expected_phrases=_string_list(
                    row.get("expected_phrases"), f"cases[{index}].expected_phrases"
                ),
                max_age_seconds=max_age,
                expected_failure_mode=failure_mode,
                challenge_class=challenge_class,
                support_status=_string(row.get("support_status"), "support_status"),
                expected_completion_status=_string(
                    row.get("expected_completion_status"), "expected_completion_status"
                ),
                evidence_mode=_string(row.get("evidence_mode"), "evidence_mode"),
                max_duplicate_retrievals=row.get("max_duplicate_retrievals"),
                challenge_class=challenge_class,
                support_status=support_status,
                expected_completion_status=completion_status,
                evidence_mode=evidence_mode,
                max_duplicate_retrievals=max_duplicates,
            )
        )
    if not cases:
        raise BenchmarkError("dataset must contain at least one case")
    return dataset_id, tuple(cases)


def load_observations(raw: bytes, expected_dataset_id: str) -> tuple[CaseObservation, ...]:
    """Load result observations and reject missing, duplicate, or malformed cases."""
    try:
        payload = _mapping(json.loads(raw), "results")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError("results must be valid UTF-8 JSON") from exc
    if payload.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkError("unsupported results schema_version")
    if set(payload) != {"schema_version", "dataset_id", "cases"}:
        raise BenchmarkError("results fields do not match schema version 1.1.0")
    if payload.get("dataset_id") != expected_dataset_id:
        raise BenchmarkError("results dataset_id does not match dataset")
    observations: list[CaseObservation] = []
    seen: set[str] = set()
    for index, item in enumerate(_list(payload.get("cases"), "results.cases")):
        row = _mapping(item, f"results.cases[{index}]")
        if set(row) != {
            "case_id", "retrieved", "claims", "failure_mode", "completion_status",
            "latency_ms", "resource_bytes", "request_count", "retry_count", "evidence_mode",
        }:
            raise BenchmarkError(f"results.cases[{index}] fields do not match schema version 1.1.0")
        case_id = _string(row.get("case_id"), f"results.cases[{index}].case_id")
        if case_id in seen:
            raise BenchmarkError(f"duplicate result case_id: {case_id}")
        seen.add(case_id)
        retrieved: list[Evidence] = []
        for evidence_index, raw_evidence in enumerate(
            _list(row.get("retrieved"), f"results.cases[{index}].retrieved")
        ):
            evidence = _mapping(raw_evidence, f"results.cases[{index}].retrieved[{evidence_index}]")
            if set(evidence) != {"url", "retrieved_at", "title", "text"}:
                raise BenchmarkError("retrieved evidence fields do not match schema")
            retrieved.append(
                Evidence(
                    url=_url(evidence.get("url"), "retrieved.url"),
                    retrieved_at=_timestamp(evidence.get("retrieved_at"), "retrieved.retrieved_at"),
                    title=_text(evidence.get("title"), "retrieved.title"),
                    text=_text(evidence.get("text"), "retrieved.text"),
                )
            )
        claims: list[Claim] = []
        for claim_index, raw_claim in enumerate(
            _list(row.get("claims"), f"results.cases[{index}].claims")
        ):
            claim = _mapping(raw_claim, f"results.cases[{index}].claims[{claim_index}]")
            if set(claim) != {"text", "citations"}:
                raise BenchmarkError("claim fields do not match schema")
            citations = tuple(
                _url(url, "claim.citations[]")
                for url in _list(claim.get("citations"), "claim.citations")
            )
            claims.append(Claim(text=_string(claim.get("text"), "claim.text"), citations=citations))
        failure_mode = row.get("failure_mode")
        if failure_mode is not None:
            failure_mode = _string(failure_mode, "failure_mode")
        completion_status = _string(row.get("completion_status"), "completion_status")
        evidence_mode = _string(row.get("evidence_mode"), "evidence_mode")
        if completion_status not in _ALLOWED_COMPLETION:
            raise BenchmarkError("completion_status is invalid")
        if evidence_mode not in _ALLOWED_EVIDENCE_MODES:
            raise BenchmarkError("evidence_mode is invalid")
        measurements = {
            "latency_ms": (row.get("latency_ms"), _MAX_LATENCY_MS),
            "resource_bytes": (row.get("resource_bytes"), _MAX_RESOURCE_BYTES),
            "request_count": (row.get("request_count"), _MAX_REQUEST_COUNT),
            "retry_count": (row.get("retry_count"), _MAX_RETRY_COUNT),
        }
        for field, (value, maximum) in measurements.items():
            minimum = 1 if field == "request_count" else 0
            if type(value) is not int or not minimum <= value <= maximum:
                raise BenchmarkError(f"{field} must be an integer from {minimum} to {maximum}")
        observations.append(
            CaseObservation(
                case_id=case_id,
                retrieved=tuple(retrieved),
                claims=tuple(claims),
                failure_mode=failure_mode,
                completion_status=completion_status,
                latency_ms=measurements["latency_ms"][0],
                resource_bytes=measurements["resource_bytes"][0],
                request_count=measurements["request_count"][0],
                retry_count=measurements["retry_count"][0],
                evidence_mode=evidence_mode,
            )
        )
    if not observations:
        raise BenchmarkError("results must contain at least one case")
    return tuple(observations)


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN.findall(text.lower()) if token not in _STOP_WORDS}


def _claim_is_grounded(claim: Claim, evidence_by_url: Mapping[str, Evidence]) -> bool:
    if not claim.citations:
        return False
    claim_tokens = _tokens(claim.text)
    if not claim_tokens:
        return False
    cited = [evidence_by_url.get(url) for url in claim.citations]
    if any(item is None for item in cited):
        return False
    for item in cited:
        if item is None:
            continue
        source_tokens = _tokens(f"{item.title} {item.text}")
        overlap = len(claim_tokens & source_tokens) / len(claim_tokens)
        if overlap >= 0.5:
            return True
    return False


def _mean(values: Sequence[float | None]) -> float | None:
    observed = [value for value in values if value is not None]
    if not observed:
        return None
    return round(sum(observed) / len(observed), 6)


def load_threshold_registry(raw: bytes, expected_dataset_id: str) -> dict[str, object]:
    """Load a threshold registry; unapproved thresholds must remain empty and fail closed."""
    try:
        payload = _mapping(json.loads(raw), "threshold registry")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError("threshold registry must be valid UTF-8 JSON") from exc
    required = {
        "schema_version", "dataset_id", "approval_status", "owner",
        "approval_reference", "thresholds",
    }
    if set(payload) != required:
        raise BenchmarkError("threshold registry fields do not match schema")
    if payload["schema_version"] != "1.0.0" or payload["dataset_id"] != expected_dataset_id:
        raise BenchmarkError("threshold registry version or dataset ID does not match")
    approval_status = payload["approval_status"]
    if approval_status not in {"approved", "not_approved"}:
        raise BenchmarkError("threshold approval_status is invalid")
    thresholds = _mapping(payload["thresholds"], "thresholds")
    if approval_status == "not_approved":
        if payload["owner"] is not None or payload["approval_reference"] is not None or thresholds:
            raise BenchmarkError("unapproved thresholds must not contain owners or numeric values")
        return dict(payload)
    owner = _string(payload["owner"], "threshold owner")
    approval_reference = _string(payload["approval_reference"], "threshold approval_reference")
    del owner, approval_reference
    allowed_metrics = {
        "retrieval_recall", "source_diversity_coverage", "extraction_coverage",
        "citation_grounding_rate", "freshness_rate", "failure_calibration_accuracy",
        "outcome_correctness_rate", "evidence_quality_score", "latency_ms_mean",
        "latency_ms_p95", "resource_bytes_mean", "request_count_mean", "retry_count_mean",
    }
    if not thresholds or not set(thresholds).issubset(allowed_metrics):
        raise BenchmarkError("approved thresholds must name supported benchmark metrics")
    for name, raw_bounds in thresholds.items():
        bounds = _mapping(raw_bounds, f"thresholds.{name}")
        if not bounds or not set(bounds).issubset({"min", "max"}):
            raise BenchmarkError(f"thresholds.{name} must contain min and/or max")
        values: dict[str, float] = {}
        for bound, value in bounds.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise BenchmarkError(f"thresholds.{name}.{bound} must be a finite number")
            values[bound] = float(value)
        if "min" in values and "max" in values and values["min"] > values["max"]:
            raise BenchmarkError(f"thresholds.{name}.min cannot exceed max")
    return dict(payload)


def _report_digest(report: Mapping[str, object]) -> str:
    unsigned = {key: value for key, value in report.items() if key != "report_sha256"}
    canonical = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_report(report: Mapping[str, object]) -> None:
    """Validate the deterministic report digest and the minimum report envelope."""
    if report.get("schema_version") != _REPORT_SCHEMA_VERSION:
        raise BenchmarkError("unsupported report schema_version")
    report_digest = report.get("report_sha256")
    if not isinstance(report_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", report_digest):
        raise BenchmarkError("report_sha256 must be a lowercase SHA-256 digest")
    if _report_digest(report) != report_digest:
        raise BenchmarkError("benchmark report SHA-256 integrity check failed")
    for field in ("dataset_sha256", "results_sha256", "thresholds_sha256"):
        value = report.get(field)
        if value is not None and (
            not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
        ):
            raise BenchmarkError(f"{field} must be a lowercase SHA-256 digest or null")


def _p95(values: Sequence[int]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])


def evaluate(
    dataset_id: str,
    cases: Sequence[BenchmarkCase],
    observations: Sequence[CaseObservation],
    *,
    now: datetime,
    dataset_sha256: str,
    results_sha256: str,
    source_revision: str | None = None,
    threshold_registry: Mapping[str, object] | None = None,
    thresholds_sha256: str | None = None,
) -> dict[str, object]:
    """Evaluate recorded observations deterministically; no network or truth judgment is performed."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise BenchmarkError("evaluation now must be timezone-aware")
    if not cases or not observations:
        raise BenchmarkError("evaluation requires at least one case and one observation")
    for field, value in (("dataset_sha256", dataset_sha256), ("results_sha256", results_sha256)):
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise BenchmarkError(f"{field} must be a lowercase SHA-256 digest")
    if source_revision is not None and not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise BenchmarkError("source_revision must be a full lowercase Git commit SHA or null")
    if thresholds_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", thresholds_sha256):
        raise BenchmarkError("thresholds_sha256 must be a lowercase SHA-256 digest or null")
    registry: Mapping[str, object] = threshold_registry or {
        "approval_status": "not_approved", "owner": None,
        "approval_reference": None, "thresholds": {},
    }
    approval_status = registry.get("approval_status")
    threshold_values = _mapping(registry.get("thresholds", {}), "thresholds")
    case_ids = {case.case_id for case in cases}
    result_ids = {result.case_id for result in observations}
    if case_ids != result_ids or len(result_ids) != len(observations):
        raise BenchmarkError("results case IDs must match dataset case IDs exactly")
    observation_by_id = {result.case_id: result for result in observations}
    metric_names = (
        "retrieval_recall",
        "source_diversity_coverage",
        "extraction_coverage",
        "citation_grounding_rate",
        "freshness_rate",
        "failure_calibration_accuracy",
        "outcome_correctness_rate",
        "evidence_quality_score",
    )
    metric_values: dict[str, list[float | None]] = {name: [] for name in metric_names}
    case_reports: list[dict[str, object]] = []
    challenge_counts: dict[str, int] = {}
    completion_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    support_counts: dict[str, int] = {}
    evidence_mode_counts: dict[str, int] = {}
    for case in cases:
        observation = observation_by_id[case.case_id]
        if observation.evidence_mode != case.evidence_mode:
            raise BenchmarkError(f"evidence_mode mismatch for case {case.case_id}")
        challenge_counts[case.challenge_class] = challenge_counts.get(case.challenge_class, 0) + 1
        completion_counts[observation.completion_status] = (
            completion_counts.get(observation.completion_status, 0) + 1
        )
        failure_key = observation.failure_mode or "none"
        failure_counts[failure_key] = failure_counts.get(failure_key, 0) + 1
        support_counts[case.support_status] = support_counts.get(case.support_status, 0) + 1
        evidence_mode_counts[observation.evidence_mode] = (
            evidence_mode_counts.get(observation.evidence_mode, 0) + 1
        )

        retrieved_urls_list = [_url(item.url, "retrieved.url") for item in observation.retrieved]
        retrieved_urls = set(retrieved_urls_list)
        duplicate_count = len(retrieved_urls_list) - len(retrieved_urls)
        retrieved_domains = {
            (urlsplit(item.url).hostname or "").lower().rstrip(".")
            for item in observation.retrieved
        }
        retrieval_recall = len(set(case.expected_urls) & retrieved_urls) / len(case.expected_urls)
        diversity_coverage = (
            len(set(case.expected_domains) & retrieved_domains) / len(case.expected_domains)
        )
        all_text = "\\n".join(
            f"{item.title}\\n{item.text}" for item in observation.retrieved
        ).lower()
        extraction_coverage = (
            sum(1 for phrase in case.expected_phrases if phrase.lower() in all_text)
            / len(case.expected_phrases)
        )
        evidence_by_url = {item.url: item for item in observation.retrieved}
        citation_grounding = (
            sum(1 for claim in observation.claims if _claim_is_grounded(claim, evidence_by_url))
            / len(observation.claims)
            if observation.claims
            else None
        )
        freshness_values: list[bool] = []
        for item in observation.retrieved:
            try:
                freshness = assess_freshness(
                    item.retrieved_at,
                    now=now,
                    max_age=timedelta(seconds=case.max_age_seconds),
                )
            except ProvenanceError as exc:
                raise BenchmarkError(f"invalid freshness input for {case.case_id}") from exc
            freshness_values.append(freshness is FreshnessStatus.FRESH)
        freshness_rate = (
            sum(1 for value in freshness_values if value) / len(freshness_values)
            if freshness_values
            else None
        )
        failure_accuracy = float(observation.failure_mode == case.expected_failure_mode)
        completion_accuracy = float(
            observation.completion_status == case.expected_completion_status
        )
        duplicate_policy_ok = duplicate_count <= case.max_duplicate_retrievals
        outcome_correctness = float(
            completion_accuracy == 1.0 and failure_accuracy == 1.0 and duplicate_policy_ok
        )
        evidence_quality = _mean(
            [
                retrieval_recall,
                diversity_coverage,
                extraction_coverage,
                citation_grounding,
                freshness_rate,
            ]
        )
        metrics: dict[str, float | None] = {
            "retrieval_recall": round(retrieval_recall, 6),
            "source_diversity_coverage": round(diversity_coverage, 6),
            "extraction_coverage": round(extraction_coverage, 6),
            "citation_grounding_rate": (
                round(citation_grounding, 6) if citation_grounding is not None else None
            ),
            "freshness_rate": round(freshness_rate, 6) if freshness_rate is not None else None,
            "failure_calibration_accuracy": failure_accuracy,
            "outcome_correctness_rate": outcome_correctness,
            "evidence_quality_score": round(evidence_quality or 0.0, 6),
        }
        for name, value in metrics.items():
            metric_values[name].append(value)
        case_reports.append(
            {
                "case_id": case.case_id,
                "challenge_class": case.challenge_class,
                "support_status": case.support_status,
                "evidence_mode": observation.evidence_mode,
                "completion_status": observation.completion_status,
                "failure_mode": observation.failure_mode,
                "retrieved_item_count": len(observation.retrieved),
                "distinct_domain_count": len(retrieved_domains),
                "duplicate_retrieval_count": duplicate_count,
                "expected_max_duplicate_retrievals": case.max_duplicate_retrievals,
                "metrics": metrics,
                "measurements": {
                    "latency_ms": observation.latency_ms,
                    "resource_bytes": observation.resource_bytes,
                    "request_count": observation.request_count,
                    "retry_count": observation.retry_count,
                },
            }
        )
    summary: dict[str, float | None] = {
        name: _mean(values) for name, values in metric_values.items()
    }
    summary.update(
        {
            "latency_ms_mean": _mean([float(item.latency_ms) for item in observations]),
            "latency_ms_p95": _p95([item.latency_ms for item in observations]),
            "resource_bytes_mean": _mean([float(item.resource_bytes) for item in observations]),
            "request_count_mean": _mean([float(item.request_count) for item in observations]),
            "retry_count_mean": _mean([float(item.retry_count) for item in observations]),
        }
    )
    modes = set(evidence_mode_counts)
    overall_evidence_mode = (
        next(iter(modes)) if len(modes) == 1 else "mixed"
    )
    qualification_status = "not_evidenced"
    qualification_reason = "source_revision_missing"
    if source_revision is not None:
        if overall_evidence_mode != "live":
            qualification_reason = "synthetic_or_mixed_evidence_cannot_qualify_live_quality"
        elif approval_status != "approved":
            qualification_reason = "thresholds_not_approved"
        else:
            failures: list[str] = []
            unavailable: list[str] = []
            for name, raw_bounds in threshold_values.items():
                bounds = _mapping(raw_bounds, f"thresholds.{name}")
                value = summary.get(name)
                if not isinstance(value, (int, float)):
                    unavailable.append(name)
                    continue
                if "min" in bounds and value < bounds["min"]:
                    failures.append(name)
                if "max" in bounds and value > bounds["max"]:
                    failures.append(name)
            if unavailable:
                qualification_reason = "threshold_metrics_unavailable:" + ",".join(sorted(unavailable))
            elif failures:
                qualification_status = "fail"
                qualification_reason = "thresholds_failed:" + ",".join(sorted(failures))
            else:
                qualification_status = "pass"
                qualification_reason = "approved_thresholds_satisfied"

    report: dict[str, object] = {
        "schema_version": _REPORT_SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "results_sha256": results_sha256,
        "thresholds_sha256": thresholds_sha256,
        "source_revision": source_revision,
        "evaluation_time": now.astimezone(UTC).isoformat(),
        "evidence_mode": overall_evidence_mode,
        "quality_claim": (
            "synthetic_contract_fixture_not_live_quality"
            if overall_evidence_mode == "synthetic"
            else "mixed_synthetic_and_live_observations"
            if overall_evidence_mode == "mixed"
            else "live_observations_require_independent_review"
        ),
        "qualification": {
            "status": qualification_status,
            "reason": qualification_reason,
            "threshold_approval_status": approval_status or "not_approved",
            "threshold_owner": registry.get("owner"),
            "threshold_approval_reference": registry.get("approval_reference"),
        },
        "counts": {
            "case_count": len(cases),
            "challenge_class_counts": dict(sorted(challenge_counts.items())),
            "completion_status_counts": dict(sorted(completion_counts.items())),
            "failure_mode_counts": dict(sorted(failure_counts.items())),
            "support_status_counts": dict(sorted(support_counts.items())),
            "evidence_mode_counts": dict(sorted(evidence_mode_counts.items())),
        },
        "methodology": {
            "aggregation": "macro-average per case; null metrics are excluded",
            "citation_grounding": (
                "heuristic lexical overlap; cited URL must exist in retrieved evidence and "
                "at least 50% of non-stopword claim tokens must occur in one cited source"
            ),
            "evidence_quality_score": (
                "mean of retrieval recall, source-diversity coverage, extraction coverage, "
                "and available citation-grounding/freshness metrics; not factual truth"
            ),
            "outcome_correctness_rate": (
                "expected completion status and failure classification match, and duplicate "
                "retrieval count does not exceed the case limit"
            ),
            "latency_p95": "nearest-rank 95th percentile across case latency_ms measurements",
            "freshness": "explicit case max_age_seconds and five-minute future clock-skew allowance",
            "truth_boundary": (
                "metrics measure observed retrieval/evidence properties, not factual truth"
            ),
        },
        "summary": summary,
        "cases": case_reports,
    }
    report["report_sha256"] = _report_digest(report)
    validate_report(report)
    return report

def _format_metric(value: object) -> str:
    if value is None:
        return "n/a"
    if not isinstance(value, (int, float)):
        raise BenchmarkError("metric values must be numeric or null")
    return f"{value:.3f}"


def render_markdown(report: Mapping[str, object]) -> str:
    """Render a compact, URL-free human-readable evaluation report."""
    summary = cast(Mapping[str, object], report["summary"])
    lines = [
        f"# TWI benchmark report: {report['dataset_id']}",
        "",
        f"- Evaluation time: {report['evaluation_time']}",
        f"- Dataset SHA-256: {report['dataset_sha256']}",
        f"- Results SHA-256: {report['results_sha256']}",
        "",
        "## Macro-average metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for name, value in summary.items():
        rendered = _format_metric(value)
        lines.append(f"| {name} | {rendered} |")
    lines.extend(
        [
            "",
            "## Per-case metrics",
            "",
            "| Case | Items | Domains | Recall | Diversity | "
            "Extract | Grounding | Fresh | Failure match |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for raw_case in cast(list[object], report["cases"]):
        case = cast(Mapping[str, object], raw_case)
        metrics = cast(Mapping[str, object], case["metrics"])
        values = [
            _format_metric(metrics[name])
            for name in (
                "retrieval_recall",
                "source_diversity_coverage",
                "extraction_coverage",
                "citation_grounding_rate",
                "freshness_rate",
                "failure_calibration_accuracy",
            )
        ]
        lines.append(
            f"| {case['case_id']} | {case['retrieved_item_count']} | "
            f"{case['distinct_domain_count']} | " + " | ".join(values) + " |"
        )
    lines.extend(
        [
            "",
            "Citation grounding is a lexical heuristic, not semantic proof. These metrics do not",
            "establish factual truth, source authority, or production readiness.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument(
        "--now", required=True, help="fixed timezone-aware ISO-8601 evaluation time"
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args(argv)
    try:
        dataset_raw = args.dataset.read_bytes()
        results_raw = args.results.read_bytes()
        now = _timestamp(args.now, "--now")
        dataset_id, cases = load_dataset(dataset_raw)
        observations = load_observations(results_raw, dataset_id)
        report = evaluate(
            dataset_id,
            cases,
            observations,
            now=now,
            dataset_sha256=hashlib.sha256(dataset_raw).hexdigest(),
            results_sha256=hashlib.sha256(results_raw).hexdigest(),
        )
        rendered_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
        rendered_markdown = render_markdown(report)
        if args.json_out:
            args.json_out.write_text(rendered_json, encoding="utf-8")
        if args.markdown_out:
            args.markdown_out.write_text(rendered_markdown, encoding="utf-8")
        sys.stdout.write(rendered_json)
    except (OSError, BenchmarkError, ProvenanceError) as exc:
        parser.error(str(exc))
    return 0
