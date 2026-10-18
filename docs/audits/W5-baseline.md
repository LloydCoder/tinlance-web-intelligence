# W5 baseline audit — verified web agent and governed workflows

## Evidence reviewed

- Main commit: af1aea81fb090c5fd480bf1e617718b9ba1b1ce2.
- Main CI run: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39159210700 — completed successfully.
- TWI implements source-backed citation verification against successful, caller-accessible fetch/browser jobs. It explicitly does not assess factual truth.
- TWI exposes authenticated, tenant/subject-scoped source-evidence export with idempotency, a leased outbox, bounded retries, and a World Intelligence client.
- The Platform repository contains the governed TWI MCP adapter, audience-bound service-token issuer contract, risk/approval enforcement for source-evidence export, and adapter tests. See https://github.com/LloydCoder/tinlance-agent-platform/blob/main/docs/integrations/tinlance-web-intelligence.md.
- The TSIC repository did not previously register TWI in its ecosystem/service/adapter registries. The missing integration contract is being addressed by https://github.com/LloydCoder/tinlance-system-integration/pull/81.

## Required authority boundaries

- Agent Platform owns identity, authorization, policy, human approval, consequential execution, audit and authoritative execution evidence.
- TWI owns acquisition and source-backed observations only.
- World Intelligence owns canonical entity/event/relationship and temporal world-state semantics.
- Agent OS owns task orchestration and lifecycle.
- Platform SDK owns typed consumer contracts.
- TSIC owns cross-repository contracts and conformance.

## Disposition

**W5 is not certified complete yet.** TWI and Platform implementation evidence exists, but TSIC registry/conformance integration must pass CI and merge, and the final contract references must be reconciled. A green TWI repository workflow alone does not prove ecosystem interoperability or a production deployment.
