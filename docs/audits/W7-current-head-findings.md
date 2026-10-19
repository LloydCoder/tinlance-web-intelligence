# W7 follow-up — current-head workflow and release-supply-chain findings

**Review date:** 2026-10-19  
**Reviewed TWI main:** `d411706b31aedc4ac20b788d272b5b72f1af4449`
**Scope:** current CI/release/staging configuration and the W7–W12 status recorded in the repository roadmap.
**Decision:** W7 remains **OPEN**; private beta remains **NOT CERTIFIED**.

## Current-head reconciliation

The repository roadmap now records additional work beyond the original W7 baseline: dependency and container vulnerability scans were added; PRs #27 and #28 added staging topology, PostgreSQL role/TLS safeguards and browser-broker contracts; PR #25 added adversarial regression coverage; and later work added API and durable queue/outbox metrics, provenance manifests, and an offline benchmark. These are repository changes, not proof that the target environment is deployed or operationally validated.

The roadmap records that effective branch inspection found `main` unprotected with no active rulesets, and that saving a ruleset required GitHub MFA/sudo. This document treats that as a recorded audit result; the connected GitHub repository tool surface used for this review does not independently expose the effective ruleset API response. Release provenance was exercised separately: workflow run [#39227160547](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39227160547) completed successfully on source `afd3807a09f5495669e6dd7ec10f6aa71be05b92`, including artifact attestation, independent verification, and tampered-wheel rejection. The tested release workflow differs from current `main` only by removal of the temporary verification-branch push trigger.

## Findings from the current configuration

| Control | Evidence | Assessment |
|---|---|---|
| CI coverage | `.github/workflows/ci.yml` runs Python 3.12/3.13 quality/type checks, Bandit, tests against PostgreSQL, migration checks, Chromium runtime smoke tests, browser isolation/egress checks, and reproducible artifact validation. | Repository checks are configured. Whether they are mandatory for every protected-branch update is not established; the roadmap says branch protection is currently absent. |
| Action pinning | Reviewed CI and release workflow steps use full commit SHAs for the checkout, setup-python, provenance-attestation, and artifact-upload actions. | Positive evidence for the reviewed actions; not a complete organization-wide supply-chain audit. |
| Workflow permissions | CI has top-level `contents: read`; the release job scopes OIDC and attestations permissions to the release job. | Good least-privilege pattern in the reviewed files. Organization-level Actions policy and fork settings are not independently verified here. |
| Static/dependency checks | Ruff, mypy, Bandit, `pip check`, and pinned `pip-audit==2.10.1` are configured; Dependabot weekly updates are configured for pip and GitHub Actions. | Vulnerability scanning is configured and blocks on findings. The reports use 30-day workflow artifact retention; durable archival is still open. |
| Container security | The isolation job builds four images, tests proxy-only egress and Chromium sandboxing, and scans API, worker, browser-worker, and egress-proxy images with pinned Trivy. | Actionable HIGH/CRITICAL findings and scanner failures block CI. Reports use 30-day workflow artifact retention; durable archival is still open. |
| Reproducible release | Release workflow builds from two clean `git archive HEAD` trees, normalizes source distributions and compares SHA-256 digests. | Exercised successfully in the non-production workflow-dispatch run [#39227160547](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39227160547). |
| SBOM | Release workflow generates `dist/twi-build-environment.cdx.json` with CycloneDX using the project metadata. | Generation is configured. Confirm its actual contents and runtime dependency coverage from a completed run before calling it a complete release SBOM. |
| Provenance | The release workflow invokes `actions/attest-build-provenance` with OIDC and verifies release artifacts using `gh attestation verify` against the expected repo, workflow, and source digest. Run [#39227160547](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39227160547) passed, including a tampered-wheel negative check. | **Exercised on the verification branch.** Durable customer distribution and long-term evidence retention remain open. |
| Artifact distribution | The release workflow uploads release artifacts and evidence as a workflow artifact with 30-day retention. | Temporary artifact retention alone is not a durable customer release channel. |
| Staging | `deployments/compose/staging.yml` defines API, worker, migration, browser broker/worker, egress proxy and World Intelligence exporter services with external credential requirements. | Deployment topology is repository evidence; no approved target workspace or live staging run is established. |

## W7 exit blockers

1. **G1 — Enforceable branch governance:** the repository roadmap records that `main` is unprotected and ruleset creation was blocked by MFA/sudo. The authorized repository owner must complete the GitHub security step to apply a suitable ruleset, then capture effective rule IDs, review requirements, required status checks, bypass actors, and evidence timestamp. Do not claim G1 passed before the resulting settings are re-read.
2. **G2 — Vulnerability assurance:** the pinned dependency audit and four-image scan controls are implemented in CI. Archive their machine-readable reports durably and retain explicit risk dispositions for unfixed HIGH/CRITICAL findings.
3. **G3 — Provenance exercise:** the non-production workflow-dispatch run [#39227160547](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39227160547) passed independent verification of release artifacts against the expected repository/workflow/source and rejected a tampered wheel. Preserve evidence beyond 30-day workflow retention and implement a durable customer distribution strategy.
4. **G4 — Evidence pack:** retain run links, artifact metadata/hashes, SBOM, vulnerability results, attestation verification output, effective rules, owner, timestamps and residual-risk decisions in a durable audit record.
5. **Environment gates:** confirm the staging provider/workspace before any billable provisioning. Then verify PostgreSQL TLS and role separation, secrets and rotation, real API/browser egress, cross-system Platform → TWI → World Intelligence journey, monitoring/alert delivery, backup restore, rollback and on-call response.

## Gate state

- **G1 branch governance:** **OPEN — effective rules must be applied and re-read**.
- **G2 CI/security enforceability:** **IMPLEMENTED IN WORKFLOWS; durable report retention and mandatory-check enforcement remain open**.
- **G3 release traceability:** **EXERCISED — non-production provenance verification and tampered-wheel rejection passed; durable distribution/retention remain open**.
- **G4 evidence ownership:** **OPEN**.
- **G5 W7 exit:** **NOT MET**.

No infrastructure was provisioned and no GitHub security settings were changed during this review. This document does not claim a live penetration test, restore drill, deployed staging environment, security certification, completed release, or private-beta approval. W8–W10 repository work already present on main does not bypass the serial W7 release gate.
