"""Fail when the source and packaged PostgreSQL migration copies drift."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    canonical_dir = root / "db" / "migrations"
    packaged_dir = files("tinlance_web_intelligence.persistence.migrations")
    canonical = {path.name for path in canonical_dir.glob("*.sql")}
    packaged = {
        path.name
        for path in canonical_dir.glob("*.sql")
        if packaged_dir.joinpath(path.name).is_file()
    }
    if canonical != packaged:
        raise SystemExit("PostgreSQL migration filenames differ; synchronize them before merge")
    for name in sorted(canonical):
        if (canonical_dir / name).read_bytes() != packaged_dir.joinpath(name).read_bytes():
            raise SystemExit(f"PostgreSQL migration copies differ: {name}")
    print(f"PostgreSQL migrations are synchronized ({len(canonical)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
