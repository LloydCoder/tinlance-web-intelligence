import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const html = await readFile(path.join(root, 'app.html'), 'utf8');
const css = await readFile(path.join(root, 'styles.css'), 'utf8');
const investigationCss = await readFile(path.join(root, 'investigation.css'), 'utf8');
const main = await readFile(path.join(root, 'src/main.js'), 'utf8');
const oauth = await readFile(path.join(root, 'src/api/oauth-pkce.ts'), 'utf8');

async function sourceFiles(directory) {
  const result = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) result.push(...await sourceFiles(full));
    else if (entry.isFile() && /\.(?:js|ts)$/.test(entry.name)) result.push(full);
  }
  return result;
}

test('interactive controls retain visible focus and forced-colors support', () => {
  assert.match(css, /:focus-visible/);
  assert.match(css, /@media \(forced-colors: active\)/);
  assert.match(css, /outline: 2px solid Highlight/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(investigationCss, /input:focus-visible/);
});

test('document exposes language, skip link, landmarks, and labelled primary navigation', () => {
  assert.match(html, /<html lang="en">/);
  assert.match(html, /class="skip-link" href="#main"/);
  assert.match(html, /<aside id="workspace-sidebar" class="sidebar" aria-label="Primary navigation">);
  assert.match(html, /<main id="main" tabindex="-1">/);
  assert.match(html, /<nav class="primary-nav">/);
});

test('dynamic application source does not use raw HTML injection sinks', async () => {
  const files = await sourceFiles(path.join(root, 'src'));
  assert.ok(files.length > 0);
  for (const file of files) {
    const source = await readFile(file, 'utf8');
    assert.doesNotMatch(source, /(?:\.innerHTML\s*=|\.outerHTML\s*=|\.insertAdjacentHTML\s*\()/i, path.relative(root, file));
  }
  assert.match(main, /textContent =/);
  assert.match(main, /document.createElement/);
});

test('external links use safe navigation and suppress referrer leakage', () => {
  assert.match(main, /link\.rel = 'noopener noreferrer'/);
  assert.match(main, /link\.referrerPolicy = 'no-referrer'/);
  assert.match(main, /url\.username \|\| url\.password/);
  assert.match(html, /name="referrer" content="no-referrer"/);
});

test('OAuth access tokens remain in memory and are not written to browser storage', () => {
  assert.match(oauth, /Access token stays in memory only/);
  assert.match(oauth, /this\.accessToken = tokenResponse\.access_token/);
  assert.doesNotMatch(oauth, /(?:localStorage|sessionStorage)\.setItem\([^;]*(?:access_token|refresh_token|token)/i);
  assert.doesNotMatch(main, /localStorage/);
});

test('frontend has no inline event-handler attributes or untrusted external script imports', () => {
  assert.doesNotMatch(html, /\son[a-z]+\s*=/i);
  assert.doesNotMatch(html, /<(?:script|link)\b[^>]+(?:src|href)\s*=\s*["']https?:\/\//i);
});
