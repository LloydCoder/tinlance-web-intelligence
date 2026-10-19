# Platform MCP integration contract

## Authority boundary

Tinlance Agent Platform is the canonical remote MCP server and owns protocol negotiation, caller identity, authorization, policy, approvals, tool invocation evidence, and audit. TWI deliberately does not expose a competing `/mcp` endpoint.

TWI provides a versioned internal HTTP API for durable search/fetch jobs and publishes the tool contracts in `src/tinlance_web_intelligence/integrations/agent_platform/tool_catalog.py` and `schemas/mcp-tools/`. A Platform-owned operation adapter translates the registered MCP operation into the corresponding TWI API request, passes a Platform-issued token whose audience is the TWI API, and propagates authenticated tenant/subject context. It must never forward an inbound MCP token to a different audience.

## Operations

- `twi.jobs.create_search` → `POST /v1/jobs` with `kind=search` and `Idempotency-Key`.
- `twi.jobs.create_browser` → `POST /v1/jobs` with `kind=browser`, the `Idempotency-Key` header, and `twi:browser` scope. The Platform adapter applies open-world acquisition policy; TWI does not replace Platform authorization or approval.
- `twi.jobs.create_fetch` → `POST /v1/jobs` with `kind=fetch` and `Idempotency-Key`.
- `twi.jobs.read` → `GET /v1/jobs/{job_id}`.
- `twi.jobs.cancel` → `POST /v1/jobs/{job_id}/cancel`.
- `twi.research.verify` → `POST /v1/research/verify`; requires `twi:research:verify` and only verifies citation provenance and exact excerpt matches against successful, caller-accessible TWI fetch/browser jobs. It does not establish factual truth.
- `twi.world_intelligence.export_source_evidence` → `POST /v1/integrations/world-intelligence/exports`; requires `twi:observations:export`, an idempotency key, and a source quote that matches captured text. Platform policy treats it as a consequential state-changing operation and applies required approval before execution.
- `twi.world_intelligence.export_status` → `GET /v1/integrations/world-intelligence/exports/{event_id}`; requires `twi:observations:export:read` and is tenant/subject scoped.

The Platform adapter maps MCP tool names to these operations, applies Platform policy and scope decisions, and preserves idempotency semantics. Caller-supplied `tenant_id` or `subject_id` is not trusted identity.

## Verified repository integration — 2026-10-19

The repository integration gate is implemented and post-merge verified:

- Platform adapter and tests are present at [Platform main](https://github.com/LloydCoder/tinlance-agent-platform/tree/882be4ef03f78084ce800a715029a0b1346ebdd2/packages/mcp/src/tinlance_agent_platform_mcp) and the [TWI API handler](https://github.com/LloydCoder/tinlance-agent-platform/blob/882be4ef03f78084ce800a715029a0b1346ebdd2/packages/app/src/tinlance_agent_platform_app/twi_api_handler.py).
- The canonical ecosystem lock pins TWI at `7b48b28ccd76b9ea2f09a2f524469c4a3ffe8dcc`, Platform at `882be4ef03f78084ce800a715029a0b1346ebdd2`, and TSIC at `bd2e7582ad29eb460be36ca45b073b99fdeadfbf`.
- TADL integration PR [#94](https://github.com/LloydCoder/tinlance-agent-developer/pull/94) merged as `9f53387aa10e4fae0bc23686688d9794a527df01`.
- Post-merge [Ecosystem Integration](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39200004842) passed on that main commit. It materializes the exact pinned revisions, runs the TWI package suite, runs Platform-owned TWI MCP/API adapter tests, and executes the canonical TSIC and ecosystem P2–P10 gates.

## Release boundary

This verifies repository-level contracts and tests, not the live target deployment. Platform MCP registration, effective operation-level policy, audience-bound credentials, World Intelligence ingestion, production network controls, secrets, monitoring, backup/restore, and explicit private-beta approval must still be verified for the exact target environment. Private beta remains **NOT CERTIFIED** until the checklist in `docs/operations/private-beta-readiness.md` is satisfied with deployment evidence.
