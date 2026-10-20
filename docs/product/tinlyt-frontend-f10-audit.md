# Tinlyt Frontend F10 — Accessibility, Security and Resilience Forensic Audit

**Phase:** F10 — Accessibility, security and resilience
**Status:** Follow-up implementation submitted; exact-head and post-merge Frontend/repository CI are required before acceptance.

## Existing implementation reviewed

- PR #89 added source-level guards against `innerHTML`, `outerHTML`, `insertAdjacentHTML`, inline event handlers and external script imports; it also added forced-colors focus styling and security/accessibility assertions.
- The document already includes language metadata, a skip link, semantic landmarks, labelled primary navigation, polite status regions, responsive breakpoints, and reduced-motion styles.
- External links are restricted and referrer leakage is suppressed; OAuth access tokens remain in memory rather than browser storage.

## Forensic findings and remediation

- Source-level assertions alone did not exercise the built application in a real browser. Add a pinned Playwright/Chromium test to the Frontend workflow against the generated `apps/web/dist` artifact.
- The muted-text token `--color-subtle: #758195` provided only approximately 4.0–4.34:1 contrast on some raised surfaces (`#1c2330` and `#171c25`), below the WCAG 2.2 AA 4.5:1 threshold for normal text. Change it to `#8996aa`, which yields at least 5.2:1 on those checked surfaces.
- Browser checks verify document language/title, landmarks, unique IDs, label associations, accessible button names, valid navigation targets, skip-link keyboard behavior, visible focus in forced-colors mode, representative contrast ratios, mobile reflow, reduced-motion behavior, and absence of uncaught browser errors or failed local assets.
- The Frontend workflow installs pinned Playwright and Chromium, builds the exact static artifact first, then tests that artifact. Increase the job timeout to accommodate browser installation.

## Security boundaries

- Keep the existing no-raw-HTML-injection gate and safe text-node rendering.
- Keep authentication tokens in memory only and do not introduce browser storage for credentials.
- Preserve no-referrer behavior and `noopener noreferrer` for dynamic external links.
- Do not loosen the API origin allowlist or add a broad static CSP that would conflict with approved deployment-specific API origins. Hosting must configure appropriate CSP/security headers for the target environment.

## Research references

- [W3C Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/): focus visibility, keyboard operation, reflow, contrast and target-size criteria.
- [W3C WAI-ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/): semantic interaction patterns and accessible naming.
- [OWASP DOM-based XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html): safe DOM APIs and avoiding injection sinks.

## Acceptance gates

1. Exact-head Frontend workflow passes dependency audit, static security, source tests, build and real Chromium browser checks.
2. Exact-head full repository CI passes Python 3.12/3.13, browser container isolation, and reproducible artifact validation.
3. Review changed files and test output, including any contrast/reflow failures; remediate rather than suppress failures.
4. After merge, Frontend and full repository CI pass on the exact main commit.
5. Keep manual screen-reader testing, representative assistive technology/browser combinations, production security headers, live identity configuration, and deployment certification as explicit residual gates.

## Non-claims

Passing automated checks is not a complete WCAG conformance audit. This phase does not certify every page state, screen-reader/browser combination, live production deployment, private-beta readiness, or GA readiness.
