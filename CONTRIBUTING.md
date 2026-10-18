# Contributing

1. Read the architecture boundary and threat model before implementation.
2. Keep changes scoped to one workstream and one pull request.
3. Add tests for behavior, error cases, security boundaries, and regressions.
4. Never claim a feature is implemented without executable tests and evidence.
5. Run `make check` and update documentation/contracts with code changes.
6. Do not add credentials, real user data, captured private content, or unlicensed datasets.
7. Preserve source attribution, uncertainty, timestamps, and lineage.
8. Obtain required review and wait for all required CI checks before merge.

Prefer small interfaces and explicit dependency injection. Avoid global mutable state, hidden network access, unsafe defaults, and implicit cross-repository authority. Any contract change affecting consumers must include compatibility analysis and a TSIC conformance plan.
