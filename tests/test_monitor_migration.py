from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_monitor_migration_is_synchronized_and_versioned() -> None:
    source = ROOT / "db" / "migrations" / "002_monitors.sql"
    packaged = (
        ROOT
        / "src"
        / "tinlance_web_intelligence"
        / "persistence"
        / "migrations"
        / "002_monitors.sql"
    )

    assert source.read_bytes() == packaged.read_bytes()
    sql = source.read_text(encoding="utf-8")
    assert "ALTER TABLE jobs" in sql
    assert "monitor_run_results" in sql
    assert "traceparent" in sql
    assert "VALUES (2)" in sql
