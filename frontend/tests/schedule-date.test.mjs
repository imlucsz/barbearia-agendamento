import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import { readFile } from "node:fs/promises";
import * as dates from "../assets/js/booking-date.mjs";

const source = (await readFile(new URL("../assets/js/schedule.js", import.meta.url), "utf8")).replace(/^import .*;\r?\n/gm, "");
const tick = () => new Promise(resolve => setImmediate(resolve));
function harness(search = "?service_id=1&barbeiro_id=2", get = async () => []) {
  const node = () => ({ children: [], listeners: {}, attributes: {}, value: "", disabled: false,
    addEventListener(name, fn) { this.listeners[name] = fn; },
    setAttribute(name, value) { this.attributes[name] = value; },
    append(...children) { this.children.push(...children); },
    prepend(child) { this.children.unshift(child); },
    replaceChildren() { this.children = []; },
  });
  const nodes = Object.fromEntries(["date-input", "slots-container", "confirmation-content", "confirm-btn"].map(id => [id, node()]));
  const calls = [];
  const location = { search, pathname: "/pages/client-date.html" };
  const context = vm.createContext({ ...dates, Intl, URLSearchParams, console, window: { location },
    getToken: () => "test-access", api: {
      get: async (path, options) => { calls.push({ path, options }); return get(path, options); },
      post: async (path, body) => { calls.push({ path, body }); },
    }, document: { addEventListener() {}, getElementById: id => nodes[id], createElement: node, createTextNode: text => text },
  });
  vm.runInContext(source, context);
  return { nodes, calls, context, location };
}

test("incomplete typing and invalid change never request HTTP or retain old slots", async () => {
  const h = harness();
  h.context.setupDatePicker();
  const input = h.nodes["date-input"];
  assert.equal(input.min, dates.bookingDateBounds().min);
  assert.equal(input.max, dates.bookingDateBounds().max);
  for (const value of ["", "2026-11-", "0002-11-11", "0202-11-11", "0020-11-11", "2026-02-30"]) {
    input.value = value;
    h.nodes["slots-container"].children = [{ textContent: "old slot" }];
    input.listeners.input();
    await input.listeners.change();
    assert.equal(input.attributes["aria-invalid"], "true");
    assert.equal(h.nodes["slots-container"].children.length, 1);
  }
  assert.equal(h.calls.length, 0);
});

test("valid date queries availability; stale response cannot restore invalid slots", async () => {
  let resolve;
  const h = harness(undefined, () => new Promise(done => { resolve = done; }));
  h.context.setupDatePicker();
  const input = h.nodes["date-input"];
  input.value = dates.bookingDateBounds().max;
  const pending = input.listeners.change();
  assert.equal(h.calls.length, 1);
  input.value = "0020-11-11";
  input.listeners.input();
  resolve([{ horario: "09:00", data_hora: `${dates.bookingDateBounds().max}T09:00:00` }]);
  await pending;
  assert.equal(h.nodes["slots-container"].children[0].attributes.role, "alert");
});

test("valid date and time submit booking; invalid confirmation makes no HTTP call", async () => {
  const tomorrow = new Date(Date.now() + 86400000);
  const value = `${dates.localDateInZone(tomorrow)}T12:00:00`;
  const h = harness(`?service_id=1&barbeiro_id=2&date_time=${value}`, async path => path.startsWith("/services/")
    ? { nome: "Corte", duracao_minutos: 30, preco: 40 } : [{ barbeiro_id: 2, barbeiro_nome: "Teste" }]);
  await h.context.loadConfirmation();
  await h.nodes["confirm-btn"].listeners.click();
  assert.equal(h.calls.at(-1).path, "/appointments/");
  assert.equal(h.calls.at(-1).body.data_hora, value);
  assert.equal(h.location.href, "client-appointments.html");
  const invalid = harness("?service_id=1&barbeiro_id=2&date_time=0002-11-11T12:00:00");
  await invalid.context.loadConfirmation();
  await tick();
  assert.equal(invalid.calls.length, 0);
  assert.equal(invalid.nodes["confirm-btn"].disabled, true);
});
