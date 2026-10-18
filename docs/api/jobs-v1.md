# TWI Jobs API v1

The API is intended for trusted internal callers using Platform-issued access tokens whose audience is the configured TWI API resource. TWI validates issuer, audience, signature, token type, expiry, tenant, subject, and delegated scopes. It does not accept caller-supplied identity fields and never forwards an inbound token to another service.

## Routes

- `GET /health/live` — liveness probe; no sensitive details.
- `GET /health/ready` — readiness probe backed by the durable job repository.
- `POST /v1/jobs` — create an idempotent `search`, `fetch`, or `browser` job. Requires `Idempotency-Key` and the matching `twi:search`, `twi:fetch`, or `twi:browser` scope. Returns `202 Accepted`.
- Browser jobs accept only HTTPS public URLs, `wait_until=domcontentloaded|load`, a 1–30 second timeout, and an optional bounded JPEG screenshot. The isolated worker permits only GET/HEAD page requests, blocks service workers and downloads, and uses an authenticated CONNECT-only egress proxy. Browser interactions with external side effects are not supported.
- `GET /v1/jobs/{job_id}` — read a job in the caller's tenant. Requires `twi:jobs:read`; `twi:jobs:read:any` permits tenant-scoped administrative reads.
- `POST /v1/jobs/{job_id}/cancel` — request cancellation of a caller-owned job. Requires `twi:jobs:cancel`.

## Job semantics

- Idempotency is scoped to `(tenant_id, subject_id, idempotency_key)`. Reusing a key with a different canonical payload returns `409 Conflict`.
- Jobs use explicit queued/running/succeeded/failed/cancelled states, bounded attempts, worker leases, lease-expiry recovery, and sanitized error codes.
- A running cancellation is cooperative: the current bounded acquisition finishes or times out, and the result is not committed if cancellation was requested.
- SQLite with WAL and `synchronous=FULL` is the W3 durable single-node backend. Multi-replica production operation is not claimed until the W6 PostgreSQL backend and deployment gate are complete.
