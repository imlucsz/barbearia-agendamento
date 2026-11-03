import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.', testMatch: 'estrelinha-cinematic.spec.mjs', workers: 1, reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:4186', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
  globalSetup: './home-experience-setup.mjs',
});
