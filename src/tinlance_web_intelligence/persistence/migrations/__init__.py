"""Versioned PostgreSQL migrations packaged with TWI.

Keep this ordered registry as the single source of truth for migration runners
and repository bootstrap helpers. CI verifies every file has an identical
canonical copy under db/migrations/.
"""

MIGRATION_FILES = (
    "001_production_postgres.sql",
    "002_monitors.sql",
    "003_commercial_usage.sql",
    "004_redact_artifact_source_urls.sql",
)
LATEST_SCHEMA_VERSION = 4
