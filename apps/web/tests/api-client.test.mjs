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

test('requires an injected Platform token provider and restricts cross-origin API URLs', () => {
  assert.throws(() => new TwiApiClient({ baseUrl: '/api/twi' }), TwiApiError);
  assert.throws(() => new TwiApiClient({
    baseUrl: 'http://api.example.com',
    tokenProvider: { async getAccessToken() { return 'token'; } }
  }), TwiApiError);
  assert.throws(() => new TwiApiClient({
    baseUrl: 'https://api.example.com',
    tokenProvider: { async getAccessToken() { return 'token'; } }
  }), TwiApiError);
  assert.doesNotThrow(() => new TwiApiClient({
    baseUrl: 'https://api.example.com',
    allowedOrigins: ['https://api.example.com'],
    tokenProvider: { async getAccessToken() { return 'token'; } }
  }));
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


test('exports canonical evidence packages using the vendor JSON media type', async () => {
  const contentSha = '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824';
  const packageBody = {
    format: 'application/vnd.tinlance.twi-evidence+json',
    schema_version: '1.0.0',
    export_id: `sha256:${contentSha}`,
    artifact_id: `sha256:${contentSha}`,
    content_sha256: contentSha,
    content_type: 'text/html',
    byte_size: 5,
    source_revision: 'b'.repeat(40),
    provenance: {
      schema_version: '1.0.0',
      requested_url_sha256: 'e'.repeat(64),
      final_url_sha256: 'f'.repeat(64),
      status_code: 200,
      content_type: 'text/html',
      content_sha256: contentSha,
      byte_size: 5,
      retrieved_at: '2026-10-20T00:00:00Z',
      redirect_count: 0,
      extractor_version: 'extractor/1.0'
    },
    content_base64: 'aGVsbG8=',
    interpretation: {
      provenance_kind: 'acquisition_observation',
      truth_assessment: 'not_provided',
      source_authority_assessment: 'not_provided'
    }
  };
  let captured;
  const exactResponseBody = JSON.stringify(packageBody, null, 2) + '\n';
  const client = makeClient(async (url, init) => {
    captured = { url: String(url), init };
    return new Response(exactResponseBody, {
      status: 200,
      headers: { 'content-type': 'application/vnd.tinlance.twi-evidence+json; charset=utf-8' }
    });
  });
  const result = await client.exportEvidencePackage('job_01');
  assert.equal(result.evidence.schema_version, '1.0.0');
  assert.equal(result.evidence.interpretation.truth_assessment, 'not_provided');
  assert.equal(new TextDecoder().decode(result.bytes), exactResponseBody);
  assert.equal(captured.init.cache, 'no-store');
  assert.match(captured.url, /\/v1\/jobs\/job_01\/evidence$/);
  const legacyResult = await client.exportEvidence('job_01');
  assert.equal(legacyResult.content_sha256, contentSha);
  const wrongMediaTypeClient = makeClient(async () => new Response(JSON.stringify(packageBody), {
    status: 200,
    headers: { 'content-type': 'application/json' }
  }));
  await assert.rejects(
    wrongMediaTypeClient.exportEvidencePackage('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
  const deniedEvidenceClient = makeClient(async () => new Response(JSON.stringify({ detail: 'must not be surfaced' }), {
    status: 403,
    headers: { 'content-type': 'application/json' }
  }));
  await assert.rejects(
    deniedEvidenceClient.exportEvidencePackage('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'permission_denied' && !error.message.includes('must not be surfaced')
  );
  const malformedEvidenceClient = makeClient(async () => new Response('{broken', {
    status: 200,
    headers: { 'content-type': 'application/vnd.tinlance.twi-evidence+json' }
  }));
  await assert.rejects(
    malformedEvidenceClient.exportEvidencePackage('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
  const tamperedClient = makeClient(async () => new Response(JSON.stringify({
    ...packageBody,
    content_base64: 'd29ybGQ='
  }), {
    status: 200,
    headers: { 'content-type': 'application/vnd.tinlance.twi-evidence+json' }
  }));
  await assert.rejects(
    tamperedClient.exportEvidence('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
});

test('bounds raw evidence package bytes before JSON parsing', async () => {
  const client = makeClient(async () => new Response('oversized', {
    status: 200,
    headers: {
      'content-type': 'application/vnd.tinlance.twi-evidence+json',
      'content-length': '30000001'
    }
  }));
  await assert.rejects(
    client.exportEvidencePackage('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
});

test('validates verification responses without claiming factual truth', async () => {
  const verification = {
    verification_id: 'verify-01',
    verifier_version: 'twi-citation-verifier/1.0.0',
    verified_at: '2026-10-20T00:00:00Z',
    report_sha256: 'c'.repeat(64),
    status: 'citation_mismatch',
    factual_truth_assessed: false,
    source_count: 1,
    claim_count: 1,
    citation_count: 1,
    claims: [{
      claim_id: 'claim-1',
      statement: 'A claim to check',
      citation_status: 'citation_mismatch',
      citations: [{
        job_id: 'job_01',
        quote: 'quoted text longer than eight',
        quote_match: false,
        match_status: 'quote_not_found',
        source: {
          url: 'https://example.com/source',
          retrieved_at: '2026-10-20T00:00:00Z',
          media_type: 'text/html',
          content_sha256: 'd'.repeat(64)
        }
      }]
    }]
  };
  const client = makeClient(async () => new Response(JSON.stringify(verification), {
    status: 200,
    headers: { 'content-type': 'application/json' }
  }));
  const result = await client.verifyResearch({
    claims: [{ claim_id: 'claim-1', statement: 'A claim to check', citations: [{ job_id: 'job_01', quote: 'quoted text longer than eight' }] }]
  });
  assert.equal(result.factual_truth_assessed, false);
  assert.equal(result.status, 'citation_mismatch');
});

test('rejects verification output that overstates factual truth', async () => {
  const client = makeClient(async () => new Response(JSON.stringify({
    verification_id: 'verify-01',
    verifier_version: 'v1',
    verified_at: '2026-10-20T00:00:00Z',
    report_sha256: 'c'.repeat(64),
    status: 'all_citations_match_captured_text',
    factual_truth_assessed: true,
    claims: []
  }), { status: 200, headers: { 'content-type': 'application/json' } }));
  await assert.rejects(
    client.verifyResearch({
      claims: [{ claim_id: 'claim-1', statement: 'A claim to check', citations: [{ job_id: 'job_01', quote: 'quoted text longer than eight' }] }]
    }),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
});


test('rejects oversized API responses before parsing JSON', async () => {
  const client = makeClient(async () => new Response('{}', {
    status: 200,
    headers: {
      'content-type': 'application/json',
      'content-length': '30000001'
    }
  }));
  await assert.rejects(
    client.getJob('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'invalid_response'
  );
});


test('bounds Platform access-token provider latency', async () => {
  const client = new TwiApiClient({
    baseUrl: '/api/twi',
    tokenProvider: { getAccessToken: () => new Promise(() => {}) },
    timeoutMs: 1000,
    fetchImpl: async () => { throw new Error('fetch must not be called'); }
  });
  await assert.rejects(
    client.getJob('job_01'),
    (error) => error instanceof TwiApiError && error.code === 'request_timeout'
  );
});
