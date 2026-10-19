from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_commercial_usage_migration_is_synchronized_and_versioned() -> None:
    source = ROOT / "db" / "migrations" / "003_commercial_usage.sql"
    packaged = (
        ROOT / "src" / "tinlance_web_intelligence" / "persistence" / "migrations"
        / "003_commercial_usage.sql"
    )
    assert source.read_bytes() == packaged.read_bytes()
    sql = source.read_text(encoding="utf-8")
    assert "twi_usage_reservations" in sql
    assert "twi_usage_events" in sql
    assert "append-only" in sql
    assert "VALUES (3)" in sql
