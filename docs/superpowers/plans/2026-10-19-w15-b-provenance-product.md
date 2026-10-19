# W15-B Implementation Plan

This plan is evidence-gated. Do not mark W15-B complete based on documentation, package scaffolding, or a successful unit-test subset alone.

- [x] B1 — Audit and reuse the existing acquisition provenance manifest, content-addressed artifact stores, and successful fetch job result.
- [x] B2 — Define a deterministic, versioned export format with source revision, byte content, digest, lineage, and explicit non-truth semantics.
- [x] B3 — Implement deterministic package builder and validator with canonical serialization, strict schema checks, stable export IDs, size limits, and integrity verification.
- [x] B4 — Add dedicated-scope, tenant/subject-scoped export endpoint and deployment source-revision binding.
- [x] B5 — Add package schema, API docs, and focused adversarial tests.
- [x] B6 — Focused unit/API/schema tests, full CI, Python 3.12/3.13 checks, reproducible artifact validation, and browser isolation passed on exact PR head `c9331b33e997bae010ada4bc4cebd3c36ee42b4a` in [run #39303747429](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39303747429).
- [x] B7 — Fixed lint and typing blockers; forensic review covered authorization, tenant isolation, metadata redaction, deterministic serialization, tamper validation, artifact integrity, deployment source revision, tool catalog parity, and external consumer mismatch. CI reports lint/type/security/test success on the reviewed head.
- [x] B8 — Merged PR [#61](https://github.com/LloydCoder/tinlance-web-intelligence/pull/61) as `8bdf2453dbdcbd7552935ee5c0fac1b106dfe595`; exact-head CI passed in [run #39304607623](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39304607623) and post-merge main CI passed in [run #39305123725](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39305123725).
- [x] B9 — Reconciled roadmap and readiness documentation before W15-C. Post-merge main CI passed in [run #39305123725](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39305123725) on merge commit `8bdf2453dbdcbd7552935ee5c0fac1b106dfe595`; Platform-side tool registration, immutable retention, and external deployment evidence remain unresolved.

## External constraints

- Production artifact export requires the shared PostgreSQL artifact store; process-local memory storage is not durable across API/worker processes.
- Deployment must inject `TWI_SOURCE_REVISION` as the full immutable source commit SHA for exports to be enabled.
- This package is integrity-checked but not signed; authenticity, immutable retention, backup recovery, and external audit archive configuration remain separate deployment controls.
- The export schema does not infer source truth, authority, completeness, or safety.
