async (page) => {
  // Run with browser_run_code_unsafe({ filename: absolutePathToThisFile }).
  // Requires only the static server documented in README.md. No API or database.
  const context = await page.context().browser().newContext({ locale: 'pt-BR' });
  page = await context.newPage(); // Fresh cache/storage, isolated from research tabs.
  const origin = 'http://127.0.0.1:4192';
  const paths = [['a', 'a-editorial.html'], ['b', 'b-minimal.html'], ['c', 'c-experimental.html']];
  const errors = [];
  const requests = [];
  const results = [];
  const onError = error => errors.push(error.message);
  const onConsole = message => { if (message.type() === 'error') errors.push(message.text()); };
  const onRequest = request => requests.push({ url: request.url(), method: request.method() });
  page.on('pageerror', onError); page.on('console', onConsole); page.on('request', onRequest);
  const check = (name, pass, detail = '') => {
    results.push({ name, pass: Boolean(pass), ...(detail ? { detail } : {}) });
  };
  try {
    for (const [id, file] of paths) {
      for (const width of [320, 390, 768, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(`${origin}/${file}`);
        await page.evaluate(() => document.fonts.ready);
        check(`${id}: layout ${width}`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        check(`${id}: heading ${width}`, await page.locator('h1').count() === 1);
        check(`${id}: visible controls >= 44px ${width}`, await page.locator('button,a').evaluateAll(elements =>
          elements.filter(element => element.getClientRects().length && !element.classList.contains('skip'))
            .every(element => element.getBoundingClientRect().height >= 43.9)));
      }
      // All booking CTAs must explain the boundary, close via Escape, restore focus.
      const controls = page.locator('[data-preview]');
      for (let i = 0; i < await controls.count(); i++) {
        const control = controls.nth(i);
        await control.click();
        check(`${id}: CTA ${i + 1} opens labeled modal`, await page.locator('dialog[open]').count() === 1
          && await page.locator('dialog').getAttribute('aria-labelledby') === 'dialog-title');
        check(`${id}: CTA ${i + 1} no fake reservation`, await page.locator('dialog').innerText().then(text => text.includes('Nenhuma reserva foi criada.')));
        await page.keyboard.press('Escape');
        check(`${id}: CTA ${i + 1} restores focus`, await control.evaluate(element => element === document.activeElement));
      }
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(`${origin}/${file}`);
      const menu = page.getByRole('button', { name: 'Menu +' });
      await menu.focus(); await page.keyboard.press('Enter');
      check(`${id}: keyboard opens mobile menu`, await menu.getAttribute('aria-expanded') === 'true');
      await page.keyboard.press('Escape');
      check(`${id}: Escape closes mobile menu`, await menu.getAttribute('aria-expanded') === 'false'
        && await menu.evaluate(element => element === document.activeElement));
      await menu.click();
      await page.locator('nav a').first().click();
      check(`${id}: anchor closes mobile menu`, await menu.getAttribute('aria-expanded') === 'false');
      await page.locator('main [data-preview]').first().click();
      // Native modal must keep focus inside it.
      let trapped = true;
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');
        trapped &&= await page.evaluate(() => !!document.activeElement.closest('dialog'));
      }
      check(`${id}: modal keyboard focus trap`, trapped);
      await page.getByRole('button', { name: 'Fechar prévia' }).focus();
      await page.keyboard.press('Shift+Tab');
      check(`${id}: reverse focus cycle`, await page.getByRole('button', { name: 'Continuar explorando' }).evaluate(element => element === document.activeElement));
      await page.getByRole('button', { name: 'Continuar explorando' }).click();
      check(`${id}: modal explicit close`, await page.locator('dialog[open]').count() === 0);
    }
    await page.goto(`${origin}/b-minimal.html`);
    await page.locator('input[name="service"]').first().focus();
    await page.keyboard.press('ArrowDown');
    check('b: native radio keyboard selection and summary', await page.locator('[data-selection]').textContent() === 'Barba');
    await page.locator('.b-continue').click();
    check('b: selected service follows CTA', await page.locator('.dialog-selected').textContent() === 'Você explorou: Barba.');
    await page.keyboard.press('Escape');
    await page.goto(`${origin}/c-experimental.html`);
    await page.getByRole('button', { name: 'Compacta', exact: true }).click();
    check('c: composition responds with explicit state', await page.locator('.sculpture').getAttribute('data-form') === 'compact'
      && await page.getByRole('button', { name: 'Compacta', exact: true }).getAttribute('aria-pressed') === 'true'
      && await page.getByRole('button', { name: 'Aberta', exact: true }).getAttribute('aria-pressed') === 'false');
    await page.emulateMedia({ reducedMotion: 'reduce' });
    check('c: reduced motion disables transition', await page.locator('.coil').evaluate(element => getComputedStyle(element).transitionDuration === '0s'));
    check('c: reduced motion disables smooth scroll', await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior === 'auto'));
    await page.getByRole('button', { name: 'Aberta', exact: true }).click();
    check('c: composition remains usable with reduced motion', await page.locator('.sculpture').getAttribute('data-form') === 'open');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto(`${origin}/index.html`);
    check('gallery: three prototypes reachable', await page.locator('.direction-copy .button').count() === 3);
    check('no browser or CSP errors', errors.length === 0, errors.join('; '));
    check('no remote or mutating requests', requests.every(request => request.url.startsWith(origin + '/') && request.method === 'GET'));
    check('no local storage or cookies', await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0)
      && (await context.cookies(origin)).length === 0);
    return { browser: context.browser()?.version(), passed: results.filter(result => result.pass).length,
      failed: results.filter(result => !result.pass), total: results.length, results };
  } finally {
    page.off('pageerror', onError); page.off('console', onConsole); page.off('request', onRequest);
    await context.close();
  }
}
