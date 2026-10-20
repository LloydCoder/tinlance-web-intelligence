import test from 'node:test';
import assert from 'node:assert/strict';
import { TwiApiClient } from '../.test-build/api/client.js';
import { TwiApiError } from '../.test-build/api/errors.js';

const job = {
  job_id: 'job_01',
  tenant_id: 'tenant-private',
  subject_id: 'subject-private',
  idempotency_key: 'caller-key-is-not-returned-by-client',
  kind: 'search',
  payload: { query: 'primary source', limit: 5 },
  status: 'queued',
  created_at: '2026-10-20T00:00:00Z',
  updated_at: '2026-10-20T00:00:00Z',
  attempts: 0,
  max_attempts: 3,
  result: null,
  error_code: null,
  cancel_requested: false
};

function makeClient(fetchImpl, overrides = {}) {
  return new TwiApiClient({
    baseUrl: '/api/twi',
    tokenProvider: { async getAccessToken() { return 'ephemeral-test-token'; } },
    fetchImpl,
    idempotencyKeyFactory: () => 'test-idempotency-key-0001',
    ...overrides
  });
}

test('submits a strict job with bearer token, idempotency and safe fetch options', async () => {
  let captured;
  const client = makeClient(async (url, init) => {
    captured = { url: String(url), init };
    return new Response(JSON.stringify(job), { status: 202, headers: { 'content-type': 'application/json' } });
  });
  const result = await client.createJob({ kind: 'search', payload: { query: 'primary source', limit: 5 } });
  assert.equal(result.job_id, 'job_01');
  assert.equal(result.status, 'queued');
  assert.equal(captured.init.headers.Authorization, 'Bearer ephemeral-test-token');
  assert.equal(captured.init.headers['Idempotency-Key'], 'test-idempotency-key-0001');
  assert.equal(captured.init.redirect, 'error');
  assert.equal(captured.init.credentials, 'omit');
  assert.equal(captured.init.cache, 'no-store');
  assert.equal(JSON.parse(captured.init.body).kind, 'search');
  assert.match(captured.url, /\/api\/twi\/v1\/jobs$/);
  assert.equal('tenant_id' in result, false);
  assert.equal('subject_id' in result, false);
  assert.equal('idempotency_key' in result, false);
});

test('requires an injected Platform token provider and rejects invalid base URLs', () => {
  assert.throws(() => new TwiApiClient({ baseUrl: '/api/twi' }), TwiApiError);
  assert.throws(() => new TwiApiClient({
    baseUrl: 'http://api.example.com',
    tokenProvider: { async getAccessToken() { return 'token'; } }
  }), TwiApiError);
});

test('rejects malformed search payloads before network access', async () => {
  let called = false;
  const client = makeClient(async () => { called = true; return new Response('{}'); });
  await assert.rejects(
    client.createJob({ kind: 'search', payload: { query: 'x'.repeat(401) } }),
    (error) => error instanceof TwiApiError && error.code === 'validation_error'
  );
  assert.equal(called, false);
});

test('rejects non-HTTPS browser jobs before network access', async () => {
  let called = false;
  const client = makeClient(async () => { called = true; return new Response('{}'); });
  await assert.rejects(
    client.createJob({ kind: 'browser', payload: { url: 'http://example.com' } }),
    (error) => error instanceof TwiApiError && error.code === 'validation_error'
  );
  assert.equal(called, false);
});

test('maps authorization failures without exposing raw response content', async () => {
  const client = makeClient(async () => new Response('private server detail', {
    status: 403,
    headers: { 'content-type': 'text/plain', 'x-request-id': 'req-test-01' }
  }));
  await assert.rejects(
    client.getJob('job_01'),
    (error) => error instanceof TwiApiError
      && error.code === 'permission_denied'
      && error.requestId === 'req-test-01'
      && !error.message.includes('private server detail')
  );
});

test('rejects a malformed job response rather than trusting it', async () => {
  const client = makeClient(async () => new Response(JSON.stringify({ job_id: 'x', status: 'invented' }), {
    status: 200,
    headers: { 'content-type': 'application/json' }
  }));
  await assert.rejects(
    client.getJob('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
});

test('times out bounded requests and does not retry writes implicitly', async () => {
  let calls = 0;
  const client = makeClient((_url, init) => new Promise((_resolve, reject) => {
    calls += 1;
    init.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  }), { timeoutMs: 1000 });
  await assert.rejects(
    client.getJob('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'request_timeout'
  );
  assert.equal(calls, 1);
});
