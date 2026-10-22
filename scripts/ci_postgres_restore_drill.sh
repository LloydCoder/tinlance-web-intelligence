#!/usr/bin/env bash
set -Eeuo pipefail

: "${TWI_TEST_POSTGRES_DSN:?CI PostgreSQL DSN is required}"
: "${TWI_TEST_POSTGRES_PASSWORD:?CI PostgreSQL password is required}"

# This drill is restricted to the ephemeral localhost PostgreSQL service in CI.
readarray -t db_config < <(python - <<'PY'
import os
from urllib.parse import unquote, urlsplit

parsed = urlsplit(os.environ["TWI_TEST_POSTGRES_DSN"])
if parsed.scheme not in {"postgres", "postgresql"}:
    raise SystemExit("restore drill requires a PostgreSQL test DSN")
if parsed.hostname not in {"localhost", "127.0.0.1"}:
    raise SystemExit("restore drill refuses non-local database hosts")
if not parsed.username or not parsed.path.strip("/"):
    raise SystemExit("restore drill DSN must include a user and database")
print("127.0.0.1")
print(parsed.port or 5432)
print(unquote(parsed.username))
print(unquote(parsed.path.lstrip("/")))
PY
)
db_host="${db_config[0]}"
db_port="${db_config[1]}"
db_user="${db_config[2]}"
source_db="${db_config[3]}"
target_db="twi_restore_drill"
export PGPASSWORD="$TWI_TEST_POSTGRES_PASSWORD"
tmp_dir="$(mktemp -d)"

client() {
  docker run --rm --network host -e PGPASSWORD -v "$tmp_dir:/backup" postgres:17-alpine "$@"
}

cleanup() {
  client dropdb --if-exists --host "$db_host" --port "$db_port" --username "$db_user" "$target_db" >/dev/null 2>&1 || true
  client psql --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$source_db" \
    --quiet --command "DROP TABLE IF EXISTS twi_restore_drill_probe" >/dev/null 2>&1 || true
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

client psql --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$source_db" \
  --set ON_ERROR_STOP=1 --command "
    DROP TABLE IF EXISTS twi_restore_drill_probe;
    CREATE TABLE twi_restore_drill_probe (
      probe_id text PRIMARY KEY,
      payload text NOT NULL
    );
    INSERT INTO twi_restore_drill_probe (probe_id, payload)
    VALUES ('ci-round-trip', 'restore-ok');
  "

client dropdb --if-exists --host "$db_host" --port "$db_port" --username "$db_user" "$target_db"
client createdb --host "$db_host" --port "$db_port" --username "$db_user" "$target_db"

client pg_dump --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$source_db" \
  --format=custom --no-owner --no-privileges --file=/backup/twi-postgres.dump
test -s "$tmp_dir/twi-postgres.dump"
sha256sum "$tmp_dir/twi-postgres.dump"

client pg_restore --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$target_db" \
  --no-owner --no-privileges --exit-on-error /backup/twi-postgres.dump

probe="$(client psql --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$target_db" \
  --tuples-only --no-align --quiet --command \
  "SELECT payload FROM twi_restore_drill_probe WHERE probe_id='ci-round-trip'")"
test "$probe" = "restore-ok"

schema_version="$(client psql --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$target_db" \
  --tuples-only --no-align --quiet --command \
  "SELECT max(version) FROM twi_schema_migrations")"
test "$schema_version" = "4"

for table in jobs twi_artifact_records twi_usage_events twi_billing_event_receipts twi_source_evidence_outbox; do
  source_count="$(client psql --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$source_db" \
    --tuples-only --no-align --quiet --command "SELECT count(*) FROM $table")"
  restored_count="$(client psql --host "$db_host" --port "$db_port" --username "$db_user" --dbname "$target_db" \
    --tuples-only --no-align --quiet --command "SELECT count(*) FROM $table")"
  if [[ "$source_count" != "$restored_count" ]]; then
    printf 'restore verification failed for %s: source=%s restored=%s\n' \
      "$table" "$source_count" "$restored_count" >&2
    exit 1
  fi
done

printf 'PostgreSQL dump/restore round-trip passed: schema version %s; probe and persistence-table counts verified.\n' "$schema_version"
