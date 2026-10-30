import test from "node:test";
import assert from "node:assert/strict";
import { expireSessionOnUnauthorized, shouldRefreshSession } from "../assets/js/session.mjs";

test("only authenticated non-session endpoints attempt silent refresh after 401", () => {
  assert.equal(shouldRefreshSession(401, true, "/appointments/"), true);
  assert.equal(shouldRefreshSession(401, true, "/auth/refresh"), false);
  assert.equal(shouldRefreshSession(401, true, "/auth/logout"), false);
  assert.equal(shouldRefreshSession(403, true, "/appointments/"), false);
  assert.equal(shouldRefreshSession(401, false, "/appointments/"), false);
});

function createSessionHarness(pathname = "/frontend/pages/client-date.html", search = "?service_id=7") {
  const values = new Map([
    ["token", "test-token"],
    ["user", JSON.stringify({ id: 1 })],
  ]);
  return {
    values,
    storage: { removeItem: (key) => values.delete(key) },
    location: { pathname, search, href: "" },
  };
}

test("authed 401 clears the cached session and returns to the current destination after login", () => {
  const harness = createSessionHarness();

  const handled = expireSessionOnUnauthorized(
    401,
    true,
    harness.storage,
    harness.location,
  );

  assert.equal(handled, true);
  assert.equal(harness.values.has("token"), false);
  assert.equal(harness.values.has("user"), false);
  assert.equal(
    harness.location.href,
    "login.html?redirect=client-date.html%3Fservice_id%3D7",
  );
});

test("403 keeps the authenticated session intact", () => {
  const harness = createSessionHarness();

  const handled = expireSessionOnUnauthorized(
    403,
    true,
    harness.storage,
    harness.location,
  );

  assert.equal(handled, false);
  assert.equal(harness.values.has("token"), true);
  assert.equal(harness.location.href, "");
});

test("blocked-account 403 clears the session while other 403 responses do not", () => {
  const blockedHarness = createSessionHarness();
  assert.equal(expireSessionOnUnauthorized(
    403, true, blockedHarness.storage, blockedHarness.location,
    JSON.stringify({ detail: "Conta bloqueada" }),
  ), true);
  assert.equal(blockedHarness.values.has("token"), false);
  assert.match(blockedHarness.location.href, /^login\.html\?redirect=/);

  const forbiddenHarness = createSessionHarness();
  assert.equal(expireSessionOnUnauthorized(
    403, true, forbiddenHarness.storage, forbiddenHarness.location,
    JSON.stringify({ detail: "Acesso negado" }),
  ), false);
  assert.equal(forbiddenHarness.values.has("token"), true);
});

test("public unauthenticated requests do not clear a stored session on 401", () => {
  const harness = createSessionHarness();

  const handled = expireSessionOnUnauthorized(
    401,
    false,
    harness.storage,
    harness.location,
  );

  assert.equal(handled, false);
  assert.equal(harness.values.has("token"), true);
  assert.equal(harness.location.href, "");
});
