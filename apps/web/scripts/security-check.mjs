import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const files = [];
async function collect(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) await collect(full);
    else if (entry.isFile() && /\.(js|ts|css|html)$/.test(entry.name)) files.push(full);
  }
}
await collect(path.join(root, 'src'));
files.push(path.join(root, 'index.html'), path.join(root, 'styles.css'));

const checks = [
  ['dynamic code execution', /\beval\s*\(|\bnew\s+Function\s*\(/i],
  ['unsafe document writing', /document\.write\s*\(/i],
  ['inline event handler', /\son[a-z]+\s*=/i],
  ['javascript URL', /javascript\s*:/i],
  ['external resource load', /(?:<(?:script|link)\b[^>]+(?:src|href)\s*=\s*["']https?:\/\/|@import\s+url\(\s*["']?https?:\/\/)/i],
  ['private key material', /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/i],
  ['AWS access key pattern', /\bAKIA[0-9A-Z]{16}\b/],
  ['high-entropy-looking API secret', /\b(?:sk|rk|pk)_[A-Za-z0-9]{32,}\b/],
];
const failures = [];
for (const file of files) {
  const source = await readFile(file, 'utf8');
  for (const [label, pattern] of checks) {
    if (pattern.test(source)) failures.push(`${path.relative(root, file)}: ${label}`);
  }
}
if (failures.length) {
  process.stderr.write(failures.join('\n') + '\n');
  process.exit(1);
}
console.log(`Static security checks passed for ${files.length} frontend source files.`);
