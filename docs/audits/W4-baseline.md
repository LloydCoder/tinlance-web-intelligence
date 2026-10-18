# W4 baseline audit — isolated browser workers

## Scope

W4 adds a dedicated Playwright browser worker for bounded, read-only page capture; an authenticated internal broker for browser job leasing and result delivery; a destination-validating egress proxy; container-level isolation; and adversarial policy tests.

## Required controls

- Chromium sandbox remains enabled; the container runs as a non-root user, drops unnecessary capabilities, uses a read-only root filesystem, applies a seccomp profile and explicit CPU/memory/PID limits.
- Browser workers do not receive the shared SQLite database volume. They communicate with the trusted broker over a private control network and have no direct public egress.
- Browser traffic is routed through an authenticated proxy that resolves destinations at connection time, rejects non-public IPs, pins the resolved destination and bounds tunnel lifetime and bytes.
- Browser contexts are non-persistent. Downloads, service workers, WebSockets, caller-provided scripts, clicks, form submissions, uploads and authenticated browsing are not enabled.
- Retrieved page content is untrusted data. It cannot change policy, caller identity, authorization or execution authority.

## Implementation references

- `apps/browser_worker/main.py`
- `apps/browser_broker/main.py`
- `apps/egress_proxy/main.py`
- `src/tinlance_web_intelligence/browser/`
- `src/tinlance_web_intelligence/security/egress_proxy.py`
- `deployments/compose/browser-isolated.yml`
- `deployments/docker/browser.Dockerfile`
- `deployments/security/chromium-seccomp.json`
- `tests/test_browser_policies.py`
- `tests/test_browser_runtime.py`
- `tests/test_egress_proxy.py`
- `tests/test_browser_broker.py`

## Verification boundary

The isolated Compose workflow is a security-test harness. It must verify the Compose topology, build all images, prove that the browser worker cannot reach the public Internet directly, and launch Chromium with its sandbox enabled. Python CI also runs lint, type checking, security lint, unit/contract tests and a browser runtime smoke test on Python 3.12 and 3.13.

## Final verification and disposition

- PR #12 was merged to `main` using squash merge as commit [9af6a77a83a8031d3aafb242c048b5fb2f5cb8eb](https://github.com/LloydCoder/tinlance-web-intelligence/commit/9af6a77a83a8031d3aafb242c048b5fb2f5cb8eb).
- Exact PR-head CI run [39154470930](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39154470930) passed all three jobs: Python 3.12, Python 3.13, and browser container isolation.
- Post-merge main CI run [39154598849](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39154598849) passed the same three jobs.
- Branch push CI run [39154466728](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39154466728) also passed all three jobs.

**Disposition:** W4 implementation gate is complete at repository/CI level. This does not certify a production deployment or claim that private-beta readiness has been achieved.

## Residual limitations

- SQLite remains a single-node job store shared by the API and trusted broker; it is not a multi-replica production queue. W6 must implement and test a production durable store and lease/recovery behavior.
- The Compose network boundary is not a substitute for production cloud/VPC egress policy, runtime security controls, secret rotation or deployment-specific threat review.
- Browser capture is read-only. Any consequential external interaction requires a separate W5 capability, Platform authorization and, where required, explicit human approval.

## Research baseline

The controls follow the defensive principles in the [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [Playwright's browser launch documentation](https://playwright.dev/python/docs/api/class-browsertype), and the [MCP security best practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices). References are design inputs; CI and integration evidence are still required for certification.
