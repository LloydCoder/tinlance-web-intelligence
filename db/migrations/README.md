# Database migrations

The PostgreSQL schema is versioned at db/migrations/001_production_postgres.sql and packaged at src/tinlance_web_intelligence/persistence/migrations/001_production_postgres.sql for installed deployments. The copies must remain byte-identical; scripts/check_migration_sync.py and CI enforce this.

The adapter applies only idempotent CREATE TABLE/INDEX statements and records schema version 1. Future migrations must be append-only, versioned, reviewed, and tested against both a fresh database and a prior-version fixture. Do not run destructive migrations automatically on service startup.
