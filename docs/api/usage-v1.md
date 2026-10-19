# Usage API v1

## Endpoint

`GET /v1/usage?dimension={dimension}&period_start={timestamp}&limit={n}`

Requires a verified Agent Platform principal and either `twi:usage:read` or
`twi:usage:read:any`. Tenant and subject are always taken from the verified principal;
caller-supplied identity fields are not accepted.

- `dimension`: 1–80 ASCII letters, digits, underscore, dot, colon, or hyphen.
- `period_start`: timezone-aware ISO-8601 timestamp. The API normalizes it to UTC.
- `limit`: optional integer from 1 to 500; defaults to 100.

The response contains a schema version, dimension and normalized period, committed usage,
configured quota/remaining allowance when an entitlement resolver is available, and a
bounded list of payload-free usage facts. Event output omits tenant and subject identifiers,
raw operation payloads, source URLs, billing payloads, and payment credentials.

Example response:

```json
{
  "schema_version": 1,
  "dimension": "search_requests_month",
  "period_start": "2026-10-01T00:00:00Z",
  "used": 12,
  "quota_limit": 1000,
  "remaining": 988,
  "plan_id": "customer-basic",
  "plan_version": 1,
  "events": [
    {
      "event_id": "opaque-event-id",
      "feature": "search",
      "dimension": "search_requests_month",
      "period_start": "2026-10-01T00:00:00Z",
      "quantity": 1,
      "occurred_at": "2026-10-19T10:00:00+00:00",
      "schema_version": 1
    }
  ],
  "returned": 1
}
```

If entitlement state is unavailable or the requested quota dimension is not configured, a
configured production resolver fails closed with HTTP 503. Missing read scopes return 403.
This API reports TWI usage facts; it is not a statement of invoice balance, payment settlement,
tax, refunds, or provider billing status.

The event list is bounded, not an unbounded export interface. Consumers requiring full-period
exports should use a future cursor-paginated export contract rather than increase `limit`
beyond 500.
