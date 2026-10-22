import { cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
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
for (const file of ['index.html', 'app.html', 'brand.css', 'landing.css', 'site-nav.css', 'site-nav.js', 'favicon.svg', 'tinlyt-logo-dark-bg.svg', 'tinlyt-logo-light-bg.svg', 'runtime-config.js', 'early-access.js', 'styles.css', 'investigation.css', 'features.html', 'how-it-works.html', 'solutions/research.html', 'solutions/competitive-intelligence.html', 'solutions/due-diligence.html', 'solutions/investigations.html', 'book-demo.html', 'status.html', 'insights.html', 'manifest.webmanifest', 'use-cases.html', 'pricing.html', 'enterprise.html', 'developers.html', 'integrations.html', 'security.html', 'privacy.html', 'terms.html', 'contact.html', 'docs.html', 'faq.html', 'pages.css']) {
  const destination = path.join(out, file);
  await mkdir(path.dirname(destination), { recursive: true });
  const siteKey = process.env.EARLY_ACCESS_TURNSTILE_SITE_KEY || '';
  const enabled = process.env.EARLY_ACCESS_ENABLED === 'true' && siteKey.length > 0;
  if (file === 'runtime-config.js') {
    const source = await readFile(path.join(root, file), 'utf8');
    const configured = source
      .replace('earlyAccessEnabled: false', 'earlyAccessEnabled: ' + JSON.stringify(enabled))
      .replace(
        'earlyAccessTurnstileSiteKey: ""',
        'earlyAccessTurnstileSiteKey: ' + JSON.stringify(siteKey),
      );
    await writeFile(destination, configured, 'utf8');
  } else if (file.endsWith('.html')) {
    const source = await readFile(path.join(root, file), 'utf8');
    const configured = enabled ? source : source
      .replaceAll('<a class="nav-cta" href="/contact">Request early access</a>', '<a class="nav-cta" href="/features">Explore platform</a>')
      .replaceAll('<a class="button primary" href="/contact">Request early access</a>', '<a class="button primary" href="/features">Explore platform</a>');
    await writeFile(destination, configured, 'utf8');
  } else {
    await cp(path.join(root, file), destination);
  }
}
await cp(path.join(root, 'src/main.js'), path.join(out, 'src/main.js'));
console.log('Tinlyt frontend built at apps/web/dist');
