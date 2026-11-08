import { expect, test } from '@playwright/test';

const user = { id: 1, nome: 'Admin fictício', role: 'admin' };
const rows = date => [{ id: 10, horario: '09:30', nome_cliente: `Cliente ${date}`, servico_nome: 'Corte fictício', profissional_nome: 'Equipe fictícia', status: 'confirmado' }];

async function openAgenda(page, agendaHandler, usersFail = false) {
  await page.clock.setFixedTime(new Date('2026-12-30T12:00:00-03:00'));
  await page.addInitScript(user => {
    window.BARBEARIA_API_URL = `${location.origin}/__agenda_test_api`;
    localStorage.setItem('token', 'fictitious-test-token');
    localStorage.setItem('user', JSON.stringify(user));
  }, user);
  await page.route('**/__agenda_test_api/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace('/__agenda_test_api', '');
    if (path === '/admin/agenda') return agendaHandler(route, url.searchParams.get('data'));
    if (path === '/users/' && usersFail) return route.fulfill({ status: 500, json: { detail: 'Falha fictícia em clientes' } });
    return route.fulfill({ json: path === '/auth/me' ? user : [] });
  });
  await page.goto('/pages/admin.html');
}

test('agenda survives users failure and navigates weeks and dates by keyboard', async ({ page }) => {
  await openAgenda(page, (route, date) => route.fulfill({ json: rows(date) }), true);
  const list = page.locator('#agendaList');
  await expect(list).toContainText('Cliente 2026-12-30');
  await expect(list).toContainText('09:30');
  await expect(list).toContainText('Corte fictício');
  const next = page.getByRole('button', { name: 'Próxima semana', exact: true });
  await next.focus();
  await page.keyboard.press('Enter');
  await expect(next).toBeFocused();
  await expect(list).toContainText('Cliente 2027-01-06');
  await expect(page.locator('#dateRoll [aria-pressed="true"]')).toHaveAttribute('data-date', '2027-01-06');
  const previous = page.getByRole('button', { name: 'Semana anterior', exact: true });
  await previous.focus();
  await page.keyboard.press('Space');
  await expect(list).toContainText('Cliente 2026-12-30');
  await previous.click();
  await expect(list).toContainText('Cliente 2026-12-23');
  await next.click();
  const saturday = page.locator('#dateRoll [data-date="2027-01-02"]');
  await saturday.focus();
  await page.keyboard.press('ArrowRight');
  const sunday = page.locator('#dateRoll [data-date="2027-01-03"]');
  await expect(sunday).toBeFocused();
  await expect(sunday).toHaveAttribute('aria-pressed', 'true');
  await expect(sunday).toHaveAccessibleName(/domingo.*03\/01\/2027/);
  await expect(list).toContainText('Cliente 2027-01-03');
  await page.keyboard.press('PageUp');
  await expect(page.locator('#dateRoll [data-date="2026-12-27"]')).toBeFocused();
  await page.keyboard.press('End');
  await expect(page.locator('#dateRoll [data-date="2027-01-02"]')).toBeFocused();
  await page.keyboard.press('Home');
  await expect(page.locator('#dateRoll [data-date="2026-12-27"]')).toBeFocused();
  await page.locator('#dateRoll [data-date="2026-12-29"]').click();
  await expect(page.locator('#dateRoll [data-date="2026-12-29"]')).toBeFocused();
  await expect(list).toContainText('Cliente 2026-12-29');
  await expect(page.locator('#agendaDayLabel')).toContainText('29/12/2026');
});

test('real agenda errors remain visible', async ({ page }) => {
  await openAgenda(page, route => route.fulfill({ status: 500, json: { detail: 'Falha fictícia da agenda' } }), true);
  await expect(page.locator('#agendaList')).toContainText('Erro interno do servidor');
  await expect(page.locator('#agendaList .agenda-row')).toHaveCount(0);
});

test('late reference preserves charged amount and focus after editing', async ({ page }) => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  await openAgenda(page, (route, date) => route.fulfill({ json: rows(date) }));
  // Newer routes run first; delay services on reload after the catch-all exists.
  await page.route('**/__agenda_test_api/services/', async route => {
    await pending;
    await route.fulfill({ json: [{ id: 5, nome: 'Corte tardio' }] });
  });
  await page.reload();
  const amount = page.locator('#charged-10');
  await amount.fill('37.50');
  const response = page.waitForResponse(response => response.url().endsWith('/services/'));
  release();
  await response;
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect(amount).toHaveValue('37.50');
  await expect(amount).toBeFocused();
});

test('late agenda response cannot replace the selected date appointments', async ({ page }) => {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  let firstRoute;
  const received = new Promise(resolve => { firstRoute = resolve; });
  await openAgenda(page, async (route, date) => {
    if (date === '2026-12-30') { firstRoute(); await pending; }
    await route.fulfill({ json: rows(date) });
  });
  await received;
  await page.getByRole('button', { name: 'Próxima semana', exact: true }).click();
  await expect(page.locator('#agendaList')).toContainText('Cliente 2027-01-06');
  const response = page.waitForResponse(response => response.url().includes('data=2026-12-30'));
  release();
  await response;
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await expect(page.locator('#agendaList')).toContainText('Cliente 2027-01-06');
  await expect(page.locator('#agendaList')).not.toContainText('Cliente 2026-12-30');
});
