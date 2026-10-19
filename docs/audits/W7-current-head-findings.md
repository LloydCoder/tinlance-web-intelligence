# W7 follow-up — current-head workflow and release-supply-chain findings

**Review date:** 2026-10-19  
**Reviewed TWI main:** `5ec7e724ec9228a6bd871ca87b0143d0f230c766`  
**Scope:** current CI/release/staging configuration and the W7–W10 status recorded in the repository roadmap.  
**Decision:** W7 remains **OPEN**; private beta remains **NOT CERTIFIED**.

## Current-head reconciliation

The repository roadmap now records additional work beyond the original W7 baseline: PR #26 added dependency metadata checks and initial SBOM/checksum/attestation steps; PRs #27 and #28 added staging topology, PostgreSQL role/TLS safeguards and browser-broker contracts; PR #25 added adversarial regression coverage; PR #29 and the subsequent W10 work added API and durable queue/outbox metrics. These are repository changes, not proof that the target environment is deployed or operationally validated.

The roadmap also records that effective branch inspection found `main` unprotected with no active rulesets, that saving a ruleset required GitHub MFA/sudo, and that the provenance-attestation service had not yet been exercised. This document treats that as a recorded audit result; the connected GitHub repository tool surface used for this review does not independently expose the effective ruleset API response.

## Findings from the current configuration

| Control | Evidence | Assessment |
|---|---|---|
| CI coverage | `.github/workflows/ci.yml` runs Python 3.12/3.13 quality/type checks, Bandit, tests against PostgreSQL, migration checks, Chromium runtime smoke tests, browser isolation/egress checks, and reproducible artifact validation. | Repository checks are configured. Whether they are mandatory for every protected-branch update is not established; the roadmap says branch protection is currently absent. |
| Action pinning | Reviewed CI and release workflow steps use full commit SHAs for the checkout, setup-python, provenance-attestation, and artifact-upload actions. | Positive evidence for the reviewed actions; not a complete organization-wide supply-chain audit. |
| Workflow permissions | CI has top-level `contents: read`; the release job scopes OIDC and attestations permissions to the release job. | Good least-privilege pattern in the reviewed files. Organization-level Actions policy and fork settings are not independently verified here. |
| Static/dependency checks | Ruff, mypy, Bandit and `pip check` are configured; Dependabot weekly updates are configured for pip and GitHub Actions. | Dependency metadata consistency is not the same as vulnerability scanning. A vulnerability-database audit and explicit failure policy still need evidence. |
| Container security | The isolation job builds the browser stack and tests proxy-only egress and Chromium sandboxing. | These are isolation tests, not container-image vulnerability scans. No image vulnerability scanner was observed in the reviewed CI/release workflow. |
| Reproducible release | Release workflow builds from two clean `git archive HEAD` trees, normalizes source distributions and compares SHA-256 digests. | Configured; the current review did not establish a completed release run on a test tag. |
| SBOM | Release workflow generates `dist/twi-build-environment.cdx.json` with CycloneDX using the project metadata. | Generation is configured. Confirm its actual contents and runtime dependency coverage from a completed run before calling it a complete release SBOM. |
| Provenance | Release workflow invokes `actions/attest-build-provenance` with OIDC and attestation permissions. The roadmap says the attestation service has not yet been exercised. | **Not operationally verified.** A configured action is not evidence of a valid, retrievable, independently verified attestation. |
| Artifact distribution | The release workflow uploads artifacts as a workflow artifact with 30-day retention. No durable release publication step was observed in the reviewed workflow. | Temporary artifact retention alone is not a durable customer release channel. |
| Staging | `deployments/compose/staging.yml` defines API, worker, migration, browser broker/worker, egress proxy and World Intelligence exporter services with external credential requirements. | Deployment topology is repository evidence; no approved target workspace or live staging run is established. |

## W7 exit blockers

1. **G1 — Enforceable branch governance:** the repository roadmap records that `main` is unprotected and ruleset creation was blocked by MFA/sudo. The authorized repository owner must complete the GitHub security step to apply a suitable ruleset, then capture effective rule IDs, review requirements, required status checks, bypass actors, and evidence timestamp. Do not claim G1 passed before the resulting settings are re-read.
2. **G2 — Vulnerability assurance:** add a pinned dependency vulnerability audit to CI/release and choose an image-scanning control for shipped containers. The scan must emit machine-readable evidence, fail on the defined severity threshold, and distinguish scanner/network failure from a clean result.
3. **G3 — Provenance exercise:** execute a non-production test-tag release; preserve the exact source SHA, wheel/sdist, SBOM, checksums and attestation; independently verify the attestation against the expected repository/workflow/source and show tampered or unsigned artifacts are rejected. Decide and implement a durable distribution/retention strategy.
4. **G4 — Evidence pack:** retain run links, artifact metadata/hashes, SBOM, vulnerability results, attestation verification output, effective rules, owner, timestamps and residual-risk decisions in a durable audit record.
5. **Environment gates:** confirm the staging provider/workspace before any billable provisioning. Then verify PostgreSQL TLS and role separation, secrets and rotation, real API/browser egress, cross-system Platform → TWI → World Intelligence journey, monitoring/alert delivery, backup restore, rollback and on-call response.

## Gate state

- **G1 branch governance:** **OPEN — effective rules must be applied and re-read**.
- **G2 CI/security enforceability:** **PARTIAL — repository tests exist; vulnerability/image scan coverage and mandatory-check enforcement need evidence**.
- **G3 release traceability:** **PARTIAL — reproducible build, checksums, SBOM generation and attestation action are configured; a test release and independent attestation verification are missing**.
- **G4 evidence ownership:** **OPEN**.
- **G5 W7 exit:** **NOT MET**.

No infrastructure was provisioned and no GitHub security settings were changed during this review. This document does not claim a live penetration test, restore drill, deployed staging environment, security certification, completed release, or private-beta approval. W8–W10 repository work already present on main does not bypass the serial W7 release gate.
