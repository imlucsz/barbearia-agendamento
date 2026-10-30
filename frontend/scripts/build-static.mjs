import { cp, mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export function validatePublicApiUrl(value) {
  if (!value) throw new Error("PUBLIC_API_URL is required to build the hosted frontend");
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error("PUBLIC_API_URL must be an absolute HTTPS API origin");
  }
  if (
    parsed.protocol !== "https:" || !parsed.hostname || parsed.username || parsed.password ||
    parsed.pathname !== "/" || parsed.search || parsed.hash
  ) {
    throw new Error("PUBLIC_API_URL must be an HTTPS origin without credentials, path, query, or fragment");
  }
  return parsed.origin;
}

export async function buildStaticSite({
  sourceDir = frontendRoot,
  outputDir = path.join(frontendRoot, "dist"),
  publicApiUrl = process.env.PUBLIC_API_URL,
} = {}) {
  const apiOrigin = validatePublicApiUrl(publicApiUrl);
  const source = path.resolve(sourceDir);
  const output = path.resolve(outputDir);
  if (source === output || output.startsWith(`${source}${path.sep}`) === false) {
    throw new Error("Static output directory must be a child of the frontend source directory");
  }

  await rm(output, { recursive: true, force: true });
  await mkdir(output, { recursive: true });
  const excluded = new Set([".node-version", "dist", "e2e", "node_modules", "scripts", "tests"]);
  for (const entry of await readdir(source, { withFileTypes: true })) {
    if (excluded.has(entry.name)) continue;
    await cp(path.join(source, entry.name), path.join(output, entry.name), { recursive: true });
  }

  const runtimeConfigPath = path.join(output, "assets", "js", "render-api-config.js");
  await mkdir(path.dirname(runtimeConfigPath), { recursive: true });
  await writeFile(
    runtimeConfigPath,
    `window.BARBEARIA_API_URL = ${JSON.stringify(apiOrigin)};\n`,
    "utf8",
  );

  const htmlPaths = [];
  async function collectHtml(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) await collectHtml(fullPath);
      else if (entry.isFile() && entry.name.endsWith(".html")) htmlPaths.push(fullPath);
    }
  }
  await collectHtml(output);
  const injection = '  <script src="/assets/js/render-api-config.js"></script>\n';
  for (const htmlPath of htmlPaths) {
    const html = await readFile(htmlPath, "utf8");
    if (!/<\/head\s*>/i.test(html)) {
      throw new Error(`Cannot inject API configuration because ${path.relative(output, htmlPath)} has no closing head tag`);
    }
    await writeFile(htmlPath, html.replace(/<\/head\s*>/i, `${injection}</head>`), "utf8");
  }
  return { htmlFiles: htmlPaths.length, apiOrigin };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = await buildStaticSite();
    console.log(`Static frontend prepared (${result.htmlFiles} HTML files).`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
