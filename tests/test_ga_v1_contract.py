"""Adversarial tests for the GA v1 release decision contract."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_ga_v1_contract import validate

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT = _ROOT / "docs/releases/ga-v1-contract.json"
_SCHEMA = _ROOT / "schemas/ga-v1-release-decision.schema.json"
_GATES = _ROOT / "docs/readiness/w15-gates.json"


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_current_contract_is_valid_but_not_certified() -> None:
    result = validate(_CONTRACT, _SCHEMA, _GATES)
    assert result["valid"] is True
    assert result["decision"] == "not_certified"
    assert result["nonpassing_gates"]


def test_rejects_missing_required_gate(tmp_path: Path) -> None:
    contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    contract["required_gates"].pop()
    contract_path = tmp_path / "contract.json"
    _write_json(contract_path, contract)
    with pytest.raises(ValueError, match="required-gate set"):
        validate(contract_path, _SCHEMA, _GATES)


def test_rejects_unknown_gate_status(tmp_path: Path) -> None:
    registry = json.loads(_GATES.read_text(encoding="utf-8"))
    registry["gates"][0]["status"] = "maybe"
    gates_path = tmp_path / "gates.json"
    _write_json(gates_path, registry)
    with pytest.raises(ValueError, match="unknown or missing gate status"):
        validate(_CONTRACT, _SCHEMA, gates_path)


def test_rejects_ga_approval_while_any_gate_is_not_passing(tmp_path: Path) -> None:
    contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
    contract["decision"] = "approved"
    contract["source_revision"] = "a" * 40
    contract["evidence_pack_sha256"] = "b" * 64
    contract["support_contract"] = {
        "published": True,
        "version": "1.0.0",
        "constraints_reference": "docs/releases/support.md",
    }
    contract["benchmark_qualification"] = {
        "status": "pass",
        "threshold_registry_sha256": "c" * 64,
        "approval_reference": "approval://benchmark",
    }
    contract["security_review"] = {
        "status": "pass",
        "source_revision": "a" * 40,
        "evidence_reference": "security-review.json",
    }
    contract["residual_risk"] = {
        "status": "accepted",
        "owner": "release-owner",
        "disposition_reference": "risk-register.json",
    }
    contract["release_approval"] = {
        "status": "approved",
        "approver": "release-owner",
        "approval_reference": "approval://ga",
        "approved_at": "2026-10-19T20:00:00Z",
    }
    contract["customer_constraints"] = {
        key: True for key in contract["customer_constraints"]
    }
    contract_path = tmp_path / "contract.json"
    _write_json(contract_path, contract)
    with pytest.raises(ValueError, match="non-passing"):
        validate(contract_path, _SCHEMA, _GATES)


def test_rejects_candidate_revision_mismatch() -> None:
    with pytest.raises(ValueError, match="source revision"):
        validate(_CONTRACT, _SCHEMA, _GATES, expected_revision="f" * 40)
