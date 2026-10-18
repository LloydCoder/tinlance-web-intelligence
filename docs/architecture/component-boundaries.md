# Component boundaries

| Component | Owns | Explicitly does not own |
| --- | --- | --- |
| TWI | Search/fetch/browser acquisition, extraction, acquisition artifact references, collection provenance, observations, monitoring | Canonical world state, identity authority, approval authority, agent lifecycle |
| World Intelligence | Canonical entities/events/relationships, temporal world state, correlation, contradiction, world signals | Browser execution or agent execution authority |
| Agent Platform | Identity, authz, policy, approvals, governed execution, secrets, budgets, audit | Web extraction semantics |
| Agent OS | Workspace, task orchestration and lifecycle | Authorization policy authority |
| Platform SDK | Typed client-facing contracts | Runtime execution authority |
| TADL | Agent artifacts, packaging and developer workflows | Runtime policy enforcement |
| TSIC | Cross-repository conformance and interoperability | Runtime identity or execution authority |

Any boundary change requires an ADR, consumer compatibility tests, and a TSIC conformance update.
