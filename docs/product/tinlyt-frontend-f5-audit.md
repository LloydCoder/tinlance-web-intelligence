# Tinlyt Frontend F5 — Evidence Inspection Forensic Audit

**Audit date:** 2026-10-20  
**Phase:** F5 — Evidence inspection and export  
**Status:** Accepted for repository implementation; production integration remains a separate deployment gate.

## Scope and exact-commit evidence

F5 added a reachable evidence inspector, typed export of the canonical evidence package, exact-byte download, bounded response reading, provenance rendering, dynamic integrity state, and session/job-change clearing.

- PR #76 — `feat(frontend): implement Tinlyt F5 evidence inspection`
- PR head commit: `b16098ff4d60ca3839969f16ab9045beae29c604`
- Merge commit: `bab5e13fd67f219b8d25ab1baf2dcb61df3bdb8a`
- Exact-PR Frontend workflow: [#39388640468](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39388640468) — success.
- Exact-PR repository CI: [#39388640435](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39388640435) — success.
- Post-merge Frontend workflow on the merge commit: [#39389037708](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39389037708) — success.
- Post-merge repository CI on the merge commit: [#39389037674](https://github.com/LloydCoder/tinlance-web-intelligence/actions/runs/39389037674) — success.

## Forensic findings

### Accepted implementation

1. The evidence inspector is a real navigation target with an honest empty state. The integrity badge remains “Awaiting package” until schema and captured-content validation succeeds.
2. Evidence export is offered only for an authenticated, service-reported successful fetch job with a returned result. TWI's existing endpoint and its `twi:evidence:export` permission plus tenant/subject enforcement remain authoritative.
3. The client requires the exact `application/vnd.tinlance.twi-evidence+json` media type (allowing media-type parameters), rejects other JSON media types, and reads at most 30,000,000 response bytes before parsing.
4. The client preserves the exact response bytes while separately parsing and validating the package. Schema version, metadata consistency, captured byte size, and SHA-256 are validated. The download action writes those original bytes rather than reserializing the object.
5. The inspector renders metadata through text-only DOM APIs. It shows URL fingerprints, source revision, observed HTTP status, retrieval timestamp, redirect count, extractor version, content type, size, and digest; it does not render captured HTML or fabricate raw URLs.
6. The package and bytes are held in memory only. Sign-out clears the current job/result/evidence view; an auth-session epoch prevents late responses from an earlier identity session or job selection from repainting the UI.
7. The UI explicitly distinguishes content-integrity validation from a digital signature, source-authority assessment, and factual truth. The status badge does not claim validation before a package is loaded.

### Defects found and fixed before merge

- TypeScript initially flagged unsafe indexing of a split media-type value. The client now handles a missing/empty media type safely; exact-PR typecheck passed.
- The first F5 test pass exposed brittle source-level lifecycle assertions after F4's session-race guard was added. Tests were reconciled to assert the actual supported request/session guard rather than a stale line ordering.
- Forensic review found that a static “Integrity checked” badge would imply validation before a package existed. It was changed to a pending state and flips to “Digest verified” only after package validation.
- Review found that a late export response could leave the inspector displaying a stale loading message after a job change. The handler now clears that stale state and does not restore actions for a stale job.
- Async job, lookup, cancellation, and evidence responses are guarded by the current authorization-session epoch; logout clears displayed job results and in-memory evidence bytes.

### Test evidence

The Frontend workflow passed lint/source hygiene, syntax check, TypeScript typecheck, dependency audit, static security checks, tests, and build. API-client tests cover exact response-byte preservation, legacy export compatibility, strict media type, oversized responses, permission-denied mapping without exposing server response content, malformed JSON, tampered captured content, and bounded reads. Shell tests cover the evidence inspector's empty/validated states, metadata fields, explicit download, truth-claim boundaries, and session guards.

## Residual limitations

- UI tests are still primarily API-client unit tests and static shell assertions; they do not yet prove a real-browser download interaction under concurrent network/session changes. F10 must add browser-level interaction and accessibility tests.
- CI does not prove a production identity-provider configuration, a live deployment, or end-to-end authorization against a deployed tenant. Those remain deployment/release gates.
- The UI does not claim immutable retention, external audit archival, or a digital signature. The package's content digest validates captured bytes against the package metadata only.

## F5 exit decision

**Accepted for repository implementation.** Exact-PR Frontend and repository CI, plus both post-merge main workflows, passed on the final F5 code. The audit findings above were fixed before merge. Proceed to F6 (claim verification UI) without treating repository CI as production deployment certification.
