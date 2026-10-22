# Database migrations

The PostgreSQL schema is versioned under `db/migrations/` and packaged under `src/tinlance_web_intelligence/persistence/migrations/` for installed deployments. Each numbered SQL file must have a byte-identical packaged copy. `scripts/check_migration_sync.py` compares both complete filename sets and file bytes; CI enforces this.

- Migration 001 establishes the production persistence schema.
- Migration 002 adds tenant-scoped monitors, monitor results, the monitor job kind, and trace context.
- Migration 003 adds atomic quota reservations, append-only usage facts, and payload-free billing event receipts.
- Migration 004 removes historical query strings from persisted artifact source URLs because query values may contain credentials, signed-link parameters, personal search terms, or other sensitive data.

The ordered `MIGRATION_FILES` registry in the packaged migration module is the single source of truth for the explicit migration runner and adapter bootstrap helpers. The latest schema version is 4. Runtime adapters fail closed on older schemas; run the explicit migration job before deploying the matching application revision.

Migrations must be append-only, reviewed, idempotent, and tested against both a fresh database and a prior-version fixture. Do not run destructive migrations automatically during normal service startup. Historical backups created before migration 004 may still contain old query strings; expire those backups under the approved backup-retention policy rather than claiming the migration can rewrite immutable backup files.
