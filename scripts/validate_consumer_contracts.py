"""Validate pinned consumer contract metadata without inventing external revisions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

_REVISION = re.compile(r"^[0-9a-f]{40}$")


def validate(matrix_path: Path) -> dict[str, object]:
    root = matrix_path.resolve().parent.parent
    matrix = cast(dict[str, Any], json.loads(matrix_path.read_text(encoding="utf-8")))
    if matrix.get("schema_version") != "1.0.0" or not isinstance(matrix.get("consumers"), list):
        raise ValueError("invalid consumer matrix header")
    consumers = cast(list[dict[str, Any]], matrix["consumers"])
    seen: set[str] = set()
    results = []
    for item in consumers:
        name = item.get("name")
        if not isinstance(name, str) or name in seen:
            raise ValueError("consumer names must be unique strings")
        seen.add(name)
        revision, state = item.get("revision"), item.get("status")
        fixture = (root / item["fixture"]).resolve()
        if root not in fixture.parents or not fixture.is_file():
            raise ValueError(f"missing or out-of-tree fixture for {name}")
        if state == "pass":
            if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
                raise ValueError(f"passing consumer {name} requires a full immutable revision")
            snapshot = json.loads(fixture.read_text(encoding="utf-8"))
            if snapshot.get("revision") != revision:
                raise ValueError(f"consumer fixture revision mismatch for {name}")
        elif state == "not_evidenced":
            if revision is not None:
                raise ValueError(f"not-evidenced consumer {name} cannot imply a revision")
        else:
            raise ValueError(f"invalid consumer status for {name}")
        results.append({"name": name, "status": state})
    manifests = list((root / "schemas/mcp-tools").glob("*.json"))
    names = [json.loads(path.read_text(encoding="utf-8"))["name"] for path in manifests]
    if not manifests or len(names) != len(set(names)):
        raise ValueError("local tool manifests must be present and uniquely named")
    return {"valid": True, "consumers": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.matrix)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
