# W7 remediation update — 2026-10-19

**Reviewed main revision:** `272cedd76590a6b512b58fda42a6af0e25b46542`  
**Decision:** W7 remains **OPEN**. The code-level vulnerability scanning gap is remediated and verified; governance, release-attestation exercise, durable evidence retention and operational release controls remain incomplete. Private beta remains **NOT CERTIFIED**.

## Verified remediation

### Dependency vulnerability auditing

- PR #34: https://github.com/LloydCoder/tinlance-web-intelligence/pull/34
- Exact-head CI run: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39216694386
- Post-merge main CI: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39216890595
- CI now installs pinned `pip-audit==2.10.1` and runs strict vulnerability auditing against the fully pinned `requirements-dev.txt` on Python 3.12 and 3.13.
- The first scan found `multidict==6.7.0` affected by CVE-2026-104874 / GHSA-54p9-h82j-f925. The pin was upgraded to `multidict==6.9.1`.
- The final Python 3.13 audit artifact contained 58 dependency records and **0 vulnerabilities**; Python 3.12's exact-head check also passed. CI retains each JSON report for 30 days.

### Container image vulnerability scanning

- PR #35: https://github.com/LloydCoder/tinlance-web-intelligence/pull/35
- Exact-head CI run: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39218841043
- Post-merge main CI: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39219155112
- API, worker, browser-worker and egress-proxy runtime images now use Ubuntu 24.04 Noble with Python 3.12 virtual environments, current OS package upgrades, non-root UID/GID 10001 and image-specific runtime dependencies.
- Trivy is pinned to immutable action commit `ed142fd0673e97e23eac54620cfb913e5ce36c25` and scanner version `v0.76.0`. CI scans all four images, uploads full JSON reports, and fails on scanner errors or HIGH/CRITICAL findings with a published fixed version.
- The exact-head scan reports for all four images contained **zero Trivy findings**. The browser egress proxy-bypass test, Chromium sandbox test, Python 3.12/3.13 suites, and reproducible release artifact validation all passed on the exact PR head and again on post-merge main.
- Trivy artifact: https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39218841043/artifacts/12170488702 (30-day retention; expires 2026-11-18). Archive the reports and checksums in durable audit storage before expiry. CI success is not a release approval.

## Remaining W7 exit blockers

| Gate | Status | Required evidence/action |
|---|---|---|
| G1 — branch governance | **OPEN / BLOCKED** | Read-only inspection of GitHub repository settings on 2026-10-19 found no active rulesets/branch protection for `main`. No settings were changed. Apply an active ruleset requiring PRs, one independent approval, the four required CI checks, conversation resolution, no force-pushes and no branch deletion; then re-read and record effective rule IDs, bypass actors and timestamp. An independent reviewer must be available before enforcing one approval. |
| G2 — CI/security gates | **IMPLEMENTED; operational policy still open** | Strict Python dependency audit and four-image Trivy scans are running in CI. Full scan reports must be archived durably; any future unfixed HIGH/CRITICAL finding needs explicit VEX/risk disposition before staging or release, as defined in `docs/security/container-vulnerability-policy.md`. |
| G3 — release provenance | **OPEN / NOT EXERCISED** | The release workflow is configured to generate a CycloneDX SBOM, checksums and GitHub build-provenance attestations. A non-production `workflow_dispatch`/test-tag run and independent attestation verification have not been observed. Verify each artifact against the expected repository, source SHA and workflow; demonstrate tampered artifacts fail verification. |
| G4 — durable evidence/ownership | **OPEN** | Persist ruleset evidence, dependency audit reports, image scan reports, SBOM, checksum manifest, provenance verification output, owners, timestamps and residual-risk decisions beyond 30-day workflow artifact retention. |
| G5 — W7 exit | **NOT MET** | G1, G3 and G4 must be evidenced; residual risks must be fixed or explicitly accepted by the authorized owner. |

## Boundaries

No infrastructure was provisioned, no production settings were changed, and no deployment, live penetration test, restore drill, signed release verification or private-beta approval is claimed. W8–W10 repository changes already present on main do not bypass the serial W7 release gate.
