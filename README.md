# Tinlance Web Intelligence

Evidence-first web discovery, retrieval, extraction, and monitoring for the Tinlance ecosystem.

> **Status:** W1 foundation is merged. W2 search/fetch/extraction is under implementation; no production deployment is claimed.

## Scope

TWI owns web search and retrieval adapters, safe HTTP acquisition, isolated browser work, content extraction, acquisition artifacts, collection provenance, and source-backed observations. It exports observations to Tinlance World Intelligence through versioned contracts.

## Authority boundaries

- **Tinlance Agent Platform** is authoritative for identity, authorization, policy, approvals, governed execution, secrets, budgets, and audit.
- **Tinlance Agent OS** owns workspace, task orchestration, and lifecycle.
- **Platform SDK** provides typed consumer contracts.
- **TADL** owns governed agent artifacts and developer workflows.
- **Tinlance World Intelligence** owns canonical entities, events, relationships, temporal world state, correlation, contradiction, and world-level signals.
- **TSIC** validates cross-repository interoperability and conformance.

TWI is a service/product layer, not an authority plane. It must not bypass Platform policy or duplicate World Intelligence semantics.

## Development

Requires Python 3.12+ or 3.13.

```bash
make install
make check
```

Network-capable acquisition must use connection-time DNS/IP validation, redirect revalidation, bounded resource use, and deployment egress controls. See [SSRF controls](docs/security/ssrf-controls.md).

See [workstream plan](docs/roadmap/phases.md) and [component boundaries](docs/architecture/component-boundaries.md).
