import { defineConfig } from '@playwright/test';

// Real page with fictitious intercepted API data; no backend or migrations.
export default defineConfig({
  testDir: '.',
  testMatch: 'agenda-navigation.spec.mjs',
  outputDir: '../../test-results/agenda-navigation',
  workers: 1,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:4186', timezoneId: 'America/Sao_Paulo', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  globalSetup: './home-experience-setup.mjs',
});
