"""Fail-closed TLS validation for operational PostgreSQL backup and restore commands."""
from __future__ import annotations

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
    except ValueError as exc:
        raise ValueError("database URL is malformed") from exc
    if parsed.scheme not in {"postgres", "postgresql"} or not host or not parsed.path.strip("/"):
        raise ValueError("a PostgreSQL URL with host and database is required")
    if not username or password is None:
        raise ValueError("database credentials are required")
    if parse_qs(parsed.query, keep_blank_values=True).get("sslmode") != ["verify-full"]:
        raise ValueError("sslmode=verify-full is required")


def main() -> int:
    try:
        validate_database_url(os.environ["TWI_DATABASE_URL"])
    except (KeyError, ValueError) as exc:
        print(f"database TLS validation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
