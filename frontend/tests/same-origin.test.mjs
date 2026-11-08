import test from "node:test";
import assert from "node:assert/strict";
import { readFile, mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import vm from "node:vm";
import { buildStaticSite } from "../scripts/build-static.mjs";

test("unified service configuration uses the actual page origin, overriding legacy API settings", async () => {
  const code = await readFile(new URL("../assets/js/same-origin-config.js", import.meta.url), "utf8");
  const window = { location: { origin: "https://barbearia.example" }, BARBEARIA_API_URL: "https://old-api.example" };
  vm.runInNewContext(code, { window });
  assert.equal(window.BARBEARIA_API_URL, "https://barbearia.example");
});

test("legacy static entry redirects paths, query and reset fragment without running the old app", async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), "barbearia-origin-"));
  t.after(async () => {
    assert.equal(path.dirname(root), path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('barbearia-origin-'));
    await rm(root, { recursive: true, force: true });
  });
  const source = path.join(root, "frontend");
  const output = path.join(source, "dist");
  await mkdir(path.join(source, "pages"), { recursive: true });
  await writeFile(path.join(source, "pages/reset.html"), '<html><head></head><body><script type="module" src="old.js"></script></body></html>');
  await buildStaticSite({ sourceDir: source, outputDir: output, publicApiUrl: "https://canonical.example", redirectToApiOrigin: true });
  const html = await readFile(path.join(output, "pages/reset.html"), "utf8");
  assert.ok(!html.includes("old.js"));
  assert.ok(html.includes('href="https://canonical.example/pages/reset.html"'));
  let redirected;
  vm.runInNewContext(await readFile(path.join(output, "assets/js/render-api-config.js"), "utf8"), {
    window: { location: { pathname: "/pages/reset.html", search: "?source=email", hash: "#token=fixture", replace: value => { redirected = value; } } },
  });
  assert.equal(redirected, "https://canonical.example/pages/reset.html?source=email#token=fixture");
});
