# W7 baseline — governance and release supply chain

**Baseline date:** 2026-10-19  
**Baseline TWI main commit:** `cf992a6fd11b0ff44e6de377af40812af1221790`  
**Baseline TWI CI:** [run 39200421248](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39200421248) — completed successfully.  
**Release state:** W7 baseline only; private beta remains **NOT CERTIFIED**.

## Evidence classification

Use these labels consistently:

- **Repository verified:** directly supported by the reviewed source, configuration, or completed GitHub run.
- **Operationally verified:** exercised in the actual target environment with recorded evidence.
- **Proposed / unverified:** a requirement or assertion that still needs direct evidence.

A green CI run is repository evidence, not proof of production deployment, branch protection, or release authorization.

## Reconciled baseline

| Area | Current evidence | Classification |
|---|---|---|
| TWI main CI | Baseline revision `cf992a6fd11b0ff44e6de377af40812af1221790`; later main CI also passed on `3b96b06caf9f0afe8a9fdec96ff64e42e3b13246` in [run 39224876152](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39224876152). | Repository verified |
| Python and test gates | CI runs Python 3.12 and 3.13 quality/type/security lint, unit/contract/PostgreSQL integration tests, migration checks, Chromium smoke tests, and a browser-isolation job. | Repository verified |
| Browser network isolation | CI builds the isolated Compose services, checks that direct public egress is blocked while proxy access works, and launches Chromium with its sandbox enabled. This proves the CI topology, not the target deployment's network policy. | Repository verified; deployment unverified |
| Release workflow | `.github/workflows/release.yml` runs on `v*` tags or manual dispatch, runs quality/type/security/database checks, validates the development Compose configuration, builds the Python distribution, installs the wheel, and runs `scripts/verify_release.py`. | Repository verified |
| Release provenance | W7 PR #26 verified reproducible wheel/sdist outputs and CycloneDX SBOM generation. Non-production Release readiness run [#39227160547](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39227160547) generated artifact attestations, independently verified provenance for each artifact, and rejected a tampered wheel. No customer-facing release publication is claimed. | Repository-level attestation and tamper verification passed; customer release unverified |
| Main branch governance | Recheck on 2026-10-19: the GitHub branches API returned `protected=false`, `protection.enabled=false`, and required status-check enforcement `off` for `main`; the repository rulesets API returned an empty list. The connected GitHub integration's dedicated branch-protection endpoint returned 403 because its installation lacks administration-read access. The successful branch/ruleset responses are direct evidence that no repository-level protection is currently reported; inherited organization rules are not proven by this repository-only read. | Repository-level protection absent; inherited organization rules not verified |
| TADL ecosystem integration | TADL main commit `e249aef82b096d99345b7482c8f39c031dfee77a`; post-merge Ecosystem Integration run [39208247623](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39208247623) completed successfully. | Repository verified |
| TWI reviewed pin | TADL `ecosystem.lock.json` pins TWI to `cf992a6fd11b0ff44e6de377af40812af1221790`, matching the audited TWI main revision at that time. The pin must be reconciled to a reviewed release SHA before a release candidate is certified. | Repository verified at baseline; current release pin reconciliation required |
| World Intelligence security pin | TADL lock and manifest pin World Intelligence to `a156844575795b5fe9ce80b6e090a0d828e592d4`, the merged Platform-JWT security fix. The follow-up TADL main integration run passed against the updated lock. | Repository verified |
| Production deployment | No deployment-specific evidence has been supplied or verified for production PostgreSQL, secret-manager rotation, actual API/browser egress, monitoring, backup restore, or on-call response. | Operationally unverified |
| Private-beta approval | The existing private-beta checklist remains unchecked; no authorized release approval is recorded here. | Not certified |

## Current recheck — 2026-10-19

- Latest observed `main` commit at recheck: `3b96b06caf9f0afe8a9fdec96ff64e42e3b13246`.
- Main CI [run 39224876152](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39224876152) passed all four jobs. A separate run previously observed as cancelled is not treated as a failure or as a passing run; use the exact main run above as the current successful evidence.
- Non-production Release readiness run [39227160547](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39227160547) passed on temporary test commit `afd3807a09f5495669e6dd7ec10f6aa71be05b92`, including signed artifact attestations, independent provenance verification, and the tampered-wheel negative test. The temporary branch trigger was removed from the final PR head; this run is test evidence, not a customer release.
- The initial open-PR search was stale/incomplete: a subsequent live search found PRs #54, #55, and #56 open. PR #54 is a duplicate W12 closeout whose content is already represented on `main`; PR #55 is premature W13 work while W7–W12 release gates remain open; this PR (#56) is the W7 evidence-reconciliation change.
- `main` is reported unprotected by the branches API and no repository rulesets were returned. This is a confirmed W7 blocker, not a documentation-only issue. The connected integration cannot mutate or fully inspect branch governance because its GitHub installation lacks the required administration permissions.
- Do not close G1 until an authorized owner enables enforceable rules and effective settings are read back. If inherited organization policy is relied on, capture evidence from the organization-level ruleset scope and prove it applies to this repository.

## W7 objective

Establish enforceable repository governance and a traceable, reproducible release supply chain without treating documentation or green CI as a substitute for configuration and release evidence.

## W7 acceptance tests

### G1 — Branch governance is inspected and evidenced

- Retrieve the effective rules for `main`, including repository and inherited organization rulesets and branch-protection settings.
- Record the exact API/UI evidence, retrieval timestamp, repository, and effective rule identifiers.
- Verify that direct pushes and force pushes are restricted as intended; required pull-request review and status checks are explicit; bypass actors are narrow and justified.
- Verify the required checks correspond to real workflows and cannot be satisfied by a different commit or an outdated check.
- If settings cannot be read or a required control is absent, record a blocker; do not report this gate as passed.

### G2 — CI and security gates are enforceable

- Exercise a pull request against the exact head SHA and confirm all required checks are attached to that SHA.
- Verify workflow permissions follow least privilege, third-party actions use immutable commit references, and secrets are unavailable to untrusted fork code.
- Review dependency, static-analysis, secret-scanning, and container/image scanning coverage. Record findings and risk acceptance explicitly; do not claim a scan passed if no such run exists.
- Confirm post-merge main checks pass for the resulting merge commit.

### G3 — Release artifacts are traceable

- Build the distribution from a clean, exact commit using the pinned toolchain.
- Verify artifact contents, hashes, metadata, and reproducibility expectations; record the source SHA and workflow run.
- Define and implement the required SBOM, vulnerability results, provenance/attestation, and signature verification appropriate to the release threat model.
- Verify the published artifact maps to the reviewed source commit and that tampered or unsigned artifacts fail the configured verification policy.
- Exercise the release workflow with a non-production test release path before using it for a customer-facing release.

### G4 — Evidence and ownership are durable

- Store links or machine-readable records for the effective branch rules, exact-head checks, release artifacts, hashes, scan results, and attestations.
- Assign an owner and timestamp to each gate; document remediation and accepted residual risk.
- Preserve the authority boundary: TWI acquires and exports evidence; Agent Platform remains the identity, policy, approval, and execution authority; World Intelligence remains the canonical world-state layer; TSIC remains the system-of-systems conformance authority.

### G5 — W7 exit decision

W7 is complete only when G1–G4 have evidence, the exact PR head and post-merge main checks are green, and unresolved governance or release-supply-chain blockers are either fixed or explicitly risk-accepted by the authorized owner. A passing documentation PR alone cannot satisfy W7.

## Explicitly outside this baseline

- No branch-protection/ruleset mutation has been made by this audit.
- No production or staging infrastructure has been provisioned.
- No live penetration test, backup restore drill, production release, or private-beta approval is claimed.
- W8–W15 remain proposed workstreams; W8 findings may create evidence-backed corrective tasks in W9/W10 without relaxing serial release gates.
