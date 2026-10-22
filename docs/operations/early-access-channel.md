# Tinlyt early-access request channel

## Architecture

The public static site submits JSON to the Vercel serverless endpoint at `/api/early-access`. The endpoint enforces an exact HTTPS origin, checks the JSON content type, validates and bounds fields, verifies Cloudflare Turnstile server-side including its hostname, rate-limits by keyed hashes of client IP and normalized email, stores the request before sending transactional email, and records delivery outcomes separately. A saved request is authoritative even if email delivery fails.

## Required Vercel environment variables

- `EARLY_ACCESS_ENABLED`: feature flag enforced by both the static build and the server endpoint. Keep `false` in Production until the intended Supabase database is migrated, server-only secrets and Resend sender/inbox are verified, privacy is approved, and Preview passes the full test matrix. A disabled flag must reject direct API submissions as well as hide the form.

Configure these in the Tinlyt Vercel project, initially for Preview only:

- `SUPABASE_URL`: URL of the database project intentionally selected for Tinlyt.
- `SUPABASE_SECRET_KEY`: server-only Supabase secret key (preferred), or legacy `SUPABASE_SERVICE_ROLE_KEY`. Never use a `NEXT_PUBLIC_` prefix.

The endpoint sends modern `sb_secret_` keys only in the `apikey` header because these keys are not JWTs. The legacy `SUPABASE_SERVICE_ROLE_KEY` fallback is sent in both `apikey` and `Authorization: Bearer` headers. Keep either key server-only.
- `TURNSTILE_SECRET_KEY`: Cloudflare Turnstile secret for the site key used by the form.
- `RESEND_API_KEY`: server-only Resend API key.
- `RESEND_FROM_EMAIL`: sender on a verified Resend domain, only after the sender identity is confirmed.
- `EARLY_ACCESS_NOTIFY_EMAIL`: monitored team inbox that should receive requests.
- `EARLY_ACCESS_ALLOWED_ORIGIN`: exact HTTPS origin of the tested deployment, with no path or trailing slash. Use a stable Preview hostname for Preview and `https://tinlyt.tinlance.com` for Production.
- `EARLY_ACCESS_RATE_LIMIT_SALT`: server-only cryptographically random secret of at least 32 characters. Never commit it, expose it to the browser, or reuse a password.
- `EARLY_ACCESS_PRIVACY_NOTICE_VERSION`: non-empty identifier for the exact approved privacy notice shown to applicants; do not activate intake until the notice and version match.

Set `EARLY_ACCESS_TURNSTILE_SITE_KEY` as a Vercel build environment variable. The frontend build injects this public site key into the generated `dist/runtime-config.js`; do not edit the source runtime config for each deployment. Use separate Turnstile widgets/keys for Preview and Production, and restrict each widget to the matching hostname. The site key is public; the Siteverify secret is server-only. The form remains disabled unless `EARLY_ACCESS_ENABLED=true` and a site key is present in the same build; the API also checks `EARLY_ACCESS_ENABLED` server-side so direct POST requests cannot bypass a disabled form.

## Database setup

Review `supabase/migrations/20261022072400_early_access_requests.sql` and apply it only to the database explicitly selected for Tinlyt. It is intentionally separate from `db/migrations/`, which belongs to the core TWI service and its packaged migration set. The migration enables RLS, revokes browser-role privileges, gives the server role only the insert/read-ID/update-delivery-status permissions it needs, and keeps rate-limit state in the non-exposed `tinlyt_private` schema. The rate-limit RPC is `SECURITY INVOKER` and executable only by `service_role`. Do not apply it to the currently connected Supabase project until that project is confirmed as the Tinlyt data store. Verify the Data API is enabled and `public` is an exposed schema for the server-side PostgREST calls; public browser roles still have no grants on the intake table.

## Preview-first activation checklist

1. **Confirm project identity before touching the database.** Verify the dedicated Supabase project name/ref, organization, region, active/healthy status, and intended purpose. Do not apply the migration to a generic/shared project or the core TWI database. Record metadata, not credentials, in the deployment evidence ledger.
2. **Apply and verify the migration.** Apply `supabase/migrations/20261022072400_early_access_requests.sql` only to the confirmed dedicated project. Verify `public.early_access_requests`, `tinlyt_private.early_access_rate_limits`, and `public.consume_early_access_rate_limit`; inspect migration history, RLS and grants; run Supabase security and performance advisors.
3. **Approve privacy notice.** Complete the controller/legal entity, contact address, purpose, lawful basis, retention period, rights-request channel, processors, and any international-transfer disclosures. Set `EARLY_ACCESS_PRIVACY_NOTICE_VERSION` to the exact notice version.
4. **Configure Preview only.** Use a stable Preview hostname and matching Turnstile widget/site key and server-side secret. Set `EARLY_ACCESS_ENABLED=true` and `EARLY_ACCESS_TURNSTILE_SITE_KEY` only for Preview. Configure Preview-only Supabase credentials and Resend settings; do not point Preview at production lead data. Never expose secret/service-role keys, Turnstile secrets, Resend keys, or the rate-limit salt in browser code or `NEXT_PUBLIC_` variables.
5. **Test the positive path.** Submit through the actual Preview form. Verify success, exactly one row with the expected consent/privacy version, team notification, applicant confirmation, and persisted delivery statuses.
6. **Test duplicate handling.** Submit the same normalized email with a fresh valid Turnstile token. Verify generic success on unique-constraint conflict and no second row.
7. **Test rate limiting.** With controlled test identities and fresh valid tokens, verify the sixth request in a 15-minute window receives HTTP 429 and `Retry-After`; verify limiter failure is fail-closed. Do not load-test Production.
8. **Test bot and validation paths.** Verify invalid/expired tokens and hostname mismatch are rejected; honeypot submissions create no row; invalid origin, wrong content type, missing consent, malformed fields and oversized payloads are rejected.
9. **Test failures.** Missing config fails closed with 503; database failure never returns success; team-notification and applicant-confirmation failures are recorded independently while the lead remains stored; failure to persist delivery status is visible in logs/alerts.
10. **Review and sign off.** Attach timestamped, redacted evidence for every test path, review Supabase advisors and Vercel logs, and get explicit owner approval before Production activation.

Vercel environment variables are scoped to Production, Preview, and Development and are injected into a deployment; changing them requires a new deployment. Verify variable names and environment scope without printing values. Use separate Preview and Production Turnstile widgets/secrets. The site key is public; the Siteverify secret is server-only.

## Lead review operations

Initially review leads in the dedicated Supabase dashboard: Table Editor → `public.early_access_requests`. Restrict access to the owner and explicitly authorized reviewers; use individual accounts, MFA/passkeys where available, least privilege, and prompt access removal. Never share the owner account or expose a service-role key to a browser. Review `status`, `created_at`, `notification_status`, and `confirmation_status`. A custom admin UI is deferred unless a concrete workflow need is established; if built later, it must use authenticated server-side access, authorization checks and audit logging.

## Production activation

Keep `EARLY_ACCESS_ENABLED=false` in Production until Preview tests pass, the privacy notice is approved, the dedicated project is verified, email delivery is verified, and the owner explicitly approves launch. Configure Production-scoped credentials and a separate Production Turnstile widget/secret. Confirm the Production origin is exactly `https://tinlyt.tinlance.com`, then redeploy. Verify the live form is enabled and submit one controlled test request; confirm the row and both email outcomes before accepting public leads. If any check fails, disable intake and investigate.

## Data handling

The form requests only information needed to review a product evaluation. Marketing opt-in is separate and optional. Do not collect passwords, API keys, private keys, or sensitive customer data. The request endpoint does not promise acceptance or immediate workspace access.

## Operational limitation

The endpoint relies on server-verified Turnstile, a honeypot, and a database-backed limit of five requests per keyed client-IP hash and five per normalized-email hash per 15-minute window. The RPC fails closed if unavailable and opportunistically deletes stale rate-limit rows older than 24 hours. Email is best-effort; database storage is authoritative. Add operational alerting before scaling public traffic.
