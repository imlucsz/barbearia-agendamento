import test from "node:test";
import assert from "node:assert/strict";
import { expireSessionOnUnauthorized } from "../assets/js/session.mjs";

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
