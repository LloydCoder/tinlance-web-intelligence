from __future__ import annotations

import configparser
import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from scripts.create_pg_service import parse_service_values, write_service_file
from scripts.validate_restore_target import validate_restore_target, verify_backup_checksum

def test_service_file_decodes_uri_credentials_and_is_owner_only(tmp_path: Path) -> None:
    dsn = (
        "postgresql://backup:p%3Ass%25word@db.example.com:5432/twi_backup"
        "?sslmode=verify-full&sslrootcert=%2Fetc%2Fssl%2Froot.pem"
        "&connect_timeout=5&application_name=twi-backup&target_session_attrs=primary"
    )
    destination = tmp_path / "service.conf"
    write_service_file(dsn, destination, "twi_backup")

    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(destination, encoding="utf-8")
    assert parser["twi_backup"]["host"] == "db.example.com"
    assert parser["twi_backup"]["dbname"] == "twi_backup"
    assert parser["twi_backup"]["password"] == "p:ss%word"  # nosec B105
    assert parser["twi_backup"]["sslmode"] == "verify-full"
    assert parser["twi_backup"]["sslrootcert"] == "/etc/ssl/root.pem"
    assert parser["twi_backup"]["connect_timeout"] == "5"
    assert parser["twi_backup"]["target_session_attrs"] == "primary"

@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://backup:secret@db.example.com/twi_backup",
        "postgresql://backup:secret@db.example.com/twi_backup?sslmode=require",
        (
            "postgresql://backup:secret@db.example.com/twi_backup"
            "?sslmode=verify-full&options=-csearch_path%3Dpublic"
        ),
        (
            "postgresql://backup:secret@db.example.com/twi_backup"
            "?sslmode=verify-full&application_name=a&application_name=b"
        ),
        "postgresql://backup:p%0Aword@db.example.com/twi_backup?sslmode=verify-full",
    ],
)
def test_service_parser_rejects_unsafe_dsn_values(dsn: str) -> None:
    with pytest.raises(ValueError):
        parse_service_values(dsn)

def test_service_file_rejects_invalid_name_and_symlink(tmp_path: Path) -> None:
    dsn = "postgresql://backup:secret@db.example.com/twi_backup?sslmode=verify-full"
    with pytest.raises(ValueError, match="service name is invalid"):
        write_service_file(dsn, tmp_path / "service.conf", "../unsafe")

    target = tmp_path / "target.conf"
    target.write_text("do not overwrite", encoding="utf-8")
    link = tmp_path / "service-link.conf"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="must not be a symlink"):
        write_service_file(dsn, link, "twi_backup")
    assert target.read_text(encoding="utf-8") == "do not overwrite"

def test_restore_target_rejects_primary_identity_and_wrong_target_name() -> None:
    primary = "postgresql://primary:secret@db.example.com:5432/twi_restore?sslmode=verify-full"
    with pytest.raises(ValueError, match="matches the primary"):
        validate_restore_target(
            target_dsn=primary,
            primary_dsn=primary,
            expected_database="twi_restore",
        )

    target = (
        "postgresql://restore:secret@recovery.example.com:5432/twi_recovery"
        "?sslmode=verify-full"
    )
    with pytest.raises(ValueError, match="does not match"):
        validate_restore_target(
            target_dsn=target,
            primary_dsn="postgresql://primary:secret@db.example.com/twi?sslmode=verify-full",
            expected_database="wrong_restore",
        )
    with pytest.raises(ValueError, match="must end in"):
        validate_restore_target(
            target_dsn="postgresql://restore:secret@recovery.example.com/twi?sslmode=verify-full",
            primary_dsn=(
                "postgresql://primary:secret@db.example.com/twi_primary"
                "?sslmode=verify-full"
            ),
            expected_database="twi",
        )

def test_restore_target_accepts_distinct_recovery_database() -> None:
    target = (
        "postgresql://restore:secret@recovery.example.com:5432/twi_recovery"
        "?sslmode=verify-full"
    )
    primary = "postgresql://primary:secret@db.example.com:5432/twi?sslmode=verify-full"
    assert validate_restore_target(
        target_dsn=target,
        primary_dsn=primary,
        expected_database="twi_recovery",
    ) == ("recovery.example.com", 5432, "twi_recovery")

def test_backup_checksum_is_bound_to_selected_file_and_filename(tmp_path: Path) -> None:
    backup = tmp_path / "twi-20261019T120000Z.dump"
    payload = b"representative backup bytes"
    backup.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    sidecar = tmp_path / "twi-20261019T120000Z.dump.sha256"
    sidecar.write_text(f"{digest}  {backup.name}\n", encoding="ascii")

    assert verify_backup_checksum(backup_file=backup, checksum_file=sidecar) == digest

    sidecar.write_text(f"{digest}  another.dump\n", encoding="ascii")
    with pytest.raises(ValueError, match="does not identify"):
        verify_backup_checksum(backup_file=backup, checksum_file=sidecar)

    sidecar.write_text(f"{'0' * 64}  {backup.name}\n", encoding="ascii")
    with pytest.raises(ValueError, match="does not match"):
        verify_backup_checksum(backup_file=backup, checksum_file=sidecar)

    sidecar.write_text(f"{digest}  {backup.name}\nextra\n", encoding="ascii")
    with pytest.raises(ValueError, match="exactly one"):
        verify_backup_checksum(backup_file=backup, checksum_file=sidecar)

def test_restore_checksum_rejects_symlink_sidecar(tmp_path: Path) -> None:
    backup = tmp_path / "backup.dump"
    backup.write_bytes(b"data")
    actual = tmp_path / "actual.sha256"
    actual.write_text(f"{hashlib.sha256(b'data').hexdigest()}  backup.dump\n", encoding="ascii")
    sidecar = tmp_path / "backup.dump.sha256"
    sidecar.symlink_to(actual)
    with pytest.raises(ValueError, match="must not be a symlink"):
        verify_backup_checksum(backup_file=backup, checksum_file=sidecar)

def test_backup_and_restore_scripts_use_service_names_not_dsn_arguments() -> None:
    root = Path(__file__).resolve().parents[1]
    backup = (root / "scripts/backup_postgres.sh").read_text(encoding="utf-8")
    restore = (root / "scripts/restore_postgres.sh").read_text(encoding="utf-8")
    assert "TWI_BACKUP_DATABASE_URL" in backup
    assert '--dbname="service=twi_backup"' in backup
    assert '"$TWI_DATABASE_URL"' not in backup
    assert "unset TWI_BACKUP_DATABASE_URL TWI_DATABASE_URL" in backup
    assert "TWI_RESTORE_DATABASE_URL" in restore
    assert "TWI_PRIMARY_DATABASE_URL" in restore
    assert '--dbname="service=twi_restore"' in restore
    assert 'python3 "$script_dir/validate_restore_target.py"' in restore
    assert '--dbname="$TWI_DATABASE_URL"' not in restore
    assert "unset TWI_RESTORE_DATABASE_URL TWI_PRIMARY_DATABASE_URL TWI_DATABASE_URL" in restore

def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o700)

def _run_shell_script(script_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    bash_path = shutil.which("bash")
    assert bash_path is not None
    return subprocess.run(  # nosec B603: fixed repository script, controlled test environment
        [bash_path, str(script_path)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

def test_backup_script_uses_service_file_and_cleans_failed_partial_dump(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "pg-dump-args.txt"
    service_path_file = tmp_path / "service-path.txt"
    _write_executable(
        fake_bin / "pg_dump",
        """#!/usr/bin/env bash
set -Eeuo pipefail
[[ -z "${TWI_BACKUP_DATABASE_URL:-}" \\
  && -z "${TWI_DATABASE_URL:-}" \\
  && -z "${TWI_OTHER_DATABASE_URL:-}" ]] || exit 90
[[ -z "${PGPASSWORD:-}" && -z "${PGHOSTADDR:-}" && -z "${PGOPTIONS:-}" ]] || exit 95
[[ -f "${PGSERVICEFILE:-}" ]] || exit 91
[[ "$(stat -c '%a' "$PGSERVICEFILE")" == "600" ]] || exit 92
grep -q '^\\[twi_backup\\]$' "$PGSERVICEFILE" || exit 93
printf '%s\\n' "$@" > "$PG_DUMP_ARGS_FILE"
printf '%s' "$PGSERVICEFILE" > "$PGSERVICE_PATH_RECORD"
target=""
for argument in "$@"; do
  case "$argument" in --file=*) target="${argument#--file=}" ;; esac
done
[[ -n "$target" ]] || exit 94
printf 'sample pg dump bytes' > "$target"
if [[ "${PG_DUMP_FAIL:-0}" == 1 ]]; then exit 17; fi
exit 0
""",
    )
    backup_dir = tmp_path / "encrypted-backup"
    env = os.environ.copy()
    env.update(
        {
            "TWI_BACKUP_DATABASE_URL": (
                "postgresql://backup:super-secret@db.example.com:5432/twi"
                "?sslmode=verify-full"
            ),
            "TWI_BACKUP_DIR": str(backup_dir),
            "TWI_OTHER_DATABASE_URL": (
                "postgresql://other:secret@other.example.com/twi"
                "?sslmode=verify-full"
            ),
            "PGPASSWORD": "ambient-password",
            "PGHOSTADDR": "192.0.2.1",
            "PGOPTIONS": "-csearch_path=public",
            "PG_DUMP_ARGS_FILE": str(args_file),
            "PGSERVICE_PATH_RECORD": str(service_path_file),
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
        }
    )

    successful = _run_shell_script(root / "scripts/backup_postgres.sh", env)
    assert successful.returncode == 0, successful.stderr
    args = args_file.read_text(encoding="utf-8")
    assert "service=twi_backup" in args
    assert "super-secret" not in args
    assert len(list(backup_dir.glob("*.dump"))) == 1
    assert len(list(backup_dir.glob("*.dump.sha256"))) == 1
    assert stat.S_IMODE(backup_dir.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in backup_dir.iterdir())
    assert not Path(service_path_file.read_text(encoding="utf-8")).exists()

    for path in backup_dir.iterdir():
        path.unlink()
    env["PG_DUMP_FAIL"] = "1"
    failed = _run_shell_script(root / "scripts/backup_postgres.sh", env)
    assert failed.returncode == 17
    assert list(backup_dir.iterdir()) == []
    assert "super-secret" not in failed.stdout + failed.stderr

def test_restore_script_preflights_target_checksum_and_secret_safe_service(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "pg-restore-args.txt"
    service_path_file = tmp_path / "service-path.txt"
    _write_executable(
        fake_bin / "pg_restore",
        """#!/usr/bin/env bash
set -Eeuo pipefail
[[ -z "${TWI_RESTORE_DATABASE_URL:-}" \\
  && -z "${TWI_DATABASE_URL:-}" \\
  && -z "${TWI_OTHER_DATABASE_URL:-}" ]] || exit 90
[[ -z "${PGPASSWORD:-}" && -z "${PGHOSTADDR:-}" && -z "${PGOPTIONS:-}" ]] || exit 95
[[ -z "${TWI_PRIMARY_DATABASE_URL:-}" ]] || exit 91
[[ -f "${PGSERVICEFILE:-}" ]] || exit 92
[[ "$(stat -c '%a' "$PGSERVICEFILE")" == "600" ]] || exit 93
grep -q '^\\[twi_restore\\]$' "$PGSERVICEFILE" || exit 94
printf '%s\\n' "$@" > "$PG_RESTORE_ARGS_FILE"
printf '%s' "$PGSERVICEFILE" > "$PGSERVICE_PATH_RECORD"
""",
    )
    backup = tmp_path / "known-good.dump"
    backup.write_bytes(b"verified backup fixture")
    digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    (tmp_path / "known-good.dump.sha256").write_text(
        f"{digest}  {backup.name}\\n", encoding="ascii"
    )
    env = os.environ.copy()
    env.update(
        {
            "TWI_CONFIRM_RESTORE": "YES",
            "TWI_RESTORE_DATABASE_URL": (
                "postgresql://restore:restore-secret@recovery.example.com:5432/twi_restore"
                "?sslmode=verify-full"
            ),
            "TWI_PRIMARY_DATABASE_URL": (
                "postgresql://primary:primary-secret@primary.example.com:5432/twi"
                "?sslmode=verify-full"
            ),
            "TWI_BACKUP_FILE": str(backup),
            "TWI_RESTORE_TARGET_DATABASE": "twi_restore",
            "TWI_OTHER_DATABASE_URL": "postgresql://other:secret@other.example.com/twi?sslmode=verify-full",
            "PGPASSWORD": "ambient-password",
            "PGHOSTADDR": "192.0.2.1",
            "PGOPTIONS": "-csearch_path=public",
            "PG_RESTORE_ARGS_FILE": str(args_file),
            "PGSERVICE_PATH_RECORD": str(service_path_file),
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
        }
    )
    restored = _run_shell_script(root / "scripts/restore_postgres.sh", env)
    assert restored.returncode == 0, restored.stderr
    args = args_file.read_text(encoding="utf-8")
    assert "service=twi_restore" in args
    assert "restore-secret" not in args
    assert "primary-secret" not in args
    assert not Path(service_path_file.read_text(encoding="utf-8")).exists()

    args_file.unlink()
    env["TWI_PRIMARY_DATABASE_URL"] = (
        "postgresql://primary:primary-secret@recovery.example.com:5432/twi_restore"
        "?sslmode=verify-full"
    )
    blocked = _run_shell_script(root / "scripts/restore_postgres.sh", env)
    assert blocked.returncode == 2
    assert "matches the primary" in blocked.stderr
    assert not args_file.exists()
