import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { formatDocumentDate, isValidCnpj, legalIdentificationLine, normalizeLegalConfiguration } from "../assets/js/legal.mjs";
import { CONSENT_MAX_AGE_DAYS, CONSENT_STORAGE_KEY, isThirdPartyContentEnabled, readConsent, saveConsent, setThirdPartyConsent } from "../assets/js/cookie-consent.mjs";
import { INSTALLATION_CONFIG } from "../assets/js/installation-config.mjs";

function memoryStorage() {
  const data = new Map();
  return { getItem: (key) => data.get(key) ?? null, setItem: (key, value) => data.set(key, String(value)) };
}

test("CNPJ validation uses check digits", () => {
  assert.equal(isValidCnpj("11.222.333/0001-81"), true);
  assert.equal(isValidCnpj("11222333000181"), true);
  assert.equal(isValidCnpj("11.222.333/0001-82"), false);
  assert.equal(isValidCnpj("00.000.000/0000-00"), false);
  assert.equal(isValidCnpj(""), false);
});

test("legal configuration never invents company data", () => {
  const empty = normalizeLegalConfiguration(INSTALLATION_CONFIG.legal);
  assert.equal(empty.razaoSocial, "");
  assert.equal(empty.cnpj, "");
  assert.deepEqual([...empty.missing], ["razaoSocial", "cnpj", "endereco", "email"]);
  assert.equal(legalIdentificationLine(empty), "");

  const filled = normalizeLegalConfiguration({ razaoSocial: " Barbearia Exemplo LTDA ", cnpj: "11222333000181", endereco: "Rua Exemplo, 10", email: "contato@example.com", encarregadoEmail: "invalido" });
  assert.equal(filled.cnpj, "11.222.333/0001-81");
  assert.equal(filled.encarregadoEmail, "");
  assert.deepEqual([...filled.missing], []);
  assert.equal(legalIdentificationLine(filled), "Barbearia Exemplo LTDA · CNPJ 11.222.333/0001-81 · Rua Exemplo, 10");
  assert.equal(normalizeLegalConfiguration({ cnpj: "11.222.333/0001-82" }).cnpj, "");
});

test("document dates are shown in Brazilian format", () => {
  assert.equal(formatDocumentDate("2026-11-18"), "18/11/2026");
  assert.equal(formatDocumentDate(""), "Não informado");
});

test("third-party consent is stored, validated and expires", () => {
  const storage = memoryStorage();
  const now = new Date("2026-11-18T12:00:00Z");
  assert.equal(readConsent(storage, now), null);
  saveConsent(storage, false, now);
  assert.equal(readConsent(storage, now).terceiros, false);
  saveConsent(storage, true, now);
  assert.equal(readConsent(storage, now).terceiros, true);
  const expired = new Date(now.getTime() + (CONSENT_MAX_AGE_DAYS + 1) * 86400000);
  assert.equal(readConsent(storage, expired), null);
  storage.setItem(CONSENT_STORAGE_KEY, "{not json");
  assert.equal(readConsent(storage, now), null);
  storage.setItem(CONSENT_STORAGE_KEY, JSON.stringify({ version: 1, terceiros: "yes", decididoEm: now.toISOString() }));
  assert.equal(readConsent(storage, now), null);
});

test("Google map is shown by default until the visitor disables it", () => {
  const stored = new Map();
  const storage = { getItem: (key) => stored.get(key) ?? null, setItem: (key, value) => stored.set(key, value), removeItem: (key) => stored.delete(key) };
  assert.equal(isThirdPartyContentEnabled({ localStorage: storage }), true);
  setThirdPartyConsent(false, { localStorage: storage });
  assert.equal(isThirdPartyContentEnabled({ localStorage: storage }), false);
});

test("revocation wins over a stored permission when storage cannot be written", () => {
  const stored = new Map([[CONSENT_STORAGE_KEY, JSON.stringify({ version: 1, terceiros: true, decididoEm: new Date().toISOString() })]]);
  const storage = {
    getItem: (key) => stored.get(key) ?? null,
    setItem: () => { throw new Error("QuotaExceededError"); },
    removeItem: (key) => stored.delete(key),
  };
  const windowRef = { localStorage: storage };
  assert.equal(isThirdPartyContentEnabled(windowRef), true);
  setThirdPartyConsent(false, windowRef);
  assert.equal(isThirdPartyContentEnabled(windowRef), false);
  assert.equal(readConsent(storage), null);
});

test("pages avoid third-party tracking and CDN scripts", async () => {
  const pages = ["index", "cadastro", "login", "privacidade", "termos", "cookies", "debug-estrelinha"];
  for (const page of pages) {
    const html = await readFile(new URL(`../pages/${page}.html`, import.meta.url), "utf8");
    assert.doesNotMatch(html, /googletagmanager|google-analytics|gtag\(|fbq\(|hotjar|clarity\.ms|cdn\.jsdelivr|unpkg\.com/i, page);
  }
});

test("legal pages are linked to configurable controller data", async () => {
  for (const page of ["privacidade", "termos"]) {
    const html = await readFile(new URL(`../pages/${page}.html`, import.meta.url), "utf8");
    for (const field of ["razaoSocial", "cnpj", "endereco", "email"]) assert.match(html, new RegExp(`data-legal="${field}"`), `${page}:${field}`);
  }
});
