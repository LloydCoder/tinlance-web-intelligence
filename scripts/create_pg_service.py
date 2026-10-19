"""Create a short-lived, owner-only libpq service file without exposing DSNs in argv."""
from __future__ import annotations

import configparser
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

if __package__:
    from scripts.check_database_tls import validate_database_url
else:  # Executed directly by the operational shell scripts.
    from check_database_tls import validate_database_url

_SERVICE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,62}$")
_ENV_NAME = re.compile(r"^TWI_(?:BACKUP|RESTORE|PRIMARY)_DATABASE_URL$")
_ALLOWED_QUERY_KEYS = frozenset(
    {
        "sslmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "connect_timeout",
        "application_name",
        "target_session_attrs",
    }
)
_ALLOWED_TARGET_SESSION_ATTRS = frozenset(
    {"any", "read-write", "read-only", "primary", "standby", "prefer-standby"}
)

def _safe_value(value: str, label: str) -> str:
    if (
        not value
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(f"{label} contains invalid or non-normalized characters")
    return value

def parse_service_values(dsn: str) -> dict[str, str]:
    """Parse an approved TLS PostgreSQL URL into a bounded libpq service mapping."""
    validate_database_url(dsn)
    try:
        parsed = urlsplit(dsn)
        port = parsed.port if parsed.port is not None else 5432
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("PostgreSQL service URL is malformed") from exc
    unknown = set(query) - _ALLOWED_QUERY_KEYS
    if unknown:
        raise ValueError("PostgreSQL service URL contains unsupported query parameters")
    if any(len(values) != 1 for values in query.values()):
        raise ValueError("PostgreSQL service URL query parameters must not be duplicated")
    if query.get("sslmode") != ["verify-full"]:
        raise ValueError("sslmode=verify-full is required")
    if not 1 <= port <= 65535:
        raise ValueError("PostgreSQL service port is invalid")

    values = {
        "host": _safe_value(parsed.hostname or "", "host"),
        "port": str(port),
        "dbname": _safe_value(unquote(parsed.path.lstrip("/")), "database"),
        "user": _safe_value(unquote(parsed.username or ""), "username"),
        "password": _safe_value(unquote(parsed.password or ""), "password"),
        "sslmode": "verify-full",
    }
    for key in ("sslrootcert", "sslcert", "sslkey", "application_name"):
        if key in query:
            values[key] = _safe_value(query[key][0], key)
    if "connect_timeout" in query:
        timeout = query["connect_timeout"][0]
        if not timeout.isdecimal() or not 1 <= int(timeout) <= 60:
            raise ValueError("connect_timeout must be an integer from 1 to 60")
        values["connect_timeout"] = timeout
    if "target_session_attrs" in query:
        target = query["target_session_attrs"][0]
        if target not in _ALLOWED_TARGET_SESSION_ATTRS:
            raise ValueError("target_session_attrs is invalid")
        values["target_session_attrs"] = target
    return values

def write_service_file(dsn: str, destination: str | os.PathLike[str], service_name: str) -> Path:
    """Write a service file with mode 0600, rejecting symlinks and unsafe values."""
    if not isinstance(service_name, str) or not _SERVICE_NAME.fullmatch(service_name):
        raise ValueError("PostgreSQL service name is invalid")
    path = Path(destination)
    if path.is_symlink():
        raise ValueError("PostgreSQL service file must not be a symlink")
    parent = path.parent
    if not parent.is_dir():
        raise ValueError("PostgreSQL service file parent directory must exist")
    if path.exists():
        file_stat = path.stat()
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_uid != os.getuid():
            raise ValueError("PostgreSQL service file must be an owned regular file")
    values = parse_service_values(dsn)
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser[service_name] = values
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            parser.write(stream)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        path.chmod(0o600)
    return path

def main() -> int:
    """Build a service file from named environment variables, never a DSN argument."""
    dsn_env = os.environ.get("TWI_PG_SERVICE_DSN_ENV", "")
    service_name = os.environ.get("TWI_PG_SERVICE_NAME", "")
    destination = os.environ.get("TWI_PG_SERVICE_FILE", "")
    if not _ENV_NAME.fullmatch(dsn_env) or not service_name or not destination:
        print("PostgreSQL service-file configuration is incomplete", file=sys.stderr)
        return 2
    dsn = os.environ.get(dsn_env)
    if not dsn:
        print(f"{dsn_env} is required", file=sys.stderr)
        return 2
    try:
        write_service_file(dsn, destination, service_name)
    except (OSError, ValueError) as exc:
        print(f"PostgreSQL service-file creation failed: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
