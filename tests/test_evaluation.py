from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tinlance_web_intelligence.evaluation.benchmark import (
    BenchmarkError,
    evaluate,
    load_dataset,
    load_observations,
    render_markdown,
)

_ROOT = Path(__file__).resolve().parents[1]
_DATASET = _ROOT / "benchmarks/twi/v1/cases.json"
_RESULTS = _ROOT / "benchmarks/twi/v1/sample_results.json"


def _loaded() -> tuple[str, tuple[object, ...], tuple[object, ...], bytes, bytes]:
    dataset_raw = _DATASET.read_bytes()
    results_raw = _RESULTS.read_bytes()
    dataset_id, cases = load_dataset(dataset_raw)
    observations = load_observations(results_raw, dataset_id)
    return dataset_id, cases, observations, dataset_raw, results_raw


def test_benchmark_is_deterministic_and_reports_each_required_metric() -> None:
    dataset_id, cases, observations, dataset_raw, results_raw = _loaded()
    report = evaluate(
        dataset_id,
        cases,  # type: ignore[arg-type]
        observations,  # type: ignore[arg-type]
        now=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        dataset_sha256=__import__("hashlib").sha256(dataset_raw).hexdigest(),
        results_sha256=__import__("hashlib").sha256(results_raw).hexdigest(),
    )
    again = evaluate(
        dataset_id,
        cases,  # type: ignore[arg-type]
        observations,  # type: ignore[arg-type]
        now=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        dataset_sha256=__import__("hashlib").sha256(dataset_raw).hexdigest(),
        results_sha256=__import__("hashlib").sha256(results_raw).hexdigest(),
    )
    assert report == again
    summary = report["summary"]
    assert isinstance(summary, dict)
    assert summary["retrieval_recall"] == pytest.approx(5 / 6)
    assert summary["source_diversity_coverage"] == pytest.approx(5 / 6)
    assert summary["extraction_coverage"] == pytest.approx(2 / 3)
    assert summary["citation_grounding_rate"] == pytest.approx(0.5)
    assert summary["freshness_rate"] == pytest.approx(5 / 6)
    assert summary["failure_calibration_accuracy"] == 1.0
    assert "docs.python.org" not in json.dumps(report)
    assert "lexical heuristic" in render_markdown(report)


def test_results_must_match_dataset_case_ids() -> None:
    dataset_id, cases, observations, dataset_raw, results_raw = _loaded()
    changed = json.loads(results_raw)
    changed["cases"].pop()
    bad_observations = load_observations(
        json.dumps(changed).encode(), dataset_id
    )
    with pytest.raises(BenchmarkError, match="case IDs must match"):
        evaluate(
            dataset_id,
            cases,  # type: ignore[arg-type]
            bad_observations,
            now=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
            dataset_sha256="a" * 64,
            results_sha256="b" * 64,
        )


def test_dataset_rejects_duplicate_case_ids() -> None:
    payload = json.loads(_DATASET.read_bytes())
    payload["cases"].append(payload["cases"][0])
    with pytest.raises(BenchmarkError, match="duplicate benchmark case_id"):
        load_dataset(json.dumps(payload).encode())


def test_results_reject_url_userinfo_and_naive_timestamps() -> None:
    dataset_id, _ = load_dataset(_DATASET.read_bytes())
    payload = json.loads(_RESULTS.read_bytes())
    payload["cases"][0]["retrieved"][0]["url"] = "https://user:pass@example.org/"
    with pytest.raises(BenchmarkError, match="without userinfo"):
        load_observations(json.dumps(payload).encode(), dataset_id)
    payload = json.loads(_RESULTS.read_bytes())
    payload["cases"][0]["retrieved"][0]["retrieved_at"] = "2026-10-19T11:00:00"
    with pytest.raises(BenchmarkError, match="timezone-aware"):
        load_observations(json.dumps(payload).encode(), dataset_id)
