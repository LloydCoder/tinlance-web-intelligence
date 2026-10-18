#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${TWI_DATABASE_URL:?TWI_DATABASE_URL is required}"
: "${TWI_BACKUP_DIR:?TWI_BACKUP_DIR must point to the approved encrypted backup mount}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 "$script_dir/check_database_tls.py"
command -v pg_dump >/dev/null 2>&1 || { echo "pg_dump is required" >&2; exit 127; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 127; }

mkdir -p -- "$TWI_BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$TWI_BACKUP_DIR/twi-$timestamp.dump"
[[ ! -e "$backup_file" ]] || { echo "backup path already exists" >&2; exit 1; }

pg_dump --format=custom --no-owner --no-privileges --file="$backup_file" "$TWI_DATABASE_URL"
(cd "$TWI_BACKUP_DIR" && sha256sum "$(basename "$backup_file")" > "$(basename "$backup_file").sha256")
chmod 600 "$backup_file" "$backup_file.sha256"
echo "Backup created: $backup_file"
echo "Checksum file: $backup_file.sha256"
