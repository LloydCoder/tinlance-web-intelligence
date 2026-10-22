import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const sourceRoot = path.join(root, 'src');
const files = [];
async function collect(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) await collect(full);
    else if (entry.isFile() && /\.(js|ts|css|html)$/.test(entry.name)) files.push(full);
  }
}
await collect(sourceRoot);
files.push(path.join(root, 'index.html'), path.join(root, 'app.html'), path.join(root, 'landing.css'), path.join(root, 'site-nav.css'), path.join(root, 'site-nav.js'), path.join(root, 'styles.css'), path.join(root, 'investigation.css'), path.join(root, 'runtime-config.js'), path.join(root, 'early-access.js'), path.join(root, 'solutions/research.html'), path.join(root, 'solutions/competitive-intelligence.html'), path.join(root, 'solutions/due-diligence.html'), path.join(root, 'solutions/investigations.html'), path.join(root, 'book-demo.html'), path.join(root, 'status.html'), path.join(root, 'insights.html'), path.join(root, 'manifest.webmanifest'), path.join(root, 'features.html'), path.join(root, 'how-it-works.html'), path.join(root, 'use-cases.html'), path.join(root, 'pricing.html'), path.join(root, 'enterprise.html'), path.join(root, 'developers.html'), path.join(root, 'integrations.html'), path.join(root, 'security.html'), path.join(root, 'privacy.html'), path.join(root, 'terms.html'), path.join(root, 'contact.html'), path.join(root, 'docs.html'), path.join(root, 'faq.html'), path.join(root, 'pages.css'));
const failures = [];
for (const file of files) {
  const text = await readFile(file, 'utf8');
  if (text.includes('\u0000')) failures.push(`${path.relative(root, file)} contains a NUL byte`);
  if (file.endsWith('.html') && !/<!doctype html>/i.test(text)) failures.push('index.html must declare HTML5 doctype');
}
if (failures.length) {
  process.stderr.write(failures.join('\n') + '\n');
  process.exit(1);
}
console.log(`Source hygiene checks passed for ${files.length} file(s).`);
