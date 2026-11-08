import { test, expect } from '@playwright/test';
import { readFile, mkdir } from 'node:fs/promises';

test('staff tasks, confirmation, profile navigation and recovery from errors', async ({ page }, info) => {
  const source = await readFile(new URL('./staff-workspace.browser.js', import.meta.url), 'utf8');
  const screenshotDir = info.outputPath('screenshots');
  await mkdir(screenshotDir, { recursive: true });
  const result = await Function(`return (${source})`)()(page, { screenshotDir });
  await info.attach('checks', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  expect(result.errors).toEqual([]);
  expect(result.unexpected).toEqual([]);
  expect(result.failures).toEqual([]);
  expect(result.total).toBeGreaterThan(100);
});
