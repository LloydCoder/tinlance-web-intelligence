"""Offline, deterministic evaluation of retrieval and evidence-quality observations."""

from __future__ import annotations

import argparse
import hashlib
import json
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


_STOP_WORDS = frozenset(
    {
        "about", "after", "also", "and", "are", "for", "from", "into", "its",
        "not", "of", "our", "that", "the", "their", "then", "this", "through",
        "to", "was", "were", "with", "you", "your",
    }
)
_TOKEN = re.compile(r"[a-z0-9_]{3,}")
_SCHEMA_VERSION = "1.0.0"


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
    if payload.get("dataset_id") != expected_dataset_id:
        raise BenchmarkError("results dataset_id does not match dataset")
    observations: list[CaseObservation] = []
    seen: set[str] = set()
    for index, item in enumerate(_list(payload.get("cases"), "results.cases")):
        row = _mapping(item, f"results.cases[{index}]")
        case_id = _string(row.get("case_id"), f"results.cases[{index}].case_id")
        if case_id in seen:
            raise BenchmarkError(f"duplicate result case_id: {case_id}")
        seen.add(case_id)
        retrieved: list[Evidence] = []
        for evidence_index, raw_evidence in enumerate(
            _list(row.get("retrieved"), f"results.cases[{index}].retrieved")
        ):
            evidence = _mapping(raw_evidence, f"results.cases[{index}].retrieved[{evidence_index}]")
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
            citations = tuple(
                _url(url, "claim.citations[]")
                for url in _list(claim.get("citations"), "claim.citations")
            )
            claims.append(Claim(text=_string(claim.get("text"), "claim.text"), citations=citations))
        failure_mode = row.get("failure_mode")
        if failure_mode is not None:
            failure_mode = _string(failure_mode, "failure_mode")
        observations.append(
            CaseObservation(
                case_id=case_id,
                retrieved=tuple(retrieved),
                claims=tuple(claims),
                failure_mode=failure_mode,
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


def evaluate(
    dataset_id: str,
    cases: Sequence[BenchmarkCase],
    observations: Sequence[CaseObservation],
    *,
    now: datetime,
    dataset_sha256: str,
    results_sha256: str,
) -> dict[str, object]:
    """Evaluate recorded observations without network access or nondeterministic time."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise BenchmarkError("evaluation now must be timezone-aware")
    case_ids = {case.case_id for case in cases}
    result_ids = {result.case_id for result in observations}
    if case_ids != result_ids or len(result_ids) != len(observations):
        raise BenchmarkError("results case IDs must match dataset case IDs exactly")
    observation_by_id = {result.case_id: result for result in observations}
    case_reports: list[dict[str, object]] = []
    metric_names = (
        "retrieval_recall",
        "source_diversity_coverage",
        "extraction_coverage",
        "citation_grounding_rate",
        "freshness_rate",
        "failure_calibration_accuracy",
    )
    metric_values: dict[str, list[float | None]] = {name: [] for name in metric_names}
    for case in cases:
        observation = observation_by_id[case.case_id]
        retrieved_urls = {_url(item.url, "retrieved.url") for item in observation.retrieved}
        retrieved_domains = {
            (urlsplit(item.url).hostname or "").lower().rstrip(".")
            for item in observation.retrieved
        }
        retrieval_recall = len(set(case.expected_urls) & retrieved_urls) / len(case.expected_urls)
        diversity_coverage = (
            len(set(case.expected_domains) & retrieved_domains) / len(case.expected_domains)
        )
        all_text = "\n".join(f"{item.title}\n{item.text}" for item in observation.retrieved).lower()
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
        metrics: dict[str, float | None] = {
            "retrieval_recall": round(retrieval_recall, 6),
            "source_diversity_coverage": round(diversity_coverage, 6),
            "extraction_coverage": round(extraction_coverage, 6),
            "citation_grounding_rate": (
                round(citation_grounding, 6) if citation_grounding is not None else None
            ),
            "freshness_rate": round(freshness_rate, 6) if freshness_rate is not None else None,
            "failure_calibration_accuracy": failure_accuracy,
        }
        for name, value in metrics.items():
            metric_values[name].append(value)
        case_reports.append(
            {
                "case_id": case.case_id,
                "retrieved_item_count": len(observation.retrieved),
                "distinct_domain_count": len(retrieved_domains),
                "metrics": metrics,
            }
        )
    return {
        "schema_version": _SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_sha256,
        "results_sha256": results_sha256,
        "evaluation_time": now.astimezone(UTC).isoformat(),
        "methodology": {
            "aggregation": "macro-average per case; null metrics are excluded",
            "citation_grounding": (
                "heuristic lexical overlap; cited URL must exist in retrieved evidence and "
                "at least 50% of non-stopword claim tokens must occur in one cited source"
            ),
            "freshness": (
                "explicit case max_age_seconds and five-minute future clock-skew allowance"
            ),
            "truth_boundary": (
                "metrics measure observed retrieval/evidence properties, not factual truth"
            ),
        },
        "summary": {name: _mean(values) for name, values in metric_values.items()},
        "cases": case_reports,
    }


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
