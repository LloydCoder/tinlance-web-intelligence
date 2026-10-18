# Workstream plan and gates

Workstreams are executed serially. A workstream is complete only after implementation, relevant automated/integration/security tests, green required CI, reconciled documentation, and an evidence-backed audit. A directory scaffold or successful compile is insufficient.

1. **W1 — Foundation and contracts:** package layout, configuration, contracts, security invariants, CI and developer tooling.
2. **W2 — Search, fetch and extraction:** provider adapters, safe retrieval, normalization, source-backed results and artifact references.
3. **W3 — Durable task API and remote MCP:** versioned API, persisted jobs, authentication/authorization integration, retries and observability.
4. **W4 — Isolated browser workers:** worker isolation, destination controls, resource budgets, session lifecycle and adversarial tests.
5. **W5 — Verified web agent and governed workflows:** evidence-linked synthesis, Platform authorization, approval boundaries, OS lifecycle and World Intelligence export.
6. **W6 — Private beta and commercial readiness:** deployment, operational runbooks, backup/recovery, performance/security gates, release and TSIC conformance evidence.

## Global exit gates

- Tests prove positive, negative, failure, and recovery behavior.
- No authority duplication or unsupported completion claims.
- Dependency and security checks pass; known critical/high findings are resolved or explicitly risk-accepted by the authorized owner.
- API/contracts and docs agree with implementation.
- CI green on the exact PR head; merge only after required checks pass.
- Production readiness is not claimed without deployment-specific evidence.
