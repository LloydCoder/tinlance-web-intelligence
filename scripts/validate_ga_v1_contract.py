"""Fail-closed structural and evidence validation for the GA v1 release contract."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"pass", "fail", "not_evidenced"}

def validate(contract_path: Path, schema_path: Path, gates_path: Path, evidence_pack_path: Path | None = None, expected_revision: str | None = None) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    registry = json.loads(gates_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(contract), key=lambda error: list(error.path))
    if errors:
        raise ValueError("contract schema invalid: " + "; ".join(error.message for error in errors[:5]))
    if registry.get("schema_version") != "1.0.0" or not isinstance(registry.get("gates"), list):
        raise ValueError("readiness gate registry is malformed")
    rows = registry["gates"]
    if any(not isinstance(row, dict) or row.get("status") not in _STATUSES for row in rows):
        raise ValueError("readiness registry has an unknown or missing gate status")
    registry_by_name = {row.get("gate"): row for row in rows}
    if None in registry_by_name or len(registry_by_name) != len(rows):
        raise ValueError("readiness registry contains missing or duplicate gate names")
    required = contract["required_gates"]
    if set(required) != set(registry_by_name) or len(required) != len(registry_by_name):
        raise ValueError("GA contract required-gate set differs from the reviewed readiness registry")
    nonpassing = sorted(name for name in required if registry_by_name[name]["status"] != "pass")
    revision = contract.get("source_revision")
    if expected_revision is not None and revision != expected_revision:
        raise ValueError("GA contract source revision does not match the requested candidate revision")
    pack = None
    if evidence_pack_path is not None:
        pack_bytes = evidence_pack_path.read_bytes()
        pack = json.loads(pack_bytes)
        if contract.get("evidence_pack_sha256") != hashlib.sha256(pack_bytes).hexdigest():
            raise ValueError("evidence pack SHA-256 does not match the release contract")
        if pack.get("source_revision") != revision:
            raise ValueError("evidence pack source revision does not match the release contract")
        if pack.get("ready") is not True or any(row.get("status") != "pass" for row in pack.get("gates", [])):
            raise ValueError("evidence pack is not ready")
    elif contract["decision"] == "approved":
        raise ValueError("approved release requires an evidence pack file")
    if contract["decision"] == "approved":
        if not _SHA40.fullmatch(revision or "") or not _SHA64.fullmatch(contract.get("evidence_pack_sha256") or ""):
            raise ValueError("approved release requires source revision and evidence-pack digest")
        if nonpassing:
            raise ValueError("cannot approve GA while required gates are non-passing: " + ", ".join(nonpassing))
        if not contract["support_contract"]["published"] or not contract["support_contract"]["version"] or not contract["support_contract"]["constraints_reference"]:
            raise ValueError("approved release requires a published versioned customer support contract")
        if contract["benchmark_qualification"]["status"] != "pass" or not contract["benchmark_qualification"]["approval_reference"] or not _SHA64.fullmatch(contract["benchmark_qualification"]["threshold_registry_sha256"] or ""):
            raise ValueError("approved release requires approved benchmark thresholds and evidence")
        if contract["security_review"]["status"] != "pass" or contract["security_review"]["source_revision"] != revision or not contract["security_review"]["evidence_reference"]:
            raise ValueError("approved release requires a passing security review bound to this revision")
        if contract["residual_risk"]["status"] != "accepted" or not contract["residual_risk"]["owner"] or not contract["residual_risk"]["disposition_reference"]:
            raise ValueError("approved release requires an authorized residual-risk disposition")
        if contract["release_approval"]["status"] != "approved" or not contract["release_approval"]["approver"] or not contract["release_approval"]["approval_reference"] or not contract["release_approval"]["approved_at"]:
            raise ValueError("approved release requires named, evidenced, timestamped approval")
        if not all(contract["customer_constraints"].values()):
            raise ValueError("approved release requires every customer-constraint publication gate")
    return {"valid": True, "decision": contract["decision"], "required_gate_count": len(required), "nonpassing_gates": nonpassing, "evidence_pack_checked": pack is not None}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("docs/releases/ga-v1-contract.json"))
    parser.add_argument("--schema", type=Path, default=Path("schemas/ga-v1-release-decision.schema.json"))
    parser.add_argument("--gates", type=Path, default=Path("docs/readiness/w15-gates.json"))
    parser.add_argument("--evidence-pack", type=Path)
    parser.add_argument("--revision")
    args = parser.parse_args()
    try:
        result = validate(args.contract, args.schema, args.gates, args.evidence_pack, args.revision)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
