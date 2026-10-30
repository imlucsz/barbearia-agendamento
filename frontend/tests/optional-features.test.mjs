import test from "node:test";
import assert from "node:assert/strict";
import { initializeOptionalFeatures, installationFeatureEnabled } from "../assets/js/optional-features.mjs";

function fakeDocument() {
  const appended = [];
  const mount = { removed: false, remove() { this.removed = true; } };
  return {
    appended,
    mount,
    head: { append: (node) => appended.push(node) },
    createElement: (tagName) => ({ tagName }),
    querySelector: () => mount,
  };
}

test("optional installation feature flags default on and can disable the mascot", () => {
  assert.equal(installationFeatureEnabled("estrelinhaWidget", {}), true);
  assert.equal(installationFeatureEnabled("estrelinhaWidget", { estrelinhaWidget: false }), false);
});

test("disabled mascot is removed without loading CSS or Three.js", async () => {
  const documentRef = fakeDocument();
  let loaded = false;
  const result = await initializeOptionalFeatures({
    documentRef,
    features: { estrelinhaWidget: false },
    loadWidget: async () => { loaded = true; },
  });

  assert.deepEqual(result, { widgetEnabled: false });
  assert.equal(documentRef.mount.removed, true);
  assert.equal(documentRef.appended.length, 0);
  assert.equal(loaded, false);
});

test("enabled mascot loads its stylesheet and widget", async () => {
  const documentRef = fakeDocument();
  let loaded = false;
  await initializeOptionalFeatures({
    documentRef,
    features: { estrelinhaWidget: true },
    loadWidget: async () => { loaded = true; },
  });

  assert.equal(documentRef.appended.length, 1);
  assert.equal(documentRef.appended[0].rel, "stylesheet");
  assert.match(documentRef.appended[0].href, /estrelinha\.css$/);
  assert.equal(loaded, true);
});
