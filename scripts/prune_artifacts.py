"""Safely inspect or prune expired tenant-scoped acquisition artifacts."""
from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta

from tinlance_web_intelligence.persistence.postgres_artifacts import PostgresArtifactStore
from scripts.check_database_tls import validate_database_url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retention-days", type=int, default=int(os.environ.get("TWI_ARTIFACT_RETENTION_DAYS", "30")))
    parser.add_argument("--tenant-id", help="Limit pruning to one tenant; default covers all tenants")
    parser.add_argument("--apply", action="store_true", help="Delete expired records and unreferenced bytes")
    args = parser.parse_args()
    if not 1 <= args.retention_days <= 3650:
        parser.error("--retention-days must be between 1 and 3650")
    if args.apply and os.environ.get("TWI_CONFIRM_ARTIFACT_PRUNE") != "YES":
        parser.error("destructive pruning requires TWI_CONFIRM_ARTIFACT_PRUNE=YES")

    dsn = os.environ.get("TWI_ARTIFACT_MAINTENANCE_DATABASE_URL")
    if not dsn:
        parser.error("TWI_ARTIFACT_MAINTENANCE_DATABASE_URL is required for artifact pruning")
    validate_database_url(dsn)
    cutoff = datetime.now(UTC) - timedelta(days=args.retention_days)
    store = PostgresArtifactStore(dsn)
    try:
        count = store.count_expired(cutoff, tenant_id=args.tenant_id)
        if not args.apply:
            print(f"Dry run: {count} capture records are older than {args.retention_days} days.")
            return 0
        deleted = store.prune_before(cutoff, tenant_id=args.tenant_id)
        print(f"Pruned {deleted} expired capture records and unreferenced content.")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
