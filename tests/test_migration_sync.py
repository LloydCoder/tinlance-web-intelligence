from __future__ import annotations

from pathlib import Path

import pytest
from scripts.check_migration_sync import validate_migration_sync

from tinlance_web_intelligence.persistence.migrations import (
    LATEST_SCHEMA_VERSION,
    MIGRATION_FILES,
)


def test_migration_sync_rejects_extra_packaged_files(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    packaged = tmp_path / "packaged"
    canonical.mkdir()
    packaged.mkdir()
    (canonical / "001.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (packaged / "001.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (packaged / "999_untracked.sql").write_text("SELECT 2;\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="unexpected packaged files"):
        validate_migration_sync(canonical, packaged)


def test_migration_sync_rejects_missing_or_different_copies(tmp_path: Path) -> None:
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


def test_migration_registry_tracks_latest_version_and_redaction_migration() -> None:
    assert LATEST_SCHEMA_VERSION == 4
    assert MIGRATION_FILES[-1] == "004_redact_artifact_source_urls.sql"
    assert len(MIGRATION_FILES) == LATEST_SCHEMA_VERSION
