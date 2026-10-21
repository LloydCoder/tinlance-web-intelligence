# Tinlyt / TWI Phase and Release Ledger

This is a live checklist, not a completion claim. Update statuses only with evidence attached to the exact commit and environment.

| Track | Gate | Required exit evidence | Initial status |
|---|---|---|---|
| Brand | Logo and tokens | Official logo-kit assets in build; no improvised mark; contrast/accessibility checks | In progress |
| F0 | Baseline | Source-of-truth, inventory, dependency and status reconciliation | In progress |
| F1 | Landing and shell | `/` marketing, `/app` workspace, responsive/keyboard/reduced-motion checks | In progress |
| F2 | Identity and security | Approved Platform configuration; auth/session and negative authorization tests | Blocked pending Platform inputs |
| F3 | Investigations | Authenticated end-to-end request/response, errors and tenant tests | Unverified |
| F4 | Runs | Real lifecycle, cancellation, retries, timeouts and persistence tests | Unverified |
| F5 | Evidence | Provenance, exact export bytes, integrity/schema validation and access checks | Unverified |
| F6 | Verify | Claim/citation contract tests; no false factual-verdict semantics | Unverified |
| F7 | Monitors | Durable persistence, scheduling/lifecycle and alert delivery tests | Unverified |
| F8 | Developer | API/MCP examples run against supported contracts; accurate docs | Unverified |
| F9 | Administration | Server-enforced roles, tenant boundaries and audit evidence | Unverified |
| F10 | Hardening | Security, accessibility, performance, resilience and supply-chain checks | In progress |
| F11 | Release qualification | Required CI green, approved staging, live probe, end-to-end checks, rollback and restore evidence | Blocked |
| W1–W6 | Core milestones | Reconcile merged changes and acceptance criteria; live browser isolation and beta gates | Historical claims require verification |
| W7+ | Expansion | Roadmap mapped to source, acceptance criteria, dependencies and release order | Unverified |
| Operations | Staging | Approved cost/region, dedicated DB, network policy, identity, backup/restore and live evidence | Blocked pending provisioning |
| Commercial | Billing | Approved contract, resolver, durable ledger, payment/reconciliation tests | Blocked |
| Launch | Public release | Trademark/domain review, approved Privacy/Terms, owner launch approval | Not approved |

## Completion rule
Every gate records owner, source paths, acceptance criteria, dependencies, test command/result, workflow URL, commit SHA, environment, timestamp, open risks and recovery path. Missing required proof means the gate is not complete.
