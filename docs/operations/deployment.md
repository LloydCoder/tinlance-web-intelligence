# Deployment topology and production requirements

## Persistence

Run the explicit migration job before API and worker startup. The runtime role must not have DDL privileges; production uses a separate TWI_MIGRATION_DATABASE_URL role with TLS certificate and hostname verification. The migration runner serializes migration execution with a PostgreSQL advisory lock and verifies the schema version. The API and workers fail closed if the schema is absent or unsupported.

PostgreSQL is the supported production persistence backend for jobs, usage facts, billing-event receipts, tenant-scoped content-addressed artifacts, and the World Intelligence source-evidence outbox. Configure TWI_DATABASE_URL as a secret. Production configuration fails closed unless it is a PostgreSQL URL with a hostname, database, credentials, and sslmode=verify-full. Configure a trusted CA and verify the server hostname. Do not put credentials in command-line arguments, logs, images, or committed files.

SQLite is supported only for development, tests, and the single-host browser-isolation harness. Do not run multiple API/worker replicas against a shared SQLite file.

## Services and network

- The API accepts application traffic only from the Platform gateway and approved health probes. The API container has no general outbound network access in the reference Compose topology.
- Acquisition workers need explicit outbound access for approved public-web retrieval; apply destination and egress policy at the deployment network layer.
- Browser workers must have no direct Internet egress, no database mount or application credentials, and must use the authenticated TWI egress proxy. Preserve Chromium sandboxing and resource limits.
- The World Intelligence export worker needs outbound access only to the configured World Intelligence endpoint and approved identity/telemetry services.
- PostgreSQL is reachable only from the application network. Use separate roles for runtime and backup operations, least-privilege grants, connection limits, encrypted storage, and managed backups.
- Use the deployment secret manager for Platform identity configuration, Brave API keys, browser broker/proxy credentials, and World Intelligence service credentials.

## Readiness and operations

Readiness checks verify the configured job repository and outbox database connectivity. Liveness is intentionally independent of downstream readiness. Configure alerts for readiness failures, queue age, retry/dead-letter counts, outbox delivery lag, browser failures, and provider rate limits.

Run scripts/backup_postgres.sh from an approved backup environment. Restore is destructive and requires the explicit confirmation and isolated target checks documented in backup-and-restore.md. Private beta requires a witnessed restore drill and deployment-specific network-policy verification.

## Limits

The PostgreSQL adapters and integration tests establish repository-level behavior; they do not certify the target cloud deployment, secret rotation, database HA/failover, monitoring alerts, or actual backup recovery. Do not claim production readiness until the deployment-specific evidence is reviewed.
# W15 monitor deployment notes

Production monitor storage requires PostgreSQL migration 002 and the runtime least-privilege database role. Deploy API and worker from the same immutable source revision. The worker must enable the `monitor` job kind and apply the configured maximum response bytes. Do not configure a second scheduler: Agent OS invokes run operations.

Before enabling customer monitors, verify backup/restore for monitor definitions and the deletion redaction policy, database migration rollback/recovery against a real PostgreSQL service, safe DNS/redirect egress, trace collector configuration, alert delivery, and retention ownership. The local environment has no PostgreSQL DSN or Docker, so those database and deployment checks remain `not_evidenced`.


## Customer evidence export

The `GET /v1/jobs/{job_id}/evidence` route requires the dedicated `twi:evidence:export` scope and a successful fetch job owned by the verified tenant/subject. Staging Compose passes `TWI_SOURCE_REVISION` to the API; set it to the exact 40-character lowercase Git commit SHA represented by the deployed artifact. If it is absent or malformed, evidence export returns 503 rather than emitting unbound provenance. API and worker releases should use the same immutable image/source revision.

The evidence package contains the captured source bytes. Treat exports as customer data: enforce the Platform authorization policy, use TLS, avoid shared caches, and apply the approved customer retention policy. The package is hash-integrity-checked but not digitally signed; it does not replace immutable retention, backup recovery, or an external audit archive. It records acquisition observations and does not assert source truth or authority.
