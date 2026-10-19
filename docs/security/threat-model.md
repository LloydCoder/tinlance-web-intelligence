# Threat model (initial)

## Assets

- Credentials and delegated caller context.
- Internal service/network availability.
- Raw acquired content and its provenance.
- Observation integrity and consumer contracts.
- Job state, resource budgets, and auditability.

## Trust boundaries

1. Internet → acquisition worker: hostile URL, DNS answers, redirects, response bodies.
2. Web content → extraction/LLM: prompt injection, malformed documents, deceptive metadata.
3. Worker → API/control plane: serialized results and untrusted worker messages.
4. TWI → Tinlance ecosystem: caller identity, tenant context, contract compatibility, and authority boundaries.

## Required mitigations

- Restrict schemes to HTTP(S); reject userinfo and local/internal destinations.
- Resolve and classify every address at connection time; reject any unsafe answer; pin the approved destination or use a transport that prevents DNS rebinding.
- Revalidate each redirect and cap redirect count.
- Apply connect/read/total timeouts, response-size limits, decompression limits, content-type checks, concurrency and per-tenant budgets.
- Run browsers in isolated ephemeral workers with deny-by-default egress and no application secrets.
- Treat all external content as untrusted data and clearly separate source text from instructions.
- Use authenticated service-to-service calls and operation-level authorization; never trust caller-supplied tenant/identity claims.
- Redact secrets and sensitive data from logs; retain minimal evidence according to policy.
- Test both allowed and denied paths. URL parser tests do not prove deployment egress isolation.

## Residual risks

A domain can resolve differently between validation and connection. A compliant production transport and network-level egress enforcement are mandatory before live acquisition is considered safe.

## Monitor-specific threats

- **Target and query disclosure:** monitor targets are persisted for execution. Public API results omit targets; logs, traces, metrics, and evidence must not include URL query values. Deletion redacts target and policy.
- **Baseline races and replay:** capture results use a stored baseline version compare-and-set. Idempotency conflicts are rejected, and failed/stale captures do not advance the baseline.
- **Tenant/subject leakage:** every monitor and associated job read is tenant scoped, with explicit same-tenant administrative scopes; negative API tests cover subject separation.
- **Trace data leakage:** only validated `traceparent` is accepted. Baggage is omitted and span attributes are allowlisted. Export remains a no-op by default.
- **Operational controls:** monitor creation and run enqueue do not schedule recurrence. Agent OS owns cadence; pause prevents new enqueues while accepted work drains.

These are repository controls. Live DNS/redirect behavior, target egress, trace collector configuration, retention approval, and independent security assessment remain environment evidence gates.
