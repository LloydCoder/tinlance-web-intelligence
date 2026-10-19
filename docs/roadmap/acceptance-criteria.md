# Acceptance criteria

Each workstream must attach evidence for:

- scope and ownership boundary;
- implementation and code review;
- unit, contract, integration, security, concurrency and relevant end-to-end tests;
- CI workflow run and exact commit SHA;
- threat-model and operational-document updates;
- consumer compatibility and TSIC conformance where applicable;
- migration behavior and recovery semantics for persistence changes;
- unresolved risks and explicit non-goals.

A check that has not run is not passing. A workflow configuration is not proof that a workflow passed. Repository CI is not proof of a deployed environment, network policy, secret rotation, or backup recovery.


## W15 commercial/product subphases

- **W15-A — Commercial readiness:** durable usage facts, atomic quota enforcement, tenant-scoped entitlements, idempotent billing-event receipts, retry/replay safety, and reconciliation tests. Live provider settlement remains an external gate.
- **W15-B — Provenance export:** deterministic schema-versioned package, artifact/provenance consistency, tenant-and-subject authorization, dedicated export scope, full source revision binding, tamper detection, and explicit non-truth semantics. Captured bytes remain customer data; exports are not signed attestations.
- **W15-C — Hard-job qualification:** versioned hard-case fixtures, deterministic evaluator and report hashes, correctness/evidence/latency/resource metrics, failure classification, and reviewed thresholds. Synthetic and live results must be labeled separately.
- **W15-D — Deployment readiness:** reproducible supported deployment, strict configuration, migration and recovery behavior, tested backup/restore scripts, health checks, and deployment threat controls. Self-hosting is excluded from GA v1 unless explicitly approved and evidenced.
- **W15-E — GA decision:** versioned support contract, consistent product claims and limits, source-bound release evidence, benchmark/security qualification, and reviewed residual-risk/owner approvals. If external gates are missing or failed, release status remains not certified.
