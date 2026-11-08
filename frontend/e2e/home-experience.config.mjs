import { defineConfig } from '@playwright/test';

// Presentation-only checks: static frontend and intercepted, fictitious API data.
export default defineConfig({
  testDir: '.',
  testMatch: 'home-experience.spec.mjs',
  outputDir: '../../test-results/home-experience',
  workers: 1,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:4186', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } } },
    { name: 'tablet', use: { viewport: { width: 820, height: 1180 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    { name: 'small', use: { viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true } },
  ],
  globalSetup: './home-experience-setup.mjs',
});
