import { defineConfig } from '@playwright/test';

// Start auth-session-server.py with a local certificate before running this suite.
export default defineConfig({
  testDir: '.', testMatch: 'auth-session.spec.mjs', workers: 1,
  timeout: 120000, outputDir: '../../test-results/auth-session', reporter: 'list',
  use: { browserName: 'chromium' },
});
