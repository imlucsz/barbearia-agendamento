import { test, expect } from '@playwright/test';

test('three brief cameos share a decorative canvas and honor reduced motion', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('barbearia.home.intro.v1', 'seen'));
  await page.goto('/pages/index.html#services');
  const slots = page.locator('[data-estrelinha-cameo]');
  await expect(slots).toHaveCount(3);
  for (const name of ['opening', 'passage', 'finale']) {
    const slot = page.locator(`[data-estrelinha-cameo="${name}"]`);
    await slot.evaluate(node => node.scrollIntoView({ block: 'center', behavior: 'instant' }));
    await expect(slot).toHaveClass(/is-visible/);
    await expect(slot.locator('canvas')).toHaveAttribute('aria-hidden', 'true');
    await expect(page.locator('.estrela-cameo-canvas')).toHaveCount(1);
    await expect(slot).not.toHaveClass(/is-visible/, { timeout: 5500 });
  }
  const opening = page.locator('[data-estrelinha-cameo="opening"]');
  await opening.evaluate(node => node.scrollIntoView({ block: 'center', behavior: 'instant' }));
  await page.waitForTimeout(300);
  await expect(opening).not.toHaveClass(/is-visible/);
  await expect(page.locator('.estrela-cameo-canvas')).not.toHaveAttribute('tabindex');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.reload();
  const finale = page.locator('[data-estrelinha-cameo="finale"]');
  await finale.evaluate(node => node.scrollIntoView({ block: 'center', behavior: 'instant' }));
  await expect(finale).toHaveClass(/is-visible/);
  expect(await finale.evaluate(node => getComputedStyle(node).animationName)).toBe('none');
  await expect(finale).not.toHaveClass(/is-visible/, { timeout: 4000 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
