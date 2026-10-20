import { cp, mkdir, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const out = path.join(root, 'dist');
await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
await cp(path.join(root, 'index.html'), path.join(out, 'index.html'));
await cp(path.join(root, 'styles.css'), path.join(out, 'styles.css'));
await cp(path.join(root, 'src'), path.join(out, 'src'), { recursive: true });
console.log('Tinlyt static frontend built at apps/web/dist');
