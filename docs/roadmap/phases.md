# Workstream plan and gates

Workstreams are executed serially. A workstream is complete only after implementation, relevant automated/integration/security tests, green required CI, reconciled documentation, and an evidence-backed audit. A directory scaffold or successful compile is insufficient.

| Workstream | Scope | Status |
| --- | --- | --- |
| W1 | Foundation, contracts, configuration, security invariants, CI | Merged; CI green on Python 3.12 and 3.13 |
| W2 | Search, safe fetch, extraction, source-backed results and artifact references | Merged; CI green on Python 3.12 and 3.13 |
| W3 | Durable task API, authenticated job lifecycle, Platform MCP operation contracts | Merged; PR #11 and main CI green |
| W4 | Isolated browser workers and constrained egress proxy | Merged as PR #12 (`9af6a77`); PR-head and post-merge CI green (runs [39154470930](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39154470930) and [39154598849](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39154598849)) |
| W5 | Verified web agent and governed workflows, World Intelligence and TSIC integration | Not started |
| W6 | Private beta, operations, security, performance, release and conformance | Not started |

## Global exit gates

- Tests prove positive, negative, failure, and recovery behavior.
- No authority duplication or unsupported completion claims.
- Dependency and security checks pass; known critical/high findings are resolved or explicitly risk-accepted by the authorized owner.
- API/contracts and docs agree with implementation.
- CI green on the exact PR head; merge only after required checks pass.
- Production readiness is not claimed without deployment-specific evidence.
