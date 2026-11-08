import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'password-visibility.spec.mjs',
  outputDir: '../../test-results/password-visibility',
  workers: 1,
  reporter: 'list',
  // Secrets are synthetic, but do not record field values in traces/screenshots.
  use: { baseURL: 'http://127.0.0.1:4186', trace: 'off', screenshot: 'off', video: 'off' },
  projects: [
    { name: 'chromium-desktop', use: { browserName: 'chromium', viewport: { width: 1280, height: 800 } } },
    { name: 'chromium-small', use: { browserName: 'chromium', viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true } },
    { name: 'firefox-desktop', use: { browserName: 'firefox', viewport: { width: 1280, height: 800 } } },
    { name: 'webkit-desktop', use: { browserName: 'webkit', viewport: { width: 1280, height: 800 } } },
  ],
  globalSetup: './home-experience-setup.mjs',
});
