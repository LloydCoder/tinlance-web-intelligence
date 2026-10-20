# Tinlyt Frontend F9 — Usage and Tenant Administration Forensic Audit

**Phase:** F9 — Usage and tenant administration  
**Status:** Implementation submitted; acceptance is pending exact-head Frontend and full repository CI, forensic review, and post-merge checks.

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
- **Post-merge follow-up (PR #86):** forensic comparison found that a self-consistent response could still report a different dimension or period from the request. The follow-up now binds response dimension and timestamp to the original query and rejects event counts above the requested page limit. Regression tests cover mismatched response dimension and period; final acceptance remains pending exact-head and post-merge CI.
- Session epoch checks prevent old responses from rendering after identity changes; usage results and cursors are not persisted in browser storage.

## Acceptance gates

1. Exact-head Frontend workflow passes locked install, lint, syntax check, TypeScript, dependency audit, static security, tests, and build.
2. Exact-head full repository CI passes Python 3.12/3.13, browser isolation, and reproducible artifact validation.
3. Review usage schema validation, error/403/503 handling, session clearing, and pagination.
4. Post-merge Frontend and full repository CI pass on main.
5. Live authorization and entitlement-resolver behavior remain deployment gates.

## Non-claims

This phase does not implement tenant administration because no verified tenant-administration API contract was identified. It does not certify live identity configuration, deployment, billing-provider integration, private-beta readiness, or GA readiness.
