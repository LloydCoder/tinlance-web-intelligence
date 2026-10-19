from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from scripts.validate_consumer_contracts import validate


def test_current_consumer_unknowns_are_explicitly_not_evidenced() -> None:
    result = validate(Path("contracts/consumer-matrix.json"))
    assert result["valid"] is True
    consumers = cast(list[dict[str, Any]], result["consumers"])
    assert all(row["status"] == "not_evidenced" for row in consumers)


def test_passing_consumer_requires_exact_fixture_revision(tmp_path: Path) -> None:
    root = tmp_path
    (root / "schemas/mcp-tools").mkdir(parents=True)
    (root / "schemas/mcp-tools/tool.json").write_text('{"name":"tool"}', encoding="utf-8")
    fixture = root / "fixtures/tool.json"
    fixture.parent.mkdir()
    fixture.write_text('{"revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}', encoding="utf-8")
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
