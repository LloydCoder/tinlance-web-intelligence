# Tinlyt Frontend F11 — Production Artifact and Release Qualification

**Phase:** F11  
**Status:** Implementation submitted; acceptance requires exact-head and post-merge Frontend and full repository CI.  
**Scope:** deterministic validation of the built static artifact and a loopback HTTP delivery smoke test.

## Implementation

The Frontend workflow builds `apps/web/dist`, then runs `npm run release-check`. The check verifies the Tinlyt title and entry assets, walks relative JavaScript imports, scans public runtime configuration for common privileged credential patterns, serves the built artifact over loopback HTTP, and validates asset status/MIME types, `X-Content-Type-Options: nosniff`, HTML cache policy, missing assets, encoded traversal and unsupported methods.

## Forensic boundaries

- The local server is a test harness; its headers do not prove production CDN, reverse-proxy or host configuration.
- Credential-pattern checks are regression guards, not secret scanning or proof arbitrary secrets cannot be embedded in assets.
- Static import inspection is not a full JavaScript bundler or runtime semantic analysis.
- Existing API-client tests and backend CI remain separate gates for schemas, identity, authorization and tenant isolation.
- This does not prove DNS/TLS, production CSP/security headers, live OAuth/API connectivity, deployment, private-beta readiness or GA readiness. TWI W15 gates remain independent.

## Exit criteria

- [ ] Exact PR-head Frontend workflow passes including `npm run release-check`.
- [ ] Exact PR-head full repository CI passes (Python 3.12/3.13, browser-container isolation and reproducible artifact validation).
- [ ] Forensic review confirms missing assets, wrong MIME types, traversal attempts and invalid methods fail without weakening assertions.
- [ ] Post-merge Frontend and full repository CI pass on the exact main commit.
- [ ] Deployment-specific smoke, identity/API, security-header and operational evidence is tracked separately before any deployment or release-readiness claim.

## Acceptance decision

F11 repository implementation is accepted only after exact-head and post-merge CI is green and the audit is reconciled. External deployment qualification remains open until exercised against an explicitly configured target environment.
