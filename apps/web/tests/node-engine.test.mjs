import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const manifestUrl = new URL('../package.json', import.meta.url);

test('frontend runtime is pinned to the Node 22 line used by CI', async () => {
  const manifest = JSON.parse(await readFile(manifestUrl, 'utf8'));
  assert.equal(manifest.engines?.node, '22.x');
});
