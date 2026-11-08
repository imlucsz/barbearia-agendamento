// Isolated local frontend only; every API response is a fictitious fixture.
async (page, options = {}) => {
  const base = 'http://127.0.0.1:4186';
  const checks = [], errors = [], unexpected = [], contexts = [], screenshots = [];
  const check = (ok, name) => checks.push({ name, ok: Boolean(ok) });
  async function shot(p, name) {
    if (!options.screenshotDir) return;
    const path = `${options.screenshotDir}/staff-${name}.png`;
    await p.screenshot({ path, fullPage: true }); screenshots.push(path);
  }
  try {
    for (const role of ['admin', 'barbeiro']) {
      const ctx = await page.context().browser().newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' }); contexts.push(ctx);
      const user = { id: role === 'admin' ? 1 : 9, nome: role === 'admin' ? 'Administrador de teste' : 'Lucas de teste', role };
      await ctx.addInitScript(({ base, user }) => { window.BARBEARIA_API_URL = base + '/__staff'; localStorage.setItem('token', 'ui-fixture'); localStorage.setItem('user', JSON.stringify(user)); }, { base, user });
      const state = { calls: [], failUpdate: false, failAgenda: false, empty: false, delay: 0, serviceFailure: false, scheduleFailure: false, userDelay: 300 };
      const services = [{ id: 1, nome: 'Corte clássico', descricao: 'Descrição de teste', preco: 55, duracao_minutos: 40 }];
      const barbers = [{ id: 9, nome: 'Lucas de teste' }, { id: 10, nome: 'Rafael de teste' }];
      const clients = [{ id: 5, nome: '<img src=x onerror="window.xss=1"> Cliente teste', email: 'cliente@example.test', role: 'cliente', bloqueado: false }];
      const appointments = [{ id: 71, user_id: 5, nome_cliente: 'Cliente teste', service_id: 1, barbeiro_id: 9, data_hora: '2026-11-07T23:00:00', status: 'confirmado', preco: 55, duracao_minutos: 40 }, { id: 72, nome_cliente: 'Outro cliente', service_id: 1, barbeiro_id: 9, data_hora: '2026-11-07T09:00:00', status: 'concluido', preco: 55, duracao_minutos: 40 }];
      await ctx.route('**/*', async route => {
        const url = new URL(route.request().url());
        if (url.origin !== base) { unexpected.push(url.origin); return route.abort(); }
        if (!url.pathname.startsWith('/__staff')) return route.continue();
        const path = url.pathname.slice('/__staff'.length), method = route.request().method(), body = route.request().postDataJSON();
        state.calls.push({ path, method, body, query: url.search });
        const reply = (data, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
        if (path === '/auth/me') { if (state.userDelay) await new Promise(r => setTimeout(r, state.userDelay)); return reply(user); }
        if (path === '/services/') {
          if (method === 'POST' && state.serviceFailure) return reply({ detail: 'Não foi possível salvar o serviço.' }, 503);
          return reply(method === 'GET' ? services : { id: 2, ...body });
        }
        if (path === '/users/barbeiros') return reply(barbers);
        if (path === '/users/') return reply(clients);
        if (path.startsWith('/services/')) return reply({ id: 1, ...body });
        if (path === '/admin/agenda' || path === '/admin/me/agenda') return state.failAgenda ? reply({ detail: 'Falha na consulta' }, 500) : reply(state.empty ? [] : appointments);
        if (path === '/appointments/71') {
          await new Promise(r => setTimeout(r, state.delay));
          if (state.failUpdate) return reply({ detail: 'Não foi possível salvar. Tente novamente.' }, 503);
          Object.assign(appointments[0], body); return reply(appointments[0]);
        }
        if (path.startsWith('/horario/jornadas')) {
          if (method !== 'GET') return state.scheduleFailure ? reply({ detail: 'Horário conflitante.' }, 409) : reply({ id: 1, ...body });
          return reply([{ id: 1, barbeiro_id: Number(path.split('/').pop()), dia_semana: 1, hora_inicio: '09:00', hora_fim: '18:00', ativo: true }]);
        }
        if (path.startsWith('/horario/bloqueios')) return reply(method === 'GET' ? [{ id: 2, barbeiro_id: Number(path.split('/').pop()), inicio: '2026-11-10T09:00:00', fim: '2026-11-10T12:00:00', tipo: 'folga', motivo: 'Folga fictícia', ativo: true }] : { id: 2, ...body });
        if (path.startsWith('/barbeiro-servico/')) return reply([]);
        if (path === '/informacoes/') return reply({ nome: 'Barbearia de teste', endereco: 'Endereço fictício', telefone: '11999999999', dias_atendimento: 'Segunda a sábado', horario_funcionamento: '09h às 18h' });
        if (path === '/admin/avaliacoes') return reply([]);
        if (path === '/admin/auditoria') return reply({ items: [], total: 0 });
        if (path === '/admin/relatorio') return reply({ total_agendamentos: 2, total_receita: 110, ticket_medio: 55 });
        if (path === '/admin/agendamentos') return reply({ id: 90, ...body }, 201);
        unexpected.push(`${method} ${path}`); return reply({}, 404);
      });
      const p = await ctx.newPage(); p.setDefaultTimeout(5000); p.on('pageerror', e => errors.push(e.message));
      await p.goto(base + '/pages/admin.html#financeiro');
      check(await p.locator('.admin-only:visible').count() === 0, `${role}: administrative panels hidden before verified profile`);
      await p.waitForFunction(() => document.body.dataset.staffReady === 'true');
      await p.evaluate(() => document.fonts.ready);
      check(await p.locator('.admin-section:visible').count() === 1, `${role}: one active panel`);
      check(p.url().endsWith(role === 'admin' ? '#financeiro' : '#agenda'), `${role}: direct link respects profile`);
      await p.locator('[data-staff-area=agenda]').click();
      await p.locator('.agenda-row').first().waitFor();
      check((await p.locator('#staff-title').textContent()) === (role === 'admin' ? 'Agenda da barbearia' : 'Minha agenda'), `${role}: distinct heading`);
      check(await p.locator('#agenda-summary > div').count() === 4, `${role}: actual response summary`);
      check(await p.locator('.admin-nav a:visible').count() === (role === 'admin' ? 6 : 1), `${role}: appropriate navigation`);
      check(await p.evaluate(() => { const ids = [...document.querySelectorAll('[id]')].map(el => el.id); return new Set(ids).size === ids.length; }), `${role}: no duplicate IDs`);
      for (const width of [1440, 390, 320]) {
        await p.setViewportSize({ width, height: 1000 });
        await p.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        check(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${role}/${width}: no page overflow`);
        check(await p.locator('.date-item.selected').evaluate(el => { const a = el.getBoundingClientRect(), b = el.closest('.date-roll').getBoundingClientRect(); return a.left >= b.left - 1 && a.right <= b.right + 1; }), `${role}/${width}: selected date visible after resize`);
        if (width !== 320) await shot(p, `${role}-${width}`);
      }
      await p.locator('[data-appointment-status=cancelado]').click();
      check(state.calls.filter(c => c.method === 'PUT').length === 0, `${role}: clicking destructive action does not mutate`);
      check(await p.locator('#staff-action-context').textContent().then(t => t.includes('Cliente teste') && t.includes('23:00')), `${role}: confirmation identifies reservation`);
      await p.keyboard.press('Escape');
      check(!await p.locator('#staff-action-dialog').isVisible(), `${role}: Escape cancels`);
      check(await p.locator('[data-appointment-status=cancelado]').evaluate(el => el === document.activeElement), `${role}: focus returns to action`);
      state.failUpdate = true; state.delay = 350;
      await p.locator('[data-appointment-status=concluido]').click();
      await p.fill('#staff-action-amount', '');
      await p.locator('#staff-action-dialog [type=submit]').click();
      check(state.calls.filter(c => c.method === 'PUT').length === 0, `${role}: empty amount never submitted`);
      await p.fill('#staff-action-amount', '62.50');
      await p.locator('#staff-action-dialog [type=submit]').click();
      check(await p.locator('#staff-action-dialog [type=submit]').isDisabled(), `${role}: pending action cannot repeat`);
      await p.locator('#staff-action-dialog form').dispatchEvent('submit');
      await p.keyboard.press('Escape');
      check(await p.locator('#staff-action-dialog').isVisible(), `${role}: Escape cannot dismiss pending mutation`);
      await p.locator('#staff-action-error:not([hidden])').waitFor();
      check(await p.locator('.agenda-row').count() === 2, `${role}: failed mutation preserves agenda`);
      check(await p.locator('#staff-action-amount').inputValue() === '62.50', `${role}: failed mutation preserves amount`);
      check(await p.locator('#staff-action-error').evaluate(el => document.activeElement === el), `${role}: error is focused`);
      state.failUpdate = false;
      await p.locator('#staff-action-dialog [type=submit]').click();
      await p.locator('#staff-action-dialog').waitFor({ state: 'hidden' });
      check(state.calls.filter(c => c.path === '/appointments/71' && c.method === 'PUT').length === 2, `${role}: one request per explicit attempt`);
      check(state.calls.filter(c => c.path === '/appointments/71').at(-1).body.valor_cobrado === 62.5, `${role}: existing charged amount contract`);
      check(await p.locator('#agenda-feedback').isVisible(), `${role}: saved feedback`);
      check(await p.locator('[data-appointment-status]').count() === 0, `${role}: completed rows have no active actions`);
      appointments[0].status = 'confirmado';
      await p.click('#agenda-retry'); await p.locator('[data-appointment-status=falta]').waitFor();
      await p.locator('[data-appointment-status=falta]').click();
      await p.locator('#staff-action-dialog [type=submit]').click();
      await p.locator('#staff-action-dialog').waitFor({ state: 'hidden' });
      check(state.calls.filter(c => c.path === '/appointments/71').at(-1).body.status === 'falta', `${role}: absence confirmed`);
      appointments[0].status = 'confirmado';
      await p.click('#agenda-retry'); await p.locator('[data-appointment-status=cancelado]').waitFor();
      await p.locator('[data-appointment-status=cancelado]').click();
      await p.locator('#staff-action-dialog [type=submit]').click();
      await p.locator('#staff-action-dialog').waitFor({ state: 'hidden' });
      check(state.calls.filter(c => c.path === '/appointments/71').at(-1).body.status === 'cancelado', `${role}: cancellation confirmed`);
      appointments[0].status = 'confirmado';
      await p.click('#agenda-retry'); await p.locator('[data-appointment-status=falta]').waitFor();
      await p.locator('[data-appointment-status=falta]').click();
      const beforeStale = state.calls.filter(c => c.path === '/appointments/71').length;
      await p.evaluate(() => { const date = document.querySelector('#agenda-date'); date.value = '2026-12-04'; date.dispatchEvent(new Event('change')); });
      await p.locator('#staff-action-dialog [type=submit]').click();
      await p.locator('#staff-action-error').getByText('A agenda mudou.', { exact: false }).waitFor();
      check(state.calls.filter(c => c.path === '/appointments/71').length === beforeStale, `${role}: stale confirmation cannot mutate another date`);
      await p.click('[data-dialog-cancel]');
      state.failAgenda = true; await p.click('#agenda-retry');
      await p.locator('.agenda-empty.error').waitFor();
      check(await p.locator('#agenda-summary').textContent() === '', `${role}: failed read removes stale summary`);
      state.failAgenda = false; state.empty = true; await p.click('#agenda-retry');
      await p.getByText('Nenhuma reserva nesta data.', { exact: false }).waitFor();
      check(!(await p.locator('#agendaList').textContent()).includes('Todas as vagas livres'), `${role}: empty reservations do not claim availability`);
      state.empty = false;
      await p.fill('#agenda-date', '2026-12-03'); await p.locator('#agenda-date').dispatchEvent('change');
      await p.waitForFunction(() => document.querySelector('#agendaDayLabel').textContent.includes('03/12/2026'));
      check(state.calls.some(c => c.query.includes('2026-12-03')), `${role}: direct date uses existing agenda API`);
      await p.click('#agenda-today');
      if (role === 'admin') {
        for (const hash of ['clientes', 'equipe', 'jornadas', 'servicos', 'financeiro', 'institucional', 'avaliacoes', 'auditoria', 'agendamento-manual']) {
          await p.evaluate(hash => { location.hash = hash; }, hash);
          await p.locator(`#${hash}`).waitFor();
          check(await p.locator('.admin-section:visible').count() === 1, `${hash}: isolated task panel`);
          check(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${hash}: mobile layout contained`);
        }
        await p.fill('#manual-customer-name', 'Cliente avulso de teste');
        await p.selectOption('#manual-service', '1'); await p.selectOption('#manual-barber', '9');
        await p.fill('#manual-date', '2026-11-10T14:00');
        await p.locator('#manual-appointment-form [type=submit]').click();
        await p.locator('#manual-message .alert-success').waitFor();
        check(state.calls.some(c => c.path === '/admin/agendamentos' && c.method === 'POST' && c.body.nome_cliente === 'Cliente avulso de teste'), 'manual booking retains existing contract');
        await p.evaluate(() => { location.hash = 'servicos'; });
        await p.locator('[data-service-edit="1"]').click();
        check(await p.locator('#service-form').isVisible() && await p.locator('#service-form').getAttribute('data-mode') === 'edit', 'edit opens correct service form');
        await p.click('#service-cancel-edit');
        check(!await p.locator('#service-form').isVisible(), 'cancel editing closes service editor');
        await p.locator('#servicos summary').click();
        await p.fill('#service-name', 'Serviço de teste'); await p.fill('#service-price', '45'); await p.fill('#service-duration', '30');
        state.serviceFailure = true;
        await p.locator('#service-form [type=submit]').click();
        await p.locator('#services-admin-list .alert-danger').waitFor();
        check(await p.locator('#service-name').inputValue() === 'Serviço de teste', 'service error retains form values');
        state.serviceFailure = false;
        await p.locator('#service-form [type=submit]').click();
        await p.locator('#services-admin-list .alert-success').waitFor();
        check(state.calls.some(c => c.path === '/services/' && c.method === 'POST'), 'new service uses existing endpoint');
        await p.evaluate(() => { location.hash = 'jornadas'; });
        await p.selectOption('#schedule-barber', '10');
        await p.locator('[data-schedule-edit]').click();
        check(await p.locator('#schedule-barber').isDisabled(), 'editing weekly hours locks professional');
        await p.fill('#schedule-end', '17:00');
        state.scheduleFailure = true;
        await p.locator('#schedule-form [type=submit]').click();
        await p.locator('#schedules-list .alert-danger').waitFor();
        check(await p.locator('#schedule-end').inputValue() === '17:00', 'hours error retains edits');
        state.scheduleFailure = false;
        await p.locator('#schedule-form [type=submit]').click();
        await p.waitForFunction(() => !document.querySelector('#schedule-barber').disabled);
        check(await p.locator('#schedule-barber').inputValue() === '10', 'saving hours retains selected professional');
        check(state.calls.some(c => c.method === 'PUT' && c.path === '/horario/jornadas/1' && c.body.barbeiro_id === 10), 'external form-associated selector included in payload');
        await p.selectOption('#block-barber', '10');
        await p.locator('[data-block-edit]').click();
        await p.locator('#block-form [type=submit]').click();
        await p.waitForFunction(() => !document.querySelector('#block-barber').disabled);
        check(await p.locator('#block-barber').inputValue() === '10', 'saving leave retains professional');
        await shot(p, 'hours-mobile');
        await p.evaluate(() => { location.hash = 'financeiro'; });
        await p.locator('[data-finance-period=week]').click();
        await p.locator('.finance-metric').first().waitFor();
        check(state.calls.some(c => c.path === '/admin/relatorio'), 'quick financial range uses existing report');
        await p.evaluate(() => { location.hash = 'clientes'; });
        check(await p.locator('#clients-list img').count() === 0 && await p.evaluate(() => !window.xss), 'customer markup remains text');
        await p.goBack();
        await p.locator('#financeiro').waitFor();
        check(await p.locator('#financeiro').isVisible(), 'browser Back restores previous task');
        await p.reload(); await p.waitForFunction(() => document.body.dataset.staffReady === 'true');
        check(await p.locator('#financeiro').isVisible(), 'reload preserves current task');
      } else {
        for (const hash of ['servicos', 'agendamento-manual', 'auditoria']) {
          await p.evaluate(hash => { location.hash = hash; }, hash);
          await p.waitForFunction(() => location.hash === '#agenda');
          check(await p.locator('.admin-only:visible').count() === 0, `barber hash ${hash} cannot expose administrative sections`);
        }
        check(!state.calls.some(c => ['/users/', '/admin/agenda', '/admin/relatorio', '/admin/auditoria'].includes(c.path)), 'barber has no administrative API requests');
      }
    }
  } catch (error) { errors.push(error.stack || error.message); }
  finally { for (const ctx of contexts) await ctx.close(); }
  check(errors.length === 0, 'no JavaScript or runner errors'); check(unexpected.length === 0, 'local and declared requests only');
  return { total: checks.length, passed: checks.filter(c => c.ok).length, failures: checks.filter(c => !c.ok), errors, unexpected, screenshots };
}
