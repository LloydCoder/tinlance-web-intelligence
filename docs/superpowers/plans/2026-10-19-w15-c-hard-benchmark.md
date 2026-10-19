# W15-C Implementation Plan

- [x] C1 — Audit and reuse the current offline evaluator, six v1 cases, deterministic timestamp, and dataset/result hashing.
- [x] C2 — Extend dataset/result contracts for challenge class, support status, completion outcome, evidence mode, latency, resource bytes, requests, and retries.
- [x] C3 — Add hard cases for JavaScript-heavy pages, pagination/duplicates, conflicting sources, transient recovery, anti-bot outcomes, and unsupported paths.
- [x] C4 — Add outcome-contract correctness, evidence-quality composite, latency/resource metrics, per-class counts, source revision, and deterministic report hash.
- [x] C5 — Add threshold registry that fails closed as not_evidenced until an authorized owner approves explicit numeric thresholds.
- [x] C6 — Add strict schema validation and adversarial tests; preserve URL-free reports and the non-truth boundary.
- [x] C7 — Full CI passed on exact PR head `57fad22ead23c0b0298eaf0c29d9fd2d7165bfa0` in [PR run #39310534386](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39310534386). Phase-specific forensic audit fixed threshold-registry digest bypasses, unknown failure classifications, stale tests, and strict typing issues.
- [x] C8 — Merged PR [#62](https://github.com/LloydCoder/tinlance-web-intelligence/pull/62) as `309baed3956cee4b6afdd33244ab5253e900e9a1`; post-merge main CI passed in [run #39311190074](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39311190074).
- [x] C9 — Reconciled roadmap, benchmark guide, W15-B closeout, and this plan. The checked-in threshold registry remains unapproved and synthetic observations remain non-qualifying; external W15 gates are unchanged.

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
