# Security Policy

Tinlyt handles untrusted web content, delegated identity, customer evidence, and network acquisition. Security reports should be handled privately.

## Supported versions

Until the project publishes a supported release, the default branch is a development baseline. No production support or patch SLA is implied. Supported release branches will be listed here when introduced.

## Report a vulnerability privately

Do not disclose exploitable details, proof-of-concept payloads, credentials, access tokens, customer data, or private evidence in public issues or pull requests.

Preferred reporting path:

1. Open this repository's **Security** tab.
2. Select **Report a vulnerability** to create a private GitHub Security Advisory, if private vulnerability reporting is enabled.
3. Include the affected commit/tag, impact, prerequisites, reproduction steps, and suggested mitigation. Redact secrets and personal data.

If private vulnerability reporting is unavailable, email [hello@tinlance.com](mailto:hello@tinlance.com?subject=%5BSECURITY%5D%20Tinlyt%20vulnerability%20report) with the subject **[SECURITY] Tinlyt vulnerability report**. This mailbox is the project's public contact route; the maintainer should confirm that it is actively monitored. Do not use a public issue as a fallback for sensitive details.

## Response expectations

The maintainer aims to:

| Activity | Target |
| --- | --- |
| Acknowledge a report | Within 5 business days |
| Initial triage and severity assessment | Within 10 business days |
| Status updates | At least every 10 business days while active |
| Remediation and disclosure | Coordinated with the reporter, based on severity, exploitability, affected versions, and release readiness |

These are response targets, not a guaranteed service-level agreement. Complex reports, upstream dependencies, or unavailable deployment evidence may require more time. Allow reasonable time for investigation and coordinated remediation before public disclosure.

## Scope and useful report details

Relevant areas include authentication and authorization, tenant isolation, SSRF and DNS rebinding, redirect handling, browser isolation and egress, prompt-injection boundaries, evidence integrity, secrets handling, dependency/supply-chain compromise, data retention, and denial-of-service/resource exhaustion.

Please include:

- A concise description and security impact.
- Affected version, commit, endpoint, or deployment topology.
- Reproduction steps and minimum required privileges.
- Relevant logs or traces after removing secrets and customer data.
- Whether the issue is reproducible against the current default branch.

## Security design invariants

- External web content and retrieved documents are untrusted data.
- Authorization is derived from verified Platform identity; caller-supplied tenant identity is not trusted.
- Network destinations and every redirect are validated; deployment egress controls remain required.
- Browser workers are isolated, resource-limited, and separated from application credentials.
- Secrets are injected at runtime and must not enter source control or logs.
- Evidence integrity does not establish source truth, source authority, or a digital signature.
- Repository tests do not certify the security of a live deployment.

See [the threat model](docs/security/threat-model.md), [SSRF controls](docs/security/ssrf-controls.md), and [private-beta readiness gates](docs/operations/private-beta-readiness.md).
