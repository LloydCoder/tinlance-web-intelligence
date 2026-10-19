"""Fail-closed TLS validation for operational PostgreSQL backup and restore commands."""
from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import parse_qs, urlsplit

def validate_database_url(dsn: str) -> None:
    """Require a credentialed PostgreSQL URL with hostname-verifying TLS."""
    try:
        parsed = urlsplit(dsn)
        host = parsed.hostname
        username = parsed.username
        password = parsed.password
        port = parsed.port
    except ValueError as exc:
        raise ValueError("database URL is malformed") from exc
    if (
        parsed.scheme not in {"postgres", "postgresql"}
        or not host
        or not parsed.path.strip("/")
        or parsed.fragment
    ):
        raise ValueError("a PostgreSQL URL with host and database and no fragment is required")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("database port must be between 1 and 65535")
    if not username or password is None:
        raise ValueError("database credentials are required")
    if parse_qs(parsed.query, keep_blank_values=True).get("sslmode") != ["verify-full"]:
        raise ValueError("sslmode=verify-full is required")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env",
        choices=(
            "TWI_DATABASE_URL", "TWI_BACKUP_DATABASE_URL",
            "TWI_RESTORE_DATABASE_URL", "TWI_PRIMARY_DATABASE_URL",
        ),
        default="TWI_DATABASE_URL",
        help="name of the environment variable containing the DSN (never pass the DSN itself)",
    )
    args = parser.parse_args(argv)
    try:
        validate_database_url(os.environ[args.env])
    except (KeyError, ValueError) as exc:
        print(f"database TLS validation failed for {args.env}: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
