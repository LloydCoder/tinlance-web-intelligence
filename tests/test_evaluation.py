from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tinlance_web_intelligence.evaluation.benchmark import (
    BenchmarkCase,
    BenchmarkError,
    CaseObservation,
    evaluate,
    load_dataset,
    load_observations,
    main,
    render_markdown,
)

_ROOT = Path(__file__).resolve().parents[1]
_DATASET = _ROOT / "benchmarks/twi/v1/cases.json"
_RESULTS = _ROOT / "benchmarks/twi/v1/sample_results.json"


def _loaded() -> tuple[
    str, tuple[BenchmarkCase, ...], tuple[CaseObservation, ...], bytes, bytes
]:
    dataset_raw = _DATASET.read_bytes()
    results_raw = _RESULTS.read_bytes()
    dataset_id, cases = load_dataset(dataset_raw)
    observations = load_observations(results_raw, dataset_id)
    return dataset_id, cases, observations, dataset_raw, results_raw


def test_benchmark_is_deterministic_and_reports_each_required_metric() -> None:
    dataset_id, cases, observations, dataset_raw, results_raw = _loaded()
    report = evaluate(
        dataset_id,
        cases,
        observations,
        now=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        dataset_sha256=hashlib.sha256(dataset_raw).hexdigest(),
        results_sha256=hashlib.sha256(results_raw).hexdigest(),
    )
    again = evaluate(
        dataset_id,
        cases,
        observations,
        now=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        dataset_sha256=hashlib.sha256(dataset_raw).hexdigest(),
        results_sha256=hashlib.sha256(results_raw).hexdigest(),
    )
    assert report == again
    summary = report["summary"]
    assert isinstance(summary, dict)
    assert set(summary) >= {
        "retrieval_recall", "source_diversity_coverage", "extraction_coverage",
        "citation_grounding_rate", "freshness_rate", "failure_calibration_accuracy",
        "outcome_correctness_rate", "evidence_quality_score", "latency_ms_mean",
        "latency_ms_p95", "resource_bytes_mean", "request_count_mean", "retry_count_mean",
    }
    for metric in (
        "retrieval_recall", "source_diversity_coverage", "extraction_coverage",
        "citation_grounding_rate", "freshness_rate", "failure_calibration_accuracy",
        "outcome_correctness_rate", "evidence_quality_score",
    ):
        assert summary[metric] is None or 0.0 <= summary[metric] <= 1.0
    counts = report["counts"]
    qualification = report["qualification"]
    assert isinstance(counts, dict)
    assert isinstance(qualification, dict)
    assert counts["case_count"] == len(cases)
    assert qualification["status"] == "not_evidenced"
    assert report["evidence_mode"] == "synthetic"
    assert "docs.python.org" not in json.dumps(report)
    assert "lexical heuristic" in render_markdown(report)



def test_approved_thresholds_without_registry_digest_cannot_qualify() -> None:
    dataset_id, cases, observations, dataset_raw, results_raw = _loaded()
    live_cases = tuple(replace(case, evidence_mode="live") for case in cases)
    live_observations = tuple(
        replace(observation, evidence_mode="live") for observation in observations
    )
    report = evaluate(
        dataset_id,
        live_cases,
        live_observations,
        now=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        dataset_sha256=hashlib.sha256(dataset_raw).hexdigest(),
        results_sha256=hashlib.sha256(results_raw).hexdigest(),
        source_revision="a" * 40,
        threshold_registry={
            "schema_version": "1.0.0",
            "dataset_id": dataset_id,
            "approval_status": "approved",
            "owner": "quality-owner",
            "approval_reference": "approval-123",
            "thresholds": {"retrieval_recall": {"min": 0.0}},
        },
        thresholds_sha256=None,
    )
    qualification = report["qualification"]
    assert isinstance(qualification, dict)
    assert qualification["status"] == "not_evidenced"
    assert qualification["reason"] == "threshold_registry_hash_missing"


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
            cases,
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



def test_dataset_and_results_reject_unknown_failure_classifications() -> None:
    dataset_payload = json.loads(_DATASET.read_bytes())
    dataset_payload["cases"][0]["expected_failure_mode"] = "made_up_failure"
    with pytest.raises(BenchmarkError, match="expected_failure_mode is invalid"):
        load_dataset(json.dumps(dataset_payload).encode())

    dataset_id, _ = load_dataset(_DATASET.read_bytes())
    results_payload = json.loads(_RESULTS.read_bytes())
    results_payload["cases"][0]["failure_mode"] = "made_up_failure"
    with pytest.raises(BenchmarkError, match="failure_mode is invalid"):
        load_observations(json.dumps(results_payload).encode(), dataset_id)


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



def test_cli_writes_deterministic_json_and_markdown_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    json_out = tmp_path / "report.json"
    markdown_out = tmp_path / "report.md"
    assert main(
        [
            "--dataset",
            str(_DATASET),
            "--results",
            str(_RESULTS),
            "--now",
            "2026-10-19T12:00:00Z",
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    ) == 0
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["dataset_id"] == "twi-hardjobs-v1"
    assert report["summary"]["failure_calibration_accuracy"] == 1.0
    assert report["qualification"]["status"] == "not_evidenced"
    assert "Macro-average metrics" in markdown_out.read_text(encoding="utf-8")
    assert "dataset_sha256" in capsys.readouterr().out
