# Tinlyt Frontend F3 — Forensic Closeout Audit

**Status:** Accepted for repository implementation after pre-merge and post-merge CI passed.  
**Repository:** `LloydCoder/tinlance-web-intelligence`  
**Product:** Tinlyt  
**Phase:** F3 — investigation submission and source-backed results  
**PR:** [#71](https://github.com/LloydCoder/tinlance-web-intelligence/pull/71)  
**Merge commit:** `8bcbb893bf63c3e189959d214b7ac009228e8143`

## Evidence reviewed

- PR-head Frontend workflow #39382383072: success on `932e2437771d0c78c379ad13bc87cf3376c84892`.
- PR-head repository CI workflow #39382383105: success on `932e2437771d0c78c379ad13bc87cf3376c84892`; Python 3.12, Python 3.13, browser container isolation, and reproducible release artifact validation all passed.
- Post-merge Frontend workflow #39382794389: success on `8bcbb893bf63c3e189959d214b7ac009228e8143`.
- Post-merge repository CI workflow #39382794200: success on `8bcbb893bf63c3e189959d214b7ac009228e8143`; all four jobs passed.
- Changed-file review covered the application markup, investigation stylesheet, static build and source/security checks, request builder, application behavior, tests, frontend contract, and F0 audit reconciliation.

## Implementation findings

1. The investigation form submits only the existing supported `search`, `fetch`, and `browser` job kinds through the existing typed `TwiApiClient`.
2. Live controls remain disabled until the approved Platform identity callback succeeds. The frontend does not create its own identity or authorization authority.
3. Search payloads are bounded and normalized; fetch URLs require HTTP(S); browser URLs require HTTPS on port 443; embedded credentials are rejected before submission. Backend policy remains authoritative.
4. Job state is retrieved from TWI using the returned job ID. Polling is bounded, manual refresh remains available for active jobs, and the UI does not claim completion when the service has not returned a terminal state.
5. Search results are rendered as source cards only from returned result records. Fetch responses show source URL, retrieval metadata, content digest, description, and a bounded captured-text preview when those fields are present.
6. Untrusted values are rendered using `textContent` and explicit DOM elements. Dynamic source links are limited to HTTP(S), reject embedded credentials, and use `rel="noopener noreferrer"` and `referrerPolicy="no-referrer"`.
7. Results and errors do not invent source counts, confidence, timestamps, status, or factual truth. A successful acquisition is explicitly not presented as proof of truth.
8. The static build copies the new stylesheet; frontend checks cover TypeScript, JavaScript syntax, source hygiene, static security, request validation, terminal states, and build output.

## Remaining scope and non-claims

- F3 does not provide cancellation controls, a persistent run history, a dedicated evidence-export view, claim verification UI, monitor management UI, tenant administration, production deployment, private beta, or GA. These belong to later phases and remain subject to their own gates.
- No production identity-provider credentials or live deployment smoke test were supplied in this repository workflow. CI proves repository behavior, not deployment-specific authentication or live service availability.
- The raw JSON fallback remains for operation result shapes not yet given a dedicated renderer. The UI does not treat arbitrary result fields as verified claims.
- F11 release qualification must still collect deployment-specific E2E, privacy, security, SLO, and operational evidence before any private-beta/GA claim.

## Security research

- IETF [RFC 10017 — OAuth 2.0 for Browser-Based Applications](https://www.rfc-editor.org/rfc/rfc10017.html) (August 2026) documents browser public-client requirements including Authorization Code + PKCE and redirect-flow CSRF protections.
- OWASP [DOM-based XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html) recommends text-oriented DOM sinks such as `textContent` and explicit element construction for untrusted data.

## Acceptance decision

**F3 is complete for repository implementation.** All PR-head and post-merge frontend/repository CI checks passed, and the changed files were reviewed against the F3 contract. Proceed to F4 only after this closeout documentation change also passes CI and is merged. This decision does not imply production deployment, private-beta readiness, or GA readiness.
