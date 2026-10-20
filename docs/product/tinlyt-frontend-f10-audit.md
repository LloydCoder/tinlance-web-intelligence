# Tinlyt Frontend F10 — Accessibility, Security, and Resilience Forensic Audit

**Phase:** F10  
**Implementation commit audited:** `4766230685a0a9d4e2a0dc93c209b9c9b7b1636c`  
**Audit date:** 2026-10-20
**Status:** Accepted after exact-commit Frontend and full repository CI passed.  
**Scope:** accessibility affordances, unsafe DOM injection sinks, static frontend security gates, and regression tests.

## Evidence inspected

- `apps/web/index.html`, `apps/web/styles.css`, `apps/web/investigation.css`
- `apps/web/src/main.js`, `apps/web/src/app/runtime.ts`, `apps/web/src/api/*`
- `apps/web/scripts/security-check.mjs`, `apps/web/scripts/lint.mjs`, `apps/web/tests/*`
- `.github/workflows/frontend.yml` and the main-branch Frontend run for the implementation commit.

## Findings and controls

- The app declares document language and viewport, provides a skip link and labelled primary navigation, and uses a focusable main landmark.
- CSS includes visible focus treatment, narrow viewport layouts, reduced-motion handling and forced-colors focus improvements.
- Live job controls are disabled unless the approved identity/runtime configuration is valid; absent identity settings fail closed.
- Untrusted result content is rendered through text nodes and explicitly created DOM elements. The security gate rejects dynamic code execution, `document.write`, `innerHTML`/`outerHTML` assignment, `insertAdjacentHTML`, inline event handlers, JavaScript URLs, remote resource loads, and common credential patterns.
- Dynamic external links are constrained to safe HTTP(S) URLs, omit query/fragment data in display copy, and use `noopener noreferrer` with a no-referrer policy.
- Tests assert key accessibility, runtime fail-closed, result-rendering, URL privacy, session-epoch and lifecycle invariants.

## Forensic limitation

These checks are source-level and automated regression controls, not a substitute for manual screen-reader testing, a browser accessibility tree audit, penetration testing, or deployment-specific CSP/header verification. No live production deployment was supplied as evidence in this phase.

## CI evidence

- Frontend workflow for the audited main commit: [run #39403242150](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39403242150) — success.
- Full repository CI for the same main commit: [run #39403241773](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39403241773) — success (Python 3.12/3.13 and browser isolation jobs completed successfully).

## Exit decision

**Accepted.** Frontend and full repository CI passed on the audited main commit. Source-level controls are evidenced; manual assistive-technology review and deployment-specific checks remain external release gates. F11 must add a repeatable production-artifact smoke gate. No claim of production deployment, full WCAG conformance, private-beta readiness, or GA readiness is made.
