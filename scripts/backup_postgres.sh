#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${TWI_BACKUP_DATABASE_URL:?TWI_BACKUP_DATABASE_URL is required for the dedicated backup role}"
: "${TWI_BACKUP_DIR:?TWI_BACKUP_DIR must point to the approved encrypted backup mount}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/check_database_tls.py" --env TWI_BACKUP_DATABASE_URL
command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump is required" >&2; exit 127; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 127; }
command -v awk >/dev/null 2>&1 || { echo "awk is required" >&2; exit 127; }

mkdir -p -- "$TWI_BACKUP_DIR"
chmod 700 -- "$TWI_BACKUP_DIR"
service_file=""
tmp_backup=""
tmp_checksum=""
backup_file=""
checksum_file=""
backup_published=0
published=0
cleanup() {
  [[ -z "$service_file" ]] || rm -f -- "$service_file"
  [[ -z "$tmp_backup" ]] || rm -f -- "$tmp_backup"
  [[ -z "$tmp_checksum" ]] || rm -f -- "$tmp_checksum"
  if [[ "$backup_published" == "1" && "$published" == "0" ]]; then
    [[ -z "$backup_file" ]] || rm -f -- "$backup_file"
    [[ -z "$checksum_file" ]] || rm -f -- "$checksum_file"
  fi
}
trap cleanup EXIT

service_file="$(mktemp "${TMPDIR:-/tmp}/twi-pg-service.XXXXXX")"
export PGSERVICEFILE="$service_file"
TWI_PG_SERVICE_DSN_ENV=TWI_BACKUP_DATABASE_URL \
  TWI_PG_SERVICE_NAME=twi_backup \
  TWI_PG_SERVICE_FILE="$service_file" \
  python3 "$script_dir/create_pg_service.py"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$TWI_BACKUP_DIR/twi-$timestamp.dump"
checksum_file="$backup_file.sha256"
[[ ! -e "$backup_file" && ! -e "$checksum_file" ]] || {
  echo "backup output already exists; refusing to overwrite it" >&2
  exit 1
}
tmp_backup="$(mktemp "$TWI_BACKUP_DIR/.twi-$timestamp.XXXXXX")"
tmp_checksum="$(mktemp "$TWI_BACKUP_DIR/.twi-$timestamp.sha256.XXXXXX")"

# The process argument contains only a libpq service name, never the credential-bearing DSN.
pg_dump --format=custom --no-owner --no-privileges \
  --file="$tmp_backup" --dbname="service=twi_backup"
chmod 600 -- "$tmp_backup"
digest="$(sha256sum "$tmp_backup" | awk '{print $1}')"
[[ "$digest" =~ ^[0-9a-f]{64}$ ]] || { echo "backup digest generation failed" >&2; exit 1; }
printf '%s  %s\n' "$digest" "$(basename "$backup_file")" > "$tmp_checksum"
chmod 600 -- "$tmp_checksum"

mv -n -- "$tmp_backup" "$backup_file"
[[ ! -e "$tmp_backup" ]] || {
  echo "backup output appeared concurrently; refusing to overwrite it" >&2
  exit 1
}
tmp_backup=""
backup_published=1
mv -n -- "$tmp_checksum" "$checksum_file"
[[ ! -e "$tmp_checksum" ]] || {
  echo "checksum output appeared concurrently; refusing to overwrite it" >&2
  exit 1
}
tmp_checksum=""
chmod 600 -- "$backup_file" "$checksum_file"
published=1
echo "Backup created: $backup_file"
echo "Checksum file: $checksum_file"
