"""Build a deterministic W15 evidence index without copying referenced evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


def build(gates_path: Path, output_path: Path, revision: str | None = None) -> dict[str, object]:
    root = Path.cwd().resolve()
    sha = revision or subprocess.check_output(  # noqa: S603, S607
        ["git", "rev-parse", "HEAD"], text=True  # noqa: S607
    ).strip()
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("source revision must be a full lowercase git SHA")
    source = cast(dict[str, Any], json.loads(gates_path.read_text(encoding="utf-8")))
    if source.get("schema_version") != "1.0.0" or not isinstance(source.get("gates"), list):
        raise ValueError("invalid gate registry")
    commit_epoch = int(
        subprocess.check_output(  # noqa: S603, S607
            ["git", "show", "-s", "--format=%ct", sha], text=True  # noqa: S607
        ).strip()
    )
    observed = (
        datetime.fromtimestamp(commit_epoch, UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    entries = cast(list[dict[str, Any]], source["gates"])
    rows: list[dict[str, Any]] = []
    for item in sorted(entries, key=lambda row: row["gate"]):
        ref = item["evidence_reference"]
        digest = hashlib.sha256(b"").hexdigest()
        if ref:
            path = (root / ref).resolve()
            if root not in path.parents or not path.is_file():
                raise ValueError(f"evidence reference is missing or outside repository: {ref}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(
            {
                "gate": item["gate"],
                "status": item["status"],
                "owner": item["owner"],
                "observed_at": observed,
                "source_revision": sha,
                "evidence_reference": ref,
                "sha256": digest,
            }
        )
    ready = bool(rows) and all(row["status"] == "pass" for row in rows)
    pack = {"schema_version": "1.0.0", "source_revision": sha, "ready": ready, "gates": rows}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(pack, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    return pack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision")
    args = parser.parse_args()
    build(args.gates, args.output, args.revision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
