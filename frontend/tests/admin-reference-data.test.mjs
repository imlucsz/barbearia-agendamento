import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = (await readFile(new URL('../assets/js/admin_management.js', import.meta.url), 'utf8'))
  .replace(/^import .*;\r?\n/gm, '');

function harness(failingPath, status = 500) {
  const nodes = new Map();
  const node = () => ({
    children: [], disabled: false, value: '', attributes: {},
    replaceChildren(...children) { this.children = children; },
    append(child) { this.children.push(child); },
    prepend(child) { this.children.unshift(child); },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    insertAdjacentElement(_where, child) { this.message = child; },
  });
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, node());
    return nodes.get(id);
  };
  const data = {
    '/services/': [{ id: 1, nome: 'Corte' }],
    '/users/barbeiros': [{ id: 11, nome: 'Barbeiro sem associação' }],
    '/users/': [{ id: 2, nome: 'Cliente', email: 'client@example.test' }],
  };
  const context = vm.createContext({
    api: { async get(path) {
      if (path === failingPath) throw Object.assign(new Error('Falha simulada'), { status });
      return data[path];
    } },
    document: { addEventListener() {}, getElementById: get, createElement: node },
    console: { error() {} },
  });
  vm.runInContext(source, context);
  return { get, load: () => context.loadReferenceData() };
}

test('client API failure does not erase barber and service selects', async () => {
  const h = harness('/users/');
  await h.load();
  for (const id of ['manual-barber', 'barber-service-barber', 'schedule-barber', 'block-barber']) {
    assert.equal(h.get(id).children[0].value, 11);
    assert.equal(h.get(id).disabled, false);
  }
  assert.equal(h.get('barber-service-service').children[0].textContent, 'Corte');
  assert.equal(h.get('manual-client').disabled, true);
  assert.match(h.get('manual-client').children[0].textContent, /[Ff]alha|[Ee]rro/);
});

test('barber API failure is visible at affected fields and preserves services', async () => {
  const h = harness('/users/barbeiros', 403);
  await h.load();
  assert.equal(h.get('manual-service').children[0].textContent, 'Corte');
  for (const id of ['manual-barber', 'barber-service-barber', 'schedule-barber', 'block-barber']) {
    assert.equal(h.get(id).disabled, true);
    assert.match(h.get(id).children[0].textContent, /[Ff]alha|[Ee]rro/);
  }
});

test('service API failure preserves barber catalog for scheduling and blocks', async () => {
  const h = harness('/services/');
  await h.load();
  assert.equal(h.get('block-barber').children[0].value, 11);
  assert.equal(h.get('manual-service').disabled, true);
});

test('unauthorized reference response remains an authentication error', async () => {
  const h = harness('/users/barbeiros', 401);
  await assert.rejects(h.load(), error => error.status === 401);
});

test('successful barber reference does not require an existing service association', async () => {
  const h = harness();
  await h.load();
  assert.equal(h.get('barber-service-barber').children[0].value, 11);
});
