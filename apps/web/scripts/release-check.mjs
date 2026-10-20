import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const appRoot = fileURLToPath(new URL('../', import.meta.url));
const distRoot = path.join(appRoot, 'dist');
await stat(path.join(distRoot, 'index.html'));

const mime = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.svg', 'image/svg+xml'],
  ['.png', 'image/png'],
  ['.ico', 'image/x-icon'],
]);

function localAssetPaths(html) {
  const paths = new Set(['/']);
  for (const match of html.matchAll(/\b(?:src|href)\s*=\s*["']([^"'#]+)["']/gi)) {
    const value = match[1].trim();
    if (!value || value.startsWith('data:') || value.startsWith('mailto:') || /^[a-z][a-z0-9+.-]*:/i.test(value)) continue;
    if (value.startsWith('#')) continue;
    paths.add(value.startsWith('/') ? value : `/${value}`);
  }
  return [...paths];
}

async function collectJsFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await collectJsFiles(full));
    else if (entry.isFile() && entry.name.endsWith('.js')) files.push(full);
  }
  return files;
}

const html = await readFile(path.join(distRoot, 'index.html'), 'utf8');
assert.match(html, /<title>Tinlyt — Web Intelligence<\/title>/, 'built artifact must carry the Tinlyt product title');
assert.match(html, /\/runtime-config\.js/, 'runtime configuration must be loaded by the built page');
assert.match(html, /\/src\/main\.js/, 'application entry point must be loaded by the built page');

const jsFiles = await collectJsFiles(path.join(distRoot, 'src'));
for (const file of jsFiles) {
  const source = await readFile(file, 'utf8');
  for (const match of source.matchAll(/\b(?:import|export)\s+(?:[^'"]*?\s+from\s*)?["'](\.{1,2}\/[^"']+)["']/g)) {
    const dependency = path.resolve(path.dirname(file), match[1]);
    assert.ok(dependency.startsWith(path.resolve(distRoot) + path.sep), `module import escaped dist: ${path.relative(distRoot, file)}`);
    await stat(dependency);
  }
}

const runtimeConfig = await readFile(path.join(distRoot, 'runtime-config.js'), 'utf8');
assert.doesNotMatch(runtimeConfig, /client_secret|access_token|refresh_token|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i,
  'public runtime config must not contain privileged credentials');

const server = http.createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url ?? '/', 'http://127.0.0.1').pathname);
    const relative = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
    const target = path.resolve(distRoot, relative);
    assert.ok(target === distRoot || target.startsWith(path.resolve(distRoot) + path.sep), 'path traversal rejected');
    const body = await readFile(target);
    response.writeHead(200, {
      'content-type': mime.get(path.extname(target)) ?? 'application/octet-stream',
      'x-content-type-options': 'nosniff',
      'cache-control': path.extname(target) === '.html' ? 'no-store' : 'no-cache',
    });
    response.end(body);
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
  const base = `http://127.0.0.1:${address.port}`;
  const assets = localAssetPaths(html);
  for (const asset of assets) {
    const response = await fetch(new URL(asset, base));
    assert.equal(response.status, 200, `built asset failed HTTP smoke check: ${asset}`);
    assert.ok(response.headers.get('content-type'), `missing content type for ${asset}`);
    assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  }
  const missing = await fetch(new URL('/__tinlyt_release_smoke_missing__', base));
  assert.equal(missing.status, 404, 'missing assets must not be reported as successful');
  const traversal = await fetch(new URL('/%2e%2e%2fpackage.json', base));
  assert.equal(traversal.status, 404, 'encoded path traversal must not expose files outside the build output');
  console.log(`Production artifact smoke passed: ${assets.length} page assets served; ${jsFiles.length} JS modules checked; public runtime config contains no credential patterns.`);
} finally {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}
