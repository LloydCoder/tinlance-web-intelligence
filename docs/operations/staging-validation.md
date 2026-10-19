# Staging deployment validation

## Purpose and evidence boundary

This procedure is a low-impact, read-only health and authorization probe for a deployed TWI staging API. It does not provision infrastructure, create jobs, exercise real acquisition, prove browser egress isolation, verify Platform-to-World-Intelligence delivery, or certify private beta.

Use only an explicitly approved staging origin. Never point the probe at production during a staging rehearsal.

## Prerequisites

- A deployed TWI API with a trusted HTTPS certificate and hostname.
- \`TWI_STAGING_BASE_URL\` set to the HTTPS origin/path, without credentials, query parameters, or fragment.
- Optional: \`TWI_STAGING_PROBE_TOKEN\` containing a short-lived, Platform-issued staging token for the TWI audience. The token is read from the process environment and is never printed.
- Access to the deployment's request logs and release SHA for evidence correlation.

## Deploy the staging topology

From the repository root, provision an isolated staging host and configure its cloud/host firewall before starting services. The Compose topology binds the API only to loopback and places the browser worker exclusively on internal control/egress networks; the egress proxy is the browser worker's only outbound path.

Required environment variables must be injected from the approved secret manager into the deployment shell or CI environment. Do not create a committed `.env` file. The runtime and migration DSNs must use `sslmode=verify-full` and distinct database usernames. The Platform issuer/JWKS and World Intelligence endpoint must be the intended staging environments.

```bash
docker compose -f deployments/compose/staging.yml config --quiet
docker compose -f deployments/compose/staging.yml up -d --build --wait
docker compose -f deployments/compose/staging.yml ps
```

Before enabling browser acquisition, prove from the deployed browser-worker network namespace that direct public and metadata IP connections fail while authenticated proxy access works. Compose alone cannot constrain egress for API/HTTP-acquisition/exporter containers attached to the outbound network: the host/cloud firewall must restrict API and exporter egress to approved database/identity/World Intelligence endpoints, and must enforce the documented acquisition-worker egress policy. If those controls cannot be enforced and evidenced, do not enable the staging stack for external traffic.

```bash
TWI_STAGING_BASE_URL=https://<approved-staging-host> python scripts/verify_staging.py
```

## Run

\`\`\`bash
TWI_STAGING_BASE_URL=https://<approved-staging-host> python scripts/verify_staging.py
\`\`\`

For the optional Platform token check, inject \`TWI_STAGING_PROBE_TOKEN\` from the approved secret manager or ephemeral CI secret store. Do not paste it into a command line, ticket, or chat history.

The script verifies:

1. TLS certificate and hostname validation through Python's default trust store.
2. Liveness returns HTTP 200 and the expected minimal JSON.
3. Readiness returns HTTP 200 and the expected minimal JSON.
4. An unauthenticated write request is rejected with HTTP 401 before job creation.
5. Interactive API documentation remains disabled outside development/test.
6. If a Platform token is supplied, authentication does not reject it as invalid (HTTP 403 means authenticated but missing required scope; HTTP 404 means authenticated and the random job identifier was not found).

Redirects are not followed. Network, TLS, malformed-response, unexpected status, and readiness failures cause a non-zero exit. Output contains status codes and pass/fail booleans only.

## Evidence to retain

For each run, retain the UTC timestamp, staging URL without secrets, deployed Git SHA/image digest, script version, runner identity, output JSON, and associated platform deployment/log references. Store the Platform token nowhere in the evidence pack. Redact tenant IDs and request identifiers if they can identify a customer.

## Required additional deployment tests

This smoke test is necessary but not sufficient. Before private beta, separately capture evidence for:

- Platform issuer/JWKS availability, audience enforcement, tenant and scope negative tests.
- Production PostgreSQL TLS with \`sslmode=verify-full\`, migration/runtime role separation, and schema version.
- API, acquisition worker, browser broker, browser worker, egress proxy, and World Intelligence exporter network policies.
- Browser worker direct-egress denial and Chromium sandbox inside the deployed environment.
- End-to-end source-evidence outbox delivery, retries, idempotency, lease expiry, and dead-letter handling.
- Secret rotation, encrypted backup, and witnessed restore with measured RPO/RTO.
- Monitoring, alert delivery, rollback, and incident-response rehearsal.

Record failed checks as blockers. Do not override a failed readiness check or mark a test passed based on CI-only evidence.
