"""Safely inspect or redact expired terminal job payloads and results."""
from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta

from check_database_tls import validate_database_url

from tinlance_web_intelligence.persistence.postgres_jobs import PostgresJobRepository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("TWI_JOB_DATA_RETENTION_DAYS", "30")),
    )
    parser.add_argument(
        "--tenant-id", help="Limit redaction to one tenant; default covers all tenants"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Redact expired terminal job payloads/results"
    )
    args = parser.parse_args()
    if not 1 <= args.retention_days <= 3650:
        parser.error("--retention-days must be between 1 and 3650")
    if args.apply and os.environ.get("TWI_CONFIRM_JOB_DATA_PRUNE") != "YES":
        parser.error("destructive redaction requires TWI_CONFIRM_JOB_DATA_PRUNE=YES")

    dsn = os.environ.get("TWI_JOB_MAINTENANCE_DATABASE_URL")
    if not dsn:
        parser.error("TWI_JOB_MAINTENANCE_DATABASE_URL is required for job-data retention")
    validate_database_url(dsn)
    cutoff = datetime.now(UTC) - timedelta(days=args.retention_days)
    repository = PostgresJobRepository(dsn)
    try:
        count = repository.count_expired_results(cutoff, tenant_id=args.tenant_id)
        if not args.apply:
            print(
                f"Dry run: {count} terminal jobs contain payload/results older than "
                f"{args.retention_days} days."
            )
            return 0
        redacted = repository.redact_expired_results(cutoff, tenant_id=args.tenant_id)
        print(f"Redacted payloads/results for {redacted} expired terminal jobs.")
        return 0
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
