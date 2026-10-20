import test from 'node:test';
import assert from 'node:assert/strict';
import { OAuthPkceTokenProvider } from '../.test-build/api/oauth-pkce.js';
import { TwiApiError } from '../.test-build/api/errors.js';

function storageMock() {
  const values = new Map();
  return {
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, value); },
    removeItem(key) { values.delete(key); },
    values
  };
}

function makeProvider(overrides = {}) {
  const storage = storageMock();
  const navigations = [];
  const replaced = [];
  const config = {
    issuer: 'https://identity.example.com',
    issuer: 'https://identity.example.com',
    authorizationEndpoint: 'https://identity.example.com/authorize',
    tokenEndpoint: 'https://identity.example.com/token',
    clientId: 'tinlyt-public-client',
    redirectUri: 'https://tinlyt.example.com/auth/callback',
    scope: 'twi:search twi:fetch twi:jobs:read',
    resource: 'https://twi.example.com',
    trustedIssuerOrigins: ['https://identity.example.com'],
    storage,
    navigate: (url) => navigations.push(url),
    replaceUrl: (url) => replaced.push(url),
    now: () => 1_800_000_000_000,
    ...overrides
  };
  return { provider: new OAuthPkceTokenProvider(config), storage, navigations, replaced, config };
}

test('requires explicit trusted HTTPS issuer origins', () => {
  assert.throws(() => new OAuthPkceTokenProvider({
    authorizationEndpoint: 'https://identity.example.com/authorize',
    tokenEndpoint: 'https://identity.example.com/token',
    clientId: 'tinlyt-public-client',
    redirectUri: 'https://tinlyt.example.com/auth/callback',
    scope: 'twi:search',
    resource: 'https://twi.example.com',
    trustedIssuerOrigins: []
  }), (error) => error instanceof TwiApiError && error.code === 'configuration_error');
});

test('starts Authorization Code + PKCE with S256 and no client secret', async () => {
  const { provider, storage, navigations } = makeProvider();
  await provider.beginLogin();
  assert.equal(navigations.length, 1);
  const authorization = new URL(navigations[0]);
  assert.equal(authorization.searchParams.get('response_type'), 'code');
  assert.equal(authorization.searchParams.get('client_id'), 'tinlyt-public-client');
  assert.equal(authorization.searchParams.get('code_challenge_method'), 'S256');
  assert.ok(authorization.searchParams.get('code_challenge'));
  assert.ok(authorization.searchParams.get('state'));
  assert.equal(authorization.searchParams.get('resource'), 'https://twi.example.com');
  assert.equal(authorization.searchParams.has('client_secret'), false);
  const transaction = JSON.parse(storage.getItem('tinlyt.oauth.pkce.transaction.v1'));
  assert.equal(transaction.state, authorization.searchParams.get('state'));
  assert.ok(transaction.verifier);
  assert.equal(JSON.stringify([...storage.values.values()]).includes('access_token'), false);
});

test('rejects callback state mismatch before token endpoint network access', async () => {
  let called = false;
  const { provider } = makeProvider({ fetchImpl: async () => { called = true; return new Response('{}'); } });
  await provider.beginLogin();
  await assert.rejects(
    provider.handleCallback('https://tinlyt.example.com/auth/callback?code=auth-code&state=wrong'),
    (error) => error instanceof TwiApiError && error.code === 'authentication_required'
  );
  assert.equal(called, false);
});

test('exchanges a one-time code using the stored verifier and keeps access token in memory', async () => {
  let captured;
  const { provider, storage, replaced, config } = makeProvider({
    fetchImpl: async (url, init) => {
      captured = { url: String(url), init };
      return new Response(JSON.stringify({
        access_token: 'short-lived-twi-token',
        token_type: 'Bearer',
        expires_in: 3600,
        refresh_token: 'must-not-be-persisted'
      }), { status: 200, headers: { 'content-type': 'application/json' } });
    }
  });
  await provider.beginLogin();
  const transaction = JSON.parse(storage.getItem('tinlyt.oauth.pkce.transaction.v1'));
  await provider.handleCallback(`https://tinlyt.example.com/auth/callback?code=one-time-code&state=${transaction.state}&keep=1`);
  assert.equal(await provider.getAccessToken(), 'short-lived-twi-token');
  assert.equal(captured.url, config.tokenEndpoint);
  assert.equal(captured.init.method, 'POST');
  assert.equal(captured.init.redirect, 'error');
  assert.equal(captured.init.credentials, 'omit');
  const body = new URLSearchParams(captured.init.body);
  assert.equal(body.get('grant_type'), 'authorization_code');
  assert.equal(body.get('code'), 'one-time-code');
  assert.equal(body.get('code_verifier'), transaction.verifier);
  assert.equal(body.get('resource'), 'https://twi.example.com');
  assert.equal(body.has('client_secret'), false);
  assert.equal(storage.getItem('tinlyt.oauth.pkce.transaction.v1'), null);
  assert.equal(replaced.length, 1);
  assert.equal(new URL(replaced[0]).searchParams.has('code'), false);
  assert.equal(new URL(replaced[0]).searchParams.has('state'), false);
  provider.clear();
  await assert.rejects(provider.getAccessToken(), (error) => error.code === 'authentication_required');
});

test('rejects unsupported token response and never retains it', async () => {
  const { provider, storage } = makeProvider({
    fetchImpl: async () => new Response(JSON.stringify({ access_token: 'token', token_type: 'Basic', expires_in: 3600 }), {
      status: 200, headers: { 'content-type': 'application/json' }
    })
  });
  await provider.beginLogin();
  const transaction = JSON.parse(storage.getItem('tinlyt.oauth.pkce.transaction.v1'));
  await assert.rejects(
    provider.handleCallback(`https://tinlyt.example.com/auth/callback?code=one-time-code&state=${transaction.state}`),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
  await assert.rejects(provider.getAccessToken(), (error) => error.code === 'authentication_required');
});


test('rejects callback URLs outside the configured redirect origin and path', async () => {
  let called = false;
  const { provider } = makeProvider({ fetchImpl: async () => { called = true; return new Response('{}'); } });
  await provider.beginLogin();
  await assert.rejects(
    provider.handleCallback('https://attacker.example/callback?code=stolen&state=wrong'),
    (error) => error instanceof TwiApiError && error.code === 'authentication_required'
  );
  assert.equal(called, false);
});
