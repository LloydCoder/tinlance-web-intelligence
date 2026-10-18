# Platform MCP integration contract

## Authority boundary

Tinlance Agent Platform is the canonical remote MCP server and owns protocol negotiation, caller identity, authorization, policy, approvals, tool invocation evidence, and audit. TWI deliberately does not expose a competing `/mcp` endpoint.

TWI provides a versioned internal HTTP API for durable search/fetch jobs and publishes the tool contracts in `src/tinlance_web_intelligence/integrations/agent_platform/tool_catalog.py` and `schemas/mcp-tools/`. A Platform-owned operation adapter must translate the registered MCP operation into the corresponding TWI API request, pass a Platform-issued token whose audience is the TWI API, and propagate the authenticated tenant/subject context. It must never forward an inbound MCP token to a different audience.

## Operations

- `twi.jobs.create_search` → `POST /v1/jobs` with `kind=search` and `Idempotency-Key`.
- `twi.jobs.create_browser` → `POST /v1/jobs` with `kind=browser`, the `Idempotency-Key` header, and `twi:browser` scope. The Platform adapter must apply open-world acquisition policy; TWI does not replace Platform authorization or approval.
- `twi.jobs.create_fetch` → `POST /v1/jobs` with `kind=fetch` and `Idempotency-Key`.
- `twi.jobs.read` → `GET /v1/jobs/{job_id}`.
- `twi.jobs.cancel` → `POST /v1/jobs/{job_id}/cancel`.
- `twi.research.verify` → `POST /v1/research/verify`; requires `twi:research:verify` and only verifies citation provenance and exact excerpt matches against successful, caller-accessible TWI fetch/browser jobs. It does not establish factual truth.
- `twi.world_intelligence.export_source_evidence` → `POST /v1/integrations/world-intelligence/exports`; requires `twi:observations:export`, an idempotency key, and a source quote that matches captured text. Platform policy must treat it as a consequential state-changing operation and apply any required approval before execution.
- `twi.world_intelligence.export_status` → `GET /v1/integrations/world-intelligence/exports/{event_id}`; requires `twi:observations:export:read` and is tenant/subject scoped.

The Platform adapter must map MCP tool names to these operations, apply Platform policy and scope decisions, and preserve the operation's idempotency semantics. It must not treat caller-supplied `tenant_id` or `subject_id` as trusted identity.

## Status

The durable job API and acquisition tools were established in W3/W4. W5 adds a citation-verification operation that checks claims against captured source text and scopes every referenced job to the authenticated tenant and subject. The catalog alone does not mean the tools are registered in the Platform repository; cross-repository registration and TSIC conformance remain W5 gates.
