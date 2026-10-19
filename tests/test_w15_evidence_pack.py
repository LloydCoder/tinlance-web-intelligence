from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from scripts.build_w15_evidence_pack import build
from scripts.validate_w15_evidence_pack import validate


def test_evidence_pack_is_deterministic_and_fails_closed(tmp_path: Path) -> None:
    revision = subprocess.check_output(  # noqa: S603, S607
        ["git", "rev-parse", "HEAD"], text=True  # noqa: S607
    ).strip()
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    one = build(Path("docs/readiness/w15-gates.json"), first, revision)
    two = build(Path("docs/readiness/w15-gates.json"), second, revision)
    assert first.read_bytes() == second.read_bytes()
    assert one == two
    report = validate(first, revision)
    assert report["valid"] is True
    assert report["ready"] is False
    assert cast(int, report["not_evidenced"]) >= 1


def test_evidence_validator_rejects_revision_and_content_drift(tmp_path: Path) -> None:
    revision = subprocess.check_output(  # noqa: S603, S607
        ["git", "rev-parse", "HEAD"], text=True  # noqa: S607
    ).strip()
    pack_path = tmp_path / "pack.json"
    pack = build(Path("docs/readiness/w15-gates.json"), pack_path, revision)
    with pytest.raises(ValueError, match="revision mismatch"):
        validate(pack_path, "0" * 40)
    gates = cast(list[dict[str, Any]], pack["gates"])
    row = next(row for row in gates if row["evidence_reference"])
    row["sha256"] = "0" * 64
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        validate(pack_path, revision)


def test_evidence_validator_rejects_unreviewed_pass_status(tmp_path: Path) -> None:
    revision = subprocess.check_output(  # noqa: S603, S607
        ["git", "rev-parse", "HEAD"], text=True  # noqa: S607
    ).strip()
    pack_path = tmp_path / "pack.json"
    pack = build(Path("docs/readiness/w15-gates.json"), pack_path, revision)
    gates = cast(list[dict[str, Any]], pack["gates"])
    gates[0]["status"] = "pass" if gates[0]["status"] != "pass" else "not_evidenced"
    pack["ready"] = False
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ValueError, match="reviewed gate registry"):
        validate(pack_path, revision)


def test_evidence_validator_rejects_missing_gates_expired_and_sensitive_data(
    tmp_path: Path,
) -> None:
    revision = subprocess.check_output(  # noqa: S603, S607
        ["git", "rev-parse", "HEAD"], text=True  # noqa: S607
    ).strip()
    pack_path = tmp_path / "pack.json"
    pack = build(Path("docs/readiness/w15-gates.json"), pack_path, revision)
    gates = cast(list[dict[str, Any]], pack["gates"])
    pack["gates"] = gates[:-1]
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ValueError, match="missing or duplicated"):
        validate(pack_path, revision)

    pack = build(Path("docs/readiness/w15-gates.json"), pack_path, revision)
    gates = cast(list[dict[str, Any]], pack["gates"])
    gates[0]["expires_at"] = "2000-01-01T00:00:00Z"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ValueError, match="expired"):
        validate(pack_path, revision)

    pack = build(Path("docs/readiness/w15-gates.json"), pack_path, revision)
    pack["api_key"] = "secret-value"
    pack_path.write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata"):
        validate(pack_path, revision)
