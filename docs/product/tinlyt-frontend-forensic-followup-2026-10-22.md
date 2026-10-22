# Tinlyt Frontend Forensic Follow-up — Navigation and Documentation Integrity

**Audit date:** 2026-10-22  
**Scope:** current `main` at `cf7ae86f154a148ce27fab13b588dfd8fdd56861`; workspace navigation behavior and frontend audit-document chronology.  
**Method:** source inspection of the workspace document, `src/main.js`, frontend shell tests, frontend workflow, production release-check script, and all 22 current workspace/marketing HTML documents.

## Findings and remediation

### 1. Workspace navigation state did not follow deep links or browser history — fixed in this change

The workspace navigation previously updated the active item and breadcrumb only when a user clicked a navigation link. Opening a direct URL such as `/app#evidence`, refreshing on a non-overview section, or using browser Back/Forward could leave the active navigation item and breadcrumb inconsistent with the visible hash target. The prior label also copied decorative icon text into the breadcrumb.

The fix makes the hash the source of truth, synchronizes on initial load and `hashchange`, sets exactly one `aria-current="page"`, toggles active styling consistently, and removes aria-hidden decorative icons before writing the breadcrumb. A source-level regression test covers initial hash handling, hashchange, active state and breadcrumb labeling.

### 2. The F0 audit could be mistaken for current state — fixed in this change

`tinlyt-frontend-f0-audit.md` correctly preserves what was observed at F0 but its executive finding is historically stale after subsequent frontend phases. Added an explicit dated notice that identifies it as a pre-frontend snapshot and directs readers to current source, contract and later phase audits. Historical findings remain unchanged for traceability.

## Repository checks performed during this audit

- Confirmed the current repository has no open pull requests at audit start.
- Confirmed latest known main commit was `cf7ae86f154a148ce27fab13b588dfd8fdd56861`, with the latest repository CI and frontend CI previously reported successful on that head.
- Enumerated 22 workspace and marketing HTML documents: each had an English document language, a non-empty page title, no duplicate IDs, no missing same-page fragment targets, and retained the explicit `noindex, nofollow` launch gate.
- Inspected `apps/web/vercel.json`: public route rewrites and security headers are defined. The configuration intentionally does not add a backend proxy or identity issuer configuration; those require approved deployment infrastructure and must not be fabricated in frontend code.
- Inspected `.github/workflows/frontend.yml`: locked dependency install, lint, JS syntax, TypeScript, npm audit, static security, tests, build, production artifact HTTP smoke check, and pinned Playwright/Chromium browser accessibility checks are included.
- The browser/release checks exercise built artifacts. They do not prove live production authentication, API reachability, hosting CSP correctness, manual screen-reader conformance, or private-beta/GA readiness.

## Release constraints

- Keep all interactive API controls disabled when approved Platform identity and TWI deployment configuration are absent.
- Do not introduce mock results as live runs, privileged tokens in browser storage, unsupported API routes, a broad API origin allowlist, or a fabricated backend proxy.
- Keep every marketing route `noindex, nofollow` until launch approval is explicitly recorded.
- Treat green CI as source/build quality evidence only; deployment, security, privacy, operational readiness, and consumer conformance remain separately evidenced gates.

## Acceptance

- [x] Navigation derives active state and breadcrumb from the URL hash.
- [x] Regression test added for deep links/history synchronization.
- [x] F0 document marked as historical.
- [x] Frontend quality gates passed on PR head `b8542e96de36304a5984dbfed622b0fde844638c` (run [#39733743096](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39733743096)).
- [x] Full repository CI passed on the same PR head, including Python 3.12/3.13, browser container isolation, and reproducible release artifact validation (run [#39733742966](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39733742966)).
- [ ] Changes merged only after checks pass.
- [ ] Post-merge Frontend and repository CI pass on the exact main commit.
