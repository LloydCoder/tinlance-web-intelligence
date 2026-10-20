# Tinlyt Frontend F11 — Production Artifact and Release Qualification

**Phase:** F11  
**Status:** Exact-head Frontend and full repository CI passed; final acceptance awaits merge and post-merge CI.  
**Implementation head audited:** `0bfea2472d7f2f550eea7cedf9b331be98810f23`  
**Scope:** deterministic validation of the built static artifact and a loopback HTTP delivery smoke test.

## Implementation

The Frontend workflow builds `apps/web/dist`, then runs `npm run release-check`. The check verifies the Tinlyt title and entry assets, walks relative JavaScript imports, scans public runtime configuration for common privileged credential patterns, serves the built artifact over loopback HTTP, and validates asset status/MIME types, `X-Content-Type-Options: nosniff`, HTML cache policy, missing assets, encoded traversal and unsupported methods.

The workflow path filters now include `docs/product/tinlyt-frontend-*.md`, so phase-ledger and audit changes also rerun frontend checks instead of silently bypassing the frontend gate.

## Forensic findings and remediation

- The first exact-head Frontend run failed at the new artifact smoke check because the root URL `/` was assigned an expected MIME type from its empty URL extension, even though the test server correctly serves `index.html` as HTML.
- The assertion was corrected to treat `/` as `index.html` and require `text/html; charset=utf-8`. The assertion was not weakened.
- On the corrected implementation head, the release check and the complete Frontend workflow passed. The check also confirms the emitted JavaScript imports resolve to files within `dist`, and the encoded traversal probe cannot read the adjacent `apps/web/package.json`.

## Exact-head validation evidence

- Frontend workflow run [#39405667576](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39405667576) — success on implementation head `0bfea2472d7f2f550eea7cedf9b331be98810f23`.
- Full repository CI run [#39405667756](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39405667756) — success on the same head. Python 3.12, Python 3.13, browser-container isolation and reproducible artifact validation passed.
- The initial failed Frontend attempt was on the preceding head and was superseded by the corrected, green run above.

## Forensic boundaries

- The local server is a test harness; its headers do not prove production CDN, reverse-proxy or host configuration.
- Credential-pattern checks are regression guards, not secret scanning or proof arbitrary secrets cannot be embedded in assets.
- Static import inspection is not a full JavaScript bundler or runtime semantic analysis.
- Existing API-client tests and backend CI remain separate gates for schemas, identity, authorization and tenant isolation.
- This does not prove DNS/TLS, production CSP/security headers, live OAuth/API connectivity, deployment, private-beta readiness or GA readiness. TWI W15 gates remain independent.

## Exit criteria

- [x] Exact PR-head Frontend workflow passes including `npm run release-check`.
- [x] Exact PR-head full repository CI passes (Python 3.12/3.13, browser-container isolation and reproducible artifact validation).
- [x] Forensic review confirms missing assets, wrong MIME types, traversal attempts and invalid methods fail without weakening assertions.
- [ ] Post-merge Frontend and full repository CI pass on the exact main commit.
- [ ] Deployment-specific smoke, identity/API, security-header and operational evidence is tracked separately before any deployment or release-readiness claim.

## Acceptance decision

The repository implementation is provisionally qualified at the exact PR head. F11 will be accepted only after merge, post-merge Frontend/full-repository CI, and final audit-ledger reconciliation. External deployment qualification remains open until exercised against an explicitly configured target environment.
