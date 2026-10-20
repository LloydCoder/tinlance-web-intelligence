# Tinlyt Frontend F8 — Developer Experience Forensic Audit

**Phase:** F8 — Developer experience and API reference  
**Status:** Implementation submitted; acceptance is pending exact-head Frontend and repository CI plus post-merge checks.  
**Scope:** customer-facing, copyable examples aligned to existing TWI HTTP contracts.

## Implementation

- Adds a Developer navigation target and in-app reference for the supported jobs, evidence, verification and monitor API families.
- Provides copyable curl templates for job creation and claim/citation verification. The page sends no API requests and creates no credentials.
- States the Platform-issued bearer-token boundary, required idempotency behavior, source-truth limitation, and deployment dependency on a same-origin reverse proxy or explicitly approved HTTPS API origin.
- Uses canonical `docs/api/jobs-v1.md`, `docs/api/evidence-packages-v1.md`, and `docs/api/monitors-v1.md` as authoritative detailed references.
- Does not expose credential creation/rotation, billing, quotas, undocumented endpoint response schemas, or an interactive API console.

## Security and truth boundaries

- Examples reference environment variables rather than embedding token values.
- Copy operation uses the Clipboard API only on explicit user action; failures are announced and the user may copy manually.
- The page does not make requests, persist tokens, or log copied content.
- Citation matching is not represented as factual-truth or source-authority assessment.
- API scope and tenant/subject enforcement remain server-authoritative.

## Validation required

1. Frontend workflow on the exact PR head: locked install, lint, syntax check, TypeScript, dependency audit, static security, tests, build.
2. Full repository CI on the exact PR head, including Python matrix, browser isolation, and reproducible artifact checks.
3. Review changed-file behavior and compare examples with canonical API docs and request validators.
4. After merge, verify Frontend and full repository CI on the main merge commit.
5. Keep production API origin, identity issuer/audience, CORS/reverse-proxy, live API access, and GA as external deployment gates.

## Non-claims

This phase does not establish a live developer portal, public API availability, credential provisioning, production deployment, private-beta readiness, or GA readiness.
