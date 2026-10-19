#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ "${TWI_CONFIRM_RESTORE:-}" == "YES" ]] || {
  echo "Destructive restore blocked: set TWI_CONFIRM_RESTORE=YES after review" >&2
  exit 2
}
: "${TWI_RESTORE_DATABASE_URL:?TWI_RESTORE_DATABASE_URL must identify the isolated recovery target}"
: "${TWI_PRIMARY_DATABASE_URL:?TWI_PRIMARY_DATABASE_URL must identify the primary database for target comparison}"
: "${TWI_BACKUP_FILE:?TWI_BACKUP_FILE must identify a verified custom-format dump}"
: "${TWI_RESTORE_TARGET_DATABASE:?Set the expected recovery database name}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/check_database_tls.py" --env TWI_RESTORE_DATABASE_URL
python3 "$script_dir/check_database_tls.py" --env TWI_PRIMARY_DATABASE_URL
[[ -f "$TWI_BACKUP_FILE" && ! -L "$TWI_BACKUP_FILE" ]] || {
  echo "backup file must be a regular non-symlink file" >&2
  exit 1
}
checksum_file="$TWI_BACKUP_FILE.sha256"
[[ -f "$checksum_file" && ! -L "$checksum_file" ]] || {
  echo "backup checksum must be a regular non-symlink file" >&2
  exit 1
}
command -v pg_restore >/dev/null 2>&1 || { echo "pg_restore is required" >&2; exit 127; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 127; }
command -v awk >/dev/null 2>&1 || { echo "awk is required" >&2; exit 127; }

database_name() {
  python3 - "$1" <<'PY'
import os
import sys
from urllib.parse import unquote, urlsplit

parsed = urlsplit(os.environ[sys.argv[1]])
print(unquote(parsed.path.lstrip("/")))
PY
}

database_identity() {
  python3 - "$1" <<'PY'
import json
import os
import sys
from urllib.parse import unquote, urlsplit

parsed = urlsplit(os.environ[sys.argv[1]])
print(json.dumps(
    [parsed.hostname.lower() if parsed.hostname else "", parsed.port or 5432,
     unquote(parsed.path.lstrip("/"))],
    separators=(",", ":"),
))
PY
}

target_database="$(database_name TWI_RESTORE_DATABASE_URL)"
[[ "$target_database" == "$TWI_RESTORE_TARGET_DATABASE" ]] || {
  echo "database name does not match the explicitly confirmed recovery target" >&2
  exit 2
}
case "$target_database" in
  *_restore|*_recovery|*_staging) ;;
  *) echo "restore target must end in _restore, _recovery, or _staging" >&2; exit 2 ;;
esac
target_identity="$(database_identity TWI_RESTORE_DATABASE_URL)"
primary_identity="$(database_identity TWI_PRIMARY_DATABASE_URL)"
[[ "$target_identity" != "$primary_identity" ]] || {
  echo "restore target matches the primary host, port, and database; refusing destructive restore" >&2
  exit 2
}

# Validate both the digest and the sidecar filename against the selected backup path.
mapfile -t manifest_lines < "$checksum_file"
[[ "${#manifest_lines[@]}" -eq 1 ]] || {
  echo "backup checksum manifest must contain exactly one line" >&2
  exit 1
}
if [[ "${manifest_lines[0]}" =~ ^([0-9a-f]{64})\ \ (.+)$ ]]; then
  expected_checksum="${BASH_REMATCH[1]}"
  manifest_filename="${BASH_REMATCH[2]}"
else
  echo "backup checksum manifest is malformed" >&2
  exit 1
fi
[[ "$manifest_filename" == "$(basename -- "$TWI_BACKUP_FILE")" ]] || {
  echo "backup checksum manifest does not identify the selected backup file" >&2
  exit 1
}
actual_checksum="$(sha256sum "$TWI_BACKUP_FILE" | awk '{print $1}')"
[[ "$actual_checksum" == "$expected_checksum" ]] || {
  echo "backup checksum does not match the selected backup file" >&2
  exit 1
}

service_file="$(mktemp "${TMPDIR:-/tmp}/twi-pg-service.XXXXXX")"
cleanup() { rm -f -- "$service_file"; }
trap cleanup EXIT
export PGSERVICEFILE="$service_file"
TWI_PG_SERVICE_DSN_ENV=TWI_RESTORE_DATABASE_URL \
  TWI_PG_SERVICE_NAME=twi_restore \
  TWI_PG_SERVICE_FILE="$service_file" \
  python3 "$script_dir/create_pg_service.py"

# The process argument contains only a libpq service name, never the credential-bearing DSN.
pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error \
  --dbname="service=twi_restore" "$TWI_BACKUP_FILE"
echo "Restore command completed. Run the documented recovery validation suite before use."
