import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

export default defineConfig({
  testDir: ".",
  testMatch: "booking-smart.spec.mjs",
  workers: 1,
  retries: 0,
  use: { browserName: "chromium", viewport: { width: 1280, height: 800 }, timezoneId: "America/Sao_Paulo" },
  webServer: {
    command: `"${process.env.PYTHON || "python"}" frontend/e2e/booking-smart-server.py`,
    cwd: fileURLToPath(new URL("../../", import.meta.url)),
    url: "http://127.0.0.1:4186/ready",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
