import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const html = await readFile(path.join(root, 'index.html'), 'utf8');
const css = await readFile(path.join(root, 'styles.css'), 'utf8');
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

test('unconnected actions remain disabled and visibly disclosed', () => {
  assert.match(html, /Live API integration is not configured/);
  assert.match(html, /<textarea[^>]* disabled/);
  assert.match(html, /<button class="button button-primary" type="button" disabled>/);
  assert.match(html, /No investigation has been submitted/);
});

test('product language does not claim retrieval proves truth', () => {
  assert.match(html, /retrieval is not proof of truth/);
  assert.match(html, /API integration pending/);
});

test('styles include responsive layout, visible focus and reduced motion', () => {
  assert.match(css, /:focus-visible/);
  assert.match(css, /@media \(max-width: 760px\)/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
});

test('navigation behavior changes only local presentation', () => {
  assert.match(js, /aria-current/);
  assert.doesNotMatch(js, /fetch\s*\(/);
});


test('runtime configuration is loaded before the application and contains no credentials', () => {
  assert.ok(html.indexOf('/runtime-config.js') < html.indexOf('/src/main.js'));
  assert.match(runtimeConfig, /authorizationEndpoint: ''/);
  assert.match(runtimeConfig, /tokenEndpoint: ''/);
  assert.doesNotMatch(runtimeConfig, /client_secret|access_token|refresh_token/i);
  assert.match(js, /getRuntime/);
  assert.match(html, /id="sign-in"/);
});
