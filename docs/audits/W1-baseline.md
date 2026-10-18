# W1 baseline audit — evidence record

- PR: [#1](https://github.com/LloydCoder/tinlance-web-intelligence/pull/1)
- PR head tested: `f942d50ee9fdb8e2ced4ded6a7173d3b211f6c61`
- CI run: [39138909078](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39138909078)
- Merge commit: `a39ca4e9bcc2af39b2e3490f3540f2674169d111`
- Result: merged after both matrix jobs reported success.

## Verified checks

- Python 3.12: dependency installation, Ruff, mypy, Bandit, and pytest all succeeded.
- Python 3.13: dependency installation, Ruff, mypy, Bandit, and pytest all succeeded.
- Workflow actions were pinned to immutable commit SHAs.
- Repository ownership, threat model, architecture boundaries, and workstream acceptance gates are documented.

## Limitations carried forward

- W1 introduced URL syntax checks, not a live network acquisition service.
- No production deployment, network-egress policy, DNS behavior under production networking, or operational SLO has been verified.
- The pinned development requirements file pins versions but does not yet include package artifact hashes; hash-locked dependency provenance remains a hardening item.
- Browser workers, durable jobs, remote MCP, Platform authentication, approvals, and TSIC conformance remain future workstreams.
