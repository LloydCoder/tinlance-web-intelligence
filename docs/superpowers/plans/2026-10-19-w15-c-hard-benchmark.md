# W15-C Implementation Plan

- [x] C1 — Audit and reuse the current offline evaluator, six v1 cases, deterministic timestamp, and dataset/result hashing.
- [ ] C2 — Extend dataset/result contracts for challenge class, support status, completion outcome, evidence mode, latency, resource bytes, requests, and retries.
- [ ] C3 — Add hard cases for JavaScript-heavy pages, pagination/duplicates, conflicting sources, transient recovery, anti-bot outcomes, and unsupported paths.
- [ ] C4 — Add outcome-contract correctness, evidence-quality composite, latency/resource metrics, per-class counts, source revision, and deterministic report hash.
- [ ] C5 — Add threshold registry that fails closed as not_evidenced until an authorized owner approves explicit numeric thresholds.
- [ ] C6 — Add strict schema validation and adversarial tests; preserve URL-free reports and the non-truth boundary.
- [ ] C7 — Run full CI on exact PR head, fix blockers, and perform a phase-specific forensic audit.
- [ ] C8 — Merge only after all required checks pass; verify post-merge main CI before W15-D.
- [ ] C9 — Reconcile roadmap/readiness documentation with exact SHA, run links, test evidence, and residual external gates.

## Non-goals

- No live web fetches in the evaluator.
- No unapproved numeric pass/fail thresholds.
- No truth classifier or FAS-Bench replacement.
- Synthetic fixtures are not live-quality evidence.
