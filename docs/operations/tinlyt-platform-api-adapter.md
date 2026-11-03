# Tinlyt browser-to-Platform API adapter

Tinlyt browser code must call the Tinlance Agent Platform API, never the TWI service directly.

## Request boundary

The browser sends authenticated JSON requests to `POST /v1/agent-platform` with:

- `Authorization: Bearer <short-lived Platform access token>`
- `X-Tinlance-API-Version: 1.1`
- a fresh `X-Request-ID`
- `Idempotency-Key` for idempotent writes
- `{ "operation": "...", "payload": { ... } }`

The browser does not submit `tenant_id` or `subject_id`. The Platform HTTP boundary derives both from the authenticated principal and rejects mismatches. The Platform handler routes TWI operations through its MCP policy gateway and mints a short-lived, audience-bound downstream token. The inbound browser token is not forwarded to TWI.

## Current operation mapping

| Browser capability | Platform operation |
| --- | --- |
| Create search job | `twi.jobs.create_search` |
| Create fetch job | `twi.jobs.create_fetch` |
| Create browser job | `twi.jobs.create_browser` |
| Read job | `twi.jobs.read` |
| Cancel job | `twi.jobs.cancel` |
| Verify citations | `twi.research.verify` |
| Create monitor | `twi.monitors.create` |
| Read monitor | `twi.monitors.read` |
| Run monitor | `twi.monitors.run` |
| Read monitor run | `twi.jobs.read` |
| Pause / resume monitor | `twi.monitors.pause` / `twi.monitors.resume` |
| Read tenant usage | `twi.usage.read` |
| Export evidence | `twi.jobs.export_evidence` |

## Explicitly unavailable until governed support exists

- Usage retrieval uses `twi.usage.read`, requiring the `web.usage.read` capability and downstream `twi:usage:read` scope. Usage and plan details are classified as confidential, and query pagination is bounded and validated.
- Monitor deletion is fail-closed in the browser. It is destructive and the Platform operation requires a run ID, approval ID and intent fingerprint bound to the exact request. A generic browser call must not bypass this approval workflow.
- Evidence export preserves the exact original response bytes through a base64 envelope and is bounded by the MCP transport (1 MiB response ceiling). Larger exports require a Platform-governed streaming or signed-download flow with tenant/subject binding, short expiry, content digest verification, audit evidence and revocation/expiry semantics. Do not increase the limit or add a direct TWI URL as a workaround.

## Deployment gates

Do not configure the frontend API base URL until the Platform HTTP service is deployed behind HTTPS with a production principal resolver, trusted tenant membership resolution, a configured KMS signing key and a JWKS endpoint. Do not activate OAuth until the inbound identity provider and callback settings are deployed and verified. Preview build success proves frontend compilation only; it does not prove authentication or API runtime readiness.
