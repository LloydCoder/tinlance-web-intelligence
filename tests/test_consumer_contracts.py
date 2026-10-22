from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from scripts.validate_consumer_contracts import validate


def test_current_consumer_findings_are_exact_and_fail_closed() -> None:
    result = validate(Path("contracts/consumer-matrix.json"))
    assert result["valid"] is True
    consumers = cast(list[dict[str, Any]], result["consumers"])
    assert {row["name"]: row["status"] for row in consumers} == {
        "agent-platform": "pass",
        "world-intelligence": "pass",
        "tsic": "not_evidenced",
    }


def test_current_platform_catalog_registers_monitor_and_evidence_operations() -> None:
    fixture = json.loads(
        Path(
            "contracts/fixtures/platform/c5a080c1fb4df68e45070f8cddfc30bf81edd7bb/tool-catalog.json"
        ).read_text(encoding="utf-8")
    )
    expected = {
        "twi_monitor_create",
        "twi_monitor_delete",
        "twi_monitor_pause",
        "twi_monitor_read",
        "twi_monitor_resume",
        "twi_monitor_run",
    }
    registered = set(fixture["registered_tools"])
    assert fixture["revision"] == "c5a080c1fb4df68e45070f8cddfc30bf81edd7bb"
    assert fixture["status"] == "pass"
    assert expected == set(fixture["expected_monitor_tools"])
    assert not fixture["missing_monitor_tools"]
    assert expected <= registered
    assert fixture["expected_evidence_tools"] == ["twi_evidence_export"]
    assert not fixture["missing_evidence_tools"]
    assert set(fixture["expected_evidence_tools"]) <= registered
    assert set(fixture["approval_gated_tools"]) == {
        "twi_world_intelligence_export",
        "twi_monitor_delete",
    }


def test_historical_platform_snapshot_preserves_the_original_missing_tools_finding() -> None:
    fixture = json.loads(
        Path(
            "contracts/fixtures/platform/db8473b452701d9b3807797ab1bc178b58feb96d/tool-catalog.json"
        ).read_text(encoding="utf-8")
    )
    expected = set(fixture["expected_monitor_tools"])
    assert fixture["status"] == "fail"
    assert set(fixture["missing_monitor_tools"]) == expected
    assert fixture["expected_evidence_tools"] == ["twi_evidence_export"]
    assert fixture["missing_evidence_tools"] == ["twi_evidence_export"]


def test_w15_consumer_gate_uses_the_current_platform_snapshot() -> None:
    registry = json.loads(Path("docs/readiness/w15-gates.json").read_text(encoding="utf-8"))
    gate = next(item for item in registry["gates"] if item["gate"] == "external.consumer_approvals")
    assert gate["status"] == "pass"
    assert gate["evidence_reference"] == (
        "contracts/fixtures/platform/c5a080c1fb4df68e45070f8cddfc30bf81edd7bb/tool-catalog.json"
    )


def test_tsic_requirements_are_pinned_without_claiming_external_conformance() -> None:
    fixture = json.loads(
        Path(
            "contracts/fixtures/tsic/d30d5a6ec9a19c6de7d373cba578cbd9cdc26451/conformance.json"
        ).read_text(encoding="utf-8")
    )
    assert fixture["status"] == "not_evidenced"
    assert fixture["requirement_ids"] == [f"TSIC-TWI-{number:03}" for number in range(1, 9)]


def test_passing_consumer_requires_exact_fixture_revision(tmp_path: Path) -> None:
    root = tmp_path
    (root / "schemas/mcp-tools").mkdir(parents=True)
    (root / "schemas/mcp-tools/tool.json").write_text('{"name":"tool"}', encoding="utf-8")
    fixture = root / "fixtures/tool.json"
    fixture.parent.mkdir()
    fixture.write_text(
        '{"revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","status":"pass"}',
        encoding="utf-8",
    )
    matrix = root / "contracts/consumer-matrix.json"
    matrix.parent.mkdir()
    matrix.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "consumers": [
                    {
                        "name": "x",
                        "revision": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                        "status": "pass",
                        "fixture": "fixtures/tool.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="revision mismatch"):
        validate(matrix)
