# W10 observability and SRE baseline

**Status:** implementation in progress; not an SRE certification or production operational sign-off.

## Evidence boundary

The API now has a protected Prometheus exposition endpoint and request correlation IDs. These are repository-level capabilities only. No deployed scraper, alert manager, paging integration, measured SLO, load test, or exercised rollback/on-call procedure is implied by a passing CI run.

## API telemetry contract

- Endpoint: `GET /internal/metrics`; disabled by default and returns 404 unless `TWI_METRICS_TOKEN` is configured.
- Authentication: a dedicated bearer token of at least 32 non-padded characters; never reuse the Platform token, broker token, or a World Intelligence credential.
- Network: keep the endpoint on private ingress / monitoring paths only. Do not publish it through an unauthenticated public gateway.
- Request correlation: valid `X-Request-ID` values matching `[A-Za-z0-9._-]{1,64}` are preserved; invalid or absent values are replaced with a random 32-character hexadecimal ID and returned in the response header.
- Cardinality: metrics label requests by normalized method, matched route template, and status code. They do not label by URL, query string, tenant, subject, token, source URL, or request ID. Metrics scrapes are excluded from request counters to avoid scrape recursion.

Metrics currently emitted by the API process:

| Metric | Type | Purpose |
| --- | --- | --- |
| `twi_http_requests_total` | Counter | Completed HTTP requests by method, route template and status |
| `twi_http_request_duration_seconds` | Histogram | Request latency by method and route template |
| `twi_http_in_flight_requests` | Gauge | Requests currently being handled by this process |

Each process has an independent registry. Scrape each API replica directly or configure the monitoring collector to discover every replica; do not assume counters are aggregated across processes.

## Proposed SLOs — owner approval and measurement required

These are initial engineering targets, not observed service performance and not yet approved customer commitments.

| Indicator | Proposed target | Measurement / alert |
| --- | --- | --- |
| API availability | 99.5% successful non-5xx requests over a rolling 30 days, excluding intentional 4xx responses | Burn-rate alert on 5xx and probe failures |
| API latency | p95 under 1.0 s for API control-plane requests, excluding long-running acquisition work | Histogram quantile by route template |
| Readiness | 99.9% successful readiness probes over 30 days | Alert on repeated `/health/ready` failures |
| Queue age | Oldest eligible queued job under 2 minutes during supported operating hours | Requires durable queue-age instrumentation; not implemented in this slice |
| Evidence outbox | Oldest pending delivery under 5 minutes | Requires outbox-age and delivery-result instrumentation; not implemented in this slice |
| Browser execution | At least 99% of browser jobs finish within their declared bounded timeout, excluding policy rejection | Requires browser job outcome and duration metrics; not implemented in this slice |

Do not advertise these targets externally until the owner approves them and at least one representative load-test and staging-observation window supports the numbers.

## Alert and response matrix

Alert rules and paging routes must be installed in the selected monitoring platform before the SRE gate can pass.

| Severity | Trigger | First response |
| --- | --- | --- |
| SEV-1 | Confirmed tenant data exposure, authorization bypass, or sustained total API outage | Declare incident, restrict ingress/credentials, preserve evidence, invoke incident commander |
| SEV-2 | Sustained 5xx/error-budget burn, queue age beyond target, outbox backlog growing, or browser egress control failure | Acknowledge promptly, assess blast radius, pause risky acquisition if needed, use documented rollback |
| SEV-3 | Elevated latency, repeated dependency retries, low disk/memory headroom, or non-growing backlog after recovery | Create operational ticket, inspect correlated request IDs and sanitized logs, track remediation |

Never place bearer tokens, raw page content, full source URLs with query parameters, tenant identifiers, or user-supplied request IDs in metric labels or alert payloads.

## Rollback and on-call evidence required

Before production/private beta, retain a dated evidence pack containing:

1. Exact deployed Git SHA and image digest for API, workers, browser broker, browser worker and egress proxy.
2. Monitoring target discovery, scrape success, alert-rule validation, and a witnessed test alert through the real notification channel.
3. A synthetic request showing request-ID propagation across the API and downstream delivery logs without secrets or tenant identifiers.
4. A controlled failure exercise for PostgreSQL unavailability, outbox delivery failure, browser-worker loss, and egress-proxy failure.
5. A rollback rehearsal to the previous known-good immutable image digest, with health/readiness verification and measured recovery time.
6. Named on-call owner, escalation path, runbook link, and accepted RPO/RTO.

## Remaining W10 work

- Add queue, outbox, browser, provider and worker outcome/latency/age metrics without high-cardinality labels.
- Establish real distributed trace propagation across API, worker, broker and World Intelligence export; request IDs alone are correlation, not distributed tracing.
- Deploy a collector and alerting route in the approved staging environment, then verify delivery.
- Define capacity budgets from measured load tests and tune concurrency/timeouts from evidence.
- Exercise on-call, incident response and rollback against the actual target deployment.

Until those items have evidence, W10 remains in progress and private beta remains NOT CERTIFIED.
