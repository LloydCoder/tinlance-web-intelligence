# Tinlyt Frontend F2 — Typed API Client and Platform OAuth Adapter

**Scope:** typed TWI client, runtime contract validation, OAuth 2.0 Authorization Code + PKCE public-client adapter, and test/security gates.  
**Authority boundary:** Tinlance Agent Platform remains authoritative for identity and authorization; TWI remains a downstream acquisition API.

## Delivered in this phase

- Strict TypeScript 6.0.3 compilation for the API contract layer. TypeScript 7.0.2 is the latest native-port release, but the frontend pins the stable 6.0 line until compatibility is separately validated against the repository's build and test toolchain ([TypeScript 6.0 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/), [TypeScript 7.0 announcement](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)).
- Typed operations for job creation, job read, cancellation, evidence export, and claim verification.
- Runtime validation for job requests and responses; the browser client ignores internal tenant, subject, and idempotency fields in job responses.
- Idempotency key validation/generation for job creation, finite request timeout, redirect rejection, no credential cookies, no implicit retries, and no-store request behavior.
- Sanitized typed errors for authentication, permission, not-found, conflict, validation, rate limit, timeout, network, server and invalid-response conditions.
- Canonical evidence package validation against the schema in schemas/twi-evidence-package-v1.schema.json, including the vendor media type and interpretation.truth_assessment = not_provided.
- A secret-free runtime configuration template and sign-in control wired to the OAuth adapter. The sign-in control remains disabled when required deployment settings are absent; successful authorization does not enable investigation/evidence workflows.
- OAuth 2.0 Authorization Code + PKCE (S256) adapter for a public browser client. It requires explicitly trusted HTTPS issuer endpoints, exact issuer and redirect URI validation, state and response-issuer validation, a short-lived PKCE transaction in sessionStorage, and an audience/resource value for TWI.
- Access tokens remain in memory only; refresh tokens are ignored. The adapter does not embed a client secret or trust a JWT decoded in the browser. TWI remains responsible for cryptographic issuer/audience/signature/expiry/tenant/subject/scope validation.
- CI runs locked npm ci, JavaScript syntax checks, TypeScript typecheck, static security checks, npm audit, tests and a production build.

## Deployment configuration still required

No production identity issuer identifier/endpoints, public client ID, approved redirect URI, CORS policy, or TWI audience were present in the inspected TWI or Platform repository configuration. Do not invent or commit these values. The deployment must configure an approved Platform identity issuer that supports Authorization Code + PKCE for a public client, allows the exact Tinlyt redirect URI, returns short-lived TWI-audience tokens with least-privilege scopes, and permits the configured browser token exchange under its CORS policy.

The adapter fails closed when trusted origins or token provider configuration are absent. Deployments must serve the runtime configuration without secrets and rewrite the exact configured callback path to the frontend entry point. The current application shell remains in foundation mode; this phase does not claim a live login, live API deployment, or production user session. Live product controls must remain disabled until the deployment supplies and verifies the approved identity configuration.

## Security constraints

- Never use client credentials flow or embed a client secret in the browser.
- Never persist access or refresh tokens in localStorage, URLs, logs, analytics or browser-readable durable storage.
- Keep the OAuth authorization code and state out of the URL after callback processing.
- Do not trust browser-decoded JWT claims for authorization.
- Do not expose TWI to untrusted callers by bypassing Platform authorization/policy.
- Cross-origin API requests require an explicit HTTPS origin allowlist; redirects are rejected.
- Retrieval is not proof of truth. Evidence packages are acquisition observations, not signatures or truth verdicts.

## Verification

Run from apps/web/:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run lint
npm run syntax-check
npm run typecheck
npm run security
npm audit --audit-level=high
npm test
npm run build
```

F2 code acceptance requires the exact PR-head frontend and repository CI workflows to pass. Production authentication acceptance additionally requires an end-to-end test against the configured Platform identity issuer and TWI API audience; this deployment-specific gate is not satisfied by unit tests alone.
