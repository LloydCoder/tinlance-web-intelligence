# Tinlyt Frontend F6 — Claim Verification Forensic Audit

**Audit date:** 2026-10-20  
**Phase:** F6 — Claim verification  
**Status:** Implementation merged; post-merge repository CI is pending at the time of this draft. Do not treat F6 as closed until the gate below is green.

## Scope and exact-commit evidence

F6 connects the claim-verification panel to the existing TWI research verification endpoint. It compares submitted quotes with captured source text and must not imply that a citation match establishes factual truth.

- Implementation PR: [#78](https://github.com/LloydCoder/tinlance-web-intelligence/pull/78)
- Exact PR head: `b9c437552a26098b05954af55643599c71c159b6`
- Merge commit: `806954d1e35a7c88258fea8835e95d968af7018b`
- Exact-head Frontend workflow: [#39393076817](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39393076817) — success.
- Exact-head repository CI: [#39393076842](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39393076842) — success.
- Post-merge Frontend workflow: [#39393404371](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39393404371) — success.
- Post-merge repository CI: [#39393404382](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39393404382) — pending at draft time; verify before accepting this audit.

## Forensic findings and remediation

### 1. Missing event wiring — fixed

The initial F6 implementation contained citation-row and report-rendering functions but omitted the form-submit and add/remove citation event handlers. The panel therefore looked implemented but could not submit a verification request. Added:
- Add-citation event handler with a maximum of four citations.
- Delegated remove-citation handling that preserves at least one citation row.
- Form submission with browser constraint validation, the existing typed `verifyResearch` API client, disabled-in-flight controls, explicit status messaging, and session-epoch checks.
- Stale responses from an earlier authorization session are discarded; sign-out clears the displayed report and form values.

A new shell regression test checks that these controls are wired to the API and that session and product-truth guards remain present.

### 2. Source URL privacy — fixed

The first implementation rendered source URLs including query strings and fragments. These can contain signed parameters or other sensitive values. The UI now displays only the URL origin and path when a query or fragment exists, omits those values, and suppresses the direct link in that case. Direct links are rendered only for validated HTTP(S) URLs without embedded credentials or query/fragment values, with `rel="noopener noreferrer"`.

### 3. API contract alignment — fixed

The initial form copy implied citations must reference fetch jobs only, while the existing verifier supports successful fetch **or browser** jobs. Copy and dynamic labels now match the supported API contract. The client continues to validate response shape, status/count consistency, source URL scheme/authority, citation match status, and the explicit `factual_truth_assessed: false` invariant.

### 4. Safe DOM rendering

Claim statements, quotes, identifiers, metadata, and source details are rendered using text nodes and `textContent`; captured or returned content is not interpreted as HTML. This follows the [OWASP DOM-based XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html), which recommends safe text sinks such as `textContent` rather than inserting untrusted values into HTML.

## Test evidence

The exact-head Frontend workflow passed its locked dependency install, lint/source hygiene, JavaScript syntax check, TypeScript typecheck, dependency audit, static security checks, tests, and build. The full repository CI passed its Python 3.12 and 3.13 quality/test jobs, browser container isolation checks, and reproducible release artifact validation on the exact PR head. Post-merge Frontend passed. The post-merge full repository CI result must be verified before the exit decision is final.

## Residual limitations and non-claims

- Shell regression tests do not replace real-browser interaction, keyboard/screen-reader, and concurrent-network tests; those remain in F10.
- Production identity-provider settings, the same-origin `/api/twi` reverse proxy, deployed audience/CORS configuration, and end-to-end authorization have not been certified by these repository workflows.
- Citation matching establishes only whether the submitted quote appears in captured text. It does not prove the claim is true, the source is authoritative, or the capture is digitally signed or tamper-proof.
- No production deployment, private-beta readiness, or GA readiness is claimed.

## F6 exit decision

**Pending final post-merge CI verification.** Accept F6 for repository implementation only after the post-merge repository CI linked above is green, this audit is reconciled with the final run, and the audit closeout is merged.