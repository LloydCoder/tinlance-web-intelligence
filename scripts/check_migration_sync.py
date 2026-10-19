"""Fail when the source and packaged PostgreSQL migration copies drift."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    canonical_dir = root / "db" / "migrations"
    packaged_dir = files("tinlance_web_intelligence.persistence.migrations")
    canonical_names = sorted(path.name for path in canonical_dir.glob("*.sql"))
    packaged_names = sorted(path.name for path in packaged_dir.iterdir() if path.name.endswith(".sql"))
    if canonical_names != packaged_names:
        raise SystemExit("PostgreSQL migration filenames differ between source and package")
    for name in canonical_names:
        canonical = (canonical_dir / name).read_bytes()
        packaged = packaged_dir.joinpath(name).read_bytes()
        if canonical != packaged:
            raise SystemExit(f"PostgreSQL migration copies differ for {name}")
    print("PostgreSQL migration copies are synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
