# Tinlyt early-access request channel

## Architecture

The public static site submits JSON to the Vercel serverless endpoint at `/api/early-access`. The endpoint enforces an exact HTTPS origin, checks the JSON content type, validates and bounds fields, verifies Cloudflare Turnstile server-side including its hostname, rate-limits by keyed hashes of client IP and normalized email, stores the request before sending transactional email, and records delivery outcomes separately. A saved request is authoritative even if email delivery fails.

## Required Vercel environment variables

Configure these in the Tinlyt Vercel project, initially for Preview only:

- `SUPABASE_URL`: URL of the database project intentionally selected for Tinlyt.
- `SUPABASE_SECRET_KEY`: server-only Supabase secret key (preferred), or legacy `SUPABASE_SERVICE_ROLE_KEY`. Never use a `NEXT_PUBLIC_` prefix.
- `TURNSTILE_SECRET_KEY`: Cloudflare Turnstile secret for the site key used by the form.
- `RESEND_API_KEY`: server-only Resend API key.
- `RESEND_FROM_EMAIL`: sender on a verified Resend domain, only after the sender identity is confirmed.
- `EARLY_ACCESS_NOTIFY_EMAIL`: monitored team inbox that should receive requests.
- `EARLY_ACCESS_ALLOWED_ORIGIN`: `https://tinlyt.tinlance.com`.

Set `EARLY_ACCESS_TURNSTILE_SITE_KEY` as a Vercel build environment variable. The frontend build injects this public site key into the generated `dist/runtime-config.js`; do not edit the source runtime config for each deployment. Use separate Turnstile widgets/keys for Preview and Production, and restrict each widget to the matching hostname. The site key is public; the Siteverify secret is server-only.

## Database setup

Review `supabase/migrations/20261022072400_early_access_requests.sql` and apply it only to the database explicitly selected for Tinlyt. It is intentionally separate from `db/migrations/`, which belongs to the core TWI service and its packaged migration set. The migration enables RLS, revokes browser-role privileges, gives the server role only the insert/read-ID/update-delivery-status permissions it needs, and keeps rate-limit state in the non-exposed `tinlyt_private` schema. The rate-limit RPC is `SECURITY INVOKER` and executable only by `service_role`. Do not apply it to the currently connected Supabase project until that project is confirmed as the Tinlyt data store. Verify the Data API is enabled and `public` is an exposed schema for the server-side PostgREST calls; public browser roles still have no grants on the intake table.

## Activation checklist

1. Confirm the Supabase project and apply the migration.
2. Create a Cloudflare Turnstile widget for the relevant environment hostname. Set `EARLY_ACCESS_TURNSTILE_SITE_KEY` at build time and `TURNSTILE_SECRET_KEY` server-side; the Siteverify hostname must match `EARLY_ACCESS_ALLOWED_ORIGIN`.
3. Confirm the Resend sender identity and monitored notification inbox; add the server-only API key to Vercel.
4. Set all variables for Preview and verify valid, invalid, duplicate, honeypot, expired-token, missing-config, database-failure and email-failure behavior.
5. Review the privacy notice with the responsible legal entity, controller contact, retention period, purpose and rights contact completed.
6. Only after preview evidence is green, configure Production variables and deploy. Then submit a real test request and verify the database row, team notification and applicant confirmation.

## Data handling

The form requests only information needed to review a product evaluation. Marketing opt-in is separate and optional. Do not collect passwords, API keys, private keys, or sensitive customer data. The request endpoint does not promise acceptance or immediate workspace access.

## Operational limitation

The endpoint relies on server-verified Turnstile, a honeypot, and a database-backed limit of five requests per keyed client-IP hash and five per normalized-email hash per 15-minute window. The RPC fails closed if unavailable and opportunistically deletes stale rate-limit rows older than 24 hours. Email is best-effort; database storage is authoritative. Add operational alerting before scaling public traffic.
