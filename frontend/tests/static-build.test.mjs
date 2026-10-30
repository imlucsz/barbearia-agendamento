import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile, mkdir } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { buildStaticSite, validatePublicApiUrl } from "../scripts/build-static.mjs";

test("API URL is a public HTTPS origin only", () => {
  assert.equal(validatePublicApiUrl("https://api.example.test/"), "https://api.example.test");
  for (const value of [undefined, "http://api.example.test", "https://user:pass@api.example.test", "https://api.example.test/v1", "https://api.example.test?key=secret"]) {
    assert.throws(() => validatePublicApiUrl(value), /PUBLIC_API_URL/);
  }
});

test("static build injects the public API URL before module scripts and excludes build tooling", async (t) => {
  const tempRoot = await mkdtemp(path.join(os.tmpdir(), "barbearia-static-build-"));
  t.after(() => rm(tempRoot, { recursive: true, force: true }));
  const source = path.join(tempRoot, "frontend");
  const output = path.join(source, "dist");
  await mkdir(path.join(source, "pages"), { recursive: true });
  await mkdir(path.join(source, "tests"), { recursive: true });
  await mkdir(path.join(source, "scripts"), { recursive: true });
  await writeFile(path.join(source, "pages", "index.html"), "<html><head></head><body><script type=\"module\"></script></body></html>");
  await writeFile(path.join(source, "tests", "not-published.txt"), "test");
  await writeFile(path.join(source, "scripts", "not-published.js"), "test");

  const result = await buildStaticSite({ sourceDir: source, outputDir: output, publicApiUrl: "https://api.example.test" });

  const html = await readFile(path.join(output, "pages", "index.html"), "utf8");
  const injectedAt = html.indexOf("render-api-config.js");
  assert.ok(injectedAt >= 0 && injectedAt < html.indexOf("type=\"module\""));
  assert.equal(await readFile(path.join(output, "assets", "js", "render-api-config.js"), "utf8"), 'window.BARBEARIA_API_URL = "https://api.example.test";\n');
  assert.equal(result.htmlFiles, 1);
  await assert.rejects(readFile(path.join(output, "tests", "not-published.txt")));
  await assert.rejects(readFile(path.join(output, "scripts", "not-published.js")));
});
