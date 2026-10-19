# W9 adversarial security validation

## Purpose

W9 turns the existing SSRF and browser isolation policy into repeatable adversarial tests. The suite validates application and proxy behavior; it does not substitute for target-network penetration tests or an independent security assessment.

## CI coverage added

- Legacy IPv4 spellings that some resolvers normalize to loopback/private destinations are rejected at the URL syntax layer.
- The HTTP egress proxy rejects empty DNS results and mixed public/non-public answers, including loopback, link-local, RFC1918, and private IPv6 addresses.
- DNS fixtures verify the proxy selects one already validated public IP and performs one lookup per connection decision; the proxy then connects to that IP literal rather than resolving the hostname again.
- Existing tests continue to cover direct non-public IP literals, malformed CONNECT requests, duplicate authorization headers, weak credentials, port restrictions, and request bounds.
- Existing browser-isolation CI verifies that the browser worker can reach the internal proxy but cannot bypass it to connect directly to a public IP, and verifies Chromium's sandbox inside the container.

## Attack matrix

| Threat | Repository-level test | Target-environment proof still required |
| --- | --- | --- |
| Legacy IPv4 parsing differences | URL test vectors | Test through the actual API and egress path |
| DNS rebinding / mixed answers | Resolver and proxy tests reject any non-public answer and return a validated IP literal | Verify actual network route/firewall and observed destination addresses |
| Redirect to internal metadata or control-plane IP | Existing redirect validation and resolver tests | Execute redirect chains from the deployed worker under its real egress policy |
| Browser worker direct egress | Compose CI direct-egress negative test | Repeat from the deployed browser worker and preserve packet/flow evidence |
| Unauthorized browser-broker operation | Broker authentication, lease ownership, and PostgreSQL contract tests | Verify service-network boundaries and secret rotation in staging |
| Cross-tenant object access | Tenant-scoped repository/API tests | Run negative tests against the deployed release and real Platform-issued identities |
| Resource exhaustion | Request, response, timeout, connection, tunnel, byte, and browser resource limits | Measure load/failure behavior under the agreed staging capacity profile |

## Release rule

A passing CI suite proves the tested code and CI topology. It does not prove the cloud provider's firewall, private networking, secret manager, database TLS, or deployed container privileges. Keep those items open until deployment evidence is captured. Do not accept a security exception silently; record the owner, rationale, expiry, and compensating controls.
