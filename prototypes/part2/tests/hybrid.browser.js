async (page) => {
  const browser = page.context().browser();
  const url = 'http://127.0.0.1:4194/a-hybrid.html';
  const results = [], snapshots = [], errors = [], requests = [];
  const check = (name, pass) => results.push({ name, pass: Boolean(pass) });
  const listen = p => {
    p.on('pageerror', error => errors.push(error.message));
    p.on('request', request => requests.push(request.url()));
  };
  for (const [name, width, height] of [['desktop', 1440, 1000], ['mobile', 390, 844]]) {
    const context = await browser.newContext({ viewport: { width, height } });
    const p = await context.newPage(); listen(p);
    try {
      await p.goto(url);
      await p.waitForFunction(() => document.documentElement.dataset.hybridReady === 'true');
      await p.evaluate(() => document.fonts.ready);
      check(`${name}: no overflow`, await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      check(`${name}: original identity`, (await p.locator('h1').innerText()).replace(/\s+/g, ' ').includes('O clássico nunca sai de cena.'));
      await p.locator('.h-intro [data-preview]').click();
      check(`${name}: CTA opens preview`, await p.locator('dialog[open]').count() === 1);
      await p.keyboard.press('Escape');
      check(`${name}: focus returned`, await p.locator('.h-intro [data-preview]').evaluate(e => e === document.activeElement));
      await p.locator('.h-bridge').scrollIntoViewIfNeeded();
      await p.waitForFunction(() => !!document.querySelector('[data-estrelinha-cameo] canvas'), null, { timeout: 8000 });
      check(`${name}: original mascot rendered`, await p.locator('[data-estrelinha-cameo] canvas').count() === 1);
      await p.locator('#ritual').scrollIntoViewIfNeeded();
      await p.waitForFunction(() => document.querySelector('video').readyState >= 2);
      for (const [stage, time] of [[0, 1.25], [1, 5.25], [2, 9.25], [0, 1.25]]) {
        await p.locator(`[data-stage="${stage}"]`).click();
        await p.waitForFunction(time => Math.abs(window.hybridPreview.snapshot().presentedTime - time) < .15, time, { timeout: 6000 });
        check(`${name}: chapter ${stage} / ${time}s`, await p.locator(`[data-stage="${stage}"]`).getAttribute('aria-current') === 'step');
      }
      // Physical document scroll between chapter landmarks: continuous, reversible.
      for (const progress of [.38, .66, .29]) {
        await p.evaluate(progress => {
          const t = window.ScrollTrigger.getById('lab-ritual') || window.ScrollTrigger.getById('lab-ritual-mobile');
          scrollTo(0, t.start + (t.end - t.start) * progress);
        }, progress);
        await p.waitForFunction(progress => Math.abs(window.hybridPreview.snapshot().presentedTime - progress * 10) < .2, progress, { timeout: 6000 });
        snapshots.push({ name, progress, state: await p.evaluate(() => {
          const { currentTime, presentedTime, seeks, failed, additionalRAFLoops } = window.hybridPreview.snapshot();
          return { currentTime, presentedTime, seeks, failed, additionalRAFLoops };
        }) });
        check(`${name}: scrub at ${progress}`, true);
      }
      check(`${name}: bounded completed seeking`, await p.evaluate(() => window.hybridPreview.snapshot().seeks < 200));
      await p.locator('.h-skip-ritual').click();
      check(`${name}: direct path to booking`, await p.locator('#como-funciona').evaluate(e => e.getBoundingClientRect().top < innerHeight));
      if (name === 'mobile') {
        await p.evaluate(() => scrollTo(0, 0));
        await p.locator('.menu-toggle').click();
        check('mobile: nav expanded', await p.locator('.menu-toggle').getAttribute('aria-expanded') === 'true');
        await p.keyboard.press('Escape');
        check('mobile: nav Escape', await p.locator('.menu-toggle').getAttribute('aria-expanded') === 'false');
        await p.setViewportSize({ width: 320, height: 740 });
        check('320px: no overflow', await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await p.locator('#ritual').scrollIntoViewIfNeeded();
        const disjoint = await p.evaluate(() => {
          const a = document.querySelector('.ritual-rail').getBoundingClientRect();
          const b = document.querySelector('.h-skip-ritual').getBoundingClientRect();
          return a.bottom <= b.top || b.bottom <= a.top || a.right <= b.left || b.right <= a.left;
        });
        check('320px: chapter and skip controls separated', disjoint);
      }
    } finally { await context.close(); }
  }
  const reduced = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  try {
    const p = await reduced.newPage(); listen(p);
    await p.goto(url); await p.waitForFunction(() => window.hybridPreview);
    check('reduced: static poster mode', await p.evaluate(() => window.hybridPreview.snapshot().mode === 'poster'));
    check('reduced: no video download', await p.locator('video').getAttribute('src') === null);
    check('reduced: all three chapters visible', await p.locator('.ritual-chapter').evaluateAll(nodes => nodes.every(e => getComputedStyle(e).visibility === 'visible' && getComputedStyle(e).opacity === '1')));
  } finally { await reduced.close(); }
  const fallback = await browser.newContext({ viewport: { width: 390, height: 844 } });
  try {
    const p = await fallback.newPage(); listen(p);
    await p.route('**/ritual-scrub.webm', route => route.abort());
    await p.goto(url); await p.waitForFunction(() => window.hybridPreview);
    await p.locator('#ritual').scrollIntoViewIfNeeded();
    await p.waitForFunction(() => document.querySelector('#ritual').classList.contains('video-error'));
    check('media failure: chapters remain readable', await p.locator('.ritual-chapter').evaluateAll(nodes => nodes.every(e => getComputedStyle(e).visibility === 'visible')));
    await p.locator('.h-finale [data-preview]').click();
    check('media failure: booking preview still usable', await p.locator('dialog[open]').count() === 1);
  } finally { await fallback.close(); }
  check('no JS errors', errors.length === 0);
  check('no external or API requests', requests.every(request => request.startsWith('http://127.0.0.1:4194/') && !request.includes('/api/')));
  return { browser: browser.version(), passed: results.filter(r => r.pass).length, failed: results.filter(r => !r.pass), total: results.length, errors, snapshots, results };
}
