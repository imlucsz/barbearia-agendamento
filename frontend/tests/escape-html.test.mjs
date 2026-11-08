import test from "node:test";
import assert from "node:assert/strict";

import { escapeHtml } from "../assets/js/escape-html.mjs";

test("escapes markup, quotes and ampersands before rendering API values in HTML", () => {
  assert.equal(
    escapeHtml(`<img src=x onerror="alert('x')"> &`),
    "&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt; &amp;",
  );
});

test("converts nullish values to harmless empty text", () => {
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(undefined), "");
});
