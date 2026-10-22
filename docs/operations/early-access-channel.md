# Tinlyt early-access request channel

## Architecture

The public static site submits to the Vercel serverless endpoint at \`/api/early-access\`. The endpoint verifies Cloudflare Turnstile server-side, validates and bounds every field, stores the request in PostgreSQL/Supabase before sending email, and then attempts a team notification and applicant confirmation through Resend. A saved request is successful even if email delivery fails; delivery state is tracked separately.

## Required Vercel environment variables

Configure these in the Tinlyt Vercel project, initially for Preview only:

- \`SUPABASE_URL\`: URL of the database project intentionally selected for Tinlyt.
- \`SUPABASE_SECRET_KEY\`: server-only Supabase secret key (preferred), or legacy \`SUPABASE_SERVICE_ROLE_KEY\`. Never use a \`NEXT_PUBLIC_\` prefix.
- \`TURNSTILE_SECRET_KEY\`: Cloudflare Turnstile secret for the site key used by the form.
- \`RESEND_API_KEY\`: server-only Resend API key.
- \`RESEND_FROM_EMAIL\`: sender on a verified Resend domain, only after the sender identity is confirmed.
- \`EARLY_ACCESS_NOTIFY_EMAIL\`: monitored team inbox that should receive requests.
- \`EARLY_ACCESS_ALLOWED_ORIGIN\`: \`https://tinlyt.tinlance.com\`.

The public Turnstile site key is configured in \`apps/web/runtime-config.js\` as \`earlyAccessTurnstileSiteKey\`; it is not a secret. Never commit any secret to the repository or expose one in browser code.

## Database setup

Review \`db/migrations/004_early_access_requests.sql\` and apply it only to the intended Tinlyt database. This migration has deliberately not been applied automatically because the connected Supabase project must be explicitly confirmed as the Tinlyt data store. The table enables RLS and revokes all browser-role access; only the server-side key can write through the endpoint.

## Activation checklist

1. Confirm the Supabase project and apply the migration.
2. Create a Cloudflare Turnstile widget for \`tinlyt.tinlance.com\`; set its site key in runtime config and its secret in Vercel.
3. Confirm the Resend sender identity and monitored notification inbox; add the server-only API key to Vercel.
4. Set all variables for Preview and verify valid, invalid, duplicate, honeypot, expired-token, missing-config, database-failure and email-failure behavior.
5. Review the privacy notice with the responsible legal entity, controller contact, retention period, purpose and rights contact completed.
6. Only after preview evidence is green, configure Production variables and deploy. Then submit a real test request and verify the database row, team notification and applicant confirmation.

## Data handling

The form requests only information needed to review a product evaluation. Marketing opt-in is separate and optional. Do not collect passwords, API keys, private keys, or sensitive customer data. The request endpoint does not promise acceptance or immediate workspace access.

## Operational limitation

The endpoint relies on server-verified Turnstile, a honeypot, and a database-backed limit of five requests per hashed client key per 15-minute window. The rate-limit RPC fails closed if unavailable. Add alerting and a retention/cleanup policy for rate-limit records before scaling public traffic. Email is best-effort; database storage is authoritative.
