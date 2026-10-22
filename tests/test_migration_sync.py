from __future__ import annotations

import pytest

from scripts.check_migration_sync import validate_migration_sync


def test_migration_sync_rejects_extra_packaged_files(tmp_path) -> None:
    canonical = tmp_path / "canonical"
    packaged = tmp_path / "packaged"
    canonical.mkdir()
    packaged.mkdir()
    (canonical / "001.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (packaged / "001.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (packaged / "999_untracked.sql").write_text("SELECT 2;\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="unexpected packaged files"):
        validate_migration_sync(canonical, packaged)


def test_migration_sync_rejects_missing_or_different_copies(tmp_path) -> None:
    canonical = tmp_path / "canonical"
    packaged = tmp_path / "packaged"
    canonical.mkdir()
    packaged.mkdir()
    (canonical / "001.sql").write_text("SELECT 1;\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="missing packaged copies"):
        validate_migration_sync(canonical, packaged)

    (packaged / "001.sql").write_text("SELECT 2;\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="copies differ"):
        validate_migration_sync(canonical, packaged)
