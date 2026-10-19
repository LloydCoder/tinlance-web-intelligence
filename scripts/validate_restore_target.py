"""Fail-closed validation of restore target identity and backup checksum manifest."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.create_pg_service import parse_service_values
elif __package__:
    from scripts.create_pg_service import parse_service_values
else:  # Executed directly by the operational shell scripts.
    from create_pg_service import parse_service_values

_ALLOWED_ENV_NAMES = {"TWI_RESTORE_DATABASE_URL", "TWI_PRIMARY_DATABASE_URL"}
_MANIFEST = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]{0,255})$")


def database_identity(dsn: str) -> tuple[str, int, str]:
    """Return normalized host/port/database identity after strict TLS URL validation."""
    values = parse_service_values(dsn)
    return values["host"].lower(), int(values["port"]), values["dbname"]


def validate_restore_target(
    *, target_dsn: str, primary_dsn: str, expected_database: str
) -> tuple[str, int, str]:
    """Reject a target that does not match the explicit isolated recovery target."""
    target = database_identity(target_dsn)
    primary = database_identity(primary_dsn)
    if not expected_database or expected_database != expected_database.strip():
        raise ValueError("explicit restore target database name is invalid")
    if target[2] != expected_database:
        raise ValueError("database name does not match the explicitly confirmed recovery target")
    if not target[2].endswith(("_restore", "_recovery", "_staging")):
        raise ValueError("restore target must end in _restore, _recovery, or _staging")
    if target == primary:
        raise ValueError("restore target matches the primary host, port, and database")
    return target


def verify_backup_checksum(
    *, backup_file: str | os.PathLike[str], checksum_file: str | os.PathLike[str]
) -> str:
    """Verify digest and filename binding without trusting a manifest-supplied path."""
    backup = Path(backup_file)
    sidecar = Path(checksum_file)
    for path, label in ((backup, "backup"), (sidecar, "checksum")):
        if path.is_symlink():
            raise ValueError(f"{label} file must not be a symlink")
        try:
            mode = path.stat().st_mode
        except OSError as exc:
            raise ValueError(f"{label} file is unavailable") from exc
        if not stat.S_ISREG(mode):
            raise ValueError(f"{label} file must be a regular file")
    try:
        manifest = sidecar.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("backup checksum manifest is unreadable") from exc
    if not manifest.endswith("\n") or manifest.count("\n") != 1:
        raise ValueError(
            "backup checksum manifest must contain exactly one newline-terminated line"
        )
    line = manifest[:-1]
    match = _MANIFEST.fullmatch(line)
    if match is None:
        raise ValueError("backup checksum manifest is malformed")
    expected_digest, manifest_filename = match.groups()
    if manifest_filename != backup.name:
        raise ValueError("backup checksum manifest does not identify the selected backup file")
    digest = hashlib.sha256()
    try:
        with backup.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError("backup file could not be read for checksum verification") from exc
    actual_digest = digest.hexdigest()
    if actual_digest != expected_digest:
        raise ValueError("backup checksum does not match the selected backup file")
    return actual_digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-env", choices=sorted(_ALLOWED_ENV_NAMES), required=True)
    parser.add_argument("--primary-env", choices=sorted(_ALLOWED_ENV_NAMES), required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--backup-file", required=True)
    parser.add_argument("--checksum-file", required=True)
    args = parser.parse_args(argv)
    target_dsn = os.environ.get(args.target_env, "")
    primary_dsn = os.environ.get(args.primary_env, "")
    try:
        if not target_dsn or not primary_dsn:
            raise ValueError("restore and primary database URL environment variables are required")
        validate_restore_target(
            target_dsn=target_dsn,
            primary_dsn=primary_dsn,
            expected_database=args.expected_database,
        )
        verify_backup_checksum(backup_file=args.backup_file, checksum_file=args.checksum_file)
    except (OSError, ValueError) as exc:
        print(f"restore preflight failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
