import { test, expect } from '@playwright/test';

const fixtureSecret = '  Fixture-Only-2026!  ';
const cases = [
  ['login.html', 'login-password', 'current-password', '/auth/login', 'senha'],
  ['cadastro.html', 'register-password', 'new-password', '/auth/register', 'senha'],
  ['reset.html#token=fixture-only', 'reset-password', 'new-password', '/auth/redefinir-senha', 'nova_senha'],
  ['client-account.html', 'delete-password', 'current-password', '/users/me', 'senha_atual'],
];

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.BARBEARIA_API_URL = `${location.origin}/test-api`;
    localStorage.setItem('token', 'fixture-only-session');
  });
  await page.route('**/test-api/**', route => route.fulfill({ json: { id: 1, nome: 'Fixture', email: 'fixture@example.com', role: 'cliente' } }));
});

for (const [file, id, autocomplete, endpoint, credentialKey] of cases) {
  test(`${id}: teclado, seleção, valor, sem efeitos extras e submissão`, async ({ page }) => {
    const consoleEntries = [];
    page.on('console', message => consoleEntries.push(message.text()));
    await page.goto(`/pages/${file}`);
    if (id === 'delete-password') await page.getByRole('button', { name: 'Excluir minha conta' }).click();
    const input = page.locator(`#${id}`);
    const toggle = page.getByRole('button', { name: 'Mostrar senha', exact: true });
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('type', 'button');
    await expect(toggle).toHaveAttribute('aria-controls', id);
    await expect(input).toHaveAttribute('type', 'password');
    await expect(input).toHaveAttribute('autocomplete', autocomplete);
    await expect(input).toHaveAttribute('spellcheck', 'false');
    await expect(input).toHaveAttribute('autocorrect', 'off');
    await expect(input).toHaveAttribute('autocapitalize', 'none');
    await input.fill(fixtureSecret);
    await input.evaluate(node => node.setSelectionRange(2, 8, 'backward'));
    await input.focus();
    await page.keyboard.press('Tab');
    await expect(toggle).toBeFocused();
    expect(await toggle.evaluate(node => getComputedStyle(node).outlineStyle !== 'none' && parseFloat(getComputedStyle(node).outlineWidth) >= 2)).toBe(true);
    let requests = 0;
    page.on('request', request => { if (request.url().includes('/test-api/')) requests++; });
    await page.keyboard.press('Enter');
    const hide = page.getByRole('button', { name: 'Ocultar senha', exact: true });
    await expect(hide).toBeFocused();
    await expect(input).toHaveAttribute('type', 'text');
    expect(await input.evaluate(node => [node.selectionStart, node.selectionEnd, node.selectionDirection])).toEqual([2, 8, 'backward']);
    await page.evaluate(async () => {
      const { initPasswordVisibility } = await import('/assets/js/password-visibility.mjs');
      initPasswordVisibility(document);
      initPasswordVisibility(document);
    });
    await expect(input).toHaveAttribute('type', 'text');
    await page.keyboard.press('Space');
    await expect(input).toHaveAttribute('type', 'password');
    // Reinitialize while hidden too: one click must still toggle once.
    await page.evaluate(async () => {
      const { initPasswordVisibility } = await import('/assets/js/password-visibility.mjs');
      initPasswordVisibility(document);
      initPasswordVisibility(document);
    });
    for (let count = 0; count < 4; count++) {
      await page.getByRole('button', { name: count % 2 ? 'Ocultar senha' : 'Mostrar senha', exact: true }).click();
      await expect(input).toHaveAttribute('type', count % 2 ? 'password' : 'text');
    }
    expect(await input.evaluate((node, secret) => node.value === secret, fixtureSecret)).toBe(true);
    expect(requests).toBe(0);
    expect(await page.evaluate(secret => !document.documentElement.outerHTML.includes(secret)
      && !JSON.stringify({ ...localStorage, ...sessionStorage }).includes(secret), fixtureSecret)).toBe(true);
    expect(consoleEntries.some(entry => entry.includes(fixtureSecret))).toBe(false);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const bounds = await toggle.boundingBox();
    expect(bounds.width >= 44 && bounds.height >= 44).toBe(true);
    let submissions = 0;
    await page.route(`**/test-api${endpoint}`, async route => {
      submissions++;
      expect(route.request().postDataJSON()[credentialKey] === fixtureSecret).toBe(true);
      await route.fulfill({ status: 400, json: { detail: 'Fixture: envio recebido' } });
    });
    if (id === 'login-password' || id === 'register-password') await page.locator('input[name="email"]').fill('fixture@example.com');
    if (id === 'register-password') {
      await page.locator('input[name="nome"]').fill('Fixture');
      await page.locator('input[name="consentimento_lgpd"]').check();
    }
    // Submit with the password visible too; input type must not change the payload.
    await page.getByRole('button', { name: 'Mostrar senha', exact: true }).click();
    await page.locator(`#${id}`).evaluate(node => node.form.requestSubmit());
    await expect.poll(() => submissions).toBe(1);
    expect(consoleEntries.some(entry => entry.includes(fixtureSecret))).toBe(false);
  });
}

test('desabilitado, fieldset, formulário dinâmico e reset sem listeners duplicados', async ({ page }) => {
  await page.goto('/pages/login.html');
  await page.evaluate(() => {
    const form = document.createElement('form');
    form.id = 'dynamic';
    form.innerHTML = '<fieldset disabled><label for="dynamic-password">Senha de teste</label><input id="dynamic-password" type="password" autocomplete="new-password" data-password-visibility></fieldset>';
    document.querySelector('main').append(form);
  });
  const input = page.locator('#dynamic-password');
  const toggle = page.locator('#dynamic button');
  await expect(toggle).toHaveCount(1);
  await expect(toggle).toBeDisabled();
  await page.locator('#dynamic fieldset').evaluate(node => { node.disabled = false; });
  await expect(toggle).toBeEnabled();
  await input.fill(fixtureSecret);
  await toggle.click();
  await expect(input).toHaveAttribute('type', 'text');
  await input.evaluate(node => { node.disabled = true; });
  await expect(toggle).toBeDisabled();
  await expect(input).toHaveAttribute('type', 'password');
  await input.evaluate(node => { node.disabled = false; });
  await toggle.click();
  await page.locator('#dynamic').evaluate(node => node.reset());
  await expect(input).toHaveAttribute('type', 'password');
  await expect(toggle).toHaveAccessibleName('Mostrar senha');
});

test('exclusão: fechar limpa e oculta; Tab continua no diálogo e retorna ao acionador', async ({ page }) => {
  await page.goto('/pages/client-account.html');
  const opener = page.getByRole('button', { name: 'Excluir minha conta' });
  await opener.click();
  const input = page.locator('#delete-password');
  await expect(input).toBeFocused();
  await input.fill(fixtureSecret);
  await page.keyboard.press('Tab');
  await page.keyboard.press('Space');
  await expect(input).toHaveAttribute('type', 'text');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Cancelar', exact: true })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(opener).toBeFocused();
  await opener.click();
  await expect(input).toHaveAttribute('type', 'password');
  expect(await input.inputValue() === '').toBe(true);
  await expect(page.getByRole('button', { name: 'Mostrar senha', exact: true })).toBeVisible();
});

test('fragmento desconectado, religação em fieldset e contraste dos tokens', async ({ page }) => {
  await page.goto('/pages/login.html');
  await page.evaluate(async () => {
    const { initPasswordVisibility } = await import('/assets/js/password-visibility.mjs');
    const form = document.createElement('form');
    form.id = 'fragment';
    form.innerHTML = '<input type="password" data-password-visibility autocomplete="new-password">';
    initPasswordVisibility(form);
    document.querySelector('main').append(form);
  });
  const toggle = page.locator('#fragment button');
  await expect(toggle).toHaveCount(1);
  expect(await page.locator('#fragment').evaluate(form => form.querySelector('button').getAttribute('aria-controls') === form.querySelector('input').id)).toBe(true);
  await toggle.click();
  await page.locator('#fragment').evaluate(form => {
    const fieldset = document.createElement('fieldset');
    fieldset.disabled = true;
    form.append(fieldset);
    fieldset.append(form.querySelector('.password-control'));
  });
  await expect(page.locator('#fragment input')).toHaveAttribute('type', 'password');
  await expect(toggle).toBeDisabled();
  const ratio = await page.locator('#login-form .password-visibility').evaluate(button => {
    const style = getComputedStyle(button);
    const luminance = color => color.match(/\d+/g).slice(0, 3).map(Number).map(value => {
      const n = value / 255;
      return n <= .04045 ? n / 12.92 : ((n + .055) / 1.055) ** 2.4;
    }).reduce((total, value, index) => total + value * [.2126, .7152, .0722][index], 0);
    const values = [luminance(style.color), luminance(style.backgroundColor)].sort((a, b) => b - a);
    return (values[0] + .05) / (values[1] + .05);
  });
  expect(ratio).toBeGreaterThanOrEqual(4.5);
});

test('sucessos existentes preservam redirecionamentos e remascaram formulários limpos', async ({ page }) => {
  // Stub only destination documents to avoid unrelated dashboard/HOME behavior.
  for (const destination of ['client-dashboard.html', 'index.html']) {
    await page.route(`**/pages/${destination}`, route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Fixture destination</title>' }));
  }
  for (const [file, id, , endpoint, credentialKey] of cases) {
    await page.goto(`/pages/${file}`);
    if (id === 'delete-password') await page.getByRole('button', { name: 'Excluir minha conta' }).click();
    const input = page.locator(`#${id}`);
    await input.fill(fixtureSecret);
    await page.getByRole('button', { name: 'Mostrar senha', exact: true }).click();
    if (id === 'login-password' || id === 'register-password') await page.locator('[name=email]').fill('fixture@example.com');
    if (id === 'register-password') {
      await page.locator('[name=nome]').fill('Fixture');
      await page.locator('[name=consentimento_lgpd]').check();
    }
    await page.route(`**/test-api${endpoint}`, route => {
      expect(route.request().postDataJSON()[credentialKey] === fixtureSecret).toBe(true);
      return route.fulfill({ status: id === 'register-password' ? 201 : 200, json: {
        access_token: 'fixture-only-session', user: { id: 1, nome: 'Fixture', email: 'fixture@example.com', role: 'cliente' },
        mensagem: 'Fixture: operação concluída',
      } });
    });
    await input.evaluate(node => node.form.requestSubmit());
    if (id === 'login-password') await expect(page).toHaveURL(/client-dashboard\.html$/);
    else if (id === 'delete-password') await expect(page).toHaveURL(/index\.html$/);
    else {
      await expect(input).toHaveAttribute('type', 'password');
      expect(await input.inputValue() === '').toBe(true);
      await expect(page.getByRole('button', { name: 'Mostrar senha', exact: true })).toBeVisible();
      if (id === 'register-password') await expect(page).toHaveURL(/login\.html$/);
    }
    await page.unroute(`**/test-api${endpoint}`);
  }
});
