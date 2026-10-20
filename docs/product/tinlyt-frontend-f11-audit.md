# Tinlyt Frontend F11 — Production Artifact and Release Qualification

**Phase:** F11  
**Scope:** reproducible build-artifact validation and HTTP delivery smoke checks for the static Tinlyt frontend.

## Implementation

The frontend workflow builds `apps/web/dist` and runs `npm run release-check`. The release check:

1. Confirms the built page identifies Tinlyt and references the runtime configuration and application entry point.
2. Walks the emitted JavaScript module graph and verifies relative imports resolve inside the build output.
3. Rejects common privileged credential patterns in the public runtime configuration.
4. Starts an ephemeral loopback HTTP server against the built output and requests each local HTML asset reference.
5. Checks successful asset status, content types, `X-Content-Type-Options: nosniff`, missing-asset 404 behavior, and path traversal rejection.

This gate is deterministic and runs without production credentials or network access to customer systems.

## Validation boundaries

- Existing unit/contract tests exercise API-client request/response validation and failure handling; backend CI separately validates the Python API contracts and tenant/security boundaries.
- The artifact smoke gate is **not** a real-browser E2E suite and does not prove the production reverse proxy, CSP, OAuth issuer, DNS/TLS, live API connectivity, deployment configuration, or live authorization.
- No deployment URL or approved live-test identity was supplied in this repository workflow. Production smoke evidence must be collected in the target environment before a deployment/private-beta/GA readiness claim.
- External TWI W15 gates remain independent; frontend CI does not close them.

## Exit criteria

- [ ] Exact PR-head Frontend workflow passes including the new artifact smoke gate.
- [ ] Exact PR-head full repository CI passes (Python 3.12/3.13, browser isolation, and reproducible artifact checks).
- [ ] Forensic review confirms the artifact graph and runtime configuration checks are effective.
- [ ] Post-merge Frontend and full repository CI pass on main.
- [ ] Deployment-specific live smoke, identity/API, security-header, and operational readiness evidence is recorded separately.

## Acceptance decision

F11 repository implementation is accepted only after the exact-head and post-merge CI evidence above is green. Live deployment qualification remains an external gate until exercised against an explicitly configured environment.
