import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const html = await readFile(path.join(root, 'index.html'), 'utf8');
const css = await readFile(path.join(root, 'styles.css'), 'utf8');
const investigationCss = await readFile(path.join(root, 'investigation.css'), 'utf8');
const js = await readFile(path.join(root, 'src/main.js'), 'utf8');
const runtimeConfig = await readFile(path.join(root, 'runtime-config.js'), 'utf8');

test('document declares language, viewport, title and skip navigation', () => {
  assert.match(html, /<html lang="en">/);
  assert.match(html, /name="viewport"/);
  assert.match(html, /<title>Tinlyt — Web Intelligence<\/title>/);
  assert.match(html, /class="skip-link" href="#main"/);
});

test('primary navigation and main landmark are labelled', () => {
  assert.match(html, /<aside class="sidebar" aria-label="Primary navigation">/);
  assert.match(html, /<main id="main" tabindex="-1">/);
  assert.match(html, /aria-current="page"/);
});

test('live investigation controls are disabled until authentication completes', () => {
  assert.match(html, /id="investigation-form"/);
  assert.match(html, /id="run-lookup-form"/);
  assert.match(html, /id="run-id"[^>]*disabled/);
  assert.match(html, /id="cancel-job"[^>]*hidden disabled/);
  assert.match(html, /id="submit-investigation"[^>]*disabled/);
  assert.match(html, /id="job-kind"[^>]*disabled/);
  assert.match(html, /id="sign-in"/);
  assert.match(js, /setLiveControlsEnabled\(true\)/);
  assert.match(js, /runtime\.apiClient\.createJob\(request\)/);
});

test('job response uses text rendering and announces status accessibly', () => {
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /id="job-result" class="result-content"/);
  assert.match(js, /safeWebUrl/);
  assert.match(js, /appendSourceLink/);
  assert.match(js, /link\.rel = 'noopener noreferrer'/);
  assert.match(js, /appendText\(resultContainer, 'pre', 'result-json'/);
  assert.doesNotMatch(js, /innerHTML\s*=\s*serialized/);
});

test('UI states retrieval is not a truth guarantee and does not show fixture metrics', () => {
  assert.match(html, /not an independent verdict about factual truth/);
  assert.match(html, /No fixture data is presented as live activity/);
  assert.match(js, /no completion outcome is assumed/);
  assert.match(js, /TWI reports that this job failed/);
  assert.match(js, /TWI reports that this job was cancelled/);
  assert.match(js, /activeJobId = null/);
  assert.match(js, /runtime\.apiClient\.getJob\(requestedId\)/);
  assert.match(js, /runtime\.apiClient\.cancelJob\(activeJobId\)/);
  assert.match(js, /window\.confirm/);
  assert.match(js, /job\.cancel_requested/);
});

test('styles retain visible focus, responsive behavior and reduced motion', () => {
  assert.match(css, /:focus-visible/);
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
  assert.match(investigationCss, /@media \(max-width: 600px\)/);
  assert.match(investigationCss, /:focus-visible/);
});

test('runtime configuration is loaded before application and contains no credentials', () => {
  assert.ok(html.indexOf('/runtime-config.js') < html.indexOf('/src/main.js'));
  assert.match(runtimeConfig, /authorizationEndpoint:\s*""/);
  assert.match(runtimeConfig, /tokenEndpoint:\s*""/);
  assert.doesNotMatch(runtimeConfig, /client_secret|access_token|refresh_token/i);
  assert.match(js, /getRuntime/);
});

test('API result is bounded before display and polling is bounded', () => {
  assert.match(js, /const limit = 20_000/);
  assert.match(js, /attempt < 20/);
  assert.match(js, /redirect|truth/i);
});


test('run inspection and cooperative cancellation remain tenant-scoped and explicit', () => {
  assert.match(html, /id="run-lookup-form"/);
  assert.match(html, /id="run-id"[^>]*disabled/);
  assert.match(html, /id="cancel-job"[^>]*hidden disabled/);
  assert.match(js, /runtime\.apiClient\.getJob\(requestedId\)/);
  assert.match(js, /runtime\.apiClient\.cancelJob\(activeJobId\)/);
  assert.match(js, /window\.confirm/);
  assert.match(js, /Cancellation is not complete until the service reports a terminal cancelled state/);
  assert.match(js, /if \(polling\) return/);
  assert.match(js, /job\.cancel_requested/);
  assert.match(html, /Tenant-scoped/);
});
