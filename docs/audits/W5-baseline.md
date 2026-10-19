# W5 baseline audit — verified web agent and governed workflows

## Evidence reviewed at the W5 baseline

- Initial implementation commit: af1aea81fb090c5fd480bf1e617718b9ba1b1ce2.
- Initial main CI run: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39159210700 — completed successfully.
- TWI implements source-backed citation verification against successful, caller-accessible fetch/browser jobs. It explicitly does not assess factual truth.
- TWI exposes authenticated, tenant/subject-scoped source-evidence export with idempotency, a leased outbox, bounded retries, and a World Intelligence client.
- The Platform repository contains the governed TWI MCP adapter, audience-bound service-token issuer contract, risk/approval enforcement for source-evidence export, and adapter tests. See https://github.com/LloydCoder/tinlance-agent-platform/blob/882be4ef03f78084ce800a715029a0b1346ebdd2/docs/integrations/tinlance-web-intelligence.md.
- TSIC registry/conformance work was completed in the merged revisions listed below; initial interim wording is superseded by this final disposition.

## Required authority boundaries

- Agent Platform owns identity, authorization, policy, human approval, consequential execution, audit and authoritative execution evidence.
- TWI owns acquisition and source-backed observations only.
- World Intelligence owns canonical entity/event/relationship and temporal world-state semantics.
- Agent OS owns task orchestration and lifecycle.
- Platform SDK owns typed consumer contracts.
- TSIC owns cross-repository contracts and conformance.

## Final disposition — reconciled 2026-10-19

**W5 repository-level integration and recorded conformance are verified.** This statement is limited to repository artifacts and CI evidence, not deployment certification.

- TWI PR [#14](https://github.com/LloydCoder/tinlance-web-intelligence/pull/14) merged as `af1aea81`.
- Agent Platform PR [#139](https://github.com/LloydCoder/tinlance-agent-platform/pull/139) merged; the reviewed Platform revision used by the integration gate is `882be4ef03f78084ce800a715029a0b1346ebdd2`.
- TSIC PRs [#81](https://github.com/LloydCoder/tinlance-system-integration/pull/81) and [#82](https://github.com/LloydCoder/tinlance-system-integration/pull/82) merged; the pinned TSIC revision is `bd2e7582ad29eb460be36ca45b073b99fdeadfbf`.
- TWI PyJWT compatibility PR [#19](https://github.com/LloydCoder/tinlance-web-intelligence/pull/19) merged as `7b48b28ccd76b9ea2f09a2f524469c4a3ffe8dcc`, aligning the dependency range with Platform's supported PyJWT floor.
- TADL ecosystem integration PR [#94](https://github.com/LloydCoder/tinlance-agent-developer/pull/94) merged as `9f53387aa10e4fae0bc23686688d9794a527df01`. It pins TWI, checks out exact SHAs, runs the TWI test suite from its own root, exercises the Platform MCP/API adapter tests, and retains the canonical TSIC and ecosystem conformance gates.
- The post-merge TADL [Ecosystem Integration](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004842), [CI](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200005061), [Security](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004766), [CodeQL](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004862), [Secret Scan](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004751), [Scorecard](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004886), [Supply Chain Attestation](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004905), and [Release Attestations](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004782) workflows passed on the exact main merge commit.

## Private-beta release decision

Repository CI does **not** prove a deployment is safe or operationally ready. Do not announce or enable a private beta until the owner has recorded evidence for all of the following in the target environment:

- Production identity, secrets, least-privilege database roles, and authenticated tool permissions.
- Enforced browser/network egress controls and SSRF protections at the deployed network boundary.
- Backup encryption and access control, configured retention, and a witnessed restore drill.
- Production observability, alert routing, service-level objectives, capacity limits, incident response, and recovery procedures.
- Human approval and audit-evidence checks for consequential workflows.
- Actual authenticated World Intelligence ingestion and TSIC checks for the exact target consumer versions.

The checklist in [private-beta-readiness.md](../operations/private-beta-readiness.md) remains intentionally unchecked until those deployment-specific tests are completed. No production/private-beta readiness claim is made by this repository audit.
