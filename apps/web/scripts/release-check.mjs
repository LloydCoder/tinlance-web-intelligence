import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const appRoot = fileURLToPath(new URL('../', import.meta.url));
const distRoot = path.resolve(appRoot, 'dist');
const distPrefix = distRoot + path.sep;
const mimeTypes = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.svg', 'image/svg+xml'],
  ['.png', 'image/png'],
  ['.ico', 'image/x-icon'],
]);

async function collectFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await collectFiles(fullPath));
    else if (entry.isFile()) files.push(fullPath);
  }
  return files;
}
function localAssetPaths(html) {
  const assets = new Set(['/']);
  for (const match of html.matchAll(/\b(?:src|href)\s*=\s*["']([^"'#]+)["']/gi)) {
    const value = match[1].trim();
    if (!value || value.startsWith('#') || value.startsWith('data:') || value.startsWith('mailto:')) continue;
    if (/^[a-z][a-z0-9+.-]*:/i.test(value) || value.startsWith('//')) continue;
    assets.add(value.startsWith('/') ? value : '/' + value);
  }
  return [...assets];
}
function resolveLocalAsset(pathname) {
  const decoded = decodeURIComponent(pathname);
  const pageRoutes = new Set(['/features','/how-it-works','/use-cases','/pricing','/enterprise','/developers','/integrations','/security','/privacy','/terms','/contact']);
  const cleanPath = decoded.replace(/\\/$/, '');
  const relative = decoded === '/' ? 'index.html' : cleanPath === '/app' ? 'app.html' : pageRoutes.has(cleanPath) ? cleanPath.slice(1) + '.html' : decoded.replace(/^\\/+/, '');
  const resolved = path.resolve(distRoot, relative);
  assert.ok(resolved === distRoot || resolved.startsWith(distPrefix), 'asset path must remain inside build output');
  return resolved;
}

await stat(path.join(distRoot, 'index.html'));
const html = await readFile(path.join(distRoot, 'index.html'), 'utf8');
assert.match(html, /<title>Tinlyt — Web Intelligence<\/title>/, 'built page must identify Tinlyt');
assert.match(html, /name=["']robots["'] content=["']noindex, nofollow["']/, 'marketing page must remain noindex until launch approval');
assert.match(html, /property=["']og:title["']/, 'marketing page must include Open Graph title');
const appHtml = await readFile(path.join(distRoot, 'app.html'), 'utf8');
assert.match(html, /href=["']\/app["']/, 'landing page must link to workspace');
assert.match(appHtml, /(?:src|href)=["']\/runtime-config\.js["']/, 'workspace must load runtime configuration');
assert.match(appHtml, /(?:src|href)=["']\/src\/main\.js["']/, 'workspace must load app entry point');
assert.match(html, /href=["']\/app["']/, 'landing page must link to workspace');
const jsRoot = path.join(distRoot, 'src');
const jsFiles = (await collectFiles(jsRoot)).filter((file) => file.endsWith('.js'));
assert.ok(jsFiles.length > 0, 'build must emit JavaScript modules');
for (const file of jsFiles) {
  const source = await readFile(file, 'utf8');
  for (const match of source.matchAll(/\b(?:import|export)\s+(?:[^'"]*?\s+from\s*)?["'](\.{1,2}\/[^"']+)["']/g)) {
    const dependency = path.resolve(path.dirname(file), match[1]);
    assert.ok(dependency.startsWith(distPrefix), 'module import escaped dist: ' + path.relative(distRoot, file));
    await stat(dependency);
  }
}
const runtimeConfig = await readFile(path.join(distRoot, 'runtime-config.js'), 'utf8');
assert.doesNotMatch(runtimeConfig, /client_secret|access_token|refresh_token|api[_-]?key\s*[:=]|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i,
  'public runtime config must not contain common privileged credential patterns');

const server = http.createServer(async (request, response) => {
  try {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      response.writeHead(405, { allow: 'GET, HEAD', 'x-content-type-options': 'nosniff' });
      response.end(); return;
    }
    const target = resolveLocalAsset(new URL(request.url ?? '/', 'http://127.0.0.1').pathname);
    const body = await readFile(target);
    response.writeHead(200, {
      'content-type': mimeTypes.get(path.extname(target)) ?? 'application/octet-stream',
      'x-content-type-options': 'nosniff',
      'cache-control': path.extname(target) === '.html' ? 'no-store' : 'no-cache',
    });
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch {
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8', 'x-content-type-options': 'nosniff' });
    response.end('Not found');
  }
});
await new Promise((resolve, reject) => {
  server.once('error', reject);
  server.listen(0, '127.0.0.1', resolve);
});
try {
  const address = server.address();
  assert.ok(address && typeof address === 'object');
  const base = 'http://127.0.0.1:' + address.port;
  const assets = [...new Set([...localAssetPaths(html), ...localAssetPaths(appHtml).filter((asset) => asset !== '/')])];
  const publicRoutes = ['/features','/how-it-works','/use-cases','/pricing','/enterprise','/developers','/integrations','/security','/privacy','/terms','/contact'];
  for (const route of publicRoutes) {
    const response = await fetch(new URL(route, base));
    assert.equal(response.status, 200, 'public route must resolve: ' + route);
    const page = await response.text();
    assert.match(page, /<!doctype html>/i, 'public route must serve an HTML document: ' + route);
    assert.match(page, /name="robots" content="noindex, nofollow"/, 'public page must remain noindex pending launch approval: ' + route);
    assert.match(page, /href="\\/pages.css"/, 'public page must load shared page styles: ' + route);
  }
  const appResponse = await fetch(new URL('/app', base));
  assert.equal(appResponse.status, 200, 'workspace route must resolve');
  assert.match(await appResponse.text(), /runtime-config\.js/, 'workspace route must serve the application document');
  for (const asset of assets) {
    const assetPath = new URL(asset, base).pathname;
    // The root URL is served from index.html, so its expected MIME type is HTML.
    const expectedType = ['/', '/app', '/app/'].includes(asset) ? mimeTypes.get('.html') : (mimeTypes.get(path.extname(assetPath)) ?? 'application/octet-stream');
    const response = await fetch(new URL(asset, base));
    assert.equal(response.status, 200, 'asset failed HTTP smoke check: ' + asset);
    assert.equal(response.headers.get('content-type'), expectedType, 'wrong content type: ' + asset);
    assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
    if (asset === '/') assert.equal(response.headers.get('cache-control'), 'no-store');
  }
  assert.equal((await fetch(new URL('/__tinlyt_release_smoke_missing__', base))).status, 404);
  assert.equal((await fetch(new URL('/%2e%2e%2fpackage.json', base))).status, 404, 'encoded traversal must not expose files outside dist');
  assert.equal((await fetch(new URL('/', base), { method: 'POST' })).status, 405, 'unsupported methods must be rejected');
  console.log('Production artifact smoke passed: ' + assets.length + ' local assets; ' + jsFiles.length + ' JS modules; no common privileged credential patterns.');
} finally {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}
