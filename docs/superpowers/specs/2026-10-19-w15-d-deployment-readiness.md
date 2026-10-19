# W15-D — Deployment and Self-Hosting Readiness

**Status:** implementation in progress. Self-hosting is excluded from GA v1 by the conservative documented default unless an authorized product owner explicitly approves it. This phase hardens the deployment and recovery foundation; it does not certify a real cloud deployment or restore drill.

## Objective

Close repository-level deployment safety gaps using existing Docker/Compose, configuration, PostgreSQL migration, health-check, and recovery components. Do not duplicate Agent Platform identity/policy, Agent OS scheduling, or World Intelligence truth authority.

## Forensic baseline

The repository already has isolated API/worker/browser/egress-proxy images, development/staging Compose definitions, fail-closed staging/production database TLS configuration, a versioned migration runner, readiness/liveness routes, a reproducible release workflow, and backup/restore scripts.

The current backup scripts violate their own operational contract: both pass a database URL directly to `pg_dump`/`pg_restore` as a command-line argument; they use `TWI_DATABASE_URL` rather than dedicated backup/restore credentials; restore does not compare its target to the explicitly declared primary database; and checksum verification trusts the filename embedded in the checksum manifest. These are blockers for this phase.

## Required implementation

1. **Secret-safe libpq connection setup**
   - Add a helper that validates a PostgreSQL URL with `sslmode=verify-full` and writes a short-lived, owner-only libpq service file.
   - Pass only a service name to `pg_dump`/`pg_restore`; never put credentials in process arguments or logs. Before launching the database client, remove inherited `*_DATABASE_URL` variables and ambient libpq connection overrides, then retain only the temporary `PGSERVICEFILE` pointer.
   - Reject unsupported/duplicate query parameters, malformed URLs, control characters, unsafe service names, symlink targets, and insecure file permissions.
   - Use distinct `TWI_BACKUP_DATABASE_URL` and `TWI_RESTORE_DATABASE_URL` values. Keep `TWI_DATABASE_URL` for the application runtime only.

2. **Backup integrity and failure recovery**
   - Write to a unique temporary file in the approved backup directory.
   - Create a SHA-256 manifest tied to the final backup filename, then atomically publish the dump and manifest.
   - Remove partial temporary outputs on every failure; enforce restrictive file/directory permissions.
   - Preserve the rule that backup storage must be encrypted and outside the database failure domain; encryption and mount provenance remain deployment evidence, not something repository CI can infer.

3. **Restore isolation and integrity**
   - Require explicit `TWI_CONFIRM_RESTORE=YES`, a dedicated restore DSN, an explicitly named target database, and a primary DSN for comparison.
   - Require the target database suffix `_restore`, `_recovery`, or `_staging`; reject a target matching the primary host/port/database identity.
   - Verify the backup bytes against the SHA-256 digest in the sidecar, without trusting the sidecar's filename field.
   - Keep restore destructive, fail closed, and require post-restore migration/version and integration validation.

4. **Configuration and operational contract**
   - Update scripts, unit tests, docs, and examples to agree on environment-variable names and credential handling.
   - Preserve separate migration/runtime/backup/restore/retention roles and verified TLS.
   - Validate Compose topology, health checks, migration synchronization, clean build artifacts, and shell syntax in CI.
   - Keep live deployment, cloud IAM/network policies, secret rotation, HA/failover, encrypted backup proof, witnessed restore RPO/RTO, alert delivery, and self-hosting GA approval explicitly unevidenced until externally verified.

## Acceptance criteria

- Unit tests cover valid service-file creation, mode 0600, URL decoding, TLS requirements, unsupported parameters, duplicate parameters, control-character rejection, invalid service names, and secret-safe invocation contract.
- Backup/restore scripts pass shell syntax and have tested cleanup/checksum/target-isolation logic.
- No DSN or password is passed as a command-line argument, written to logs, or emitted by the helper.
- Restore rejects the primary database identity even when the explicit confirmation flag is set.
- Checksum validation is bound to the selected backup file and rejects malformed or mismatched digests.
- Existing PostgreSQL migration, adapter, isolation, and reproducible-artifact checks remain green on Python 3.12 and 3.13.
- Exact-head CI passes, a phase-specific forensic audit is recorded, the PR is merged only after all required checks pass, and post-merge main CI passes before W15-E.

## Non-goals

- Do not enable self-hosting as a GA-v1 claim without explicit approval.
- Do not infer a production restore drill, cloud isolation, backup encryption, or operational SLOs from repository tests.
- Do not add another identity/policy authority, scheduler, MCP server, or truth classifier.
