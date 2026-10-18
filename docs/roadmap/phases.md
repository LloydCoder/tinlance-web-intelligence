# Workstream plan and gates

Workstreams are executed serially. A workstream is complete only after implementation, relevant automated/integration/security tests, green required CI, reconciled documentation, and an evidence-backed audit. A directory scaffold or successful compile is insufficient.

| Workstream | Scope | Status |
| --- | --- | --- |
| W1 | Foundation, contracts, configuration, security invariants, CI | Merged; CI green on Python 3.12 and 3.13 |
| W2 | Search, safe fetch, extraction, source-backed results and artifact references | In progress |
| W3 | Durable task API and remote MCP | Not started |
| W4 | Isolated browser workers | Not started |
| W5 | Verified web agent and governed workflows | Not started |
| W6 | Private beta, operations, security, performance, release and TSIC conformance | Not started |

## Global exit gates

- Tests prove positive, negative, failure, and recovery behavior.
- No authority duplication or unsupported completion claims.
- Dependency and security checks pass; known critical/high findings are resolved or explicitly risk-accepted by the authorized owner.
- API/contracts and docs agree with implementation.
- CI green on the exact PR head; merge only after required checks pass.
- Production readiness is not claimed without deployment-specific evidence.
