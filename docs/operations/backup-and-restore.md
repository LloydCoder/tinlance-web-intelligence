# PostgreSQL backup and recovery

## Scope

The production persistence backend stores job state, raw content-addressed artifacts, capture metadata, and the World Intelligence evidence outbox in PostgreSQL. A database backup is sensitive operational data: it can contain tenant-scoped job payloads, results, source URLs, raw response bytes, and evidence metadata.

## Backup requirements

- Use a dedicated database role with only the required read privileges for backup. Artifact retention must use a separate least-privilege `TWI_ARTIFACT_MAINTENANCE_DATABASE_URL` with SELECT/DELETE access limited to artifact tables and no DDL or job/outbox permissions.
- Supply TWI_DATABASE_URL through the deployment secret manager. Production URLs must use TLS with sslmode=verify-full and a trusted CA.
- Run scripts/backup_postgres.sh from an approved operations environment with pg_dump and Python 3 installed. The script rejects URLs unless sslmode=verify-full is set.
- Store encrypted backups outside the database failure domain. Restrict access, apply retention, and monitor backup age and failures.
- Run `python scripts/prune_artifacts.py` for artifact retention. It defaults to a dry run; destructive pruning requires `--apply` and `TWI_CONFIRM_ARTIFACT_PRUNE=YES`. Configure and audit the retention interval before enabling scheduled execution.
- Run `python scripts/prune_job_data.py` for terminal job payload/result retention. It defaults to a dry run and requires a separate least-privilege `TWI_JOB_MAINTENANCE_DATABASE_URL`; destructive redaction requires `--apply` and `TWI_CONFIRM_JOB_DATA_PRUNE=YES`. The maintenance role must be restricted to the required job columns/operations and must not have DDL, artifact, or outbox privileges.
- Preserve the SHA-256 checksum and backup metadata with the backup; do not log the DSN or source data.
- Keep a documented retention schedule and delete expired copies according to policy.

## Restore requirements

Restore is destructive. Use scripts/restore_postgres.sh only against an explicitly selected recovery target and only after setting TWI_CONFIRM_RESTORE=YES. Never test a restore against the primary production database.

Before accepting a recovery:
1. Restore into an isolated recovery database or environment.
2. Verify schema migration version and PostgreSQL connectivity.
3. Verify representative job reads, tenant isolation, idempotency, lease claiming, cancellation, and outbox delivery state.
4. Run the relevant integration and contract test suites.
5. Record RPO/RTO achieved, data loss window, operator, backup checksum, and validation evidence.

## Release gate

A successful backup command does not prove recoverability. Private-beta approval requires a witnessed restore drill from a real encrypted backup in the target deployment class. This repository's CI validates script syntax and PostgreSQL adapter behavior; it does not claim that a production backup or restore has been performed.
