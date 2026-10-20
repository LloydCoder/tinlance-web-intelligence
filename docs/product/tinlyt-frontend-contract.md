# Tinlyt Product UI Contract

**Product:** Tinlyt  
**Engineering identity:** Tinlance Web Intelligence (TWI)  
**Company:** Tinlance Limited  
**Tagline:** Discover sources. Verify claims. Preserve evidence.

This document is the implementation contract for the Tinlyt customer-facing experience. It does not claim that a frontend exists or that any endpoint is deployed. The API contract and tests remain authoritative.

## Product truth rules

1. Render only capabilities that are present in a verified API contract and enabled in the target environment.
2. Keep development fixtures visibly labelled and structurally separate from live API responses.
3. A successful retrieval means acquisition succeeded; it does not establish source truth.
4. Distinguish observed facts, source-attributed claims, inferences, conflicting observations, and unresolved information.
5. Never invent confidence scores, run stages, timings, costs, trace IDs, usage values, source records, or recovery actions.
6. Represent blocked, unsupported, failed, partial, empty, and successful states separately.
7. Preserve provenance fields and source attribution through navigation and exports.
8. Enforce tenant and subject scope on the server. Hiding a control in the UI is not authorization.
9. Never put secrets, raw credentials, or sensitive query parameters into logs, analytics, URLs, or error copy.
10. Do not describe an integrity-checked package as signed, immutable, or tamper-proof unless those properties are independently implemented and evidenced.

## Screen-to-contract map

| Screen | Current evidence-backed contract | UI implementation boundary |
|---|---|---|
| Product landing page | Product positioning only | Marketing copy must distinguish available capabilities from roadmap items. |
| Workspace / investigation dashboard | Existing job and research APIs must be mapped from route definitions before wiring | No fabricated recent investigations or metrics in live mode. |
| New investigation | Existing research/job request schema must be inspected before form implementation | Simple and advanced modes may expose only fields supported by the selected operation. |
| Investigation results | Job result and acquisition provenance contracts | Keep each finding linked to the underlying observation/source; explain missing or incomplete evidence. |
| Evidence detail | GET /v1/jobs/{job_id}/evidence for eligible successful fetch jobs; schemas/twi-evidence-package-v1.schema.json | Export availability is permission- and job-state-dependent; evidence package is not a truth verdict or digital signature. |
| Run detail | Durable job lifecycle and operation responses; inspect schemas before displaying exact states | Render only server-provided state, timing, retries, logs, and usage. Unknown fields stay absent, not guessed. |
| Collections and export | Evidence export API exists; collection persistence contract must be confirmed separately | Do not imply reusable persisted collections until an API and tenant-scoped tests exist. |
| API documentation and developer settings | Versioned schemas and API docs; credential management contract must be inspected | Do not invent credential creation, rotation, quota, or integration controls. |
| Tenant administration | Platform principal and authorization boundary | Admin operations require server-side scopes; only verified endpoints can be exposed. |
| Empty/loading/partial/blocked/failure states | Derived from actual request, job, and error contracts | State labels must preserve distinctions and offer recovery only when the API documents it. |

## Existing backend contracts to preserve

- **Monitors:** docs/api/monitors-v1.md. Create/run requests require idempotency keys. The API stores definitions and enqueues explicit capture jobs; Agent OS owns recurrence. Results are bounded observations, not truth judgments.
- **Evidence export:** docs/api/evidence-packages-v1.md. GET /v1/jobs/{job_id}/evidence requires a verified Platform principal with twi:evidence:export and a successful fetch job in the principal's tenant and subject scope. It returns a deterministic JSON package with captured bytes and versioned acquisition provenance. Package integrity is not a digital signature and does not establish upstream truth.
- **Authority boundary:** Agent Platform owns identity, authorization, policy, approvals, secrets, budgets, and governed execution. Agent OS owns orchestration and lifecycle. TWI owns acquisition and evidence capture. World Intelligence owns canonical world state and cross-source temporal intelligence. TSIC owns cross-repository conformance.

## Design system baseline

- **Visual character:** precise, restrained, editorial, enterprise-grade; original Tinlyt identity, not a clone of Linear, Perplexity, Palantir, Vercel, or Browserless.
- **Color:** neutral surfaces and high-contrast text; one restrained Tinlance accent; status must never rely on color alone.
- **Typography:** highly legible UI sans for interface and data; optional restrained editorial face for display headings; monospace only for identifiers, code, and technical metadata.
- **Layout:** persistent product navigation, compact page headers, readable content width, evidence panel adjacent to claims, responsive tables with accessible alternatives.
- **Components:** navigation, buttons, inputs, filters, data tables, status labels, evidence cards, source preview, provenance timeline, log viewer, dialogs, inline notices, and empty/loading/error states.
- **Accessibility:** keyboard-operable interactions, visible focus, semantic landmarks, associated labels, announced status updates, contrast compliance, reduced-motion support, and no color-only status encoding.
- **Responsive behavior:** preserve primary task and evidence access on narrow screens; tables may transform to stacked records rather than overflow the viewport.

## Frontend delivery sequence

1. **F0 — Contract inventory:** enumerate routes, request/response schemas, scopes, error shapes, and test coverage from the current source tree.
2. **F1 — Design-system foundation:** tokens, app shell, navigation, accessible primitives, responsive behavior, and visible fixture/live mode separation.
3. **F2 — Investigate vertical slice:** submit a supported request, observe real lifecycle states, display source-backed results, and cover partial/blocked/failure paths.
4. **F3 — Evidence vertical slice:** inspect provenance and export through the authorized endpoint; test out-of-scope and unavailable cases.
5. **F4 — Runs and Collections:** render verified run data; add persisted collections only after the required contract exists.
6. **F5 — Developer and Admin:** expose only implemented APIs and scopes; mask credentials and verify authorization boundaries.
7. **F6 — Release qualification:** component and integration tests, accessibility checks, responsive tests, dependency/security checks, exact-commit CI, and deployment-specific smoke evidence.

Each phase must be accepted against exact code and test evidence. A documentation merge or successful build alone is not completion. This contract is a starting point for implementation and must be updated when code inspection reveals more specific endpoint behavior.
