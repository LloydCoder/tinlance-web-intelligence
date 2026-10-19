# W15-D Implementation Plan

- [x] D1 — Forensically audit existing deployment, configuration, migration, health, backup/restore, Compose, and release workflows; reuse existing components.
- [ ] D2 — Add a secret-safe temporary libpq service-file helper and environment-variable-selectable TLS validation.
- [ ] D3 — Harden backup publication: dedicated role, no credential-bearing process arguments, private permissions, atomic outputs, and partial-file cleanup.
- [ ] D4 — Harden restore: dedicated restore role, primary-vs-target identity check, strict target naming/confirmation, and checksum-to-selected-file verification.
- [ ] D5 — Add adversarial tests for URL/service parsing, permissions, credential handling, target isolation, checksum integrity, and cleanup paths.
- [ ] D6 — Reconcile backup/restore and deployment docs, examples, environment variables, and conservative self-hosting exclusion.
- [ ] D7 — Run lint, typing, security, unit/contract/PostgreSQL, shell, migration, reproducible artifact, and browser-isolation checks on the exact PR head.
- [ ] D8 — Perform a phase-specific forensic audit; fix every repository-verifiable blocker and document external evidence limits.
- [ ] D9 — Merge only after all required exact-head checks pass; verify post-merge main CI and update roadmap/readiness evidence.

## Audit findings

- `scripts/backup_postgres.sh` currently uses the runtime DSN and supplies it directly to `pg_dump`; this contradicts the dedicated backup role and secret-handling docs.
- `scripts/restore_postgres.sh` currently supplies the DSN directly to `pg_restore` and does not compare the recovery target against a declared primary.
- Restore currently relies on `sha256sum -c`, which trusts the filename embedded in the checksum sidecar rather than independently binding the digest to the selected dump.
- The real encrypted-backup mount, cloud identity/network policy, witnessed restore drill, measured RPO/RTO, HA/failover, and production alerts cannot be proven by repository CI and must remain external/not-evidenced.
