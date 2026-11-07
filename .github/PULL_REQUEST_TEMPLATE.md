## Summary

<!-- What changed and why? -->

## Change type

- [ ] Bug fix
- [ ] Feature
- [ ] Security hardening
- [ ] Documentation
- [ ] Refactor / maintenance
- [ ] Release / operational change

## Implementation and compatibility

<!-- Describe design decisions, affected contracts, migrations, consumers, and compatibility. -->

## Security, privacy, and authority

- [ ] Tenant and subject scope remain derived from verified Platform identity.
- [ ] External content and tool output remain untrusted.
- [ ] No secrets, customer data, or sensitive evidence are introduced.
- [ ] SSRF, redirect, browser isolation, and egress implications are addressed.
- [ ] Authority boundaries and approval requirements are preserved.
- [ ] Evidence claims do not overstate truth, integrity, or readiness.

## Verification

- [ ] Focused tests pass.
- [ ] \`make check\` passes.
- [ ] Frontend checks pass when frontend files change.
- [ ] Migrations and schemas are synchronized.
- [ ] Documentation and examples match implementation.
- [ ] Checks not run are explained below.

**Commands and results:**

<!-- Paste sanitized command output or link exact-commit CI runs. -->

## Release/readiness impact

<!-- State whether this changes any readiness gate. Link evidence; do not infer deployment readiness from CI. -->

## Reviewer checklist

- [ ] Scope is focused and reviewable.
- [ ] Failure paths and authorization cases are covered.
- [ ] No unsupported product, security, or release claims are added.
