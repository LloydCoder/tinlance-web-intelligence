"""Fail-closed validation for source-bound W15 evidence indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

_SHA = re.compile(r"^[0-9a-f]{64}$")
_SECRET = re.compile(r"(?i)(bearer\s+\S+|password\s*[:=]|api[_-]?key\s*[:=]|token\s*[:=])")
_QUERY = re.compile(r"https?://[^\s?]+\?[^\s]+", re.I)


def validate(
    pack_path: Path, revision: str, gates_path: Path = Path("docs/readiness/w15-gates.json")
) -> dict[str, object]:
    pack = cast(dict[str, Any], json.loads(pack_path.read_text(encoding="utf-8")))
    registry = cast(dict[str, Any], json.loads(gates_path.read_text(encoding="utf-8")))
    if set(pack) != {"schema_version", "source_revision", "ready", "gates"}:
        raise ValueError("unexpected evidence pack metadata")
    if _SECRET.search(json.dumps(pack, sort_keys=True)) or _QUERY.search(
        json.dumps(pack, sort_keys=True)
    ):
        raise ValueError("sensitive evidence metadata rejected")
    registry_rows = cast(list[dict[str, Any]], registry["gates"])
    expected_rows = {item["gate"]: item for item in registry_rows}
    expected = set(expected_rows)
    rows = cast(list[dict[str, Any]], pack.get("gates"))
    if pack.get("schema_version") != "1.0.0" or pack.get("source_revision") != revision:
        raise ValueError("evidence pack source revision mismatch")
    if not isinstance(rows, list) or {row.get("gate") for row in rows} != expected:
        raise ValueError("required evidence gates are missing or duplicated")
    if len(rows) != len(expected):
        raise ValueError("duplicate evidence gate")
    root = Path.cwd().resolve()
    now = datetime.now(UTC)
    for row in rows:
        if set(row) - {
            "gate", "status", "owner", "observed_at", "source_revision",
            "evidence_reference", "sha256", "expires_at",
        }:
            raise ValueError("unexpected evidence gate metadata")
        declared = expected_rows[row["gate"]]
        if (
            row.get("status") != declared["status"]
            or row.get("owner") != declared["owner"]
            or row.get("evidence_reference") != declared["evidence_reference"]
        ):
            raise ValueError("evidence gate does not match the reviewed gate registry")
        if (
            row.get("status") not in {"pass", "fail", "not_evidenced"}
            or row.get("source_revision") != revision
        ):
            raise ValueError("invalid gate status or source revision")
        if not _SHA.fullmatch(row.get("sha256", "")):
            raise ValueError("invalid evidence digest")
        serialized = json.dumps(row, sort_keys=True)
        if _SECRET.search(serialized) or _QUERY.search(serialized):
            raise ValueError("sensitive evidence metadata rejected")
        observed = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("observation time must be UTC aware")
        expiry = row.get("expires_at")
        if expiry and datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= now:
            raise ValueError("evidence has expired")
        ref = row["evidence_reference"]
        if ref:
            path = (root / ref).resolve()
            if root not in path.parents or not path.is_file():
                raise ValueError("evidence reference is unavailable")
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError("evidence content digest mismatch")
    ready = all(row["status"] == "pass" for row in rows)
    if pack.get("ready") is not ready:
        raise ValueError("readiness decision does not match gate results")
    return {
        "valid": True,
        "ready": ready,
        "pass": sum(r["status"] == "pass" for r in rows),
        "not_evidenced": sum(r["status"] == "not_evidenced" for r in rows),
        "fail": sum(r["status"] == "fail" for r in rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--gates", type=Path, default=Path("docs/readiness/w15-gates.json"))
    args = parser.parse_args()
    try:
        result = validate(args.pack, args.revision, args.gates)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
