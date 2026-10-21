import { cp, mkdir, rm } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const out = path.join(root, 'dist');
await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
const compile = spawnSync(process.execPath, [
  path.join(root, 'node_modules/typescript/bin/tsc'),
  '--noEmit',
  'false',
  '--outDir',
  path.join(out, 'src'),
  '-p',
  path.join(root, 'tsconfig.json'),
], { stdio: 'inherit' });
if (compile.status !== 0) process.exit(compile.status ?? 1);
for (const file of ['index.html', 'app.html', 'brand.css', 'landing.css', 'site-nav.css', 'site-nav.js', 'favicon.svg', 'tinlyt-logo-dark-bg.svg', 'tinlyt-logo-light-bg.svg', 'runtime-config.js', 'styles.css', 'investigation.css', 'features.html', 'how-it-works.html', 'solutions/research.html', 'solutions/competitive-intelligence.html', 'solutions/due-diligence.html', 'solutions/investigations.html', 'book-demo.html', 'status.html', 'insights.html', 'manifest.webmanifest', 'use-cases.html', 'pricing.html', 'enterprise.html', 'developers.html', 'integrations.html', 'security.html', 'privacy.html', 'terms.html', 'contact.html', 'docs.html', 'faq.html', 'pages.css']) {
  await cp(path.join(root, file), path.join(out, file));
}
await cp(path.join(root, 'src/main.js'), path.join(out, 'src/main.js'));
console.log('Tinlyt frontend built at apps/web/dist');
