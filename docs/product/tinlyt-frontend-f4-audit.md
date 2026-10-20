# Tinlyt Frontend F4 — Run Lifecycle Forensic Audit

**Audit date:** 2026-10-20  
**Phase:** F4 — Run detail and lifecycle  
**Status:** Accepted for repository implementation; production integration remains a separate deployment gate.

## Scope and evidence

F4 added tenant-scoped run lookup, cancellation requests, cancellation-request visibility, bounded polling, manual refresh, terminal-state semantics, responsive controls, and regression assertions.

Implementation:
- PR #73 — `feat(frontend): implement Tinlyt F4 run lifecycle`
- Initial merge commit: `b9706d190597263634b675fe8fc551063a9928e4`
- PR #74 — `fix(frontend): prevent stale run state during cancellation`
- Remediation merge commit: `11b24f388190cba5d1068616dfe22ade9d5be386`

Exact-commit validation:
- PR #73 Frontend workflow: run [#39385212696](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39385212696) — success.
- PR #73 repository CI: run [#39385212715](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39385212715) — success.
- PR #74 Frontend workflow: run [#39385721542](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39385721542) — success.
- PR #74 repository CI: run [#39385721523](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39385721523) — success.
- Post-merge Frontend on `11b24f388190cba5d1068616dfe22ade9d5be386`: run [#39386032110](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39386032110) — success.
- Post-merge repository CI on the same commit: run [#39386032112](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39386032112) — success.

## Forensic findings and disposition

### Accepted behavior

1. Run lookup uses the existing typed TWI API client. Job IDs are validated; the browser does not submit tenant or subject identifiers. The API remains authoritative for authentication, tenant/subject scope, and authorization.
2. Cancellation is a request, not a client-side state mutation. The UI asks for confirmation, calls the existing cancellation endpoint, and does not report completion until TWI returns the terminal `cancelled` status.
3. `cancel_requested` is displayed separately from terminal job status. A job may remain queued/running after cancellation is requested.
4. Polling is bounded (at most 20 intervals of 1.5 seconds), duplicate poll loops are guarded, and a manual refresh remains available after polling stops. Live controls are disabled while unauthenticated.
5. The public job contract does not expose a log collection; the UI does not synthesize logs, trace IDs, costs, or timings.
6. Job fields and operation results are rendered from the service response. Successful acquisition is not represented as proof of source truth.

### Defect found and fixed during the post-implementation audit

The first F4 implementation allowed a status GET that started before cancellation to finish after the cancellation POST and overwrite the newer cancellation response in the UI. PR #74 closes this race by suppressing status-read rendering while cancellation is in flight, discarding in-flight GET results if cancellation has started, and disabling manual refresh during polling/cancellation. Regression assertions cover the guard and control state. Both exact-PR workflows and both post-merge main workflows passed.

### Residual limitations (not represented as completed features)

- Automated tests assert rendered markup and source-level behavior; they do not yet constitute a real-browser end-to-end interaction test of concurrent network timing.
- Production identity-provider configuration, live authorization/scope behavior, and a deployed browser-to-API smoke test are not proven by repository CI. These remain deployment-specific gates.
- The frontend does not claim persisted run history, log retrieval, or a cancellation guarantee beyond the server's reported state.

## F4 exit decision

**Accepted for repository implementation.** The initial feature, forensic remediation, exact-commit Frontend/repository CI, and post-merge main workflows all passed. The identified stale-response race was fixed before proceeding. Browser-level interaction and deployment certification remain explicit later-phase/release gates, not implied by this acceptance.
