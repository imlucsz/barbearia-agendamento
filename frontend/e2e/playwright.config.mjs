import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const projectRoot = fileURLToPath(new URL("../../", import.meta.url));
const bookingDate = (() => {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Sao_Paulo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(new Date()).map(({ type, value }) => [type, value]),
  );
  const date = new Date(Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day) + 5));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
})();

process.env.PW_E2E_BOOKING_DATE = bookingDate;

export default defineConfig({
  testDir: projectRoot + "frontend/e2e",
  testMatch: "**/*.spec.mjs",
  outputDir: projectRoot + "test-results/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
    timezoneId: "America/Sao_Paulo",
    trace: "on",
    screenshot: "on",
    actionTimeout: 10_000,
  },
  projects: [
    {
      name: "desktop-1280x800",
      use: { viewport: { width: 1280, height: 800 } },
    },
    {
      name: "mobile-390x844",
      use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true },
    },
  ],
  globalSetup: projectRoot + "frontend/e2e/start-test-environment.mjs",
});
