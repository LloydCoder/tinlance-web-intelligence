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
| Evidence detail | `GET /v1/jobs/{job_id}/evidence` and `schemas/twi-evidence-package-v1.schema.json` | Show versioned acquisition provenance; preserve exact response bytes for explicit download; package is not a truth verdict or digital signature. |
| Run detail | Durable job lifecycle and operation responses | Render only server-provided state, timings, logs and usage; omit unknown fields. |
| Collections and export | Evidence export; monitor APIs | Do not imply persisted research collections until an explicit contract exists. |
| API documentation / developer settings | Versioned schemas and API docs | Do not invent credential creation, rotation, quotas or integrations. |
| Tenant administration | Platform principal and scopes | Only verified operations; server-side authorization is mandatory. |
| Loading/empty/partial/blocked/failure states | Actual API and error contracts | Preserve distinctions and offer only documented recovery actions. |

## Existing contracts and boundaries

- **Jobs:** `POST /v1/jobs` supports `search`, `fetch`, and `browser`; requests are strict and idempotency is required. Read/cancel behavior must follow route implementation and authorization scopes.
- **Verification:** `POST /v1/research/verify` requires `twi:research:verify` and verifies bounded claims against captured source evidence. It must not be presented as an unqualified truth oracle.
- **Evidence export:** `GET /v1/jobs/{job_id}/evidence` requires a verified Platform principal with `twi:evidence:export` and a successful fetch job in that principal's tenant and subject scope. It returns a deterministic JSON package with captured bytes and versioned acquisition provenance. The client must validate the vendor media type, bounded-read and preserve the exact response bytes, validate the package schema/byte size/SHA-256, and download those same bytes only after explicit user action. Display requested/final URL hashes rather than inventing or exposing raw URLs absent from the contract. Integrity is not a digital signature and does not establish upstream truth.
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
| F4 | Run detail and lifecycle | Tenant-scoped job lookup; server-returned state and cancellation-request visibility; explicit cancellation confirmation; bounded polling/manual refresh; honest denied/failed/terminal states; no fabricated logs; exact-commit CI and forensic review. |
| F5 | Evidence inspection and export | Provenance and interpretation visible; strict vendor media type; bounded exact-byte preservation/download; schema/size/SHA-256 validation; unauthorized, unavailable, malformed, tampered and out-of-scope cases tested; no source-truth or signature claim. |
| F6 | Claim verification | Uses captured citations and real verification response; no fabricated confidence or truth guarantee. |
| F7 | Collections and monitors | Monitors follow existing API; persistent collections remain gated on a real persistence contract. |
| F8 | Developer experience | API docs/examples generated or checked against canonical schemas; no invented credential controls. |
| F9 | Tenant administration and usage | Only APIs/scopes that exist; tenant boundaries tested; unsupported billing/admin features omitted. |
| F10 | Accessibility, security and resilience | Keyboard/screen-reader, contrast including forced-colors, responsive, XSS/content isolation, dependency and failure-path checks; source-level checks reject unsafe HTML injection sinks. |
| F11 | End-to-end release qualification | Exact-commit frontend/backend contract tests and deployment-specific smoke evidence; no unsupported beta/GA claims. |

Each phase is accepted only after its own criteria and forensic review pass. A scaffold, documentation-only merge, or successful compile is insufficient. Frontend CI does not close external TWI release gates.


## Implementation evidence ledger (updated 2026-10-20)

- **F0 — accepted:** repository inventory and API/authority/CI gap audit documented in `docs/product/tinlyt-frontend-f0-audit.md`. Main CI passed on `195bcf970e86537b2d9cdb7d1b96576bd7fb1476` (workflow run #39374414981).
- **F1 — merged:** PR #68 (`feat(frontend): establish Tinlyt F1 web foundation`), merge commit `020223f79b262ec10419a8683d0cde405891b292`.
- **F2 — merged with audit remediation:** PR #69, merge commit `7ac2e61118fcf55a37082532d64ccf5e97c7e09b`; PR #70 post-merge remediation, merge commit `6675f66107e7ec90688ef208505c65aee4858cd9`. The main-branch Frontend and repository CI checks on that commit passed (workflow runs #39379087145 and #39379087133). Production identity configuration and a live end-to-end identity/API test remain deployment gates.
- **F3 — accepted:** PR #71 merged as `8bcbb893bf63c3e189959d214b7ac009228e8143`. Exact PR-head frontend quality gates and repository CI passed on `932e2437771d0c78c379ad13bc87cf3376c84892` (Frontend run #39382383072; CI run #39382383105). Post-merge main checks passed on `8bcbb893bf63c3e189959d214b7ac009228e8143` (Frontend run #39382794389; CI run #39382794200). Forensic closeout: `docs/product/tinlyt-frontend-f3-audit.md`.
- **F4 — accepted after audit remediation:** PR #73 merged as `b9706d190597263634b675fe8fc551063a9928e4`; post-merge race remediation PR #74 merged as `11b24f388190cba5d1068616dfe22ade9d5be386`. Exact-PR Frontend/repository CI passed for PR #73 (runs #39385212696/#39385212715) and PR #74 (runs #39385721542/#39385721523). Post-merge main Frontend/repository CI passed on the final F4 commit (runs #39386032110/#39386032112). Forensic closeout: `docs/product/tinlyt-frontend-f4-audit.md`. The audit found and fixed a stale status-GET versus cancellation-POST race. Real-browser concurrent-network tests and deployment identity/API checks remain later release gates.
- **F5 — accepted after forensic review:** PR #76 merged as `bab5e13fd67f219b8d25ab1baf2dcb61df3bdb8a`. Exact-PR Frontend/repository CI passed (runs #39388640468/#39388640435), and post-merge main Frontend/repository CI passed on the merge commit (runs #39389037708/#39389037674). Forensic closeout: `docs/product/tinlyt-frontend-f5-audit.md`. The client now preserves exact evidence response bytes, validates package schema/size/SHA-256, restricts media type, and clears stale evidence across session/job changes. Real-browser download interaction and deployment identity/API checks remain later release gates.
- **F6 — accepted after forensic review:** PR #78 merged as `806954d1e35a7c88258fea8835e95d968af7018b`. Exact-head Frontend/repository CI passed (runs #39393076817/#39393076842); post-merge main Frontend/repository CI passed (runs #39393404371/#39393404382). Forensic closeout: `docs/product/tinlyt-frontend-f6-audit.md`. The audit fixed missing form/citation event handlers, redacted source URL query/fragment values, aligned fetch/browser source wording, and added regression assertions. Real-browser interaction and deployment identity/API checks remain later release gates.
- **F7 — accepted after forensic review and post-merge CI:** PR #80 squash-merged as `9cbd40d5b708c8b7624e7b8ce4f5556ef5f32965`. Exact implementation-head Frontend/CI passed (#39396189878/#39396189912); post-merge main Frontend/CI passed on the merge commit (#39397034430/#39397034291). Forensic closeout: `docs/product/tinlyt-frontend-f7-audit.md`. The UI supports scoped monitor creation and ID-based lookup, explicit run enqueue/status refresh/history lookup, pause/resume, and confirmed deletion/redaction using the existing TWI monitor API. It does not invent monitor listing or recurrence; Agent OS owns recurrence. Monitor identifiers are bounded to the API contract and idempotency keys are preserved for safe retry. Live deployment/identity, browser-level interaction, and GA gates remain separate.
- **F8 — accepted after forensic review and post-merge CI:** PR #82 squash-merged as `42a6d8a06fe0eaf498ee0b7974b18dbd2e4def75`. Exact-head Frontend/repository CI passed (#39398651514/#39398651489); post-merge main Frontend/repository CI passed (#39399038723/#39399038686). Forensic closeout: `docs/product/tinlyt-frontend-f8-audit.md`. The copyable developer reference uses existing contracts and creates no credentials or API requests. Production identity/API configuration and live developer workflows remain separate deployment gates.
- **F9 — accepted after forensic review and follow-up remediation:** PR #84 merged as `5f56bab8aad5342bc246bb74fca8a027c674e95f`; follow-up PR #86 merged as `1d719567598bdadadc4eb60175343d345ed64e28`. Original F9 exact-head/post-merge Frontend and CI passed (#39400615438/#39400615424 and #39400964245/#39400964286). Follow-up exact-head Frontend/CI passed (#39401359521/#39401359455); post-merge main Frontend/CI passed (#39401917950/#39401918000). Forensic closeout: `docs/product/tinlyt-frontend-f9-audit.md`. Response dimension/period and page size are bound to the requested query. Tenant administration, credentials, and billing-provider controls remain omitted without verified contracts.

This ledger records repository implementation evidence only. It does not claim a live deployment, production identity readiness, private-beta readiness, or GA readiness.


## Security research references

- IETF [RFC 10017 — OAuth 2.0 for Browser-Based Applications](https://www.rfc-editor.org/rfc/rfc10017.html) (August 2026): public browser clients use Authorization Code + PKCE and protect the redirect flow against CSRF. Tinlyt continues to use the existing approved Platform identity integration; no parallel identity plane is introduced.
- OWASP [DOM-based XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html): untrusted content is inserted as text and DOM nodes are created explicitly; dynamic external links are restricted to HTTP(S), reject embedded credentials, and use `noopener noreferrer` plus `no-referrer`.
