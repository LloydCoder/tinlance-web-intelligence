# Database migrations

The PostgreSQL schema is versioned under `db/migrations/` and packaged under `src/tinlance_web_intelligence/persistence/migrations/` for installed deployments. Each numbered SQL file has a byte-identical packaged copy; `scripts/check_migration_sync.py` and CI enforce this. Migration 001 establishes the original schema; migration 002 adds tenant-scoped monitors, monitor results, the monitor job kind, and optional trace context.

The explicit migration job applies the versioned SQL files in order and records schema version 2. Future migrations must be append-only, versioned, reviewed, and tested against both a fresh database and a prior-version fixture. Do not run destructive migrations automatically on service startup.
