# Monitor API v1

The monitor API stores a tenant and subject scoped web target and enqueues explicit capture jobs. It does not schedule recurring work; Agent OS owns recurrence. All identity fields come from the verified Platform principal.

## Operations

| Method | Path | Scope | Behavior |
|---|---|---|---|
| POST | `/v1/monitors` | `twi:monitors:write` | Create an idempotent monitor. Requires `Idempotency-Key`; validates a public HTTP(S) target with the existing safe acquisition policy. |
| GET | `/v1/monitors/{monitor_id}` | `twi:monitors:read` | Read own subject’s monitor. `twi:monitors:read:any` permits same-tenant administrative reads. |
| POST | `/v1/monitors/{monitor_id}/runs` | `twi:monitors:write` | Enqueue a durable run and return `202` plus `Location`. Requires `Idempotency-Key`. |
| GET | `/v1/monitors/{monitor_id}/runs/{job_id}` | `twi:monitors:read` | Read a run through the tenant and subject scoped job repository. |
| POST | `/v1/monitors/{monitor_id}/pause` | `twi:monitors:write` | Stop new run requests. Already accepted work drains. |
| POST | `/v1/monitors/{monitor_id}/resume` | `twi:monitors:write` | Allow new run requests. |
| DELETE | `/v1/monitors/{monitor_id}` | `twi:monitors:delete` | Redact target and policy and remove stored run summaries. |

Unknown request fields are rejected. Cross-tenant and unauthorized subject reads use the API’s non-disclosure response. The API does not return raw page text or target URL query values. A successful first run establishes a digest baseline; later results report bounded digest and changed-unit metadata. These results are observations, not truth judgments.

## Policy

`policy.max_bytes` is optional and must be positive; when provided it can only lower the configured acquisition response limit. Acquisition continues to enforce URL validation, DNS/IP checks, redirect revalidation, response limits, and timeouts. No caller-provided tenant or subject is accepted.

## Idempotency and lifecycle

Create and run operations require keys of 16–256 characters. Replaying an identical request returns the existing resource/job; reusing a key with a different request returns a conflict. Pausing prevents future enqueue operations while work already accepted can finish. Delete redacts stored monitor data and run summaries; it does not cancel a worker lease already in progress.

## Platform tool contracts

The six monitor operations are published as `twi_monitor_create`, `twi_monitor_read`, `twi_monitor_run`, `twi_monitor_pause`, `twi_monitor_resume`, and `twi_monitor_delete` in `schemas/mcp-tools/`. Delete requires its own destructive scope and is not folded into pause.
