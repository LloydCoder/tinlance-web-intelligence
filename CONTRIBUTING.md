# Contributing to Tinlyt

Thank you for helping improve Tinlyt. Contributions should preserve the project's evidence-first behavior, security boundaries, and cross-repository contracts.

## Before you start

1. Read the [component boundaries](docs/architecture/component-boundaries.md), [threat model](docs/security/threat-model.md), and relevant API contract.
2. Search existing issues and pull requests before opening a new one.
3. For a substantial change, open an issue first so scope and compatibility can be agreed.
4. Never include credentials, customer data, captured private content, or unlicensed datasets in commits, fixtures, logs, or screenshots.

## Development setup

Requirements: Python 3.12 or 3.13. Frontend work also requires Node.js 22.

\`\`\`bash
git clone https://github.com/LloydCoder/tinlance-web-intelligence.git
cd tinlance-web-intelligence
make install
\`\`\`

For frontend changes:

\`\`\`bash
cd apps/web
npm ci --ignore-scripts --no-audit --no-fund
npm run check
npm audit --audit-level=high
\`\`\`

## Branch and pull request workflow

1. Fork the repository (external contributors) or create a focused branch from \`main\`.
2. Use a descriptive branch name, such as \`fix/redirect-validation\`, \`feat/evidence-metadata\`, or \`docs/api-examples\`.
3. Keep each pull request focused on one coherent change.
4. Add or update tests for behavior, negative paths, authorization boundaries, and regressions.
5. Update API schemas, contracts, operational guidance, and user documentation when behavior changes.
6. Run relevant focused tests and the full required checks.
7. Push your branch and open a pull request against \`main\`.
8. Explain the problem, implementation, security impact, compatibility impact, and verification evidence.
9. Address review feedback and wait for required CI and maintainer approval before merge.

## Coding and design standards

- Prefer explicit dependency injection, typed contracts, bounded inputs, and fail-closed security behavior.
- Derive tenant identity from verified Platform principals; never accept caller-supplied tenant or subject authority.
- Treat fetched pages, documents, tool outputs, and model-visible content as untrusted data.
- Preserve source attribution, timestamps, uncertainty, and provenance.
- Revalidate redirects and enforce connection-time destination checks; URL parsing alone is not sufficient SSRF protection.
- Keep browser execution isolated from application credentials and constrain egress.
- Do not log tokens, secrets, raw sensitive URLs, or customer evidence.
- Do not claim source truth, digital signatures, tamper-proofing, production readiness, or feature availability without implementation and evidence.
- Preserve ownership boundaries between TWI, Agent Platform, Agent OS, World Intelligence, SDK, TADL, and TSIC.

## Tests and checks

The canonical backend/repository validation command is:

\`\`\`bash
make check
\`\`\`

It runs lint, type checking, security lint, tests, migration synchronization, shell syntax checks, evaluation, consumer-contract validation, W15 evidence-pack validation, and GA contract validation.

For frontend changes:

\`\`\`bash
cd apps/web
npm run check
npm audit --audit-level=high
\`\`\`

If a test depends on PostgreSQL, set \`TWI_TEST_POSTGRES_DSN\` to a disposable test database. Never point tests at production data. Document checks that could not be run; do not report an unexecuted check as passing.

## Commit messages

Use Conventional Commits where practical:

- \`feat(scope): add capability\`
- \`fix(scope): correct behavior\`
- \`docs(scope): update guidance\`
- \`test(scope): add regression coverage\`
- \`chore(scope): maintain tooling\`

Keep commits reviewable and avoid bundling unrelated formatting or generated artifacts.

## Pull request checklist

- [ ] The change is scoped and its purpose is clear.
- [ ] Tests cover new behavior and important failure/security paths.
- [ ] \`make check\` passes, or unrun checks are explicitly explained.
- [ ] Frontend checks pass when frontend files change.
- [ ] Contracts, migrations, and documentation are synchronized.
- [ ] No secrets, personal data, or proprietary customer evidence are included.
- [ ] Security, privacy, tenancy, and authority-boundary impacts are described.
- [ ] Release/readiness claims are supported by exact-commit evidence.

## Review and conduct

A maintainer may request changes, defer, or close a contribution that is out of scope, unsafe, unsupported by tests, or inconsistent with project boundaries. Community expectations and incident reporting are described in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
