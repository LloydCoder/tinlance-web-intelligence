"""Check that a built TWI wheel contains its runtime package and migration resource."""
from __future__ import annotations

import importlib.resources
import sys

import tinlance_web_intelligence


def main() -> int:
    migration = importlib.resources.files(
        "tinlance_web_intelligence.persistence.migrations"
    ).joinpath("001_production_postgres.sql")
    if not migration.is_file():
        print("release verification failed: PostgreSQL migration resource missing", file=sys.stderr)
        return 1
    if not getattr(tinlance_web_intelligence, "__version__", None):
        print("release verification failed: package version missing", file=sys.stderr)
        return 1
    print("release package and migration resource verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
