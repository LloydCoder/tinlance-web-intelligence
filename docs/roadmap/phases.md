# Workstream plan and gates

Workstreams are executed serially. A workstream is complete only after implementation, relevant automated/integration/security tests, green required CI, reconciled documentation, and an evidence-backed audit. A directory scaffold or successful compile is insufficient.

| Workstream | Scope | Status |
| --- | --- | --- |
| W1 | Foundation, contracts, configuration, security invariants, CI | Merged; Python 3.12 and 3.13 CI evidence recorded |
| W2 | Search, safe fetch, extraction, source-backed results and artifact references | Merged; Python 3.12 and 3.13 CI evidence recorded |
| W3 | Durable task API, authenticated job lifecycle, Platform MCP operation contracts | Merged; PR #11 and main CI evidence recorded |
| W4 | Isolated browser workers and constrained egress proxy | Merged as PR #12; PR-head and post-merge CI evidence in docs/audits/W4-baseline.md |
| W5 | Verified web agent and governed workflows, World Intelligence export and TSIC integration | TWI implementation is on main and main CI is green; cross-repository TSIC registration is pending PR [#81](https://github.com/LloydCoder/tinlance-system-integration/pull/81). Do not certify W5 until that PR passes and merges and the contracts are reconciled. |
| W6 | PostgreSQL persistence, operations, recovery, release and private-beta readiness | In progress on work/w6-private-beta; no completion or production-readiness claim yet |

## Global exit gates

- Tests prove positive, negative, failure, concurrency, and recovery behavior.
- No authority duplication or unsupported completion claims.
- Dependency and security checks pass; known critical/high findings are resolved or explicitly risk-accepted by the authorized owner.
- API/contracts and docs agree with implementation.
- CI is green on the exact PR head; merge only after required checks pass.
- PostgreSQL-backed multi-worker job and outbox tests pass before W6 can be certified at repository level.
- Backup and restore scripts are tested safely; a real deployment restore drill remains a private-beta requirement.
- Consumer contracts and TSIC integration evidence are reconciled.
- Production readiness is not claimed without deployment-specific evidence.
