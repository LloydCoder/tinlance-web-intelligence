# Database migrations

The W3 SQLite schema is initialized by `SQLiteJobRepository` and is intended for the single-node durable job API. This is not the production multi-replica schema contract. W6 must introduce versioned PostgreSQL migrations, migration verification in CI, upgrade/rollback procedures, and a tested backup/restore path before production readiness can be claimed.
