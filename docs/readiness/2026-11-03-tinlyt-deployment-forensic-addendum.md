# Tinlyt deployment forensic addendum — 2026-11-03

## Scope and evidence boundary

This addendum reconciles the current Tinlyt frontend and Agent Platform integration state with the production deployment evidence available on 2026-11-03. It supplements the historical phase ledger; it does not certify private beta or GA.

Repositories audited:
- TWI/Tinlyt: `LloydCoder/tinlance-web-intelligence`
- Governed identity and execution boundary: `LloydCoder/tinlance-agent-platform`

Exact revisions:
- TWI main: `45211fac5138b1df5923d746bf94fff6103d2857` — Cognito PKCE resource-binding and trusted-origin correction (PR #131).
- Agent Platform main: `4e73e8272d222fd7234f86a3cf005ef2fc79b1a0` — Cognito V2 tenant-membership pre-token trigger (PR #160).

## Confirmed repository integration

The following changes are merged:
- TWI PR #128: public, allowlisted browser runtime configuration for Platform OAuth and API settings. It does not create identity services or set Vercel variables.
- TWI PR #129: routes browser operations through the governed Platform API envelope; preserves idempotency and evidence-byte integrity; fails closed for unsupported destructive monitor actions.
- TWI PR #130: calls the Platform session-revocation endpoint on sign-out and distinguishes confirmed server-side revocation from local token clearing.
- TWI PR #131: keeps Cognito resource binding on the authorization request, omits it from the authorization-code token exchange, and requires independently trusted issuer and OAuth endpoint origins.
- Platform PRs #154–#160: add strict Cognito access-token validation, session-family revocation, authenticated revocation API and audit correlation, DynamoDB revocation storage, and Cognito V2 tenant-membership claims.

These are repository-level implementation facts. They do not prove that the corresponding AWS resources or API services exist in a live environment.

## Vercel deployment state

The Vercel project is `tinlyt-web` (`prj_ypYtRbHtPYejZUHRwAYmHurmXgSM`).

The latest main-branch production deployment observed during this audit:
- Deployment: `dpl_Bkh3ppPTCarHUmJvESvPL9vV3piT`
- State: `READY`
- URL: `tinlyt-9lxk0dwfl-lloydcoders-projects.vercel.app`
- Source commit: `f94d024e0949a75dafe6df1d7c401d2ac7c0df9b` (Node 22 runtime pin)
- Aliases: `tinlyt.tinlance.com`, `tinlyt-web.vercel.app`, and the Vercel main aliases

The previous main deployment from commit `45211fac5138b1df5923d746bf94fff6103d2857` was superseded by this production deployment.

The project live flag was reported as `false` in the earlier project metadata snapshot; deployment-level metadata now confirms the latest `main` deployment is targeted at `production` and aliases include `tinlyt.tinlance.com` and `tinlyt-web.vercel.app`. Preview SSO protection is enabled; custom domains are excluded from that protection. The project-level `live` field and a production-targeted deployment are different signals; the latter confirms the current frontend release was promoted to the production deployment target.

PR #133 was merged as commit `f94d024e0949a75dafe6df1d7c401d2ac7c0df9b`; its frontend and full CI workflows passed, including Python 3.12/3.13, reproducible artifacts, and browser-container isolation. Vercel selected Node `22.x` after the package engine was pinned; this corrects the previous `>=22` declaration that caused Vercel to select Node `26.x`. The production custom-domain landing and `/app` routes both return HTTP 200.

A READY deployment is not proof that the authenticated application works. The Vercel project environment inventory returned only `EARLY_ACCESS_ENABLED=false`; the rendered production runtime config has `apiBaseUrl=/api/twi`, an empty `apiAllowedOrigins` list, and empty OAuth issuer, authorization endpoint, token endpoint, client ID, scope, resource, and trusted issuer origins. The sign-in control is therefore disabled and the workspace accurately remains in foundation mode. Direct requests to `/api/twi` and `/api/twi/health` on the production custom domain both return HTTP 404, confirming no live TWI API route is currently exposed through this frontend deployment. Do not enable live operations by setting the frontend flag alone.

The Vercel project now has an ignored-build-step guard that skips deployment only when the Git diff contains no changes under `apps/web`. If the previous/current Git SHA variables are missing, it proceeds with a build. This prevents documentation-only commits from consuming frontend build quota while keeping frontend changes build-triggered.

## AWS and runtime state

A targeted read-only inventory covered all 17 currently enabled AWS regions and queried EC2, ECS, Lambda, Cognito user pools, API Gateway v2, DynamoDB, RDS, and CloudFormation. No Tinlyt backend resources or CloudFormation stacks were found in any of those regions. The only active EC2 instances discovered were separately tagged `fusionops-production` and `Threatfade` in `eu-north-1`; these belong to other projects and were not modified. The scan is broad across the listed service families but is not a claim that every AWS service in every region was enumerated.

The connected AWS identity remains the account root principal, with MFA enabled. The account initially had no customer-managed IAM policies, no deployment role, and no GitHub OIDC provider. No AWS Budgets configuration was found. Cost Explorer charges offset by credits do not establish the remaining credit balance.

A GitHub OIDC provider was created at `arn:aws:iam::381661387870:oidc-provider/token.actions.githubusercontent.com`. The role `arn:aws:iam::381661387870:role/TinlytGitHubActionsDeployRole` now trusts only version-tagged releases from `LloydCoder/tinlance-web-intelligence` (including the repository immutable-subject form). Verification confirms it has no attached managed policies and no inline policies. The release workflow has not yet been wired to assume this role, and the role cannot provision resources in its current state.

**No application infrastructure was provisioned by this audit.** The OIDC provider and empty-trust role are IAM identity scaffolding, not a deployment. Do not add resource permissions or create billable infrastructure until the production deployment design, least-privilege action/resource policy, budget ceiling, and alerts are reviewed.

## Early-access intake state

The production Vercel environment currently contains exactly one visible variable: `EARLY_ACCESS_ENABLED=false`, applied to production, preview, and development. Its configuration comment explicitly says to keep intake disabled until a dedicated Supabase project, privacy approval, provider secrets, and preview end-to-end evidence are complete. There are no hidden production environment variables. The static contact form is therefore disabled by design. The `/api/early-access` Vercel function is deployed (GET returns the expected HTTP 405 because the handler accepts POST only), but intake cannot accept requests until all required server-side settings are configured.

The handler requires a dedicated Supabase URL and secret key, the `early_access_requests` table, the `consume_early_access_rate_limit` RPC, Resend API key/from/notification addresses, Cloudflare Turnstile site and secret keys, a rate-limit salt of at least 32 characters, the approved privacy-notice version, and the feature flag. It verifies Turnstile hostname/origin, applies hashed IP/email rate limits, persists consent timestamps and delivery status, and sends applicant/team email. No real submissions have been attempted or fabricated in this audit.

The connected Supabase account currently exposes one organization and one active project named `LloydCoder's Project` in `eu-west-1`; its purpose has not been established. I did not inspect its tables or data and did not repurpose it. A new dedicated Tinlyt early-access project was quoted at USD $0/month in that organization, but project creation was not performed because the organization choice must be confirmed by the owner. The privacy page remains an explicit legal-review draft, so the intake feature flag must stay off until the controller/contact, retention, processors, legal basis, privacy notice, and operational deletion policy are approved.

## Production composition gaps

### Agent Platform

The merged `create_twi_platform_application` factory still requires the deployment to supply a non-TWI Platform API delegate, approval verifier, environment configuration, KMS client and signing key ID, issuer/client identifiers, and TWI service base URL.

The HTTP server separately requires a trusted principal resolver and, for server-side sign-out, a session revoker. Production also needs a hardened TLS boundary, durable stores, restricted network paths, secret injection/rotation, and health/observability wiring. The repository does not supply a ready-to-run production AWS composition that creates these dependencies automatically.

### Cognito

The merged V2 pre-token trigger requires a real user pool, resource server/client configuration, and a tenant-membership source with least-privilege read access. The revocation path requires its durable DynamoDB table and correct TTL/index/permissions configuration. None of these resources was found in the inspected AWS region.

### TWI service

TWI production startup requires PostgreSQL with TLS hostname/certificate verification (`sslmode=verify-full`), migrations applied by a separate DDL identity, runtime credentials without DDL rights, durable artifact storage, and an injected entitlement resolver. Browser workers and egress controls must be isolated and exercised in the target environment. CI database tests do not satisfy these deployment requirements.

### Frontend

After the Platform and TWI endpoints are deployed, configure only public browser-safe values in Vercel: Platform API base URL, Cognito issuer, OAuth authorization/token endpoints, public client ID, allowed scopes, resource indicator, and explicit trusted origins. Do not put client secrets, signing keys, or server credentials in browser variables. Validate the generated runtime configuration and exact production origin before enabling authenticated flows.

## Release gates still open

Private beta and GA remain **NOT CERTIFIED** until evidence exists for all of the following:
1. Dedicated least-privilege AWS deployment identity and approved cost guardrails.
2. Deployed Cognito user pool, tenant-membership data source, V2 trigger, KMS signing key, and durable revocation table.
3. Production Platform API composition with verified JWT/JWKS, tenant membership, approvals, policy, revocation, audit, and durable storage.
4. Production TWI API/workers with TLS-verified PostgreSQL, migrations, durable artifacts, isolated browser execution, and restricted egress.
5. Correct Vercel production environment variables and a successful authenticated user journey.
6. Tenant-isolation and authorization tests against deployed services, including search, fetch, browser, research verification, monitors, usage, evidence export, and sign-out revocation.
7. Live alert delivery, on-call ownership, SLOs, capacity/load tests, encrypted backups, and a witnessed restore/rollback exercise.
8. Privacy/retention approval, residual-risk acceptance, TSIC exact-revision conformance, and explicit owner release approval.

## Next execution sequence

1. Establish the dedicated AWS deployment role and budget controls without using the root principal for routine provisioning.
2. Build and review a reproducible, least-privilege infrastructure deployment package for the selected region and approved budget.
3. Complete the Platform production composition and its integration tests before exposing public API endpoints.
4. Deploy Cognito, Platform, and TWI dependencies in dependency order; verify each health and security boundary.
5. Configure Vercel with public-only runtime settings and deploy the exact reviewed main revision.
6. Run authenticated end-to-end, tenant-isolation, security, recovery, and operational acceptance tests.
7. Update the W15 evidence pack only with source-bound artifacts from the actual target environment.

## Explicit non-claims

This addendum does not claim that Tinlyt backend infrastructure is deployed, OAuth login succeeds, live search/browser operations work, early-access intake is active, customer billing is enabled, or private beta/GA is approved.
