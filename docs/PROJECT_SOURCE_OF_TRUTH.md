# Tinlyt / TWI Project Source of Truth

**Reconciled:** 2026-10-21  
**Repository:** `LloydCoder/tinlance-web-intelligence`  
**Product:** Tinlyt  
**Parent business:** Tinlance Limited  
**Internal engineering identity:** Tinlance Web Intelligence (TWI)

## Evidence authority
Repository code, current provider state and commit-linked test/deployment evidence determine implementation status. Conversation history records decisions but does not override current repository evidence. Never mark a feature complete because a design, issue, PR, document or UI control exists. Distinguish implemented, tested, deployed and independently verified. Record commit SHAs, workflow URLs, environment and timestamps. Never put secrets or customer-sensitive data in evidence records.

## Product contract
Tinlyt helps teams investigate the web, retrieve and inspect source material, preserve provenance, review execution history, and compare claims with cited passages. Retrieval is not proof of truth; quote matching is not an independent factual verdict. Never fabricate sources, captures, timestamps, traces, usage, verification results, customers, certifications, uptime or pricing. Label illustrative examples clearly and distinguish operational, configured-but-unverified, blocked, planned and unavailable capabilities.

## Architecture boundaries
- **Platform:** generic consequential execution authority, identity, authorization, policy, approvals, runtime/tool boundaries, secrets, budgets, evidence, audit and observability.
- **OS:** orchestration and lifecycle, including workspaces, sessions, tasks and memory.
- **SDK:** typed client contract.
- **TADL:** developer/artifact plane.
- **TSIC:** system-of-systems conformance; it is not replaced by Memory Vault.
- **TWI/Tinlyt:** web-intelligence product implementation and customer-facing experience. Do not silently redefine platform boundaries.

## Frontend contract
- `/` is the public marketing landing page; `/app` is the existing workspace.
- Preserve Overview, Investigations, Runs, Evidence, Verify, Monitors, Developer and Usage.
- Do not change API contracts as part of the marketing route split.
- Preserve CSP, security headers, no-referrer behaviour, keyboard access, reduced-motion support and responsive layout.
- Keep the public landing page `noindex` until name/domain checks and owner launch approval are recorded.
- No analytics/tracking without explicit owner approval. No secrets in browser-delivered code or runtime config.
- Privacy and Terms must be real, reviewed pages before public launch; link other footer destinations only if they exist.

## Security and operations
Enforce authentication, authorization, tenant boundaries, entitlements and quotas on the server. Browser workers must use approved authenticated egress and must not have direct public egress where policy forbids it; test metadata/private-range denial and SSRF controls. Use least-privilege database roles, TLS certificate and hostname verification, secret-manager injection, reproducible builds and immutable release revisions. Staging and production must be distinct. Never point staging probes or destructive restore drills at production. CI-only evidence is not live deployment evidence. Private beta requires the repository's full readiness checklist, including witnessed restore and operational recovery evidence.

## Commercial and directory boundaries
Pricing policy does not imply billing is deployed. Do not charge users until entitlements, durable usage accounting, idempotency, payment flows and reconciliation are implemented and verified. ChatGPT/Claude directory readiness requires current official requirements and a working, supportable product integration.

## Release baseline
The 2026-10-20 recovery ledger records the frontend as deployed while backend/API, database, Platform identity, entitlement integration, worker/browser runtime and live staging validation remain blocked or unverified. Refresh against live provider state before current release claims. PR status is not a substitute for latest workflow results.

## Change control
Substantial work occurs on a feature branch and reviewable PR. Preserve contracts; add regression tests with fixes; run required checks; inspect built artifacts; review security and docs; then verify the exact commit's CI and deployment. Do not merge or deploy around a failing required gate.
