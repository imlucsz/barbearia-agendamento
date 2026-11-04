import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('visibility module does not read/copy secrets or add network, logging or persistence', async () => {
  const source = await readFile(new URL('../assets/js/password-visibility.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /\.value\b|localStorage|sessionStorage|console\.|\bfetch\s*\(|sendBeacon|\.innerHTML\s*=/);
});

test('only existing password fields opt in; recovery remains email-only', async () => {
  for (const page of ['login', 'cadastro', 'reset', 'client-account']) {
    const html = await readFile(new URL(`../pages/${page}.html`, import.meta.url), 'utf8');
    assert.equal((html.match(/data-password-visibility/g) || []).length, 1);
    assert.equal((html.match(/src="\.\.\/assets\/js\/password-visibility\.mjs"/g) || []).length, 1);
  }
  const forgot = await readFile(new URL('../pages/forgot.html', import.meta.url), 'utf8');
  assert.doesNotMatch(forgot, /type="password"|password-visibility/);
});
