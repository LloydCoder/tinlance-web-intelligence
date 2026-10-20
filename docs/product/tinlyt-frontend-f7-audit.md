# Tinlyt Frontend F7 — Monitor Workflows Forensic Audit

**Audit date:** 2026-10-20  
**Phase:** F7 — Monitor workflows  
**Status:** Accepted for repository implementation after exact-head Frontend and repository CI passed. Deployment certification remains separate.

## Scope and exact-commit evidence

F7 adds a customer-facing interface for the existing TWI monitor API. It does not add a monitor scheduler, duplicate Platform authorization, or fabricate a monitor-list endpoint.

- Implementation PR: [#80](https://github.com/LloydCoder/tinlance-web-intelligence/pull/80)
- Exact PR head: `f6903cb6429d271e1807ffb6a26d681014d4d6a8`
- Exact-head Frontend workflow: [#39396189878](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39396189878) — success.
- Exact-head repository CI: [#39396189912](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39396189912) — success.

## Contract reconciliation

The UI uses the existing documented operations in `docs/api/monitors-v1.md`:

- `POST /v1/monitors` — create with `Idempotency-Key` and optional bounded `policy.max_bytes`.
- `GET /v1/monitors/{monitor_id}` — explicit ID lookup.
- `POST /v1/monitors/{monitor_id}/runs` — enqueue one explicit run.
- `GET /v1/monitors/{monitor_id}/runs/{job_id}` — retrieve run state and results.
- `POST .../pause` and `POST .../resume` — pause/resume future explicit runs.
- `DELETE /v1/monitors/{monitor_id}` — destructive redaction, separately authorized.

The API is the authorization authority. The browser UI does not accept caller-supplied tenant/subject identities, infer access from hidden controls, or display target URLs returned by the API (the API does not return them).

## Forensic findings

### Accepted behavior

1. **No fabricated monitor list:** because no list endpoint exists, the user must create or enter a monitor ID. No localStorage or persistent client-side monitor history is introduced.
2. **Explicit run model:** “Run now” enqueues a single run. Recurrence is explicitly assigned to Agent OS, not the TWI frontend or monitor API.
3. **Run-state semantics:** bounded polling and explicit refresh display service-returned lifecycle state. The UI does not infer a change outcome before the service returns a result. First-baseline, changed, unchanged, and stale-capture outcomes remain distinct; digest changes are described as observations, not truth judgments.
4. **Idempotency:** create and run requests use stable pending idempotency keys across retry attempts; keys are cleared after a successful response or when the authorization session is cleared. This avoids accidental duplicate monitor/run creation after an ambiguous network result.
5. **Stale-session protection:** monitor, run, and mutation responses are discarded if the authorization-session epoch or selected monitor/run no longer matches the request.
6. **Destructive operation clarity:** deletion requires explicit confirmation and explains that target/policy/run summaries are redacted while an already accepted worker lease may finish. Pause is not misrepresented as cancellation of in-flight work.
7. **Input and response validation:** monitor and run IDs are bounded to the API client's identifier constraints. The typed API client validates monitor states, timestamp ordering, baseline digests, run payload identity, allowed result fields, digest format, and supported outcomes before rendering.
8. **Safe rendering:** values are rendered as text, not HTML. The interface does not display target URL query values, invent usage data, or claim source truth from digest changes.
9. **Access-denied and failure behavior:** server authorization remains authoritative and API errors are surfaced without fabricating a new monitor state.

### Remediation during implementation

- Aligned monitor ID input constraints with the API client's maximum identifier length.
- Fixed an HTML attribute quoting error found by the shell regression suite.
- Reconciled stale shell assertions as explicit idempotency keys and monitor run-history lookup were added.
- Added tests for malformed monitor/run responses, unsupported fields/outcomes, digest semantics, cross-resource response mismatch, idempotent create/run requests, disabled pre-auth controls, run lookup, duplicate active-run prevention, and monitor baseline refresh.

## Test and workflow evidence

The exact-head Frontend workflow passed locked dependency installation, lint/source hygiene, JavaScript syntax validation, TypeScript typechecking, dependency audit, static security checks, tests, and build.

The exact-head repository CI passed Python 3.12 and 3.13 quality/test jobs, isolated browser-container checks, and reproducible release-artifact/SBOM validation.

## Residual limitations and non-claims

- These workflows do not certify real-browser interaction or screen-reader behavior; those remain part of F10.
- No live deployment, production identity issuer/audience/CORS/reverse-proxy configuration, or end-to-end tenant authorization was certified by repository CI.
- Monitor creation does not imply recurring scheduling. Agent OS owns recurrence.
- Digest differences are acquisition observations, not factual truth assessments or proof that a source is authoritative.
- No private-beta or GA readiness is claimed.

## F7 exit decision

**Accepted for repository implementation.** The exact implementation commit passed both required workflows and the audit found no remaining F7 repository blocker. Proceed to F8 only after this audit/contract documentation is committed, its required CI is green, the PR is merged, and post-merge main CI is green.
