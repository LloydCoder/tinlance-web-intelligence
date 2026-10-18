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

## Development

Requires Python 3.12+ or 3.13.

```bash
make install
make check
```

PostgreSQL is the production persistence backend for jobs, raw content-addressed artifacts, and the World Intelligence evidence outbox. Production requires TWI_DATABASE_URL with sslmode=verify-full; SQLite is limited to development, tests, and the single-host browser-isolation harness. PostgreSQL integration tests run when TWI_TEST_POSTGRES_DSN is set.

Network-capable acquisition must use connection-time DNS/IP validation, redirect revalidation, bounded resource use, and deployment egress controls. See [SSRF controls](docs/security/ssrf-controls.md). Backup and recovery procedures are documented in [backup and restore](docs/operations/backup-and-restore.md). W6 private-beta readiness is tracked in [the readiness checklist](docs/operations/private-beta-readiness.md).

See [workstream plan](docs/roadmap/phases.md), [component boundaries](docs/architecture/component-boundaries.md), [browser isolation](docs/security/browser-isolation.md), and [Platform MCP integration](docs/integration/platform-mcp.md).
