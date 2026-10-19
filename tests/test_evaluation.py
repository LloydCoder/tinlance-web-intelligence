from __future__ import annotations

import hashlib
import json
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
    assert summary["retrieval_recall"] == pytest.approx(5 / 12)
    assert summary["source_diversity_coverage"] == pytest.approx(5 / 12)
    assert summary["extraction_coverage"] == pytest.approx(1 / 3)
    assert summary["citation_grounding_rate"] == pytest.approx(0.5)
    assert summary["freshness_rate"] == pytest.approx(2 / 3)
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
    assert report["dataset_id"] == "twi-core-v1"
    assert report["summary"]["failure_calibration_accuracy"] == 1.0
    assert "Macro-average metrics" in markdown_out.read_text(encoding="utf-8")
    assert "dataset_sha256" in capsys.readouterr().out
