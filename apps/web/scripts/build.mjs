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
for (const file of ['index.html', 'app.html', 'brand.css', 'landing.css', 'favicon.svg', 'tinlyt-logo-dark-bg.svg', 'runtime-config.js', 'styles.css', 'investigation.css']) {
  await cp(path.join(root, file), path.join(out, file));
}
await cp(path.join(root, 'src/main.js'), path.join(out, 'src/main.js'));
console.log('Tinlyt frontend built at apps/web/dist');
