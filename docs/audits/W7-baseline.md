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
| TWI main CI | Main revision `cf992a6fd11b0ff44e6de377af40812af1221790`; latest observed main CI completed successfully. | Repository verified |
| Python and test gates | CI runs Python 3.12 and 3.13 quality/type/security lint, unit/contract/PostgreSQL integration tests, migration checks, Chromium smoke tests, and a browser-isolation job. | Repository verified |
| Browser network isolation | CI builds the isolated Compose services, checks that direct public egress is blocked while proxy access works, and launches Chromium with its sandbox enabled. This proves the CI topology, not the target deployment's network policy. | Repository verified; deployment unverified |
| Release workflow | `.github/workflows/release.yml` runs on `v*` tags or manual dispatch, runs quality/type/security/database checks, validates the development Compose configuration, builds the Python distribution, installs the wheel, and runs `scripts/verify_release.py`. | Repository verified |
| Release provenance | The reviewed release workflow does not itself demonstrate a completed signed release, SBOM publication, artifact attestation, or independent provenance verification. Do not infer these from a successful build. | Proposed / unverified |
| Main branch protection | The connected repository inspection used for this audit did not expose authoritative branch ruleset/protection details. No conclusion is drawn that rulesets are absent or present. | Unverified |
| TADL ecosystem integration | TADL main commit `e249aef82b096d99345b7482c8f39c031dfee77a`; post-merge Ecosystem Integration run [39208247623](https://github.com/LloydCoder/tinlance-agent-developer/actions/runs/39208247623) completed successfully. | Repository verified |
| TWI reviewed pin | TADL `ecosystem.lock.json` pins TWI to `cf992a6fd11b0ff44e6de377af40812af1221790`, matching the audited TWI main revision. | Repository verified |
| World Intelligence security pin | TADL lock and manifest pin World Intelligence to `a156844575795b5fe9ce80b6e090a0d828e592d4`, the merged Platform-JWT security fix. The follow-up TADL main integration run passed against the updated lock. | Repository verified |
| Production deployment | No deployment-specific evidence has been supplied or verified for production PostgreSQL, secret-manager rotation, actual API/browser egress, monitoring, backup restore, or on-call response. | Operationally unverified |
| Private-beta approval | The existing private-beta checklist remains unchecked; no authorized release approval is recorded here. | Not certified |

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
