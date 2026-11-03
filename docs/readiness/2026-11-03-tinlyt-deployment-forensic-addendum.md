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

The latest main-branch deployment observed during this audit:
- Deployment: `dpl_8Q2jgrgwkNgm2KYz8iwYomvp6dqD`
- State: `READY`
- URL: `tinlyt-hc1x8zzny-lloydcoders-projects.vercel.app`
- Source commit: `45211fac5138b1df5923d746bf94fff6103d2857`

The project live flag is `false`. Custom domains include `tinlyt.tinlance.com` and `tinlyt-web.vercel.app`, plus Vercel project aliases. Preview SSO protection is enabled; custom domains are excluded from that protection.

A separate PR #133 preview was also built successfully from commit `82f1c56b6b169b835ce63378b7615a55d8b9e041`. Its rendered `/` and `/app` routes both returned HTTP 200. The workspace correctly remains in foundation mode: the sign-in control is disabled and the page states that authentication/runtime configuration is unavailable. The preview build log confirms Vercel selected Node `22.x` after the package engine was pinned; this corrects the previous `>=22` declaration that caused Vercel to select Node `26.x`.

A READY deployment is not proof that the authenticated application works. The Vercel project environment inventory returned only `EARLY_ACCESS_ENABLED=false`; no OAuth issuer/client/resource/scope or Platform API URL configuration was present. Recheck environment variables before any production promotion. Do not enable live operations by setting the frontend flag alone.

## AWS and runtime state

The previous read-only AWS audit found no Tinlyt backend stack in `eu-west-1`: no Tinlyt EC2, ECS, Lambda, Cognito, API Gateway, DynamoDB, RDS, ECR, Secrets Manager, customer KMS key, or CloudFormation stack was found there. The wider multi-region scan did not complete because the connector reached its API-call limit; this statement is limited to the fully inspected region and resource inventory.

The connected AWS identity was the account root principal, with MFA enabled. Only AWS service-linked roles were present in the inspected IAM role inventory; no Tinlyt deployment role was found. No AWS Budgets configuration was found. Cost Explorer showed charges offset by credits, but this does not establish the remaining credit balance.

**No infrastructure was provisioned by this audit.** Root credentials must not be used as a substitute for a dedicated deployment identity. Do not create billable infrastructure until an approved spend ceiling, alerts, and a least-privilege deployment role/workflow are in place.

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
