# ADR 0003: Reuse the Platform MCP gateway

- Status: accepted for W3–W5.
- Context: the existing Tinlance Agent Platform already owns the MCP protocol endpoint, principal resolution, tool gateway, authorization scopes, policy decisions, approvals, and audit evidence. A second TWI-hosted MCP server would create competing authorization and protocol surfaces.
- Decision: TWI exposes a versioned, authenticated internal HTTP API and publishes operation/tool manifests. The Platform MCP gateway remains the remote MCP endpoint and invokes the registered TWI operations through a Platform-owned adapter.
- Consequences: TWI must never accept a caller token and forward it to another audience. It verifies Platform-issued tokens for the TWI API audience, enforces the delegated scopes in those tokens, and never decides or overrides Platform policy. The Platform integration and TSIC conformance must be merged before claiming ecosystem MCP integration is operational.
