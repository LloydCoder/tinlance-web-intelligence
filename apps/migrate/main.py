"""Explicit PostgreSQL migration job; production uses a separate DDL role."""
from __future__ import annotations

import os
from typing import Any
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _validate_dsn(dsn: str, *, production: bool) -> None:
    try:
        parsed = urlsplit(dsn)
        sslmode = parse_qs(parsed.query).get("sslmode", [""])[0]
    except ValueError as exc:
        raise SystemExit("migration database URL is malformed") from exc
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not parsed.hostname
        or not parsed.username
        or not parsed.password
        or not parsed.path.strip("/")
        or parsed.fragment
    ):
        raise SystemExit(
            "migration database URL must include PostgreSQL host, credentials and database"
        )
    if production and sslmode != "verify-full":
        raise SystemExit("production migration database requires sslmode=verify-full")


def main() -> int:
    environment = os.environ.get("TWI_ENV", "development").strip().lower()
    runtime_dsn = os.environ.get("TWI_DATABASE_URL", "").strip()
    migration_dsn = os.environ.get("TWI_MIGRATION_DATABASE_URL", "").strip()
    if environment == "production":
        if not migration_dsn:
            raise SystemExit("production requires TWI_MIGRATION_DATABASE_URL")
        if not runtime_dsn:
            raise SystemExit("production requires TWI_DATABASE_URL for runtime-role comparison")
        _validate_dsn(runtime_dsn, production=True)
        _validate_dsn(migration_dsn, production=True)
        if urlsplit(runtime_dsn).username == urlsplit(migration_dsn).username:
            raise SystemExit("production migration and runtime roles must be distinct")
    else:
        migration_dsn = migration_dsn or runtime_dsn
        if not migration_dsn:
            raise SystemExit("set TWI_MIGRATION_DATABASE_URL or TWI_DATABASE_URL")
        _validate_dsn(migration_dsn, production=False)

    migration = files("tinlance_web_intelligence.persistence.migrations").joinpath(
        "001_production_postgres.sql"
    )
    if not migration.is_file():
        raise SystemExit("packaged PostgreSQL migration resource is missing")
    pool: ConnectionPool[dict[str, Any]] = ConnectionPool(
        conninfo=migration_dsn,
        min_size=1,
        max_size=2,
        kwargs={"row_factory": dict_row, "connect_timeout": 5},
        timeout=10,
        open=True,
    )
    try:
        pool.wait(timeout=10)
        with pool.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(71020261018)")
            conn.execute(migration.read_text(encoding="utf-8"), prepare=False)
            version = conn.execute(
                "SELECT max(version) AS version FROM twi_schema_migrations"
            ).fetchone()
            if version is None or version["version"] != 1:
                raise RuntimeError("PostgreSQL migration version verification failed")
    finally:
        pool.close()
    print("PostgreSQL schema migration and version verification succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
