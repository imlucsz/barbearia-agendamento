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
    getToken: () => "test-access", mountBookingCalendar: (api, params) => calls.push({ calendar: true, params: params.toString() }), api: {
      get: async (path, options) => { calls.push({ path, options }); return get(path, options); },
      post: async (path, body) => { calls.push({ path, body }); },
    }, document: { addEventListener() {}, getElementById: id => nodes[id], createElement: node, createTextNode: text => text },
  });
  vm.runInContext(source, context);
  return { nodes, calls, context, location };
}

test("date page delegates to accessible calendar and preserves rescheduling context", () => {
  const h = harness("?service_id=1&barbeiro_id=2&appointment_id=7");
  h.context.setupDatePicker();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].calendar, true);
  assert.equal(h.calls[0].params, "service_id=1&barbeiro_id=2&appointment_id=7");
});

test("date page without required context makes no availability request", () => {
  const h = harness("?service_id=1");
  h.context.setupDatePicker();
  assert.equal(h.calls.length, 0);
  assert.equal(h.location.href, "client-services.html");
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
