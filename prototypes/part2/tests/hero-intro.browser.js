async (page) => {
  const browser = page.context().browser();
  const origin = 'http://127.0.0.1:4194';
  const url = `${origin}/a-hybrid.html`;
  const results = [], errors = [];
  const check = (name, pass) => results.push({ name, pass: Boolean(pass) });
  for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
    const context = await browser.newContext({ viewport: { width, height } });
    const p = await context.newPage(); p.on('pageerror', e => errors.push(e.message));
    try {
      await p.goto(url);
      await p.waitForFunction(() => window.hybridPreview);
      const playing = await p.evaluate(() => document.documentElement.dataset.heroIntro === 'playing');
      check(`${name}: intro starts on first visit`, playing);
      if (!playing) continue;
      await p.waitForFunction(() => document.documentElement.dataset.heroIntro === 'complete', null, { timeout: 4500 });
      check(`${name}: first visit completion`, await p.evaluate(() => sessionStorage.getItem('barbearia.home.intro.v1') === 'seen'));
      check(`${name}: skip hidden after completion`, await p.locator('[data-skip-hero-intro]').isHidden());
      const geometry = await p.evaluate(() => {
        const rect = selector => document.querySelector(selector).getBoundingClientRect();
        const pole = rect('.h-pole svg'), scissors = rect('.h-tool svg'), text = rect('.h-copy'), art = rect('.h-art');
        const intersects = (a, b) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
        return {
          clear: !intersects(pole, text) && !intersects(scissors, text),
          overlaps: intersects(pole, scissors) && (scissors.top + scissors.bottom) / 2 > (pole.top + pole.bottom) / 2,
          largePole: pole.height >= (innerWidth < 700 ? 280 : 350),
          vertical: pole.height > pole.width * 2,
          frameless: getComputedStyle(document.querySelector('.h-art')).borderTopWidth === '0px',
          inViewport: art.left >= 0 && art.right <= innerWidth && document.documentElement.scrollWidth <= innerWidth,
          diagonal: getComputedStyle(document.querySelector('.h-tool')).transform !== 'none',
        };
      });
      for (const [key, pass] of Object.entries(geometry)) check(`${name}: ${key}`, pass);
      await p.locator('.h-intro [data-preview]').click();
      check(`${name}: CTA usable after intro`, await p.locator('dialog[open]').count() === 1);
      await p.keyboard.press('Escape');
      await p.getByRole('link', { name: 'Comparar direções ↗', exact: true }).click();
      await p.getByRole('link', { name: 'Explorar A híbrida' }).click();
      await p.waitForFunction(() => window.hybridPreview);
      check(`${name}: no replay after internal navigation`, await p.evaluate(() => document.documentElement.dataset.heroIntro === 'complete' && document.documentElement.dataset.heroIntroReason === 'seen'));
      await p.reload(); await p.waitForFunction(() => window.hybridPreview);
      check(`${name}: no replay on reload`, await p.evaluate(() => document.documentElement.dataset.heroIntroReason === 'seen'));
      if (name === 'mobile') {
        for (const size of [{ width: 320, height: 740 }, { width: 768, height: 1024 }, { width: 844, height: 390 }]) {
          await p.setViewportSize(size);
          check(`${size.width}: no overflow`, await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        }
      }
    } finally { await context.close(); }
  }
  for (const action of ['skip', 'Escape', 'Tab', 'scroll', 'resize', 'reduced-change']) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const p = await context.newPage(); p.on('pageerror', e => errors.push(e.message));
    try {
      await p.goto(url); await p.waitForFunction(() => window.hybridPreview);
      if (await p.locator('[data-skip-hero-intro]').count() === 0) { check(`${action}: intro cancellation available`, false); continue; }
      if (action === 'skip') await p.locator('[data-skip-hero-intro]').click();
      else if (action === 'Escape' || action === 'Tab') await p.keyboard.press(action);
      else if (action === 'scroll') await p.mouse.wheel(0, 300);
      else if (action === 'resize') await p.setViewportSize({ width: 390, height: 844 });
      else await p.emulateMedia({ reducedMotion: 'reduce' });
      await p.waitForFunction(() => document.documentElement.dataset.heroIntro === 'complete');
      check(`${action}: settles all illustrations`, await p.locator('.h-tool').evaluate(e => getComputedStyle(e).opacity === '1'));
      check(`${action}: overlay removed`, await p.locator('.h-opening').isHidden());
      if (action === 'skip') check('skip: returns focus to title', await p.locator('h1').evaluate(e => e === document.activeElement));
    } finally { await context.close(); }
  }
  for (const [name, options, suffix] of [['reduced', { reducedMotion: 'reduce' }, ''], ['anchor', {}, '#ritual']]) {
    const context = await browser.newContext(options); const p = await context.newPage();
    try {
      await p.goto(url + suffix); await p.waitForFunction(() => window.hybridPreview);
      check(`${name}: no intro`, await p.evaluate(() => document.documentElement.dataset.heroIntro === 'complete'));
      check(`${name}: no cover`, await p.locator('.h-opening').isHidden());
    } finally { await context.close(); }
  }
  const context = await browser.newContext(); const p = await context.newPage();
  try {
    await p.route('**/gsap.min.js', route => route.abort());
    await p.goto(url); await p.waitForFunction(() => document.documentElement.dataset.hybridReady === 'fallback');
    check('dependency failure: content and artwork remain visible', await p.locator('.h-tool').isVisible() && await p.locator('h1').isVisible());
    check('dependency failure: no cover', await p.locator('.h-opening').isHidden());
  } finally { await context.close(); }
  check('no JS errors', errors.length === 0);
  return { browser: browser.version(), passed: results.filter(r => r.pass).length, failed: results.filter(r => !r.pass), total: results.length, errors, results };
}
