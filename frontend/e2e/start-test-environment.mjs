import { spawn, spawnSync } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../../", import.meta.url));
const backendRoot = path.join(projectRoot, "backend");

function getBookingDate() {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(new Date()).map(({ type, value }) => [type, value]),
  );
  const date = new Date(Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day) + 5));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

export default async function startTestEnvironment() {
  const testDate = process.env.PW_E2E_BOOKING_DATE || getBookingDate();
  process.env.PW_E2E_BOOKING_DATE = testDate;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(testDate)) {
    throw new Error("Playwright did not provide a valid isolated test booking date.");
  }

  const tempRoot = await mkdtemp(path.join(os.tmpdir(), "barbearia-e2e-"));
  const dbPath = path.join(tempRoot, "barbearia_e2e_test.db");
  const databaseUrl = `sqlite:///${dbPath.replaceAll("\\", "/")}`;
  const apiUrl = "http://127.0.0.1:4174";
  const frontendUrl = "http://127.0.0.1:4173";
  let apiProcess;
  let webServer;
  const backendEnv = {
    ...process.env,
    APP_ENV: "test",
    DATABASE_URL: databaseUrl,
    SECRET_KEY: "e2e-only-secret-key-for-isolated-test-runtime-2026",
    CORS_ALLOWED_ORIGINS: frontendUrl,
    SCHEDULING_TIMEZONE: "America/Sao_Paulo",
    PYTHON_DOTENV_DISABLED: "1",
    PYTHONPATH: backendRoot,
  };
  for (const name of ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM", "PASSWORD_RESET_URL"]) {
    delete backendEnv[name];
  }

  const venvPython = process.platform === "win32"
    ? path.join(backendRoot, ".venv", "Scripts", "python.exe")
    : path.join(backendRoot, ".venv", "bin", "python");
  const python = existsSync(venvPython) ? venvPython : (process.env.PYTHON || "python");
  const runPython = (args) => {
    const result = spawnSync(python, args, {
      cwd: backendRoot,
      env: { ...backendEnv, E2E_BOOKING_DATE: testDate },
      stdio: "inherit",
      windowsHide: true,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`Isolated E2E setup command failed (${args[0]}).`);
  };
  const listen = (server, port) => new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => {
      server.removeListener("error", reject);
      resolve();
    });
  });

  try {
    // Alembic, rather than create_all(), owns test database schema creation.
    runPython(["-m", "alembic", "upgrade", "head"]);
    runPython([path.join(projectRoot, "frontend", "e2e", "seed_database.py")]);

    apiProcess = spawn(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "4174", "--no-access-log"], {
      cwd: backendRoot,
      env: backendEnv,
      stdio: "inherit",
      windowsHide: true,
    });
    apiProcess.once("error", (error) => console.error("Could not start isolated E2E API:", error.message));
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (apiProcess.exitCode !== null) throw new Error("The isolated E2E API stopped during startup.");
      try {
        if ((await fetch(`${apiUrl}/ready`)).ok) {
          ready = true;
          break;
        }
      } catch {
        // The API process is still starting.
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    if (!ready) throw new Error("The isolated E2E API did not become ready in time.");

    const webRoot = path.join(projectRoot, "frontend");
    webServer = http.createServer(async (request, response) => {
      let requestedPath;
      try {
        requestedPath = decodeURIComponent(new URL(request.url, frontendUrl).pathname);
      } catch {
        response.writeHead(400).end();
        return;
      }
      const file = path.resolve(webRoot, `.${requestedPath}`);
      if (!file.startsWith(webRoot + path.sep)) {
        response.writeHead(403).end();
        return;
      }
      try {
        let contents = await readFile(file);
        if (file.endsWith(".html")) {
          const injection = `<script>window.BARBEARIA_API_URL=${JSON.stringify(apiUrl)};</script>`;
          contents = Buffer.from(contents.toString().replace("</head>", `${injection}</head>`));
        }
        const contentType = file.endsWith(".html") ? "text/html; charset=utf-8"
          : file.endsWith(".css") ? "text/css; charset=utf-8"
            : file.endsWith(".js") || file.endsWith(".mjs") ? "text/javascript; charset=utf-8"
              : "application/octet-stream";
        response.writeHead(200, { "Content-Type": contentType, "Cache-Control": "no-store" }).end(contents);
      } catch {
        response.writeHead(404).end("Not found");
      }
    });
    await listen(webServer, 4173);
    console.log("Playwright E2E services ready with a migrated temporary SQLite database.");

    return async function stopTestEnvironment() {
      webServer.closeAllConnections();
      await new Promise((resolve) => webServer.close(resolve));
      if (apiProcess.exitCode === null) {
        const stopped = new Promise((resolve) => apiProcess.once("exit", resolve));
        apiProcess.kill();
        await Promise.race([stopped, new Promise((resolve) => setTimeout(resolve, 5_000))]);
      }
      await rm(tempRoot, { recursive: true, force: true, maxRetries: 12, retryDelay: 250 });
    };
  } catch (error) {
    apiProcess?.kill();
    if (webServer?.listening) {
      webServer.closeAllConnections();
      await new Promise((resolve) => webServer.close(resolve));
    }
    await rm(tempRoot, { recursive: true, force: true, maxRetries: 12, retryDelay: 250 });
    throw error;
  }
}
