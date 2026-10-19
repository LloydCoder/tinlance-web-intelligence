"""Fail-closed structural and evidence validation for the GA v1 release contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from scripts.validate_w15_evidence_pack import validate as validate_evidence_pack

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"pass", "fail", "not_evidenced"}


def validate(
    contract_path: Path,
    schema_path: Path,
    gates_path: Path,
    evidence_pack_path: Path | None = None,
    expected_revision: str | None = None,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    registry = json.loads(gates_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(contract),
        key=lambda error: list(error.path),
    )
    if errors:
        details = "; ".join(error.message for error in errors[:5])
        raise ValueError(f"contract schema invalid: {details}")
    if registry.get("schema_version") != "1.0.0" or not isinstance(
        registry.get("gates"), list
    ):
        raise ValueError("readiness gate registry is malformed")

    rows = registry["gates"]
    if any(
        not isinstance(row, dict) or row.get("status") not in _STATUSES
        for row in rows
    ):
        raise ValueError("readiness registry has an unknown or missing gate status")
    registry_by_name = {row.get("gate"): row for row in rows}
    if None in registry_by_name or len(registry_by_name) != len(rows):
        raise ValueError("readiness registry contains missing or duplicate gate names")

    required = contract["required_gates"]
    if set(required) != set(registry_by_name) or len(required) != len(registry_by_name):
        raise ValueError(
            "GA contract required-gate set differs from the reviewed readiness registry"
        )
    nonpassing = sorted(
        name for name in required if registry_by_name[name]["status"] != "pass"
    )
    revision = contract.get("source_revision")
    if expected_revision is not None and revision != expected_revision:
        raise ValueError(
            "GA contract source revision does not match the requested candidate revision"
        )

    if contract["decision"] == "approved" and nonpassing:
        names = ", ".join(nonpassing)
        raise ValueError(f"cannot approve GA while required gates are non-passing: {names}")

    pack = None
    if evidence_pack_path is not None:
        if not _SHA40.fullmatch(revision or ""):
            raise ValueError("evidence pack validation requires a bound source revision")
        pack_bytes = evidence_pack_path.read_bytes()
        pack = json.loads(pack_bytes)
        digest = hashlib.sha256(pack_bytes).hexdigest()
        if contract.get("evidence_pack_sha256") != digest:
            raise ValueError("evidence pack SHA-256 does not match the release contract")
        if pack.get("source_revision") != revision:
            raise ValueError("evidence pack source revision does not match the release contract")
        pack_rows = pack.get("gates")
        if not isinstance(pack_rows, list):
            raise ValueError("evidence pack gates are malformed")
        pack_by_name = {row.get("gate"): row for row in pack_rows if isinstance(row, dict)}
        if len(pack_by_name) != len(pack_rows) or set(pack_by_name) != set(required):
            raise ValueError("evidence pack gate set does not match the GA contract")
        if pack.get("ready") is not True or any(
            row.get("status") != "pass" or row.get("source_revision") != revision
            for row in pack_rows
        ):
            raise ValueError("evidence pack is not ready or is not source-bound")
        validate_evidence_pack(evidence_pack_path, revision, gates_path)
    elif contract["decision"] == "approved":
        raise ValueError("approved release requires an evidence pack file")

    if contract["decision"] == "approved":
        if not _SHA40.fullmatch(revision or "") or not _SHA64.fullmatch(
            contract.get("evidence_pack_sha256") or ""
        ):
            raise ValueError("approved release requires source revision and evidence-pack digest")
        support = contract["support_contract"]
        if (
            not support["published"]
            or not support["version"]
            or not support["constraints_reference"]
        ):
            raise ValueError(
                "approved release requires a published versioned customer support contract"
            )
        benchmark = contract["benchmark_qualification"]
        if (
            benchmark["status"] != "pass"
            or not benchmark["approval_reference"]
            or not _SHA64.fullmatch(benchmark["threshold_registry_sha256"] or "")
        ):
            raise ValueError("approved release requires approved benchmark thresholds and evidence")
        security = contract["security_review"]
        if (
            security["status"] != "pass"
            or security["source_revision"] != revision
            or not security["evidence_reference"]
        ):
            raise ValueError(
                "approved release requires a passing security review bound to this revision"
            )
        risk = contract["residual_risk"]
        if (
            risk["status"] != "accepted"
            or not risk["owner"]
            or not risk["disposition_reference"]
        ):
            raise ValueError("approved release requires an authorized residual-risk disposition")
        approval = contract["release_approval"]
        if (
            approval["status"] != "approved"
            or not approval["approver"]
            or not approval["approval_reference"]
            or not approval["approved_at"]
        ):
            raise ValueError("approved release requires named, evidenced, timestamped approval")
        if not all(contract["customer_constraints"].values()):
            raise ValueError("approved release requires every customer-constraint publication gate")

    return {
        "valid": True,
        "decision": contract["decision"],
        "required_gate_count": len(required),
        "nonpassing_gates": nonpassing,
        "evidence_pack_checked": pack is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("docs/releases/ga-v1-contract.json"))
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/ga-v1-release-decision.schema.json"),
    )
    parser.add_argument("--gates", type=Path, default=Path("docs/readiness/w15-gates.json"))
    parser.add_argument("--evidence-pack", type=Path)
    parser.add_argument("--revision")
    args = parser.parse_args()
    try:
        result = validate(
            args.contract,
            args.schema,
            args.gates,
            args.evidence_pack,
            args.revision,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
