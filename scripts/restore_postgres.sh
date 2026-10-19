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

python3 "$script_dir/validate_restore_target.py" \
  --target-env TWI_RESTORE_DATABASE_URL \
  --primary-env TWI_PRIMARY_DATABASE_URL \
  --expected-database "$TWI_RESTORE_TARGET_DATABASE" \
  --backup-file "$TWI_BACKUP_FILE" \
  --checksum-file "$checksum_file"

service_file="$(mktemp "${TMPDIR:-/tmp}/twi-pg-service.XXXXXX")"
cleanup() { rm -f -- "$service_file"; }
trap cleanup EXIT
export PGSERVICEFILE="$service_file"
TWI_PG_SERVICE_DSN_ENV=TWI_RESTORE_DATABASE_URL \
  TWI_PG_SERVICE_NAME=twi_restore \
  TWI_PG_SERVICE_FILE="$service_file" \
  python3 "$script_dir/create_pg_service.py"
unset TWI_RESTORE_DATABASE_URL TWI_PRIMARY_DATABASE_URL

# The process argument contains only a libpq service name, never the credential-bearing DSN.
pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error \
  --dbname="service=twi_restore" "$TWI_BACKUP_FILE"
echo "Restore command completed. Run the documented recovery validation suite before use."
