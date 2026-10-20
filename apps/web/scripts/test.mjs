import { readdir, rm } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const output = path.join(root, '.test-build');
await rm(output, { recursive: true, force: true });
const compile = spawnSync(process.execPath, [
  path.join(root, 'node_modules/typescript/bin/tsc'),
  '--noEmit',
  'false',
  '--outDir',
  output,
  '-p',
  path.join(root, 'tsconfig.json'),
], { stdio: 'inherit' });
if (compile.status !== 0) {
  await rm(output, { recursive: true, force: true });
  process.exit(compile.status ?? 1);
}
const entries = await readdir(path.join(root, 'tests'));
const tests = entries
  .filter((entry) => entry.endsWith('.test.mjs'))
  .map((entry) => path.join(root, 'tests', entry));
const result = spawnSync(process.execPath, ['--test', ...tests], { stdio: 'inherit', cwd: root });
await rm(output, { recursive: true, force: true });
process.exit(result.status ?? 1);
