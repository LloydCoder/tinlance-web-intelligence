# Security Policy

## Reporting

Do not publish exploitable vulnerabilities, credentials, session tokens, private data, or exploit payloads in public issues. Use GitHub's private vulnerability reporting feature if enabled for this repository. Otherwise contact the maintainers through a private channel.

## Security invariants

- All external web content and retrieved documents are untrusted data.
- Network access must be deny-by-default where possible and constrained by explicit destination policy.
- URL validation alone is not a complete SSRF control; connection-time address checks and egress restrictions are required.
- Every redirect must be revalidated. Block loopback, private, link-local, multicast, unspecified, reserved, and cloud metadata destinations.
- Browser workers must be isolated, resource limited, and separated from application credentials.
- Retrieved instructions must never override caller authorization, platform policy, or system instructions.
- Secrets must come from a secret manager or runtime environment, never source control or logs.
- MCP/API access must use resource-bound authentication and operation-level authorization; no token passthrough.
- Security claims require automated tests and deployment-level evidence.

Until a supported release is published, use the default branch as a development baseline only. No production support SLA is implied.
