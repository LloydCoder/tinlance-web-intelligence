# Browser worker isolation requirements

## Threat model

Web pages are untrusted input. They may contain prompt injection, hostile JavaScript, malicious redirects, oversized resources, browser exploits, links to internal services, and content designed to exhaust CPU or memory. Browser output is source-attributed evidence, never executable instructions or authorization policy.

## W4 controls

- Run browser automation in a separate non-root container with Chromium sandboxing enabled. Do not disable the Chromium sandbox. The browser container uses the Docker default seccomp profile plus the narrowly documented namespace syscalls required by Playwright's Chromium sandbox; the vendored profile is at deployments/security/chromium-seccomp.json.
- Give the browser worker no Platform credentials, provider API keys, cloud metadata credentials, persistent profile, reusable cookies, or caller-supplied authorization headers.
- Route browser traffic through the authenticated TWI egress proxy. The browser container has no direct Internet egress and does not share the API/Platform network.
- The proxy binds only to a loopback or unspecified IP interface, accepts only authenticated HTTPS CONNECT to port 443, resolves each destination at connection time, rejects DNS results containing private, reserved, link-local, loopback, multicast, or unspecified addresses, and connects to the validated IP literal to mitigate DNS rebinding.
- Browser-side routing permits only HTTP GET/HEAD to HTTPS URLs, validates each navigation/resource URL, blocks service workers and downloads, caps request count, navigation time, extracted text, links, and screenshot output.
- No clicks, form submissions, uploads, caller-supplied scripts, authenticated browsing, or browser actions with external side effects are supported in W4. Such capabilities require separate W5 capabilities and Platform policy/approval.
- Browser jobs use a fresh non-persistent context per job. Contexts are closed on completion or failure.
- Network egress controls are mandatory defense in depth. Application URL validation alone is not a complete SSRF control.

## Known W4 limitations

- The isolated Compose file is a single-host development and security-test harness, not proof of production network policy.
- The development/security-test Compose harness uses the single-node SQLite job store. The broker now uses the shared `JobRepository` contract and selects PostgreSQL when `TWI_DATABASE_URL` is configured; the browser worker remains database-free and receives only leased browser jobs through the authenticated broker. The PostgreSQL broker contract test runs in CI.
- The browser worker and egress proxy do not share a network with the API. The broker joins only the private browser-control network and the application network; the egress proxy joins only the private browser-egress network and its outbound network.
- SQLite remains a single-node development queue. Production must use PostgreSQL with separate DDL/runtime roles, `sslmode=verify-full`, tested multi-replica lease/recovery semantics, and environment-enforced egress restrictions. The repository tests do not prove these target-environment controls. No production readiness claim is made.

## References

- [Playwright Docker guidance for untrusted crawling and seccomp](https://playwright.dev/python/docs/next/docker)
- [Playwright BrowserContext API](https://playwright.dev/python/docs/api/class-browsercontext)
- [Playwright browser contexts](https://playwright.dev/python/docs/browser-contexts)
- [Chromium Linux sandbox design](https://chromium.googlesource.com/chromium/src/+/main/docs/linux/sandboxing.md)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
