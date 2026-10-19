# W15-B Implementation Plan

This plan is evidence-gated. Do not mark W15-B complete based on documentation, package scaffolding, or a successful unit-test subset alone.

- [x] B1 — Audit and reuse the existing acquisition provenance manifest, content-addressed artifact stores, and successful fetch job result.
- [x] B2 — Define a deterministic, versioned export format with source revision, byte content, digest, lineage, and explicit non-truth semantics.
- [x] B3 — Implement deterministic package builder and validator with canonical serialization, strict schema checks, stable export IDs, size limits, and integrity verification.
- [x] B4 — Add dedicated-scope, tenant/subject-scoped export endpoint and deployment source-revision binding.
- [x] B5 — Add package schema, API docs, and focused adversarial tests.
- [ ] B6 — Run focused unit/API/schema tests, full `make check`, Python 3.12/3.13 CI, package reproducibility, and browser isolation workflow on exact PR head.
- [ ] B7 — Fix all test/lint/type/security/contract failures and audit changed code plus existing provenance/artifact boundaries.
- [ ] B8 — Merge only after required checks are green on the exact reviewed head; verify post-merge main CI.
- [ ] B9 — Update roadmap/readiness documentation with exact source revision, run URLs, test evidence, residual risks, and external gates before W15-C.

## External constraints

- Production artifact export requires the shared PostgreSQL artifact store; process-local memory storage is not durable across API/worker processes.
- Deployment must inject `TWI_SOURCE_REVISION` as the full immutable source commit SHA for exports to be enabled.
- This package is integrity-checked but not signed; authenticity, immutable retention, backup recovery, and external audit archive configuration remain separate deployment controls.
- The export schema does not infer source truth, authority, completeness, or safety.
