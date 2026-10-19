# W15-C Implementation Plan

- [x] C1 — Audit and reuse the current offline evaluator, six v1 cases, deterministic timestamp, and dataset/result hashing.
- [x] C2 — Extend dataset/result contracts for challenge class, support status, completion outcome, evidence mode, latency, resource bytes, requests, and retries.
- [x] C3 — Add hard cases for JavaScript-heavy pages, pagination/duplicates, conflicting sources, transient recovery, anti-bot outcomes, and unsupported paths.
- [x] C4 — Add outcome-contract correctness, evidence-quality composite, latency/resource metrics, per-class counts, source revision, and deterministic report hash.
- [x] C5 — Add threshold registry that fails closed as not_evidenced until an authorized owner approves explicit numeric thresholds.
- [x] C6 — Add strict schema validation and adversarial tests; preserve URL-free reports and the non-truth boundary.
- [ ] C7 — Run full CI on the final exact PR head, fix blockers, and perform a phase-specific forensic audit.
- [ ] C8 — Merge only after all required checks pass; verify post-merge main CI before W15-D.
- [ ] C9 — Reconcile roadmap/readiness documentation with exact SHA, run links, test evidence, and residual external gates.

## Non-goals

- No live web fetches in the evaluator.
- No unapproved numeric pass/fail thresholds.
- No truth classifier or FAS-Bench replacement.
- Synthetic fixtures are not live-quality evidence.


## Forensic findings addressed during implementation

- Updated the pre-existing evaluator tests to use the expanded `twi-hardjobs-v1` dataset and assert the new outcome/operational metrics instead of stale `twi-core-v1` fixture totals.
- Fixed the seven Ruff E501 failures reported by CI in the expanded evaluator.
- Revalidate the threshold registry inside `evaluate()`, not only in the CLI loader, so programmatic callers cannot obtain a qualification pass using an incomplete approved-looking mapping.
- The benchmark remains synthetic-only in checked-in results and the threshold registry remains unapproved; the evaluator must therefore report `not_evidenced` for qualification.
- Reconciled `docs/evaluation/twi-benchmark.md` with the v1.1.0 dataset/result contract, hard-case matrix, metrics, threshold governance, and interpretation boundaries.
- Validate the dataset description as a normalized non-empty string and restrict expected/observed failure classifications to the versioned known set; adversarial tests reject unknown labels.
- Narrow threshold-bound types at the comparison boundary so strict typing verifies the evaluator's fail-closed numeric checks.
- Bind qualification to the exact raw threshold-registry bytes, verify the SHA-256 at the evaluator boundary, and reject mismatches between the raw registry and a caller-supplied parsed mapping; regression test covers a forged digest.
