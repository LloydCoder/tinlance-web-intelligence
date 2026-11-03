import test from 'node:test';
import assert from 'node:assert/strict';
import { createRuntimeConfig, renderRuntimeConfig } from '../scripts/runtime-config.mjs';

test('runtime config fails closed when Platform identity settings are absent', () => {
  const config = createRuntimeConfig({});
  assert.equal(config.apiBaseUrl, '/api/twi');
  assert.deepEqual(config.apiAllowedOrigins, []);
  assert.equal(config.oauth.issuer, '');
  assert.equal(config.oauth.authorizationEndpoint, '');
  assert.equal(config.oauth.tokenEndpoint, '');
  assert.equal(config.oauth.clientId, '');
  assert.equal(config.oauth.scope, '');
  assert.equal(config.oauth.resource, '');
  assert.deepEqual(config.oauth.trustedIssuerOrigins, []);
  assert.equal(config.earlyAccessEnabled, false);
});

test('runtime config exposes only public OAuth settings and exact allowed origins', () => {
  const config = createRuntimeConfig({
    TINLYT_API_BASE_URL: 'https://api.tinlyt.tinlance.com',
    TINLYT_API_ALLOWED_ORIGINS: 'https://api.tinlyt.tinlance.com, https://api-staging.tinlyt.tinlance.com',
    TINLYT_OAUTH_ISSUER: 'https://identity.tinlance.com/',
    TINLYT_OAUTH_AUTHORIZATION_ENDPOINT: 'https://identity.tinlance.com/authorize',
    TINLYT_OAUTH_TOKEN_ENDPOINT: 'https://identity.tinlance.com/token',
    TINLYT_OAUTH_CLIENT_ID: 'tinlyt-public-client',
    TINLYT_OAUTH_SCOPE: 'twi:search twi:fetch twi:jobs:read',
    TINLYT_OAUTH_RESOURCE: 'tinlance-web-intelligence',
    TINLYT_OAUTH_TRUSTED_ISSUER_ORIGINS: 'https://identity.tinlance.com',
    TINLYT_OAUTH_CLIENT_SECRET: 'must-never-be-exposed',
  });

  assert.equal(config.apiBaseUrl, 'https://api.tinlyt.tinlance.com');
  assert.deepEqual(config.apiAllowedOrigins, [
    'https://api.tinlyt.tinlance.com',
    'https://api-staging.tinlyt.tinlance.com',
  ]);
  assert.equal(config.oauth.issuer, 'https://identity.tinlance.com/');
  assert.equal(config.oauth.authorizationEndpoint, 'https://identity.tinlance.com/authorize');
  assert.equal(config.oauth.tokenEndpoint, 'https://identity.tinlance.com/token');
  assert.equal(config.oauth.clientId, 'tinlyt-public-client');
  assert.equal(config.oauth.scope, 'twi:search twi:fetch twi:jobs:read');
  assert.equal(config.oauth.resource, 'tinlance-web-intelligence');
  assert.deepEqual(config.oauth.trustedIssuerOrigins, ['https://identity.tinlance.com']);
  assert.equal(JSON.stringify(config).includes('must-never-be-exposed'), false);
});

test('runtime config renderer binds redirect URI to the current deployment origin', () => {
  const source = renderRuntimeConfig({
    TINLYT_OAUTH_ISSUER: 'https://identity.tinlance.com/',
    TINLYT_OAUTH_AUTHORIZATION_ENDPOINT: 'https://identity.tinlance.com/authorize',
    TINLYT_OAUTH_TOKEN_ENDPOINT: 'https://identity.tinlance.com/token',
    TINLYT_OAUTH_CLIENT_ID: 'tinlyt-public-client',
    TINLYT_OAUTH_SCOPE: 'twi:search',
    TINLYT_OAUTH_RESOURCE: 'tinlance-web-intelligence',
    TINLYT_OAUTH_TRUSTED_ISSUER_ORIGINS: 'https://identity.tinlance.com',
  });
  assert.match(source, /window\.TINLYT_RUNTIME_CONFIG/);
  assert.match(source, /window\.location\.origin \+ "\/auth\/callback"/);
  assert.match(source, /tinlyt-public-client/);
  assert.doesNotMatch(source, /client_secret|must-never-be-exposed/i);
});

test('runtime config does not enable early access without a Turnstile site key', () => {
  const config = createRuntimeConfig({
    EARLY_ACCESS_ENABLED: 'true',
    EARLY_ACCESS_TURNSTILE_SITE_KEY: '',
  });
  assert.equal(config.earlyAccessEnabled, false);
});
