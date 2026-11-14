# T0 execution baseline — 2026-11-14

**Status:** OPEN — forensic baseline established; governance and deployment blockers remain.
**Repository:** `LloydCoder/tinlance-web-intelligence`
**Observed main revision:** `48a89f64a77d125e07ac9816b73738e4e6106dc8`
**Audit date:** 2026-11-14 (UTC observations recorded below)

## 1. Evidence and method

This checkpoint uses live GitHub repository, branch, commit, workflow, readiness-file and Vercel project/deployment reads, plus live HTTP fetches of the custom-domain homepage, workspace and TWI health route. It is a bounded T0 checkpoint, not a complete source-by-source audit of all 471 repository files, every connected Tinlance repository, every cloud resource, or a private-beta/GA certification.

Evidence hierarchy: provider state and exact-revision code/configuration; exact-SHA workflow results; live deployment and HTTP observations; readiness records; historical project notes. Historical notes are not promoted to current facts without a fresh provider check.

## 2. GitHub repository state

- Repository is public, Apache-2.0, default branch `main`, not archived.
- Main HEAD: `48a89f64a77d125e07ac9816b73738e4e6106dc8` (2026-11-08).
- Main branch metadata reports `protected: false`.
- Repository rulesets endpoint returned an empty list.
- Connected GitHub integration returned HTTP 403 for the branch-protection read endpoint; branch metadata independently reports unprotected. No branch-protection mutation endpoint is available through the exposed integration tools.
- No open pull requests and no open issues were returned at the time of this checkpoint.
- Recursive tree contains 471 entries; five workflows exist: CI, Frontend, Release readiness, OpenSSF Scorecard and Supabase database tests.

### Workflow evidence

- Main CI run `42482451739`: success on `48a89f64a77d125e07ac9816b73738e4e6106dc8`.
- OpenSSF Scorecard run `42621541720`: success on the same main revision.
- Latest Frontend run in the inspected recent history: success on dependency-update revision `9d2a28527b30e1c534de3704be6c980e7b37cf6a`, not the exact main HEAD.
- Latest Supabase database test shown in the inspected recent history: success on `719fee9593fa1e0d208f5695f88527db471f6741`, not the exact main HEAD.
- The combined commit status for main reports a successful Vercel status context.

The CI workflow includes Python quality/type/security checks, dependency audit, PostgreSQL tests and restore drill, W15 evidence-pack validation, browser runtime tests, isolated Compose validation, browser egress-bypass checks, Chromium sandbox checks and Trivy container scans. Trivy action steps use `continue-on-error: true` and `exit-code: 0`, but a later explicit enforcement step checks scanner completion and fails for fixable HIGH/CRITICAL findings. Unfixed HIGH/CRITICAL findings are retained for explicit security review and are not automatically cleared.

## 3. Vercel state and live route checks

Vercel team: `lloydcoders-projects` (Hobby plan).
Project: `tinlyt-web` (`prj_ypYtRbHtPYejZUHRwAYmHurmXgSM`).
Project metadata reports `live: false`, SSO protection enabled for deployments except custom domains, and domains `tinlyt.tinlance.com` and `tinlyt-web.vercel.app`. The custom domain is verified.

Latest production-targeted deployment:
- Deployment: `dpl_dk8TcRgmqyfQzbWnGiBNoZUwbaHY`
- State: `READY`
- Source: `main` / `48a89f64a77d125e07ac9816b73738e4e6106dc8`
- URL: `tinlyt-hgixu9az5-lloydcoders-projects.vercel.app`

Live HTTP observations on 2026-11-14:
- `https://tinlyt.tinlance.com/`: HTTP 200.
- `https://tinlyt.tinlance.com/app`: HTTP 200.
- `https://tinlyt.tinlance.com/api/twi/health`: HTTP 404 (Vercel NOT_FOUND).

The homepage explicitly says workspace access is still being integrated and that live access is unavailable. It carries `noindex, nofollow`. The workspace renders Foundation mode, API disconnected, and sign-in unavailable; investigation controls are disabled. The page describes the current verifier as citation/quote matching rather than factual truth assessment, and monitors as explicit-run rather than recurring. These are honest fail-closed states, not a functioning customer production workflow.

A Vercel production deployment being READY does not mean the TWI API/backend is deployed. The project-level `live: false` field and the HTTP 404 on the health route reinforce that the frontend deployment must not be represented as a live full platform.

## 4. Existing readiness record

The current `docs/readiness/w15-gates.json` records repository gates as passing and the external consumer-approval gate as passing, but these external gates remain `not_evidenced`:
- `external.branch_governance`
- `external.deployment_and_security`
- `external.slo_alerts_and_oncall`
- `external.privacy_retention_and_risk`
- `external.live_quality_and_ga_approval`

Do not mark these gates passed based on this checkpoint. In particular, branch protection is demonstrably absent; the backend health route is 404; and no live quality/GA evidence was established.

## 5. Uploaded logo kit

The conversation upload `tinlyt-logo-kit.zip` contains a 31-entry v1 draft kit: SVG and PNG lockups/icons, favicons, PWA/app icons, usage sheets and the Outfit SIL Open Font License text. Its README explicitly says the identity is draft and the Tinlyt name/mark are not trademark-cleared; it calls for searches in TMview, USPTO and the Nigerian registry (classes 9 and 42). The production homepage currently loads `/tinlyt-logo-dark-bg.svg`. Do not treat inclusion in the repository or use on the site as trademark clearance. A byte-for-byte comparison of every supplied asset with repository assets has not yet been completed.

## 6. Confirmed blockers and risks

| ID | Priority | Finding | Required next action |
|---|---|---|---|
| T0-01 | P0 | Main branch is unprotected; rulesets endpoint empty | Repository administrator must configure required PR reviews and mandatory checks; verify enforcement independently |
| T0-02 | P0 | TWI health route returns 404; no live backend journey | Reconcile AWS/runtime state, design and approve least-privilege deployment, then deploy and verify exact target |
| T0-03 | P0 | Current workspace has no configured identity/API runtime | Complete Platform production composition and OAuth/runtime configuration; test authenticated tenant-scoped journeys |
| T0-04 | P0 | Private-beta/GA external gates remain not evidenced | Keep beta/GA and public live operations uncertified until evidence exists |
| T0-05 | P1 | Homepage remains noindex/nofollow and workspace foundation-only | Retain fail-closed state; remove noindex only after owner launch and legal/brand gates |
| T0-06 | P1 | Current verifier is quote correspondence, not semantic truth assessment | Implement and benchmark atomic claim support/contradiction assessment |
| T0-07 | P1 | Monitor UI says explicit runs only; recurrence belongs to Agent OS | Complete structured monitoring and governed recurrence integration after TAS/FCP gates |
| T0-08 | P1 | Logo/name are explicitly draft and uncleared | Complete trademark clearance and asset provenance/consistency review before public promotion |
| T0-09 | P1 | Exact-main frontend and Supabase workflow evidence not established in recent history | Run required frontend/Supabase workflows against the intended current revision and preserve exact-SHA artifacts |

## 7. Constraints carried forward

- No Render.
- No unapproved paid AWS resources or resource creation before checking the current credit/cost position and approved deployment design.
- Do not use AWS root for routine deployment.
- Do not modify FusionOps/ThreatFade resources or Tinlance's main website/domain.
- Keep early-access intake disabled until its credential, privacy/legal and end-to-end gates pass.
- Keep authenticated workspace operations disabled until Platform and TWI runtime are deployed and tested.
- Keep Tinlyt independent of TAS while preserving the agreed sequence for deep integration after TAS/FCP acceptance.
- Do not retire Parallel or TinyFish until the replacement benchmark passes.

## 8. T0 exit criteria

T0 remains OPEN until:
1. All roadmap/readiness documents are reconciled against the exact main revision.
2. Relevant source modules and tests have been re-audited against the current tree.
3. AWS, Supabase and Vercel state are reconciled without touching unrelated services or provisioning resources.
4. Repository governance is enforced or a documented administrator-owned blocker remains explicitly assigned.
5. A dependency-aware implementation backlog is linked to exact files, tests, owners and acceptance evidence.

**No application code, production configuration, cloud resource, customer data or production route was changed during this checkpoint.** The only planned repository change from this audit is this documentation checkpoint on a separate branch; it does not certify T0 completion.
