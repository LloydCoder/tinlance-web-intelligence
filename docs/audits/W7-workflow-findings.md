# W7 follow-up — workflow and release-supply-chain findings

**Review date:** 2026-10-19  
**Reviewed main baseline:** `df36c8fce2e463f0ed5d12fc3a2aa392119edc09`  
**Scope:** workflow configuration and readiness checklist review through the connected GitHub repository interface.  
**Decision:** W7 remains **IN PROGRESS**; private beta remains **NOT CERTIFIED**.

## Evidence and findings

| Control | Observed evidence | Assessment |
|---|---|---|
| Pull-request/main CI | `.github/workflows/ci.yml` checks Python 3.12/3.13, Ruff, mypy, Bandit, pytest/PostgreSQL, migration sync, browser runtime, Compose isolation, Chromium sandbox, and reproducible artifacts. | Repository controls exist; no claim that these controls are required by effective branch rules because those rules were not readable through the connected GitHub tool surface. |
| Action pinning | Reviewed CI/release workflows use full commit SHAs for checkout, setup-python, attestation, and artifact upload actions. | Positive repository evidence for reviewed actions only; not a full repository-wide action inventory. |
| Workflow permissions | CI has top-level `contents: read`; release has top-level `contents: read` and narrowly scoped job permissions including `id-token: write` and `attestations: write`. | Least-privilege direction is present in reviewed files; organization/repository Actions policy remains unverified. |
| Static security checks | CI and release run Bandit. Dependency installation runs `pip check`. Dependabot is configured for pip and GitHub Actions weekly updates. | These do not establish vulnerability-database auditing or prove no vulnerable dependencies. No `pip-audit` or equivalent dependency vulnerability scan was observed in the reviewed workflow. |
| Container security | CI builds isolated browser services and tests egress behavior and Chromium sandboxing. | No image vulnerability scanner was observed in the reviewed CI/release workflow. Build/isolation tests are not vulnerability scans. |
| Release reproducibility | Release workflow builds from two clean `git archive HEAD` trees, normalizes source distributions, and compares SHA-256 hashes. CI has a reproducible-artifact validation job too. | Repository-configured; an actual release run is needed for operational evidence. |
| SBOM | Release workflow installs `cyclonedx-bom==7.5.0` and generates `dist/twi-build-environment.cdx.json` using `cyclonedx-py environment --pyproject pyproject.toml`. | SBOM generation is configured. The evidence must still establish that the generated inventory covers the intended release/runtime dependency scope, rather than treating the filename alone as proof of complete coverage. |
| Provenance attestation | Release workflow invokes `actions/attest-build-provenance` against `dist/*`, with job permissions for OIDC and attestations. | Attestation generation is configured; no completed tagged release run, independently verified attestation, or artifact-to-source verification evidence was observed during this review. |
| Artifact retention/publication | Release workflow uploads the wheel, source archive, SBOM and checksum file as a workflow artifact with 30-day retention. | This is temporary workflow-artifact retention, not a durable customer release. No GitHub Release publication step was observed in the reviewed file. |
| Branch governance | Repository metadata confirms the linked account has admin permission, but the available connector surface did not expose effective branch protection/rulesets or inherited organization rules. | **Unverified blocker.** Do not infer that rules are absent or present. No settings were changed. |
| Staging deployment | `deployments/compose/staging.yml` defines a staging topology and requires external PostgreSQL, Platform identity, browser broker/proxy, and World Intelligence credentials. | Deployment topology is repository evidence only; no target workspace or deployed staging instance was verified. |

## Required remediation before W7 exit

1. **G1 — Governance evidence:** retrieve the effective repository and inherited organization rules for `main`; record rule identifiers, required checks, review thresholds, bypass actors and retrieval time. If the integration cannot read them, use authenticated GitHub UI/API evidence and attach it to the audit record.
2. **G2 — Vulnerability coverage:** add a pinned, reproducible dependency vulnerability audit to CI/release and decide on image scanning for every shipped container image. Produce machine-readable results and define the policy for critical/high findings; do not turn network/tool failures into silent passes.
3. **G3 — Release provenance:** run the release workflow on a non-production test tag, preserve the exact source SHA and artifact hashes, independently verify the attestation, and prove that altered artifacts fail verification. Decide whether workflow artifacts are sufficient for the beta or whether a GitHub Release/package registry is required; 30-day retention alone is not durable release distribution.
4. **G4 — Evidence ownership:** store the workflow run, artifact metadata, SBOM, checksums, attestation verification output, scan results, rule evidence, owner, timestamp and residual-risk disposition in a durable audit record.
5. **Operational gates:** choose and confirm a staging provider/workspace before provisioning anything billable. Exercise database TLS/roles, secret rotation, browser/API egress, monitoring/alerts, backup restore, rollback and on-call procedures in that environment.

## Acceptance status

- G1 branch governance: **BLOCKED / UNVERIFIED**.
- G2 CI/security enforceability: **PARTIAL**; repository checks exist, effective required-check enforcement and vulnerability/image scan coverage remain unverified/incomplete.
- G3 release traceability: **PARTIAL**; reproducible build, checksum, SBOM generation, provenance attestation and artifact upload are configured, but no observed release-run evidence, independent attestation verification, or durable publication was established.
- G4 evidence/ownership: **OPEN**.
- G5 W7 exit: **NOT MET**.

This review does not claim a deployment, penetration test, restore drill, completed release, security certification, or private-beta approval. Do not advance the serial release gate until the blockers above are evidenced or explicitly accepted by the authorized owner.
