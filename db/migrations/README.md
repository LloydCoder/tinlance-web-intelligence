# Database migrations

W3 initializes the durable single-node SQLite job store in SQLiteJobRepository. W4 includes a transactional runtime migration that rebuilds the W3 jobs table to allow the browser kind while preserving existing rows and recreating indexes. This migration is covered by tests/test_jobs_migration.py.

This is not a production multi-replica schema strategy. W6 must introduce versioned PostgreSQL migrations, schema-upgrade verification in CI, rollback procedures, and a tested backup/restore path before production readiness can be claimed.
