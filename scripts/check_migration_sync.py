"""Fail when canonical and packaged PostgreSQL migrations drift."""
from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path


def validate_migration_sync(canonical_dir: Path, packaged_dir: Traversable) -> None:
    """Require identical migration filename sets and byte-for-byte copies."""
    canonical = {path.name for path in canonical_dir.glob("*.sql")}
    packaged = {
        path.name for path in packaged_dir.iterdir()
        if path.is_file() and path.name.endswith(".sql")
    }
    if canonical != packaged:
        missing_packaged = sorted(canonical - packaged)
        unexpected_packaged = sorted(packaged - canonical)
        raise SystemExit(
            "PostgreSQL migration filenames differ; "
            f"missing packaged copies={missing_packaged}, "
            f"unexpected packaged files={unexpected_packaged}"
        )
    for name in sorted(canonical):
        if (canonical_dir / name).read_bytes() != packaged_dir.joinpath(name).read_bytes():
            raise SystemExit(f"PostgreSQL migration copies differ: {name}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    canonical_dir = root / "db" / "migrations"
    packaged_dir = files("tinlance_web_intelligence.persistence.migrations")
    validate_migration_sync(canonical_dir, packaged_dir)
    count = len(list(canonical_dir.glob("*.sql")))
    print(f"PostgreSQL migrations are synchronized ({count} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
