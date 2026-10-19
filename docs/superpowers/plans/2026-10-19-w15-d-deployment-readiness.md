# W15-D Implementation Plan

- [x] D1 — Forensically audit existing deployment, configuration, migration, health, backup/restore, Compose, and release workflows; reuse existing components.
- [x] D2 — Add a secret-safe temporary libpq service-file helper and environment-variable-selectable TLS validation.
- [x] D3 — Harden backup publication: dedicated role, no credential-bearing process arguments, private permissions, atomic outputs, and partial-file cleanup.
- [x] D4 — Harden restore: dedicated restore role, primary-vs-target identity check, strict target naming/confirmation, and checksum-to-selected-file verification.
- [x] D5 — Add adversarial tests for URL/service parsing, permissions, credential handling, target isolation, checksum integrity, and cleanup paths.
- [x] D6 — Reconcile backup/restore and deployment docs, examples, environment variables, and conservative self-hosting exclusion.
- [x] D7 — Exact-head CI passed on `5cc2dc3535a3a428179fc171acbad01f0f72b0b7`: PR run [#39317643771](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39317643771) and push run [#39317635707](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39317635707); Python 3.12, Python 3.13, reproducible release artifact validation, and browser container isolation all passed.
- [x] D8 — Phase-specific forensic audit completed. It found and fixed Ruff import/security-lint failures, mypy-only operational-script import failures, and an incorrectly escaped newline in the restore checksum fixture. Final exact-head suite: 293 passed, 1 skipped; the browser runtime sandbox test is intentionally run in its dedicated CI step, which passed.
- [ ] D9 — Merge only after the reviewed exact-head checks pass; then verify post-merge main CI and update roadmap/readiness evidence.

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
- Before invoking either database client, remove every inherited `*_DATABASE_URL` variable and ambient `PG*` connection override, then re-export only the temporary `PGSERVICEFILE` pointer. Stubbed client tests assert no runtime/operational DSNs, `PGPASSWORD`, `PGHOSTADDR`, or `PGOPTIONS` survive into the client process.
