# Tinlance Web Intelligence

Evidence-first web discovery, retrieval, extraction, and monitoring for the Tinlance ecosystem.

> **Status:** Workstream implementation and acceptance status are tracked in [the phase ledger](docs/roadmap/phases.md). Production readiness is not claimed.

## Scope

TWI owns web search and retrieval adapters, safe HTTP acquisition, isolated browser work, content extraction, acquisition artifacts, collection provenance, and source-backed observations. It exports observations to Tinlance World Intelligence through versioned contracts.

## Authority boundaries

- **Tinlance Agent Platform** is authoritative for identity, authorization, policy, approvals, governed execution, secrets, budgets, audit, and the canonical remote MCP endpoint.
- **Tinlance Agent OS** owns workspace, task orchestration, and lifecycle.
- **Platform SDK** provides typed consumer contracts.
- **TADL** owns governed agent artifacts and developer workflows.
- **Tinlance World Intelligence** owns canonical entities, events, relationships, temporal world state, correlation, contradiction, and world-level signals.
- **TSIC** validates cross-repository interoperability and conformance.

TWI is a service/product layer, not an authority plane. It must not bypass Platform policy or duplicate World Intelligence semantics. It publishes operation manifests for the existing Platform MCP gateway rather than hosting a competing MCP server.

The versioned monitor API stores tenant-scoped monitor definitions and explicit durable capture runs. Agent OS controls recurrence. Results expose bounded deterministic change digests and do not claim truth; see [Monitor API v1](docs/api/monitors-v1.md). The commercial boundary provides atomic operation quotas, append-only usage facts, provider-neutral signed-event primitives, and a tenant-scoped [Usage API v1](docs/api/usage-v1.md). Successful fetch jobs can expose a deterministic, tenant-authorized [Evidence Export API v1](docs/api/evidence-packages-v1.md) package containing captured bytes and versioned acquisition provenance; exports require `twi:evidence:export` and a full `TWI_SOURCE_REVISION`. The package is integrity-checked but not digitally signed, does not assert source truth, and includes source bytes unchanged; exports must be treated as customer data. The [W15 evidence pack](docs/readiness/w15-gates.json) is a separate source-bound release-readiness artifact; external owner and deployment gates remain open until evidenced.

## Development

Requires Python 3.12+ or 3.13.

```bash
make install
make check
```

PostgreSQL is the production persistence backend for jobs, usage facts, billing-event receipts, raw content-addressed artifacts, and the World Intelligence evidence outbox. Production requires TWI_DATABASE_URL with sslmode=verify-full and an injected entitlement resolver backed by the approved billing boundary; startup fails closed without it. No provider-specific billing adapter or commercial plan catalogue is claimed until explicitly selected and configured. SQLite is limited to development, tests, and the single-host browser-isolation harness. PostgreSQL integration tests run when TWI_TEST_POSTGRES_DSN is set.

`make check` runs tests, lint, typing, security lint, migration synchronization, deterministic evaluation, consumer contract checks, W15 evidence pack validation, and GA v1 release-contract validation. Build a local package with `python -m build --no-isolation` when the host cannot create isolated build environments.

Network-capable acquisition must use connection-time DNS/IP validation, redirect revalidation, bounded resource use, and deployment egress controls. See [SSRF controls](docs/security/ssrf-controls.md). Backup and recovery procedures are documented in [backup and restore](docs/operations/backup-and-restore.md). W6 private-beta readiness is tracked in [the readiness checklist](docs/operations/private-beta-readiness.md).

See [workstream plan](docs/roadmap/phases.md), [component boundaries](docs/architecture/component-boundaries.md), [browser isolation](docs/security/browser-isolation.md), and [Platform MCP integration](docs/integration/platform-mcp.md).
