# Tinlyt / TWI Project Source of Truth

**Reconciled:** 2026-10-21  
**Repository:** `LloydCoder/tinlance-web-intelligence`  
**Product:** Tinlyt  
**Parent business:** Tinlance Limited  
**Internal engineering identity:** Tinlance Web Intelligence (TWI)

> **Canonical consolidation:** Read [the cross-conversation consolidation audit](PROJECT_CONSOLIDATION_AUDIT_2026-10-21.md) first for the reconciled decision register, current repository/provider evidence, discrepancies, and ordered closure plan. The [phase ledger](roadmap/phase-ledger.md) is the live status table; [W1–W15 workstreams](roadmap/phases.md) retain detailed milestone evidence.

## Evidence authority

Repository code, current provider state, and commit-linked test/deployment evidence determine implementation status. Conversation history records decisions but does not override current repository evidence. Never mark a feature complete because a design, issue, PR, document, or UI control exists. Distinguish implemented, tested, deployed, live-verified, integrated, and certified. Record commit SHAs, workflow URLs, environment, timestamps, open risks, and recovery paths. Never put secrets or customer-sensitive data in evidence records.

## Canonical identity and product contract

- **Tinlance Limited** is the parent business.
- **Tinlyt** is the customer-facing product name. This supersedes the earlier Provenel naming direction for this product.
- **Tinlance Web Intelligence (TWI)** remains the internal engineering identity and repository name.
- Keep repository `LloydCoder/tinlance-web-intelligence`.
- Tagline: **“Discover sources. Verify claims. Preserve evidence.”**
- Tinlyt helps teams investigate the web, retrieve and inspect source material, preserve provenance, review execution history, monitor changes, and compare claims with cited passages.

Retrieval is not proof of truth; quote matching is not an independent factual verdict. Never fabricate sources, captures, timestamps, traces, usage, verification results, customers, certifications, uptime, or pricing behavior. Label illustrative examples clearly and distinguish operational, configured-but-unverified, blocked, planned, and unavailable capabilities.

## Architecture boundaries

- **Platform:** generic consequential execution authority, identity, authorization, policy, approvals, runtime/tool boundaries, secrets, budgets, evidence, audit, and observability.
- **OS:** orchestration and lifecycle, including workspaces, sessions, tasks, and memory.
- **SDK:** typed client contract.
- **TADL:** developer/artifact plane.
- **TSIC:** system-of-systems conformance; it is not replaced by Memory Vault.
- **World Intelligence:** canonical entities, events, relationships, temporal world state, correlation, contradiction, and world-level signals.
- **TWI/Tinlyt:** web-intelligence service/product and customer-facing experience.

TWI must not create a competing identity, approval, audit, execution authority, or MCP gateway, and must not duplicate World Intelligence semantics. Repository conformance does not establish live cross-system integration.

## Frontend contract and design

- `/` is the public marketing landing page; `/app` is the existing workspace.
- Preserve Overview, Investigations, Runs, Evidence, Verify, Monitors, Developer, and Usage.
- Do not change API contracts as part of the marketing route split.
- Primary design references: Linear, Perplexity, and Palantir Foundry. Vercel and Browserless are secondary references, not feature-parity claims.
- Use the uploaded Tinlyt logo kit and shared brand tokens. Canonical palette: Ink `#0B1220`, Paper `#F2F5FA`, Signal `#2DD4BF`, Signal deep `#0D9488`, Muted `#8996AA`.
- Preserve CSP, security headers, no-referrer behavior, keyboard access, reduced-motion support, and responsive layout.
- Keep the public landing page `noindex` until name/domain checks and owner launch approval are recorded.
- No analytics/tracking without explicit owner approval. No secrets in browser-delivered code or runtime config.
- Privacy and Terms must be real, reviewed pages before public launch; link other footer destinations only if they exist.
- Prefer accessible CSS motion for decorative depth; do not add Three.js unless a real interactive 3D graph/spatial view requires it.

## Security, operations, and commercial boundaries

Enforce authentication, authorization, tenant boundaries, entitlements, and quotas on the server. Browser workers must use approved authenticated egress and must not have direct public egress where policy forbids it; test metadata/private-range denial and SSRF controls. Use least-privilege database roles, TLS certificate and hostname verification, secret-manager injection, reproducible builds, and immutable release revisions. Staging and production must be distinct. Never point staging probes or destructive restore drills at production. CI-only evidence is not live deployment evidence. Private beta requires the full readiness checklist, including witnessed restore and operational recovery evidence.

Pricing policy does not imply billing is deployed. Do not charge users until entitlements, durable usage accounting, idempotency, payment flows, and reconciliation are implemented and verified. ChatGPT/Claude directory readiness requires current official requirements and a working, supportable product integration.

## Current evidence checkpoint — 2026-10-21

- Main SHA: `a407b211773e32a71a8cebcae9b9b2177fd5af5c`.
- PR [#97](https://github.com/LloydCoder/tinlance-web-intelligence/pull/97) delivered brand-token, logo, responsive and reduced-motion hardening.
- PR [#99](https://github.com/LloydCoder/tinlance-web-intelligence/pull/99) expanded the public website with Features, How It Works, Use Cases, Pricing, Enterprise, Developers, Integrations, Security, Privacy, Terms, Contact, Docs and FAQ pages; clean routes, build/lint inclusion and route smoke tests were added.
- Post-merge [CI run 39573798125](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39573798125) completed successfully on exact main SHA `a407b211773e32a71a8cebcae9b9b2177fd5af5c`.
- The successful CI run proves the repository checks in that workflow passed; it does not prove public deployment accessibility, SSO behavior, external integrations or production certification. Vercel state must be refreshed and verified against this new SHA.
- No open PRs; issue [#18](https://github.com/LloydCoder/tinlance-web-intelligence/issues/18) remains open for deployment-specific W5/private-beta reconciliation.
- GitHub branch-protection inspection previously returned 403 to the connected integration. Effective branch rules and mandatory checks remain unverified until an authorized owner confirms them.
- Overall private beta and GA remain **NOT CERTIFIED**. The W15 evidence registry has a failed Platform consumer-approval gate and external gates marked not evidenced. Do not change these states without evidence against the intended revisions and target environment.
- Vercel + Railway + PostgreSQL and AWS EC2 + private RDS remain unapproved options until a provider, region, cost and topology are explicitly selected.

## Change control

Substantial work occurs on a feature branch and reviewable PR. Preserve contracts; add regression tests with fixes; run required checks; inspect built artifacts; review security and docs; then verify the exact commit's CI and deployment. Do not merge or deploy around a failing required gate. Update the [phase ledger](roadmap/phase-ledger.md) and [consolidation audit](PROJECT_CONSOLIDATION_AUDIT_2026-10-21.md) when verified evidence changes.