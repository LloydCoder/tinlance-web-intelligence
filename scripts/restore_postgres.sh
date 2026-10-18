#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ "${TWI_CONFIRM_RESTORE:-}" == "YES" ]] || {
  echo "Destructive restore blocked: set TWI_CONFIRM_RESTORE=YES after review" >&2
  exit 2
}
: "${TWI_DATABASE_URL:?TWI_DATABASE_URL must identify the isolated recovery target}"
: "${TWI_BACKUP_FILE:?TWI_BACKUP_FILE must identify a verified custom-format dump}"
: "${TWI_RESTORE_TARGET_DATABASE:?Set the expected recovery database name}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/check_database_tls.py"
[[ -f "$TWI_BACKUP_FILE" ]] || { echo "backup file not found" >&2; exit 1; }
[[ -f "$TWI_BACKUP_FILE.sha256" ]] || { echo "backup checksum file not found" >&2; exit 1; }
command -v pg_restore >/dev/null 2>&1 || { echo "pg_restore is required" >&2; exit 127; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 127; }

target_database="$(python3 -c 'from urllib.parse import urlsplit; import os; print(urlsplit(os.environ["TWI_DATABASE_URL"]).path.lstrip("/"))')"
[[ "$target_database" == "$TWI_RESTORE_TARGET_DATABASE" ]] || {
  echo "database name does not match the explicitly confirmed recovery target" >&2
  exit 2
}
case "$target_database" in
  *_restore|*_recovery|*_staging) ;;
  *) echo "restore target must end in _restore, _recovery, or _staging" >&2; exit 2 ;;
esac
(cd "$(dirname "$TWI_BACKUP_FILE")" && sha256sum -c "$(basename "$TWI_BACKUP_FILE").sha256")
pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error \
  --dbname="$TWI_DATABASE_URL" "$TWI_BACKUP_FILE"
echo "Restore command completed. Run the documented recovery validation suite before use."
