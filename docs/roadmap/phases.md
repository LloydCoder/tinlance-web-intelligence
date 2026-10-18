# Workstream plan and gates

Workstreams are executed serially. A workstream is complete only after implementation, relevant automated/integration/security tests, green required CI, reconciled documentation, and an evidence-backed audit. A directory scaffold or successful compile is insufficient.

| Workstream | Scope | Status |
| --- | --- | --- |
| W1 | Foundation, contracts, configuration, security invariants, CI | Merged; Python 3.12 and 3.13 CI evidence recorded |
| W2 | Search, safe fetch, extraction, source-backed results and artifact references | Merged; Python 3.12 and 3.13 CI evidence recorded |
| W3 | Durable task API, authenticated job lifecycle, Platform MCP operation contracts | Merged; PR #11 and main CI evidence recorded |
| W4 | Isolated browser workers and constrained egress proxy | Merged as PR #12; PR-head and post-merge CI evidence in docs/audits/W4-baseline.md |
| W5 | Verified web agent and governed workflows, World Intelligence export and TSIC integration | **Complete.** TWI PR [#14](https://github.com/LloydCoder/tinlance-web-intelligence/pull/14) merged (`af1aea81`); Platform PR [#139](https://github.com/LloydCoder/tinlance-agent-platform/pull/139) merged (`882be4ef`); TSIC PRs [#81](https://github.com/LloydCoder/tinlance-system-integration/pull/81) and [#82](https://github.com/LloydCoder/tinlance-system-integration/pull/82) merged (`2e367a8a`, `afdc624d`). The obsolete conflicting TSIC PR #80 was closed after its unique schema work was reconciled into #82. Post-merge CI, security, conformance and integration workflows passed across the three repositories.
| W6 | PostgreSQL persistence, operations, recovery, release and private-beta readiness | **Repository implementation complete.** PR [#15](https://github.com/LloydCoder/tinlance-web-intelligence/pull/15) merged as `18b2fa08`; post-merge main CI run [#430](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39164413530) passed. Private-beta launch remains **not certified** until deployment-specific readiness evidence is verified; see `docs/audits/W6-final.md` and `docs/operations/private-beta-readiness.md`. |

## Global exit gates

- Tests prove positive, negative, failure, concurrency, and recovery behavior.
- No authority duplication or unsupported completion claims.
- Dependency and security checks pass; known critical/high findings are resolved or explicitly risk-accepted by the authorized owner.
- API/contracts and docs agree with implementation.
- CI is green on the exact PR head; merge only after required checks pass.
- PostgreSQL-backed multi-worker job, outbox and tenant-scoped artifact tests pass before W6 can be certified at repository level.
- Artifact retention is dry-run by default, uses a separate least-privilege maintenance DSN, and requires explicit confirmation for deletion.
- Staging and production database connections require `sslmode=verify-full`, including backup and restore operations.
- Backup and restore scripts are tested safely; a real deployment restore drill remains a private-beta requirement.
- Consumer contracts and TSIC integration evidence are reconciled.
- Production readiness is not claimed without deployment-specific evidence.
