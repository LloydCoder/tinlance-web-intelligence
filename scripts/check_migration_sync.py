"""Fail when the source and packaged PostgreSQL migration copies drift."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    canonical = (root / "db" / "migrations" / "001_production_postgres.sql").read_bytes()
    packaged = files(
        "tinlance_web_intelligence.persistence.migrations"
    ).joinpath("001_production_postgres.sql").read_bytes()
    if canonical != packaged:
        raise SystemExit("PostgreSQL migration copies differ; synchronize them before merge")
    print("PostgreSQL migration copies are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
