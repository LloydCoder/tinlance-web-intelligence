# W15-E — GA v1 product contract and release decision

**Status:** Contract implementation candidate; GA is **NOT CERTIFIED** until all required external gates are evidenced and authorized.
**Authority:** Tinlance Agent Platform owns identity, authorization, policy, approvals and execution authority. TWI owns acquisition, extraction, artifacts, provenance and bounded change observations. Agent OS owns task lifecycle and recurrence. World Intelligence owns canonical world state and truth judgments. TSIC owns system-of-systems conformance.

## Supported capability surface

GA v1 may expose only capabilities present in the reviewed repository and enabled by the target deployment:
- Search and safe URL acquisition, fetch, extraction and browser-assisted acquisition within deployed egress/security policy.
- Durable job lifecycle and idempotent operation contracts.
- Tenant-scoped artifacts, provenance and customer evidence export, only after Platform registers and authorizes the export operation.
- Explicit monitor definitions/runs with deterministic baseline/change digests. A change is an observation, not a truth judgment; recurrence belongs to Agent OS.
- Usage metering, quota reservations, entitlement checks, provider-neutral billing-event receipt and reconciliation primitives. These are not invoices, settlement, tax advice, refunds, or proof of live payment-provider integration.
- Versioned offline hard-job evaluation with deterministic reports. Synthetic fixtures do not establish live production quality.

Capabilities require the relevant deployment dependencies, scopes, database migrations, provider credentials and network controls. Source code does not prove a deployment is configured.

## Explicitly unsupported or not promised

- Self-hosting as a GA v1 offer; it is excluded until separately approved and qualified.
- Guaranteed factual truth, semantic entailment, source authority, completeness, or correctness of arbitrary web content.
- Unrestricted scraping, CAPTCHA/anti-bot bypass, guaranteed access to authenticated websites, or bypass of site access controls.
- A TWI-owned identity/policy/approval authority, scheduler, second MCP server, or automatic action triggered by observed web changes.
- Production SLOs, throughput/capacity guarantees, availability percentages, retention intervals, data residency, or support response times until explicitly approved and published with evidence.
- A selected payment provider, currency, plan price, trial, overage policy, or settlement lifecycle. These require commercial and provider decisions.
- Certified production deployment, private beta, or GA solely because repository CI is green.

## Required published customer constraints

Before any GA announcement or customer onboarding, publish a versioned, deployment-specific schedule covering:
1. Enabled operations and required Platform scopes.
2. Request/response, concurrency, payload, browser and provider limits.
3. Entitlement names, quota windows, usage definitions and behavior on quota exhaustion.
4. Retention, deletion, export, privacy, data residency and backup/recovery policy.
5. Supported regions, deployment topology, dependencies and service boundaries.
6. Pricing, currency, billing semantics, payment provider, refunds/tax handling and support channel—or explicitly state paid self-service billing is unavailable.
7. Incident communication, support ownership, approved SLO/SLA if any, and deprecation/change policy.

No value may be inferred from synthetic benchmarks, test defaults, or an unapproved draft.

## Fail-closed release decision

The machine-readable contract is docs/releases/ga-v1-contract.json; its schema is schemas/ga-v1-release-decision.schema.json; the validator is scripts/validate_ga_v1_contract.py.
- The release decision references the exact full source commit SHA and a content-addressed evidence pack built for that same revision.
- Required gate states are exactly pass, fail, or not_evidenced. Missing, unknown, expired, mismatched or invalid evidence fails closed.
- GA can be approved only when every required gate is pass, the support contract is complete, benchmark thresholds have an authorized approval reference, the residual-risk register has an authorized disposition, and a named release approver has an approval evidence reference.
- A repository validator checks structural consistency and fail-closed behavior; it cannot authenticate external approvals or prove the target deployment exists.
- Code, deployment, consumer revisions, thresholds, data policy or product-claim changes require re-evaluation against the exact candidate.
- A structurally valid decision may correctly remain not_certified.

## Current blockers

The readiness registry records the Platform consumer compatibility gate as fail. Branch governance, deployment/security, SLO/on-call, privacy/retention/risk, and live quality/GA approval remain not_evidenced. Do not change these statuses without source-bound evidence from responsible owners.

## Acceptance

- Contract and schema validation runs in CI.
- Validator rejects approval when any readiness gate is non-passing.
- Validator rejects mismatched evidence-pack/source revisions.
- Validator rejects missing approver, risk disposition, benchmark approval, or customer-constraints publication.
- Tests cover malformed data, unknown/missing gates, invalid schema version, hash/revision mismatch and tampering.
- Docs, roadmap, release notes and machine-readable registry agree.
- Exact-head Python 3.12/3.13 CI, release artifact checks and browser isolation are green.
- Post-merge main CI is green and the cross-phase audit is recorded.
- External readiness evidence is collected before any GA claim.

W15-E implementation completion means the release decision is enforceable and fail-closed—not that GA has been approved.