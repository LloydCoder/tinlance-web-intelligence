import { rm } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';

const output = '.test-build';
await rm(output, { recursive: true, force: true });
const compile = spawnSync(process.execPath, [
  'node_modules/typescript/bin/tsc',
  '--noEmit',
  'false',
  '--outDir',
  output,
  '-p',
  'tsconfig.json',
], { stdio: 'inherit' });
if (compile.status !== 0) {
  await rm(output, { recursive: true, force: true });
  process.exit(compile.status ?? 1);
}
const tests = spawnSync(process.execPath, ['--test'], { stdio: 'inherit' });
await rm(output, { recursive: true, force: true });
process.exit(tests.status ?? 1);
