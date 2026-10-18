# Acceptance criteria

Each workstream must attach evidence for:

- scope and ownership boundary;
- implementation and code review;
- unit, contract, integration, security, concurrency and relevant end-to-end tests;
- CI workflow run and exact commit SHA;
- threat-model and operational-document updates;
- consumer compatibility and TSIC conformance where applicable;
- migration behavior and recovery semantics for persistence changes;
- unresolved risks and explicit non-goals.

A check that has not run is not passing. A workflow configuration is not proof that a workflow passed. Repository CI is not proof of a deployed environment, network policy, secret rotation, or backup recovery.
