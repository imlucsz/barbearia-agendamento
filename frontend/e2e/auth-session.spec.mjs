import { test, expect } from '@playwright/test';
import { runAuthSessionChecks } from './auth-session-browser.mjs';

test('HTTPS same-origin session with third-party cookies restricted', async ({ browser }) => {
  const result = await runAuthSessionChecks(browser);
  expect(result.results.filter(r => 'passed' in r).every(r => r.passed)).toBe(true);
  expect(result.finalState.active).toBe(0);
});
