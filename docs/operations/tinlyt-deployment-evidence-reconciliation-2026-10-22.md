# Tinlyt deployment evidence reconciliation — 2026-10-22

**Status: NOT CERTIFIED for private beta.** This is a current evidence ledger, not a claim that production deployment or recovery has been completed.

## Source and CI evidence

| Check | Evidence | Result |
|---|---|---|
| Audited source revision | `main` at `f7594814fe14dbcd1115ee38096e9153b8a2a77b` | Confirmed via GitHub |
| Repository CI | [Run 39762376911](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39762376911) | All four jobs completed successfully |
| Python 3.12 | Job 119769441083 | Passed; PostgreSQL dump/restore round-trip passed |
| Python 3.13 | Job 119769440979 | Passed |
| Browser isolation | Job 119769441168 | Passed |
| Reproducible release artifact validation | Job 119769440938 | Passed |
| Remediation PRs | [#108](https://github.com/LloydCoder/tinlance-web-intelligence/pull/108), [#109](https://github.com/LloydCoder/tinlance-web-intelligence/pull/109), [#110](https://github.com/LloydCoder/tinlance-web-intelligence/pull/110), [#111](https://github.com/LloydCoder/tinlance-web-intelligence/pull/111), [#112](https://github.com/LloydCoder/tinlance-web-intelligence/pull/112) | All merged |

The CI restore test creates a PostgreSQL 17 custom-format dump, restores it into a separate database, and checks schema version 4, a probe record, and persistence-table row counts. It is **not** a witnessed restore of a real encrypted deployment backup.

## Current frontend provider evidence

Read-only Vercel inspection on 2026-10-22 returned:

- Project: `tinlyt-web` (`prj_ypYtRbHtPYejZUHRwAYmHurmXgSM`).
- Latest reported production deployment: READY, deployment `dpl_3Z6ncUanyXtqjX5LGCv1T64bW4m9`.
- That deployment is built from `main` commit `28722145517a1d8cb8b44d5fcbd175c380f1bd45`, which predates the final documentation/CI-only PR #112 merge at `f7594814fe14dbcd1115ee38096e9153b8a2a77b`.
- Project domains include `tinlyt.tinlance.com` and `tinlyt-web.vercel.app`.
- The environment-variable inventory returned zero variables and `hiddenProductionEnvCount=0`.
- The frontend remains deployed, but its runtime configuration is not integrated with a verified API origin or Platform identity configuration. A READY static/frontend deployment does not prove an authenticated product journey.

No redeploy or production environment change was attempted. The latest commit after the production deployment only adds the CI restore drill and its documentation, not a frontend behavior change.

## Remaining gates — deployment evidence is absent

| Gate | Current evidence/status | Required closure evidence |
|---|---|---|
| Dedicated Tinlyt PostgreSQL | No approved production DSN or live connection evidence in this audit | Approved dedicated database; immutable resource identity; TLS `sslmode=verify-full`; trusted CA; least-privilege runtime/migration/backup/restore/retention roles |
| Hosting/billing | Prior recovery ledger records a Render resource-creation HTTP 402; no new paid resource was attempted | Account owner chooses a supported workspace/provider and approves any recurring cost before provisioning |
| API and workers | No current live Tinlyt API deployment or health-check evidence was returned in this audit | Immutable deployed revision, API/worker inventory, authenticated readiness checks, private network and egress verification |
| Platform identity | No issuer/audience/JWKS and live Platform-issued test token verified here | Canonical Platform settings; positive and negative auth tests; tenant/scope/subject enforcement evidence |
| Entitlements | No approved production resolver contract or live billing/entitlement path verified | Reviewed canonical contract and adapter; fail-closed unknown-plan behavior; quota/billing ledger integration tests |
| Real backup recovery | CI restore round-trip passes; production recovery remains untested | Encrypted backup outside the DB failure domain; checksum/retention evidence; witnessed isolated restore; recorded achieved RPO/RTO |
| Monitoring and incident response | Repository runbooks exist; live alerts/on-call/rollback exercise not evidenced | Live metrics/logs/traces, alert delivery, named owner, and witnessed rollback/incident drill |
| GitHub branch governance | GitHub reports branch protection disabled for `main` | Enable required checks and PR-only changes through repository settings; verify rules are enforced |
| External ecosystem gates | W15 evidence pack intentionally reports `ready=false` for unevidenced integrations | Verify Platform monitor-tool registration/policy, World Intelligence consumer revision, TSIC conformance, and budget/ownership gates against live systems |

## Safety constraints

- Do not provision or modify paid resources without explicit cost approval.
- Do not reuse the unrelated Hezqara database, create a Supabase project, or invent identity/entitlement credentials.
- Do not put credentials in this ledger, public frontend variables, logs, or repository files.
- Do not enable customer traffic or describe Tinlyt as production-ready until all mandatory gates above have evidence and the authorized owner approves release.

## Release decision

Repository CI is green on the recorded main revision. **Production/private-beta release remains blocked** by external infrastructure, identity, entitlement, recovery, branch-governance, and integration evidence. Re-run this reconciliation against live provider state before any release decision.
