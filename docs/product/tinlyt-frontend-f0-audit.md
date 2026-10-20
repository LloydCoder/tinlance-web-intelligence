# Tinlyt Frontend F0 — Repository Forensic Inventory

**Status:** Accepted — PR-head CI and post-merge main CI passed.  
**Repository:** `LloydCoder/tinlance-web-intelligence`  
**Product:** Tinlyt  
**Engineering identity:** Tinlance Web Intelligence (TWI)  
**Audit baseline:** `main` inspected on 2026-10-20; acceptance evidence is linked below.  
**Scope:** frontend presence, monorepo boundaries, existing API contracts, CI coverage, and implementation risks.

## Executive finding

The inspected repository is a Python-first TWI service repository. The current `apps/` directory contains Python service entry points (API, workers, browser broker/worker, egress proxy, migrations, and World Intelligence export worker), not a browser frontend. The root `pyproject.toml` defines a Python package and no JavaScript workspace manifest was present in the inspected root listing. The existing CI workflow runs Python quality/security/integration checks; no frontend build, browser UI test, accessibility, or frontend dependency audit job was identified in `.github/workflows/ci.yml`.

**Decision:** do not assume a frontend framework, package manager, UI library, authentication SDK, or deployment target. F1 must introduce the smallest justified frontend workspace and add first-class CI for it without weakening or replacing the existing Python checks.

## Evidence inventory

| Area | Repository evidence | Finding |
|---|---|---|
| Repository identity | `README.md`, `pyproject.toml` | Python project `tinlance-web-intelligence`; TWI remains the engineering/service identity. |
| Root application layout | Root contents listing | `apps/`, `src/`, `tests/`, `schemas/`, `contracts/`, `docs/`, `deployments/`, and Python tooling are present. No root `package.json`, JS lockfile, `tsconfig.json`, or frontend app was present in the inspected listing. |
| Deployable apps | `apps/api/main.py`, `apps/worker/main.py`, directory listings | Existing app entry points are Python services. Do not repurpose or rename these to host the frontend. |
| API routes | `src/tinlance_web_intelligence/api/http/routes/jobs.py` | `POST /v1/jobs` accepts `search`, `fetch`, or `browser`, strict payloads and an idempotency key; job inspection/cancellation are tenant-scoped. Exact response fields and lifecycle states must be taken from implementation and schemas. |
| Evidence | `src/tinlance_web_intelligence/api/http/routes/evidence.py`, `docs/api/evidence-packages-v1.md`, `schemas/twi-evidence-package-v1.schema.json` | Evidence export is `GET /v1/jobs/{job_id}/evidence`, requires `twi:evidence:export`, a successful in-scope fetch job, valid artifact/provenance and full source revision. Package integrity does not establish source truth or a digital signature. |
| Claim verification | `src/tinlance_web_intelligence/api/http/routes/research.py` | `POST /v1/research/verify` requires `twi:research:verify`; bounded claims cite captured job evidence. |
| Monitors | `docs/api/monitors-v1.md` and monitor route | Tenant/subject-scoped monitor operations require scopes and idempotency where documented. API stores definitions and enqueues explicit runs; Agent OS owns recurrence. Do not promise autonomous recurring execution from this UI alone. |
| Authority boundaries | `README.md`, `docs/roadmap/phases.md` | Platform owns identity/authz/policy/approvals/secrets/budgets/audit/governed execution; OS owns orchestration/lifecycle; TWI owns acquisition/evidence capture; World Intelligence owns canonical world state; TSIC owns cross-repository conformance. |
| CI | `.github/workflows/ci.yml`, `Makefile` | Existing checks include Python 3.12/3.13, lint, typing, Bandit, dependency audit, tests, PostgreSQL integration, migration/contract/readiness checks, and browser sandbox smoke. No frontend checks were found in the inspected CI workflow. |
| Phase ledger | `docs/roadmap/phases.md` | W15 is explicitly not ready; the Platform consumer gate is failed and external deployment/security/governance/privacy/SLO/on-call/live-quality gates remain unevidenced. Frontend work must not relabel this as private-beta or GA readiness. |
| Product contract | `docs/product/tinlyt-frontend-contract.md` | The contract establishes evidence-first truth rules, screen boundaries, authority boundaries and serial F0–F11 gates. |

## Frontend blockers and required treatment

1. **No existing frontend workspace identified.** Select a maintained TypeScript framework and package manager only after recording the choice and compatibility rationale. Do not create a second repository.
2. **No frontend CI gate identified.** Add install, lockfile integrity, lint, typecheck, unit/component tests, production build, and dependency/security checks for the web workspace. Preserve all Python CI jobs.
3. **Authentication contract must be confirmed at integration time.** The UI must consume the approved Platform identity flow and server-enforced principal scopes; it must not create a parallel identity/authorization authority or store privileged secrets in browser storage.
4. **API client contract must be derived from source.** Keep strict request schemas, idempotency behavior, error semantics, cancellation and tenant/subject non-disclosure. Do not hand-write unsupported endpoint assumptions.
5. **Collections and billing/admin UI are contract-gated.** Do not imply persistent user collections, credential management, billing-provider settlement, or administrative powers unless implemented APIs and authorization tests support them.
6. **Live and fixture data must be structurally distinct.** Fixtures must be explicitly marked and must never appear as live customer history or real operational metrics.
7. **Operational readiness is external to frontend CI.** A green web build does not close W7–W15 governance, deployment, security, privacy, live quality, SLO/on-call or consumer-conformance gates.

## F0 exit criteria

- [x] Root and app structure inspected.
- [x] Frontend presence and tooling assessed from the inspected root and workflow files.
- [x] Jobs, evidence, verification, monitor, and authority boundaries mapped to source/docs.
- [x] Existing CI checks and frontend coverage gap recorded.
- [x] Blockers and F1 implementation constraints documented.
- [x] Exact PR-head CI passed on commit `0773307fc8c71264e5b0d27b4c340ec3aee11fc3` in [run #39374128740](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39374128740).
- [x] Post-merge main CI passed on merge commit `195bcf970e86537b2d9cdb7d1b96576bd7fb1476` in [run #39374414981](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39374414981).
- [x] Post-commit forensic review confirmed the report matches the repository state.

## F1 entry criteria

Build an isolated `apps/web` frontend workspace, leaving existing Python `apps/*` services intact. Start with a small responsive shell, design tokens, semantic primitives, accessible navigation, explicit live/fixture separation, and frontend CI. Avoid speculative dashboard metrics. The first end-to-end product slice should be investigation submission → durable job status → source-backed result → authorized evidence inspection.

## Limitations

This is a repository and source-contract audit, not a live deployment audit. The inspection did not establish a deployed frontend, approved production identity configuration, customer environment, live browser journey, or production readiness. Those claims require separate evidence.
