# Tinlyt / TWI Cross-Conversation Consolidation Audit

**Audit date:** 2026-10-21  
**Scope:** ChatGPT project conversations and retrieved prior-conversation context concerning Tinlance Web Intelligence, Tinlyt, and TWI; current GitHub repository, issue/PR state, CI, roadmap, readiness artifacts, and Vercel deployment metadata.  
**Repository:** [LloydCoder/tinlance-web-intelligence](https://github.com/LloydCoder/tinlance-web-intelligence)  
**Historical audit baseline:** `75ced750deef1903d23987d8e2ab9882ba6035e5` (superseded by later merges; use the live GitHub branch and the phase ledger for current state).

## 1. Executive decision

There is now one product identity and one engineering source of truth:

- **Tinlance Limited** — parent business.
- **Tinlyt** — customer-facing product.
- **Tinlance Web Intelligence (TWI)** — internal engineering/workstream and repository identity.
- **Repository remains** `LloydCoder/tinlance-web-intelligence`.
- **Tagline:** “Discover sources. Verify claims. Preserve evidence.”
- **Primary product contract:** evidence-first web investigation, retrieval, extraction, execution history, claim/citation comparison, monitoring, and provenance preservation.

**State at this audit snapshot (historical):** main was recorded at the baseline SHA above, with CI/Frontend workflows green and a Vercel deployment object reported READY. Subsequent merges, including PR #102, supersede that code snapshot. The earlier deployment object is not evidence that the latest commit is deployed or that the customer journey works. Always re-check the live branch head, exact-commit workflows, current PR/issue state, and deployment metadata before making a present-tense claim. Private-beta and GA remain separate certifications.

## 2. Evidence hierarchy and status vocabulary

Use this hierarchy when sources conflict:

1. Exact current code/configuration and provider state.
2. Commit-specific automated tests and workflow results.
3. Exact deployment revision and target-environment evidence.
4. Current phase/readiness ledgers and audit docs.
5. Conversation decisions and plans.
6. Older assistant summaries, mockups, issue text, and intended designs.

Conversation history establishes decisions and intent, not implementation. An issue, UI control, green compile, mock response, or merged PR does not prove a feature is operational.

Use these distinct states:
- **Implemented:** code/configuration exists.
- **CI-verified:** required tests/checks passed on a named commit.
- **Deployed:** provider reports the exact commit deployed.
- **Live-verified:** real request/response and operational behavior observed in the target environment.
- **Integrated:** exact consumer/provider contract and authorization verified across repository boundaries.
- **Certified:** every required release gate, owner approval, and target-environment evidence is complete.
- **Blocked / not evidenced:** required proof is absent or a known contract mismatch exists.

Never collapse these states into a generic “done.”

## 3. Canonical product and design decisions

### Identity and naming

Tinlyt supersedes the earlier **Provenel** naming direction for this product. Do not rebrand the product or repository without an explicit new decision. Keep Tinlance as the parent business and TWI as the engineering identity.

### Frontend inspirations

Primary references:
1. **Linear** — restrained navigation, hierarchy, and interaction details.
2. **Perplexity** — research-first query/results, citations, and source-oriented workflow.
3. **Palantir Foundry** — enterprise investigation, evidence lineage, and operational context.

Secondary references: **Vercel** for developer/run-state clarity and **Browserless** for browser execution concepts. These are design references, not claims of feature parity.

### Brand

Use the uploaded Tinlyt logo kit and shared tokens, not improvised marks. Canonical palette recorded in the kit: Ink `#0B1220`, Paper `#F2F5FA`, Signal `#2DD4BF`, Signal deep `#0D9488`, Muted `#8996AA`. Keep landing and workspace visually consistent. The merged frontend PR #97 also introduced responsive safeguards, touch-target improvements, focus/reduced-motion behavior, and a progressive CSS 3D scroll effect. Three.js was deliberately not added: a decorative panel tilt does not justify WebGL/dependency/mobile-battery costs. Reconsider it only for a genuine interactive 3D evidence graph/spatial view.

### Routes and UX

- `/` — public marketing landing page.
- `/app` — existing workspace.
- Preserve the established workspace surfaces: Overview, Investigations, Runs, Evidence, Verify, Monitors, Developer, Usage.
- Do not alter backend/API contracts merely to create the marketing route.
- Keep the landing page `noindex` until name/domain clearance and owner launch approval are recorded.
- No analytics/tracking without explicit owner approval. Privacy and Terms must be real reviewed pages before public launch; link only to pages that exist.
- Label examples as illustrative. Do not invent live runs, evidence, customers, usage, verification outcomes, metrics, or pricing behavior.

## 4. Architecture and authority boundaries

- **Tinlance Agent Platform:** authoritative identity, authentication/authorization, policy, approvals, governed execution, tool/runtime boundaries, secrets, budgets, audit, and canonical remote MCP gateway.
- **Tinlance Agent OS:** workspace/task orchestration and lifecycle, including recurrence where owned by OS.
- **Platform SDK:** typed consumer contract.
- **TADL:** governed developer/artifact plane.
- **TSIC:** system-of-systems conformance; not replaced by Memory Vault.
- **Tinlance World Intelligence:** canonical entities, events, relationships, temporal world state, correlation, contradiction, and world-level signals.
- **TWI/Tinlyt:** web acquisition, search/fetch, extraction, isolated browser work, source capture, provenance, web-specific observations, customer UX.

TWI must not create a competing identity, approval, audit, execution authority, or MCP gateway, and must not silently duplicate World Intelligence semantics. Repository conformance does not establish live cross-system integration.

## 5. Roadmap model — one plane, separate gates

Two roadmaps are intentionally distinct and must remain linked:

- **F0–F11:** customer-facing frontend workstream: baseline; brand/design foundation; shell/security; investigations; runs; evidence; verification; monitors/collections; developer experience; usage/admin; hardening/accessibility; integration/release qualification.
- **W1–W15:** core TWI engineering and operational-readiness workstreams: foundation/search/fetch/API/browser/agent/persistence; then governance, deployment, security, SRE, provenance, evaluation, monitoring, enterprise controls, and GA readiness.
- **Release gates:** branch governance, Platform/OS/World Intelligence/TSIC integration, deployment-specific security, restore and recovery, live quality, privacy/risk, SLO/on-call, billing, and owner approval. These are independent of F/W code completion.

A phase can have its repository implementation accepted while its external integration or release gate remains blocked. The phase ledger must show both rather than declaring a whole phase “complete” without qualification.

## 6. Repository and CI facts at the historical audit snapshot (2026-10-21)

- Main SHA: `75ced750deef1903d23987d8e2ab9882ba6035e5`.
- Merged PR: [#97 — unify Tinlyt branding and harden mobile layouts](https://github.com/LloydCoder/tinlance-web-intelligence/pull/97).
- PR #97 merged at 2026-10-21 07:13 UTC as the current main commit.
- Post-merge [CI workflow](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39560470365): **success**.
- Post-merge [Frontend workflow](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39560470415): **success**.
- Open pull requests: **0** at audit time.
- Open issues: **1** — [#18, reconcile W5 integration claims with private-beta readiness](https://github.com/LloydCoder/tinlance-web-intelligence/issues/18).
- Issue #18 must remain open until the consumer contract mismatch and missing deployment evidence it documents are reconciled with current exact revisions.
- GitHub's branch-protection endpoint returned 403 to the connected integration during this audit. A previous repository audit dated 2026-10-19 recorded `main` as unprotected with no active rulesets; that observation must be re-verified by an authorized owner. Do not claim branch governance is enforced based on CI visibility alone.

## 7. Deployment evidence recorded at the historical audit snapshot

Vercel project `tinlyt-web` reports a production-target deployment **READY** for main SHA `75ced750deef1903d23987d8e2ab9882ba6035e5` in region `iad1`. The deployment has aliases including `tinlyt-web.vercel.app`. Project metadata simultaneously reports `live: false`, and SSO protection is enabled for all deployment types except custom domains. Treat this as a provider-state ambiguity requiring a direct owner check of the intended public domain, alias protection, and live route behavior. Do not state that the complete product is publicly live or end-to-end operational from the deployment object alone.

Earlier conversations considered multiple hosting shapes (Vercel frontend with Railway API/workers and PostgreSQL; later an AWS EC2/private-RDS staging proposal). These are **proposals, not a final approved architecture**. No billable infrastructure should be provisioned until the target provider/region/cost, network boundaries, database, identity, secret handling, and recovery plan are explicitly selected and recorded.

## 8. Engineering status summary

| Area | Repository evidence | Remaining release/integration gate |
|---|---|---|
| Frontend branding/mobile | PR #97 merged; CI and Frontend workflows green on main SHA | Direct visual/live-route confirmation and Vercel alias/SSO ambiguity |
| F0–F11 frontend | Existing phase audit records F0–F11 code/test acceptance; PR #97 adds further brand/mobile improvements | Correct stale phase-ledger statuses; real authenticated consumer journey and release qualification remain separate |
| W1–W6 | Roadmap records repository implementation/recorded conformance complete through W6; prior exact CI evidence exists | W6 private beta remains NOT CERTIFIED without target deployment evidence |
| W7 governance/supply chain | CI security scans, reproducible artifact/provenance steps recorded | Effective branch rules, durable evidence retention, and mandatory-check enforcement not verified |
| W8 deployment | Staging topology and browser isolation configuration in repository | Approved live staging, secret rotation, egress, restore, and cross-system journey not evidenced |
| W9 security | Adversarial regression tests in repository | Live SSRF/redirect, tenant isolation, egress, and resource exhaustion assurance |
| W10 SRE | Tracing/metrics contracts and no-op-safe telemetry implementation | Real collector/alerts, capacity budgets, on-call and witnessed rollback |
| W11 provenance/governance | Provenance manifests, retention semantics, evidence-pack integrity | Target retention/deletion/privacy controls and tenant-scoped live evidence |
| W12 evaluation | Offline benchmark/evaluator and deterministic tests | Live representative observations, approved thresholds, consumer validation; fixtures are not truth certification |
| W13 monitors | Durable monitor definitions/runs and deterministic change digest implemented/tested | Agent OS recurrence and real-network alert delivery |
| W14 enterprise contracts | Tenant/subject-scoped API/tool contracts and schema checks | Pinned Platform snapshot lacks six monitor tools; TSIC conformance not evidenced |
| W15 GA | Evidence-pack builder/validator and subphases A–E implemented to differing degrees | Current readiness pack says NOT READY / NOT CERTIFIED; Platform consumer approval fails; other external gates unevidenced |
| Commercial/billing | Pricing policy and usage/quota code documented/implemented in repository | No charging until live entitlement enforcement, provider settlement, durable idempotency/reconciliation and cost validation are verified |
| Public launch/directory | Directory intent discussed; no readiness assertion | Current official ChatGPT/Claude directory policies, supportable integration, privacy/terms, domain/name clearance and explicit launch approval |

### Commercial policy (not an operational claim)

The approved market-facing pricing policy records $0.014 per billable agent step and $0.002 per standalone browser minute, with plan headline prices Free $0, Starter $29/mo, Pro $99/mo, Business $299/mo, Scale $799/mo, Enterprise custom. Exact plan allowances and live payment/settlement/entitlement operation are not established by the policy. Do not charge customers or advertise operational billing until the policy's implementation gates are evidenced.

## 9. Known critical discrepancies and blockers

1. **Status drift:** `docs/roadmap/phase-ledger.md` still calls Brand and F1 “In progress” and F3–F9 “Unverified,” while `docs/product/tinlyt-frontend-final-audit.md` records F0–F11 code/test acceptance. These can coexist only if the ledger explicitly separates frontend code/test acceptance from live integration/release readiness. Reconcile the ledger; do not overstate live integration.
2. **Platform consumer mismatch:** the pinned Platform snapshot recorded by the readiness artifacts lacks six monitor tools; the evidence-export tool is also recorded as missing. W15 external consumer approval is failed. This is an integration blocker, not a frontend styling task.
3. **TSIC:** current roadmap records no external conformance result for the cited TSIC revision. Re-run conformance against exact intended consumer versions and retain evidence.
4. **Branch governance:** previous audit recorded main as unprotected; current connected integration cannot read the protected-branch endpoint (403). Authorized owner must verify effective rules and required checks.
5. **Deployment truth:** Vercel reports the exact main SHA READY but project `live: false` and SSO protection enabled except custom domains. Confirm the expected public alias and access behavior.
6. **Environment operations:** no current target-environment evidence was found for production secrets/TLS/JWKS, authenticated Platform → TWI → World Intelligence ingestion, real browser egress isolation, backup/restore drill, RPO/RTO, SLO/alerts/on-call, capacity, or incident response.
7. **Privacy/legal/launch:** keep noindex and do not announce GA until reviewed Privacy/Terms, name/domain clearance, data retention/risk ownership, and explicit owner approval are recorded.
8. **Directory submissions:** do not submit to ChatGPT or Claude directories until official current policies are checked, product eligibility is established, the integration works and can be supported, and the exact submission artifacts are reviewed.

## 10. Ordered closure plan

1. **Reconcile the ledgers and docs** against this audit; remove stale/contradictory status language and preserve historical audit snapshots as dated evidence.
2. **Close Platform contract gap:** update/verify the authoritative Platform operation catalog and operation-level policies for the six monitor tools and evidence export; regenerate exact consumer fixtures and tests.
3. **Run ecosystem conformance:** verify Platform SDK/API/MCP contracts, World Intelligence ingestion, and TSIC against pinned immutable revisions; capture exact workflow and SHA evidence.
4. **Establish governance:** authorized owner verifies/enforces branch protection and required CI checks; record rules, bypass actors, approvals and timestamp.
5. **Prove staging:** choose provider/region/cost, provision only approved isolated staging, wire identity/secrets/database/TLS/egress, run live end-to-end probes, and preserve safe recovery evidence.
6. **Prove security and operations:** live SSRF/private-range/redirect/tenant-boundary/egress/resource tests; witnessed backup/restore; retention/deletion; telemetry/alerts/on-call; capacity and rollback.
7. **Prove product quality and billing:** run representative live benchmark, approve thresholds, verify plan entitlements, atomic quotas, idempotent usage, provider settlement/reconciliation, and cost-to-serve before enabling charges.
8. **Public launch review:** Privacy/Terms, domain/name checks, public route and SSO verification, owner approval, then consider directory submissions under current official policies.
9. **Certification decision:** bind the exact release SHA, evidence pack digest, unresolved risks, owner approvals and environment. If any required gate is missing, status remains **NOT CERTIFIED**.

## 11. Conversation-derived decision register

The following decisions are now canonical unless the owner explicitly changes them:

- Tinlyt product name; Tinlance Limited parent; TWI internal engineering/repository identity; no silent return to Provenel.
- Keep repository name `LloydCoder/tinlance-web-intelligence`.
- Evidence-first, provenance-preserving product; no false truth verdicts or invented operational claims.
- Primary UI references: Linear, Perplexity, Palantir Foundry; Vercel and Browserless are secondary references.
- Landing at `/`, workspace at `/app`; preserve existing API/security contracts.
- Use the uploaded Tinlyt logo kit/shared brand tokens and keep landing/workspace consistent.
- Frontend roadmap F0–F11 is distinct from core engineering roadmap W1–W15; external release gates are independent of both.
- Prefer accessible CSS motion for decorative depth; no Three.js dependency without a genuine interactive 3D product requirement.
- Vercel/Railway/PostgreSQL and AWS EC2/private RDS were considered deployment options, not final approval.
- ChatGPT/Claude directory submission is a later launch gate, not evidence of current integration.
- Only exact-commit CI, target-environment evidence, and reviewed owner approval can close release gates.

## 12. Sources of truth

- [Project source of truth](PROJECT_SOURCE_OF_TRUTH.md)
- [Phase and release ledger](roadmap/phase-ledger.md)
- [W1–W15 workstream plan](roadmap/phases.md)
- [Frontend final audit](product/tinlyt-frontend-final-audit.md)
- [Brand/frontend contract](product/brand-and-frontend-contract.md)
- [Private-beta readiness checklist](operations/private-beta-readiness.md)
- [W15 readiness gate registry](readiness/w15-gates.json)
- [W15 readiness guide](readiness/README.md)
- [Production deployment recovery ledger](operations/tinlyt-production-deployment-recovery-2026-10-20.md)
- [Open integration reconciliation issue #18](https://github.com/LloydCoder/tinlance-web-intelligence/issues/18)

**Release decision as of this audit: frontend CI/deployment revision verified; overall private beta and GA remain NOT CERTIFIED.**
