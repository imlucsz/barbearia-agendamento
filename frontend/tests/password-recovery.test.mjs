import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = (await readFile(new URL('../assets/js/auth.js', import.meta.url), 'utf8'))
  .replace(/^import .*;\r?\n/gm, '');

function harness(post) {
  let now = 0;
  let tick;
  const button = { disabled: false, dataset: {}, textContent: 'Enviar instruções' };
  const message = { focus() {}, hidden: true };
  const attributes = new Map();
  const form = {
    elements: { email: { value: 'person@example.test' } },
    querySelector: () => button,
    setAttribute: (key, value) => attributes.set(key, value),
    removeAttribute: key => attributes.delete(key),
  };
  const context = vm.createContext({
    api: { post },
    document: { addEventListener() {}, getElementById: () => message },
    Date: class extends Date { static now() { return now; } },
    window: { setInterval(fn) { tick = fn; return 1; }, clearInterval() { tick = null; } },
  });
  vm.runInContext(source, context);
  const submit = () => context.forgotPassword({ preventDefault() {}, currentTarget: form });
  return { button, message, attributes, submit, advance(seconds) { now += seconds * 1000; tick?.(); } };
}

test('recovery ignores rapid submissions while request is pending and during cooldown', async () => {
  let finish;
  let calls = 0;
  const h = harness(() => { calls++; return new Promise(resolve => { finish = resolve; }); });
  const pending = h.submit();
  const duplicate = h.submit();
  assert.equal(h.button.disabled, true);
  assert.equal(calls, 1);
  finish({ mensagem: 'Se o e-mail existir, enviaremos instruções.' });
  await Promise.all([pending, duplicate]);
  await h.submit();
  assert.equal(calls, 1);
  assert.equal(h.button.disabled, true);
  h.advance(59);
  assert.equal(h.button.disabled, true);
  h.advance(1);
  assert.equal(h.button.disabled, false);
  assert.equal(h.button.textContent, 'Enviar instruções');
});

test('recovery exposes accessible busy state and never confirms account existence', async () => {
  let finish;
  const h = harness(() => new Promise(resolve => { finish = resolve; }));
  const pending = h.submit();
  assert.equal(h.attributes.get('aria-busy'), 'true');
  finish({ mensagem: 'Se o e-mail existir, enviaremos instruções.' });
  await pending;
  assert.notEqual(h.attributes.get('aria-busy'), 'true');
  assert.match(h.message.textContent, /Se o e-mail existir/);
});

test('delivery or network error permits a safe retry after visual cooldown', async () => {
  let calls = 0;
  const h = harness(async () => { calls++; throw new Error('Serviço indisponível.'); });
  await h.submit();
  await h.submit();
  assert.equal(calls, 1);
  assert.equal(h.button.disabled, true);
  assert.match(h.message.textContent, /indisponível/);
  h.advance(60);
  await h.submit();
  assert.equal(calls, 2);
});
