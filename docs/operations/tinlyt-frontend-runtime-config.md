# Tinlyt frontend runtime configuration

The Vercel build generates `runtime-config.js` from a strict allowlist of public environment
variables. The generated file is loaded before the workspace application. It contains only public
OAuth client metadata and public API origins; it must never contain a client secret, access token,
refresh token, private key, database credential or service credential.

## Public Vercel build variables

| Variable | Purpose |
| --- | --- |
| `TINLYT_API_BASE_URL` | Tinlance Agent Platform API base URL. Browser requests use the governed `/v1/agent-platform` boundary; never point this at the downstream TWI REST service. |
| `TINLYT_API_ALLOWED_ORIGINS` | Comma-separated exact HTTPS origins allowed for cross-origin API calls. |
| `TINLYT_OAUTH_ISSUER` | Exact identity-provider issuer URL. |
| `TINLYT_OAUTH_AUTHORIZATION_ENDPOINT` | Authorization Code + PKCE authorization endpoint. |
| `TINLYT_OAUTH_TOKEN_ENDPOINT` | Authorization Code + PKCE token endpoint. |
| `TINLYT_OAUTH_CLIENT_ID` | Public OAuth client ID; no client secret is used by the browser. |
| `TINLYT_OAUTH_SCOPE` | Space-delimited least-privilege scopes requested by the public client. |
| `TINLYT_OAUTH_RESOURCE` | RFC 8707 resource indicator for the Tinlance Agent Platform API. Cognito receives it on `/oauth2/authorize`; do not send it again to `/oauth2/token`. |
| `TINLYT_OAUTH_TRUSTED_ISSUER_ORIGINS` | Comma-separated HTTPS origins explicitly trusted for the issuer and OAuth endpoints. For Cognito, include both the regional `cognito-idp` issuer origin and the managed-login/custom-domain origin. |

The redirect URI is generated as the current deployment origin plus `/auth/callback`. Register
that exact URI in the identity provider for both preview/staging and production clients as
appropriate. The authorization and token endpoints must share one trusted HTTPS origin. The issuer
must also be trusted, but may use a separate origin; Cognito's regional issuer and managed-login
domain are different origins. Cognito resource binding is requested at the authorization endpoint
and inherited by the resulting access token. The browser stores only the one-time PKCE transaction
in session storage; access tokens remain in memory.

## Fail-closed behavior

If any required identity value is missing, the workspace remains in foundation mode and live
operations stay disabled. A partial or insecure identity configuration must not be treated as a
successful connection. The API client independently validates the API origin allowlist.

Early access remains a separate feature. `EARLY_ACCESS_ENABLED=true` is effective only when a
public Turnstile site key is also configured.

## Server-side counterpart

The TWI service must independently verify Platform-issued tokens. Its runtime configuration uses:

- `TWI_IDENTITY_ISSUER`: exact Platform issuer.
- `TWI_IDENTITY_AUDIENCE`: exactly `tinlance-web-intelligence`.
- `TWI_IDENTITY_JWKS_URL`: HTTPS URL serving the Platform public JWKS.

The Platform must authenticate the interactive user, resolve tenant membership from trusted
server-side data, authorize the requested scopes, and then mint a short-lived downstream token
using its KMS-backed signer. Browser-supplied tenant IDs or scopes are never authoritative.

Do not populate the Vercel identity variables until the Platform authorization/token endpoint and
the TWI API are deployed and verified. Public build configuration is not a substitute for those
services.
