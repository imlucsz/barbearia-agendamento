import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = (await readFile(new URL('../assets/js/agenda_admin.js', import.meta.url), 'utf8'))
  .replace(/^import .*;\r?\n/gm, '');
const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };

function harness(get, { put = async () => {}, statusButtons = [] } = {}) {
  let active;
  const node = () => {
    const classes = new Set();
    return {
      children: [], dataset: {}, attributes: {}, listeners: {}, disabled: false,
      classList: { add: value => classes.add(value), contains: value => classes.has(value) },
      set innerHTML(value) { this.html = value; this.children = []; },
      get innerHTML() { return this.html || ''; },
      setAttribute(key, value) { this.attributes[key] = value; },
      appendChild(child) { this.children.push(child); },
      addEventListener(name, fn) { this.listeners[name] = fn; },
      querySelectorAll() { return []; },
      focus() { active = this; },
    };
  };
  const nodes = Object.fromEntries(['dateRoll', 'prevDates', 'nextDates', 'agendaList', 'agendaDayLabel', 'userName'].map(id => [id, node()]));
  nodes.agendaList.querySelectorAll = () => statusButtons;
  const calls = [];
  const context = vm.createContext({
    api: { put, get(path, options) { calls.push({ path, date: options?.params?.data }); return Promise.resolve().then(() => get(path, options)); } },
    getCurrentUser: () => ({ role: 'admin', nome: 'Admin' }), getToken: () => 'test', logout() {},
    escapeHtml: value => String(value), console: { error() {} }, window: { location: {} },
    document: { getElementById: id => nodes[id], querySelector: () => null, createElement: node, addEventListener() {} },
  });
  vm.runInContext(source, context);
  context.init();
  return { nodes, calls, context, active: () => active };
}
const appointment = name => [{ id: 1, horario: '09:30', nome_cliente: name, servico_nome: 'Corte', profissional_nome: 'Barbeiro', status: 'confirmado' }];

test('agenda renders despite failed users and pending auxiliary requests', async () => {
  const pending = deferred();
  const h = harness(path => {
    if (path === '/users/') throw Object.assign(new Error('users failed'), { status: 500 });
    if (path === '/services/') return pending.promise;
    return path === '/admin/agenda' ? appointment('Cliente visível') : [];
  });
  await tick();
  assert.match(h.nodes.agendaList.innerHTML, /Cliente visível/);
  assert.match(h.nodes.agendaList.innerHTML, /09:30/);
  assert.match(h.nodes.agendaList.innerHTML, /Corte/);
  pending.resolve([]);
  await tick();
  assert.match(h.nodes.agendaList.innerHTML, /Cliente visível/);
});

test('real agenda error stays visible after auxiliary data completes', async () => {
  const h = harness(path => {
    if (path === '/admin/agenda') throw Object.assign(new Error('agenda failed'), { status: 500 });
    return [];
  });
  await tick();
  assert.match(h.nodes.agendaList.innerHTML, /Erro interno do servidor/);
});

test('late reference cannot redraw agenda after input interaction', async () => {
  const services = deferred();
  const h = harness(path => path === '/services/' ? services.promise
    : path === '/admin/agenda' ? [{ id: 1, user_id: 2, service_id: 3, barbeiro_id: 4, horario: '09:30', preco: 40 }] : []);
  await tick();
  // Observe render calls, since recreating the table destroys native input state.
  let redraws = 0;
  const node = h.nodes.agendaList;
  const html = node.innerHTML;
  Object.defineProperty(node, 'innerHTML', { get: () => html, set: () => { redraws++; } });
  node.listeners.focusin();
  node.listeners.input();
  services.resolve([{ id: 3, nome: 'Corte tardio' }]);
  await tick();
  assert.equal(redraws, 0);
});

test('late reference enriches the selected day without issuing another agenda request', async () => {
  const clients = deferred();
  const h = harness(path => path === '/users/' ? clients.promise
    : path === '/admin/agenda' ? [{ id: 1, user_id: 2, horario: '09:30' }] : []);
  await tick();
  h.nodes.dateRoll.children[2].listeners.click();
  await tick();
  const before = h.calls.filter(call => call.path === '/admin/agenda').length;
  clients.resolve([{ id: 2, nome: 'Cliente tardio' }]);
  await tick();
  assert.match(h.nodes.agendaList.innerHTML, /Cliente tardio/);
  assert.equal(h.calls.filter(call => call.path === '/admin/agenda').length, before);
});

for (const navigate of [false, true]) {
  test(`failed status update ${navigate ? 'from old day cannot overwrite selected day' : 'stays visible after late reference'}`, async () => {
    const services = deferred();
    const mutation = deferred();
    const button = { dataset: { appointmentStatus: 'falta', appointmentId: '1' }, addEventListener(_name, handler) { this.click = handler; } };
    const h = harness(path => path === '/services/' ? services.promise : path === '/admin/agenda' ? appointment('Dia selecionado') : [],
      { statusButtons: [button], put: () => mutation.promise });
    await tick();
    const update = button.click();
    if (navigate) {
      h.nodes.dateRoll.children[2].listeners.click();
      await tick();
    }
    mutation.reject(new Error('Falha de atualização'));
    await update;
    services.resolve([]);
    await tick();
    assert.match(h.nodes.agendaList.innerHTML, navigate ? /Dia selecionado/ : /Falha de atualização/);
    if (navigate) assert.doesNotMatch(h.nodes.agendaList.innerHTML, /Falha de atualização/);
  });
}

test('week navigation preserves weekday, selects dates and supports keyboard across year boundary', async () => {
  const h = harness(path => path === '/admin/agenda' ? appointment('Cliente') : []);
  await tick();
  vm.runInContext('selecionarDia(new Date(2026, 11, 30))', h.context);
  assert.equal(h.nodes.prevDates.disabled, false);
  assert.equal(h.nodes.nextDates.disabled, false);
  h.nodes.nextDates.listeners.click();
  await tick();
  let selected = h.nodes.dateRoll.children.find(item => item.attributes['aria-pressed'] === 'true');
  assert.equal(selected.dataset.date, '2027-01-06');
  h.nodes.prevDates.listeners.click();
  await tick();
  selected = h.nodes.dateRoll.children.find(item => item.attributes['aria-pressed'] === 'true');
  assert.equal(selected.dataset.date, '2026-12-30');
  const last = h.nodes.dateRoll.children[6];
  last.listeners.keydown({ key: 'ArrowRight', preventDefault() {} });
  await tick();
  assert.equal(h.active().dataset.date, '2027-01-03');
  assert.equal(h.active().attributes['aria-pressed'], 'true');
  h.nodes.dateRoll.children[2].listeners.click();
  await tick();
  assert.equal(h.calls.filter(call => call.path === '/admin/agenda').at(-1).date, '2027-01-05');
  assert.match(h.nodes.agendaList.innerHTML, /Cliente/);
});

for (const staleFailure of [false, true]) {
  test(`old agenda ${staleFailure ? 'error' : 'success'} cannot overwrite selected day`, async () => {
    const old = deferred();
    let count = 0;
    const h = harness(path => path === '/admin/agenda' ? (++count === 1 ? old.promise : appointment('Novo dia')) : []);
    await tick();
    h.nodes.dateRoll.children[1].listeners.click();
    await tick();
    assert.match(h.nodes.agendaList.innerHTML, /Novo dia/);
    if (staleFailure) old.reject(Object.assign(new Error('old'), { status: 500 }));
    else old.resolve(appointment('Dia antigo'));
    await tick();
    assert.match(h.nodes.agendaList.innerHTML, /Novo dia/);
    assert.doesNotMatch(h.nodes.agendaList.innerHTML, /Dia antigo|Erro interno/);
  });
}
