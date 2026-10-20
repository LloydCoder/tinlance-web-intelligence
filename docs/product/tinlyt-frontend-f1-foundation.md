# Tinlyt Frontend F1 — Workspace and Design Foundation

**Status:** Implemented in the F1 pull request; acceptance requires the exact-head GitHub Actions run to pass and the resulting diff to be reviewed.  
**Product:** Tinlyt  
**Engineering identity:** Tinlance Web Intelligence (TWI)

## Scope delivered

- A self-contained static frontend workspace under `apps/web/`, without changing the existing Python package or its dependency management.
- A responsive application shell with primary navigation, skip link, semantic landmarks, visible focus, reduced-motion support, and narrow-screen layout.
- Design tokens and reusable CSS primitives for surfaces, typography, spacing, borders, status, forms, panels and navigation.
- A truthful foundation-mode notice. Investigation submission, account controls, runs, evidence and monitors are visibly unavailable until the real API and identity integration are implemented.
- A dependency-free Node test suite, source hygiene checks, JavaScript syntax checks and deterministic static asset build.
- A separate GitHub Actions workflow that runs only when frontend files or the workflow change, with read-only repository permissions and concurrency cancellation.

## Security and product truth

- No credentials, tokens, or privileged API operations are present in browser code.
- The form is disabled; this phase does not simulate or fabricate job submission, run results, evidence, metrics, or account state.
- The UI explicitly states that API integration is not configured.
- Navigation state is presentation-only and is not an authorization mechanism.
- The static build currently imports web fonts from Google Fonts. If the deployment requires strict self-hosting, privacy controls, or offline operation, vendor approved font files and remove the external import in a follow-up hardening change.

## Deliberate limitations

This is a foundation, not a completed product. It does not yet implement authentication, API requests, route-level page rendering, job polling, cancellation, evidence export, verification, monitors, persistence, telemetry, or deployment. F2 must select and implement the approved identity integration and typed API client before any live workflow is enabled.

## Verification commands

Run from `apps/web/`:

```sh
npm run lint
npm run typecheck
npm test
npm run build
```

The frontend workflow is an independent quality gate and does not replace the existing Python CI, API contract tests, security checks, or TWI deployment/release gates.
