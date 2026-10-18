# Tinlance Web Intelligence

Evidence-first web discovery, retrieval, extraction, and monitoring for the Tinlance ecosystem.

> **Status:** workstreams are implemented serially. Repository presence and passing tests do not imply a production deployment or production readiness.

## Scope

TWI owns web search and retrieval adapters, safe HTTP acquisition, isolated browser work, content extraction, acquisition artifacts, provenance for collection activities, and source-backed observations. It exports observations to Tinlance World Intelligence through versioned contracts.

## Authority boundaries

- **Tinlance Agent Platform** is authoritative for identity, authorization, policy, approvals, governed execution, secrets, budgets, and audit.
- **Tinlance Agent OS** owns workspace, task orchestration, and lifecycle.
- **Platform SDK** provides typed consumer contracts.
- **TADL** owns governed agent artifacts and developer workflows.
- **Tinlance World Intelligence** owns canonical entities, events, relationships, temporal world state, correlation, contradiction, and world-level signals.
- **TSIC** validates cross-repository interoperability and conformance.

TWI is a service/product layer, not an authority plane. It must not bypass Platform policy or duplicate World Intelligence semantics.

## Development

Requires Python 3.12+.

```bash
python -m pip install -e '.[dev]'
make check
```

The initial phase establishes contracts, configuration, security invariants, and CI before adding network-capable acquisition. Never run arbitrary external URLs in privileged environments.

See [docs/roadmap/phases.md](docs/roadmap/phases.md) and [docs/architecture/component-boundaries.md](docs/architecture/component-boundaries.md).
