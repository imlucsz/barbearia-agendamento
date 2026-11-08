import { test, expect } from '@playwright/test';
import { readFile, mkdir } from 'node:fs/promises';

test('internal editorial pages preserve navigation, forms, calendar and role controls', async ({ page }, info) => {
  const source = await readFile(new URL('./product-editorial.browser.js', import.meta.url), 'utf8');
  const run = Function(`return (${source})`)();
  const screenshotDir = info.outputPath('screenshots');
  await mkdir(screenshotDir, { recursive: true });
  const result = await run(page, { screenshotDir });
  await info.attach('checks', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  expect(result.errors).toEqual([]);
  expect(result.unexpected).toEqual([]);
  expect(result.failures).toEqual([]);
  expect(result.total).toBeGreaterThan(180);
});
