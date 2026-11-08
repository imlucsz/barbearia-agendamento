import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const files = ['index.html', 'a-editorial.html', 'b-minimal.html', 'c-experimental.html', 'a-hybrid.html'];

for (const file of files) {
  test(`${file}: every local link and asset resolves inside the isolated prototype`, async () => {
    const html = await readFile(resolve(root, file), 'utf8');
    for (const [, target] of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
      if (target.startsWith('#')) {
        assert.ok(html.includes(`id="${target.slice(1)}"`), `missing anchor: ${target}`);
        continue;
      }
      if (target.startsWith('data:')) continue;
      if (file === 'a-hybrid.html' && target.startsWith('/shared/')) {
        assert.doesNotMatch(target, /\.\./);
        await access(resolve(root, '../../frontend/assets', target.slice('/shared/'.length)));
        continue;
      }
      assert.ok(!/^(?:[a-z]+:|\/\/)/i.test(target), `unexpected external request: ${target}`);
      const destination = resolve(root, target);
      assert.ok(destination.startsWith(root), 'links must stay in the prototype');
      await access(destination);
    }
  });
}

test('prototype interaction code does not introduce network, storage or HTML injection sinks', async () => {
  const source = await readFile(resolve(root, 'assets/prototype.js'), 'utf8');
  // Architecture guard only; browser tests exercise real DOM behavior separately.
  assert.doesNotMatch(source, /\b(?:fetch|XMLHttpRequest|WebSocket|localStorage|sessionStorage|innerHTML|insertAdjacentHTML)\b/);
  for (const file of files.slice(1)) {
    const html = await readFile(resolve(root, file), 'utf8');
    assert.ok(html.includes("connect-src 'none'"));
    assert.ok(html.includes("form-action 'none'"));
    assert.doesNotMatch(html, /\son[a-z]+\s*=/i);
  }
});
