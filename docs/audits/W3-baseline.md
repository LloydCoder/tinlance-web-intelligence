# W3 baseline audit — durable API and job contracts

## Scope

W3 establishes the bounded HTTP API, authenticated caller context, tenant/subject-scoped job creation and retrieval, idempotency semantics, durable local job lifecycle, and the operation contracts consumed by the Tinlance Agent Platform MCP gateway.

## Evidence reviewed

- Main commit: [30bd2e500195ec827c73471e9aaa0f8fec744306](https://github.com/LloydCoder/tinlance-web-intelligence/commit/30bd2e500195ec827c73471e9aaa0f8fec744306)
- CI run: [39141606311](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39141606311)
- Both Python 3.12 and Python 3.13 CI jobs completed successfully.
- The job repository enforces tenant/subject-scoped idempotency, rejects key reuse with a different payload fingerprint, and uses lease ownership to prevent stale workers from overwriting a newer worker's result.
- Platform operation manifests are client contracts; TWI does not host a competing remote MCP authority or make authorization decisions for the Platform.

## Boundary findings

- Agent Platform remains authoritative for identity, authorization, policy, approvals, governed tool execution, secrets, budgets, audit, and authoritative execution evidence.
- Agent OS remains responsible for orchestration and lifecycle; the SDK remains a typed client surface.
- World Intelligence remains responsible for canonical entities, events, relationships, temporal state, and cross-source intelligence.
- The SQLite job store is a single-node durability mechanism, not a production multi-replica queue.

## Residual limitations

- The successful W3 CI run proves repository-level checks at the recorded commit; it does not prove a production deployment, external identity provider, or production database is configured.
- W4 browser execution must remain isolated from the shared job store and direct network egress.
- W6 must provide and verify the production persistence, deployment, backup/recovery, operational and release controls required for private beta.

## Audit disposition

W3 was merged to `main` and its recorded Python 3.12/3.13 CI jobs passed. This is an implementation baseline, not a production-readiness certification.
