# W15-D Implementation Plan

- [x] D1 — Forensically audit existing deployment, configuration, migration, health, backup/restore, Compose, and release workflows; reuse existing components.
- [x] D2 — Add a secret-safe temporary libpq service-file helper and environment-variable-selectable TLS validation.
- [x] D3 — Harden backup publication: dedicated role, no credential-bearing process arguments, private permissions, atomic outputs, and partial-file cleanup.
- [x] D4 — Harden restore: dedicated restore role, primary-vs-target identity check, strict target naming/confirmation, and checksum-to-selected-file verification.
- [x] D5 — Add adversarial tests for URL/service parsing, permissions, credential handling, target isolation, checksum integrity, and cleanup paths.
- [x] D6 — Reconcile backup/restore and deployment docs, examples, environment variables, and conservative self-hosting exclusion.
- [ ] D7 — Run lint, typing, security, unit/contract/PostgreSQL, shell, migration, reproducible artifact, and browser-isolation checks on the exact PR head.
- [ ] D8 — Perform a phase-specific forensic audit; fix every repository-verifiable blocker and document external evidence limits.
- [ ] D9 — Merge only after all required exact-head checks pass; verify post-merge main CI and update roadmap/readiness evidence.

## Audit findings

- `scripts/backup_postgres.sh` now requires `TWI_BACKUP_DATABASE_URL`, writes a temporary owner-only libpq service file, passes only `service=twi_backup` to `pg_dump`, publishes the dump and checksum atomically, and cleans partial outputs.
- `scripts/restore_postgres.sh` now requires dedicated restore and primary DSNs, uses `service=twi_restore`, and calls a tested preflight that rejects the primary host/port/database identity.
- Restore checksum validation now rejects symlinks, malformed/multi-line manifests, filename mismatches, and digest mismatches; it hashes the selected dump bytes directly.
- `scripts/check_database_tls.py` supports explicit DSN environment selection, rejects fragments/invalid ports, and never accepts a DSN as a command-line argument.
- `scripts/create_pg_service.py` rejects unsafe URL parameters and control characters, protects service-file permissions, and does not print credential values.
- Tests cover URI decoding, service-file mode, unsupported/duplicate parameters, unsafe credentials, restore target identity, checksum tampering, symlink refusal, and secret-safe script invocation.
- The real encrypted-backup mount, cloud identity/network policy, witnessed restore drill, measured RPO/RTO, HA/failover, and production alerts cannot be proven by repository CI and must remain external/not-evidenced.
- Database client processes now inherit neither the operational DSNs nor `TWI_DATABASE_URL`; tests execute both shell scripts against controlled `pg_dump`/`pg_restore` stubs to verify service-file permissions, argument safety, partial-backup cleanup, checksum enforcement, and primary-target rejection.
- Cross-phase audit aligned `make evaluation-check` with the checked-in threshold registry, so CI evaluates the same registry documented by the benchmark guide.
