# Tinlyt Product UI Contract

**Product:** Tinlyt  
**Engineering identity:** Tinlance Web Intelligence (TWI)  
**Company:** Tinlance Limited  
**Tagline:** Discover sources. Verify claims. Preserve evidence.

This is the implementation contract for the customer-facing Tinlyt experience. It does not claim that a frontend is deployed or that any endpoint is available in a target environment. The API source, schemas, and tests remain authoritative. See the repository inventory in [F0 forensic audit](tinlyt-frontend-f0-audit.md).

## Product truth rules

1. Render only capabilities present in a verified API contract and enabled in the target environment.
2. Keep development fixtures visibly labelled and structurally separate from live API responses.
3. Successful retrieval means acquisition succeeded; it does not establish source truth.
4. Distinguish observed facts, source-attributed claims, inferences, conflicting observations, and unresolved information.
5. Never invent confidence scores, run stages, timings, costs, trace IDs, usage values, source records, or recovery actions.
6. Represent blocked, unsupported, failed, partial, empty, and successful states separately.
7. Preserve provenance and source attribution through navigation and exports.
8. Enforce tenant and subject scope on the server. Hiding a control in the UI is not authorization.
9. Never put secrets, raw credentials, or sensitive query parameters into logs, analytics, URLs, or error copy.
10. Do not describe an integrity-checked package as signed, immutable, or tamper-proof unless independently implemented and evidenced.

## Screen-to-contract map

| Screen | Contract | UI implementation boundary |
|---|---|---|
| Product landing | Product positioning | Distinguish available capabilities from roadmap items. |
| Workspace / investigation dashboard | Job and research APIs | No fabricated recent investigations or metrics in live mode. |
| New investigation | Job and browser request schemas | Expose only fields supported by the selected operation. |
| Investigation results | Job result and acquisition provenance | Link each finding to underlying observation/source; explain missing or incomplete evidence. |
| Evidence detail | `GET /v1/jobs/{job_id}/evidence` and `schemas/twi-evidence-package-v1.schema.json` | Export is permission/job-state dependent; package is not a truth verdict or digital signature. |
| Run detail | Durable job lifecycle and operation responses | Render only server-provided state, timings, logs and usage; omit unknown fields. |
| Collections and export | Evidence export; monitor APIs | Do not imply persisted research collections until an explicit contract exists. |
| API documentation / developer settings | Versioned schemas and API docs | Do not invent credential creation, rotation, quotas or integrations. |
| Tenant administration | Platform principal and scopes | Only verified operations; server-side authorization is mandatory. |
| Loading/empty/partial/blocked/failure states | Actual API and error contracts | Preserve distinctions and offer only documented recovery actions. |

## Existing contracts and boundaries

- **Jobs:** `POST /v1/jobs` supports `search`, `fetch`, and `browser`; requests are strict and idempotency is required. Read/cancel behavior must follow route implementation and authorization scopes.
- **Verification:** `POST /v1/research/verify` requires `twi:research:verify` and verifies bounded claims against captured source evidence. It must not be presented as an unqualified truth oracle.
- **Evidence export:** `GET /v1/jobs/{job_id}/evidence` requires a verified Platform principal with `twi:evidence:export` and a successful fetch job in that principal's tenant and subject scope. It returns a deterministic JSON package with captured bytes and versioned acquisition provenance. Integrity is not a digital signature and does not establish upstream truth.
- **Monitors:** `docs/api/monitors-v1.md` documents tenant/subject-scoped operations. The API stores definitions and enqueues explicit runs; Agent OS owns recurrence.
- **Authority:** Agent Platform owns identity, authorization, policy, approvals, secrets, budgets, audit and governed execution. Agent OS owns orchestration and lifecycle. TWI owns acquisition/evidence capture. World Intelligence owns canonical world state and cross-source temporal intelligence. TSIC owns cross-repository conformance.

## Design system baseline

- Precise, restrained, editorial enterprise UI; original Tinlyt identity, not a clone of another product.
- Neutral surfaces, high-contrast text, restrained accent; status never relies on color alone.
- Legible UI sans; optional restrained display face; monospace for identifiers, code and technical metadata.
- Persistent product navigation, compact page headers, readable content width, evidence adjacent to claims, responsive data tables.
- Shared accessible primitives: navigation, buttons, inputs, filters, tables, status labels, evidence cards, source preview, provenance timeline, log viewer, dialogs and state notices.
- Keyboard-operable interactions, visible focus, semantic landmarks, associated labels, announced status changes, contrast compliance and reduced-motion support.
- On narrow screens, preserve the primary task and evidence access; transform tables when needed rather than forcing page-wide overflow.

## Serial frontend phases

| Phase | Scope | Exit evidence |
|---|---|---|
| F0 | Repository, frontend, API, CI and risk inventory | Audit report reviewed; CI green on exact commit. |
| F1 | Design system, frontend workspace, app shell and frontend CI | Reproducible locked install, lint, JavaScript syntax validation, static security checks, tests/build, accessible responsive primitives. TypeScript typechecking is required once a TypeScript application is adopted; the current JavaScript syntax check must not be described as a typecheck. |
| F2 | Auth integration and typed API client | Approved identity integration; no browser-held privileged secrets; typed errors, idempotency and cancellation behavior tested. |
| F3 | Investigation submission and result experience | Authenticated search/fetch/browser submission; bounded live job polling; validated job-state display; safe result rendering; partial, blocked, empty and failure states; exact-commit CI and post-merge forensic review. |
| F4 | Run detail and lifecycle | Accurate server states, safe polling/cancel behavior, accessible logs where provided. |
| F5 | Evidence inspection and export | Provenance visible; authorized export only; invalid, unavailable and out-of-scope cases tested. |
| F6 | Claim verification | Uses captured citations and real verification response; no fabricated confidence or truth guarantee. |
| F7 | Collections and monitors | Monitors follow existing API; persistent collections remain gated on a real persistence contract. |
| F8 | Developer experience | API docs/examples generated or checked against canonical schemas; no invented credential controls. |
| F9 | Tenant administration and usage | Only APIs/scopes that exist; tenant boundaries tested; unsupported billing/admin features omitted. |
| F10 | Accessibility, security and resilience | Keyboard/screen-reader, contrast, responsive, XSS/content isolation, dependency and failure-path checks. |
| F11 | End-to-end release qualification | Exact-commit frontend/backend contract tests and deployment-specific smoke evidence; no unsupported beta/GA claims. |

Each phase is accepted only after its own criteria and forensic review pass. A scaffold, documentation-only merge, or successful compile is insufficient. Frontend CI does not close external TWI release gates.


## Implementation evidence ledger (updated 2026-10-20)

- **F0 — accepted:** repository inventory and API/authority/CI gap audit documented in `docs/product/tinlyt-frontend-f0-audit.md`. Main CI passed on `195bcf970e86537b2d9cdb7d1b96576bd7fb1476` (workflow run #39374414981).
- **F1 — merged:** PR #68 (`feat(frontend): establish Tinlyt F1 web foundation`), merge commit `020223f79b262ec10419a8683d0cde405891b292`.
- **F2 — merged with audit remediation:** PR #69, merge commit `7ac2e61118fcf55a37082532d64ccf5e97c7e09b`; PR #70 post-merge remediation, merge commit `6675f66107e7ec90688ef208505c65aee4858cd9`. The main-branch Frontend and repository CI checks on that commit passed (workflow runs #39379087145 and #39379087133). Production identity configuration and a live end-to-end identity/API test remain deployment gates.
- **F3 — implementation in progress:** authenticated submission and job status polling are being added on `feat/tinlyt-f3-investigations`. Do not mark F3 accepted until exact PR-head frontend and repository CI pass, changes are audited, and post-merge main checks pass.

This ledger records repository implementation evidence only. It does not claim a live deployment, production identity readiness, private-beta readiness, or GA readiness.
