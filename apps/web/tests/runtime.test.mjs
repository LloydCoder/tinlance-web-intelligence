import test from 'node:test';
import assert from 'node:assert/strict';
import { createRuntime } from '../.test-build/app/runtime.js';

const validConfig = {
  apiBaseUrl: '/api/twi',
  apiAllowedOrigins: [],
  oauth: {
    issuer: 'https://identity.example.com',
    authorizationEndpoint: 'https://identity.example.com/authorize',
    tokenEndpoint: 'https://identity.example.com/token',
    clientId: 'tinlyt-public-client',
    redirectUri: 'https://tinlyt.example.com/auth/callback',
    scope: 'twi:search twi:fetch',
    resource: 'https://twi.example.com',
    trustedIssuerOrigins: ['https://identity.example.com']
  }
};

test('runtime fails closed when deployment identity configuration is absent', () => {
  const runtime = createRuntime(null);
  assert.equal(runtime.state, 'not_configured');
  assert.match(runtime.message, /configuration is not available/);
});

test('runtime rejects an untrusted or insecure identity configuration', () => {
  const runtime = createRuntime({
    ...validConfig,
    oauth: { ...validConfig.oauth, tokenEndpoint: 'http://identity.example.com/token' }
  });
  assert.equal(runtime.state, 'invalid_configuration');
  assert.match(runtime.message, /configuration is invalid/);
});

test('runtime composes the API client and Platform token adapter only with explicit configuration', () => {
  const originalWindow = globalThis.window;
  const storage = new Map();
  globalThis.window = {
    location: { origin: 'https://tinlyt.example.com', assign() {} },
    history: { replaceState() {} },
    sessionStorage: {
      getItem(key) { return storage.get(key) ?? null; },
      setItem(key, value) { storage.set(key, value); },
      removeItem(key) { storage.delete(key); }
    }
  };
  try {
    const runtime = createRuntime(validConfig);
    assert.equal(runtime.state, 'ready');
    if (runtime.state !== 'ready') return;
    assert.equal(typeof runtime.apiClient.createJob, 'function');
    assert.equal(typeof runtime.tokenProvider.beginLogin, 'function');
    assert.equal(typeof runtime.beginLogin, 'function');
    assert.equal(typeof runtime.handleCallback, 'function');
  } finally {
    if (originalWindow === undefined) delete globalThis.window;
    else globalThis.window = originalWindow;
  }
});
