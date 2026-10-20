import test from 'node:test';
import assert from 'node:assert/strict';
import { buildJobRequest, isTerminalJobStatus } from '../.test-build/app/investigation.js';

test('builds normalized search requests with supported limits', () => {
  assert.deepEqual(buildJobRequest('search', '  source evidence  ', '', '10'), {
    kind: 'search', payload: { query: 'source evidence', limit: 10 }
  });
});

test('rejects empty and oversized search requests', () => {
  assert.throws(() => buildJobRequest('search', '   ', '', '10'), /1–400/);
  assert.throws(() => buildJobRequest('search', 'x'.repeat(401), '', '10'), /1–400/);
  assert.throws(() => buildJobRequest('search', 'query', '', '7'), /result limit/);
});

test('builds fetch requests only for absolute HTTP(S) URLs without credentials', () => {
  assert.deepEqual(buildJobRequest('fetch', '', 'https://example.com/page', '10'), {
    kind: 'fetch', payload: { url: 'https://example.com/page' }
  });
  assert.throws(() => buildJobRequest('fetch', '', '/relative', '10'), /absolute URL/);
  assert.throws(() => buildJobRequest('fetch', '', 'https://user:pass@example.com', '10'), /embedded credentials/);
});

test('browser jobs require HTTPS and reject nonstandard ports', () => {
  assert.deepEqual(buildJobRequest('browser', '', 'https://example.com', '10'), {
    kind: 'browser', payload: { url: 'https://example.com/' }
  });
  assert.throws(() => buildJobRequest('browser', '', 'http://example.com', '10'), /HTTPS URL/);
  assert.throws(() => buildJobRequest('browser', '', 'https://example.com:8443', '10'), /HTTPS URL/);
});

test('terminal state detection is exhaustive for known job states', () => {
  assert.equal(isTerminalJobStatus('succeeded'), true);
  assert.equal(isTerminalJobStatus('failed'), true);
  assert.equal(isTerminalJobStatus('cancelled'), true);
  assert.equal(isTerminalJobStatus('queued'), false);
  assert.equal(isTerminalJobStatus('running'), false);
});
