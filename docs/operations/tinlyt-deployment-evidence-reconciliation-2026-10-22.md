# Tinlyt deployment evidence reconciliation — 2026-10-22

**Status: NOT CERTIFIED for private beta.** This is a current evidence ledger, not a claim that production deployment or recovery has been completed.

## Source and CI evidence

| Check | Evidence | Result |
|---|---|---|
| Audited source revision | `main` at `820883345cfff43f8c70b0340751258ae4677ea2` | Confirmed via GitHub |
| Repository CI | [Run 39768780762](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39768780762) | All four jobs completed successfully |
| Python 3.12 | Job 119790772334 | Passed; PostgreSQL dump/restore round-trip passed |
| Python 3.13 | Job 119790772495 | Passed |
| Browser isolation | Job 119790772501 | Passed |
| Reproducible release artifact validation | Job 119790772664 | Passed |
| Remediation PRs | [#108](https://github.com/LloydCoder/tinlance-web-intelligence/pull/108), [#109](https://github.com/LloydCoder/tinlance-web-intelligence/pull/109), [#110](https://github.com/LloydCoder/tinlance-web-intelligence/pull/110), [#111](https://github.com/LloydCoder/tinlance-web-intelligence/pull/111), [#112](https://github.com/LloydCoder/tinlance-web-intelligence/pull/112), [#114](https://github.com/LloydCoder/tinlance-web-intelligence/pull/114) | All merged |

The CI restore test creates a PostgreSQL 17 custom-format dump, restores it into a separate database, and checks schema version 4, a probe record, and persistence-table row counts. It is **not** a witnessed restore of a real encrypted deployment backup.

## Current frontend provider evidence

Read-only Vercel inspection on 2026-10-22 returned:

- Project: `tinlyt-web` (`prj_ypYtRbHtPYejZUHRwAYmHurmXgSM`).
- Latest reported production deployment: READY, deployment `dpl_CeMxzKbnp7p1nM2bxw9rEuMQyKFc`, built from the exact current `main` commit `820883345cfff43f8c70b0340751258ae4677ea2`.
- Vercel reports aliases `tinlyt.tinlance.com`, `tinlyt-web.vercel.app`, and project-generated deployment aliases. The two project domains `tinlyt.tinlance.com` and `tinlyt-web.vercel.app` are verified.
- Read-only rendered-page fetches succeeded for `/` and `/app` on both the custom domain and the Vercel alias. The landing page remains `noindex, nofollow`. The workspace states that live investigation submission requires the approved Platform identity flow and valid deployment runtime settings; it presents no fixture data as live activity.
- The Vercel project still reports `live=false` and SSO protection enabled for all deployment types except custom domains. The successful custom-domain page fetch confirms rendering, not a complete public launch or authenticated journey.
- The environment-variable inventory returned `envs=[]` and `hiddenProductionEnvCount=0`. No API origin or Platform identity configuration is currently set in this Vercel project.

Vercel automatically reports a READY production deployment for the current main SHA. No manual redeploy, environment-variable change, or frontend behavior change was performed. The exact commit's CI run 39768780762 passed all four jobs, including the PostgreSQL restore round-trip, container vulnerability policy, browser egress-proxy test, and Chromium sandbox check.

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
| External ecosystem gates | Platform consumer registration snapshot now passes against `tinlance-agent-platform` revision `c5a080c1fb4df68e45070f8cddfc30bf81edd7bb`; W15 remains `ready=false` because other gates are not evidenced | Verify effective live Platform policy, World Intelligence ingestion, TSIC conformance, and budget/ownership gates against the target systems |

## Safety constraints

- Do not provision or modify paid resources without explicit cost approval.
- Do not reuse the unrelated Hezqara database, create a Supabase project, or invent identity/entitlement credentials.
- Do not put credentials in this ledger, public frontend variables, logs, or repository files.
- Do not enable customer traffic or describe Tinlyt as production-ready until all mandatory gates above have evidence and the authorized owner approves release.

## Release decision

Repository CI is green on the recorded main revision. **Production/private-beta release remains blocked** by external infrastructure, identity, entitlement, recovery, branch-governance, and integration evidence. Re-run this reconciliation against live provider state before any release decision.
