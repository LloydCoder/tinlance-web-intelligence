"""Fail-closed tests for the explicit PostgreSQL migration runner."""
from __future__ import annotations

from apps.migrate.main import _validate_dsn, main

import pytest


def test_production_migration_dsn_requires_verified_tls() -> None:
    _validate_dsn(
        "postgresql://migrator:secret@db.example/twi?sslmode=verify-full",
        production=True,
    )
    with pytest.raises(SystemExit, match="sslmode=verify-full"):
        _validate_dsn(
            "postgresql://migrator:secret@db.example/twi?sslmode=require",
            production=True,
        )


def test_production_migration_requires_a_separate_ddl_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWI_ENV", "production")
    monkeypatch.setenv(
        "TWI_DATABASE_URL",
        "postgresql://twi_runtime:runtime-secret@db.example/twi?sslmode=verify-full",
    )
    monkeypatch.setenv(
        "TWI_MIGRATION_DATABASE_URL",
        "postgresql://twi_runtime:migration-secret@db.example/twi?sslmode=verify-full",
    )
    with pytest.raises(SystemExit, match="roles must be distinct"):
        main()


def test_production_migration_requires_dedicated_migration_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TWI_ENV", "production")
    monkeypatch.setenv(
        "TWI_DATABASE_URL",
        "postgresql://twi_runtime:runtime-secret@db.example/twi?sslmode=verify-full",
    )
    monkeypatch.delenv("TWI_MIGRATION_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit, match="TWI_MIGRATION_DATABASE_URL"):
        main()
