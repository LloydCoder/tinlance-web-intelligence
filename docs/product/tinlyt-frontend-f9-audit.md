# Tinlyt Frontend F9 — Usage and Tenant Administration Forensic Audit

**Phase:** F9 — Usage and tenant administration  
**Status:** Accepted for repository implementation after exact-head and post-merge Frontend/repository CI passed.

## Contract basis

The only verified customer-facing administrative/usage capability in this phase is `GET /v1/usage`, documented in `docs/api/usage-v1.md` and implemented in `src/tinlance_web_intelligence/api/http/routes/usage.py`.

- Requires a verified Platform principal and `twi:usage:read` or `twi:usage:read:any`.
- Tenant and subject scope come from the verified principal; callers cannot supply identity fields.
- Query inputs are dimension, timezone-aware ISO-8601 period start, bounded page limit, and an opaque cursor.
- The response includes committed usage, nullable quota/remaining/plan fields, and payload-free event facts.
- When entitlement resolution is configured but unavailable or the dimension is not configured, the backend can return HTTP 503. Missing scope returns 403.
- The endpoint reports usage facts; it is not invoice, payment settlement, tax, refund, or provider billing status.

## Implementation

- Add typed usage query/event/response models and strict response validation.
- Add a tenant-scoped Usage interface with dimension, period, bounded page size, and optional cursor.
- Display only server-returned committed usage, configured quota/remaining allowance, plan metadata when present, and payload-free events.
- Support cursor pagination without persisting cursor or usage results in browser storage.
- Clear displayed usage on sign-out and discard stale responses from earlier authorization sessions.
- Update the in-app developer reference to include the canonical usage endpoint.

## Security and truth boundaries

- No caller-supplied tenant or subject IDs, tenant switching, role editor, credential provisioning, API key rotation, or payment controls are introduced.
- The UI does not infer quota when the backend returns null and distinguishes missing entitlement state from a numeric zero.
- Usage event output is validated against the requested dimension and period; pagination metadata and counts are checked for consistency.
- No invoice balance or payment settlement claim is made.


## Forensic findings and remediation

- The first Frontend workflow exposed an overbroad negative assertion: it treated truthful explanatory copy about invoice balances as an unsupported invoice UI. The test now checks for actual unsupported control IDs instead of rejecting accurate boundary language.
- Review identified a stale-request cleanup race: a request from a prior auth-session epoch could reset the shared loading state after sign-out/re-authentication. The finally block now mutates loading/control state only when its captured session epoch still matches.
- The response parser rejects mismatched event dimension/period, inconsistent quota arithmetic, invalid event fields, and invalid has_more/cursor combinations.
- Session epoch checks prevent old responses from rendering after identity changes; usage results and cursors are not persisted in browser storage.

## Exact-commit workflow evidence

- Implementation PR: [#84](https://github.com/LloydCoder/tinlance-web-intelligence/pull/84)
- Final implementation head: `63fe7a798c21bfd807a3d1fd79fc6bfe6886bb8b`
- Exact-head Frontend workflow: [#39400615438](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39400615438) — success.
- Exact-head full repository CI: [#39400615424](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39400615424) — success.
- Squash merge commit: `5f56bab8aad5342bc246bb74fca8a027c674e95f`.
- Post-merge Frontend workflow on main: [#39400964245](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39400964245) — success.
- Post-merge full repository CI on main: [#39400964286](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39400964286) — success.

## Forensic acceptance

- Audited the typed usage parser against the canonical usage route and `docs/api/usage-v1.md`.
- Confirmed that quota arithmetic, event period/dimension, event counts, and cursor-state invariants are validated before rendering.
- Confirmed the frontend displays only payload-free event facts and server-returned usage/entitlement fields, with no inferred invoice/payment values.
- Corrected the first failing frontend regression assertion to target unsupported controls rather than truthful billing-boundary copy; rerun exact-head Frontend CI passed.
- Fixed stale-session cleanup so a prior request cannot reset the current session's usage loading state.
- Both Python matrix jobs, browser container isolation, reproducible artifact validation, and Frontend quality gates passed on the exact implementation head; post-merge main CI also passed.

## F9 exit decision

**Accepted for repository implementation.** The exact PR head and post-merge main commit passed all required Frontend and repository workflows. No remaining F9 repository blocker was found. Tenant administration beyond the existing usage endpoint remains intentionally unimplemented because no corresponding API contract was verified.

## Acceptance gates

1. Exact-head Frontend workflow passes locked install, lint, syntax check, TypeScript, dependency audit, static security, tests, and build.
2. Exact-head full repository CI passes Python 3.12/3.13, browser isolation, and reproducible artifact validation.
3. Review usage schema validation, error/403/503 handling, session clearing, and pagination.
4. Post-merge Frontend and full repository CI pass on main.
5. Live authorization and entitlement-resolver behavior remain deployment gates.

## Non-claims

This phase does not implement tenant administration because no verified tenant-administration API contract was identified. It does not certify live identity configuration, deployment, billing-provider integration, private-beta readiness, or GA readiness.
