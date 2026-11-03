const REDIRECT_URI_MARKER = '__TINLYT_REDIRECT_URI__';

function readString(env, name) {
  const value = env[name];
  return typeof value === 'string' ? value.trim() : '';
}

function readList(env, name) {
  return [...new Set(readString(env, name).split(',').map((item) => item.trim()).filter(Boolean))];
}

export function createRuntimeConfig(env = process.env) {
  const turnstileSiteKey = readString(env, 'EARLY_ACCESS_TURNSTILE_SITE_KEY');
  const earlyAccessEnabled = readString(env, 'EARLY_ACCESS_ENABLED') === 'true'
    && turnstileSiteKey.length > 0;
  return {
    apiBaseUrl: readString(env, 'TINLYT_API_BASE_URL') || '/api/twi',
    apiAllowedOrigins: readList(env, 'TINLYT_API_ALLOWED_ORIGINS'),
    earlyAccessEnabled,
    earlyAccessTurnstileSiteKey: turnstileSiteKey,
    oauth: {
      issuer: readString(env, 'TINLYT_OAUTH_ISSUER'),
      authorizationEndpoint: readString(env, 'TINLYT_OAUTH_AUTHORIZATION_ENDPOINT'),
      tokenEndpoint: readString(env, 'TINLYT_OAUTH_TOKEN_ENDPOINT'),
      clientId: readString(env, 'TINLYT_OAUTH_CLIENT_ID'),
      redirectUri: REDIRECT_URI_MARKER,
      scope: readString(env, 'TINLYT_OAUTH_SCOPE'),
      resource: readString(env, 'TINLYT_OAUTH_RESOURCE'),
      trustedIssuerOrigins: readList(env, 'TINLYT_OAUTH_TRUSTED_ISSUER_ORIGINS'),
    },
  };
}

export function renderRuntimeConfig(env = process.env) {
  const serialized = JSON.stringify(createRuntimeConfig(env), null, 2);
  const marker = JSON.stringify(REDIRECT_URI_MARKER);
  const browserConfig = serialized.replace(marker, 'window.location.origin + "/auth/callback"');
  return 'window.TINLYT_RUNTIME_CONFIG = Object.freeze(' + browserConfig + ');\n';
}
