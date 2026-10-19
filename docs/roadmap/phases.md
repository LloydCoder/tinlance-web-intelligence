# Workstream plan and gates

Workstreams are executed serially for **release-gate closure**. Implementation may expose or fix evidence-backed dependencies in later workstreams, but no phase is marked complete until its own acceptance criteria are satisfied. A directory scaffold, documentation-only merge, or successful compile is insufficient.

| Workstream | Scope | Status |
| --- | --- | --- |
| W1 | Foundation, contracts, configuration, security invariants, CI | Merged; Python 3.12 and 3.13 CI evidence recorded |
| W2 | Search, safe fetch, extraction, source-backed results and artifact references | Merged; Python 3.12 and 3.13 CI evidence recorded |
| W3 | Durable task API, authenticated job lifecycle, Platform MCP operation contracts | Merged; PR #11 and main CI evidence recorded |
| W4 | Isolated browser workers and constrained egress proxy | Merged as PR #12; PR-head and post-merge CI evidence in [W4 baseline](../audits/W4-baseline.md) |
| W5 | Verified web agent and governed workflows, World Intelligence export and TSIC integration | **Complete at repository/recorded conformance level.** TWI PR [#14](https://github.com/LloydCoder/tinlance-web-intelligence/pull/14) merged (`af1aea81`); Platform PR [#139](https://github.com/LloydCoder/tinlance-agent-platform/pull/139) merged (`882be4ef`); TSIC PRs [#81](https://github.com/LloydCoder/tinlance-system-integration/pull/81) and [#82](https://github.com/LloydCoder/tinlance-system-integration/pull/82) merged (`2e367a8a`, `afdc624d`). The obsolete conflicting TSIC PR #80 was closed after its unique schema work was reconciled into #82. Recorded post-merge CI, security, conformance and integration workflows passed across the three repositories. See [W5 audit](../audits/W5-baseline.md). |
| W6 | PostgreSQL persistence, operations, recovery, release and private-beta readiness | **Repository implementation complete; private beta NOT CERTIFIED.** PR [#15](https://github.com/LloydCoder/tinlance-web-intelligence/pull/15) merged as `18b2fa08`; closeout PR [#16](https://github.com/LloydCoder/tinlance-web-intelligence/pull/16) merged as `5f42dff6`. Deployment-specific evidence remains required; see [W6 audit](../audits/W6-final.md) and [private-beta readiness](../operations/private-beta-readiness.md). |
| W7 | Repository governance, enforceable CI, release supply chain, SBOM and provenance | **In progress; not closed.** [Baseline](../audits/W7-baseline.md) merged as `df36c8f`. PR [#22](https://github.com/LloydCoder/tinlance-web-intelligence/pull/22) added dependency metadata checks, CycloneDX build-environment SBOM, SHA-256 checksums, and GitHub build-provenance attestation steps; its main CI passed on `87c7b003`. Effective branch inspection reports no active rulesets and `main` unprotected. Ruleset creation reached GitHub's MFA/sudo prompt and could not be saved; release attestation workflow has not yet been exercised. |
| W8 | Staging deployment, production topology, ecosystem certification and live journey tests | **In progress.** PR [#23](https://github.com/LloydCoder/tinlance-web-intelligence/pull/23) routes the internal browser broker through the configured durable repository; its post-merge CI passed in [run #39210705747](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39210705747). PR [#24](https://github.com/LloydCoder/tinlance-web-intelligence/pull/24) added a non-mutating staging probe and deployment evidence runbook; its post-merge CI passed in [run #39211285094](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39211285094). No live deployment or Platform → TWI → World Intelligence journey is yet certified.
| W9 | Security assurance and adversarial validation | **In progress.** This PR adds adversarial legacy-IP parsing and proxy DNS-rebinding/mixed-answer tests plus a threat-to-evidence matrix. CI evidence is pending. Target-environment SSRF/redirect, tenant-isolation, browser-egress and resource-exhaustion tests remain mandatory.
| W10 | Observability and SRE | Proposed; establish service/queue/outbox/browser metrics, trace correlation, alert delivery, measurable SLOs, capacity budgets, and tested on-call/rollback operations. |
| W11 | Evidence provenance and data governance | Proposed; validate source lineage, integrity-vs-truth semantics, retention/deletion, freshness, tenant-scoped access, and evidence-pack completeness. |
| W12 | Intelligence quality and evaluation | Proposed; build a TWI-specific reproducible benchmark for retrieval, extraction, citation grounding, source diversity, freshness, and failure calibration. Keep FAS-Bench independent. |
| W13 | Continuous monitoring and change intelligence | Proposed; enable scheduled monitoring only after durable evidence, idempotent retries, telemetry, and safe change detection are demonstrated. |
| W14 | Enterprise tenant controls and integration contracts | Proposed; automate consumer-version contract tests and negative authorization checks while preserving Agent Platform as the sole policy authority. |
| W15 | General availability and customer operations | Proposed; requires all prior release gates, live evidence pack, reviewed risk register, support/on-call readiness, load and cost results, recovery evidence, and explicit authorized release approval. |

## Global exit gates

- Tests prove positive, negative, failure, concurrency, and recovery behavior.
- No authority duplication or unsupported completion claims.
- Dependency and security checks pass; known critical/high findings are resolved or explicitly risk-accepted by the authorized owner.
- API/contracts and documentation agree with implementation.
- CI is green on the exact PR head and post-merge main commit; branch governance must make required checks enforceable, not merely visible.
- PostgreSQL-backed multi-worker job, broker, outbox and tenant-scoped artifact tests pass.
- Artifact retention is dry-run by default, uses a separate least-privilege maintenance DSN, and requires explicit confirmation for deletion.
- Staging and production database connections require `sslmode=verify-full`, including backup and restore operations.
- Backup and restore scripts are tested safely; a real deployment restore drill remains a private-beta requirement.
- Consumer contracts and TSIC integration evidence are reconciled against exact reviewed revisions.
- Production readiness is not claimed without deployment-specific evidence.
- W7–W15 phase completion is an evidence-backed release decision; do not infer operational readiness from CI or documentation alone.
