// Run with Chromium against home-experience-setup.mjs (port 4186).
// API fixtures only: this verifies the frontend, not backend/security in production.
async (page, options = {}) => {
  const base = options.baseURL || "http://127.0.0.1:4186";
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw new Error("Local isolated server required");
  const browser = page.context().browser();
  const checks = [];
  const errors = [];
  const unexpected = [];
  const screenshots = [];
  const layoutDiagnostics = [];
  const check = (ok, name) => checks.push({ name, ok: Boolean(ok) });
  const now = new Date();
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo", year: "numeric", month: "2-digit", day: "2-digit" }).format(now);
  const day = n => new Date(new Date(today + "T12:00:00Z").getTime() + n * 86400000).toISOString().slice(0, 10);
  const slots = n => ["10:00", "14:30", "16:00"].map(h => ({ horario: h, data_hora: `${day(n)}T${h}:00` }));
  const services = [
    { id: 1, nome: "Corte clássico", descricao: "Um corte preciso, do seu jeito.", preco: 55, duracao_minutos: 40 },
    { id: 2, nome: "Barba & acabamento", descricao: "Desenho, alinhamento e cuidado.", preco: 40, duracao_minutos: 30 },
    { id: 3, nome: "Corte e barba", descricao: "O ritual completo, sem pressa.", preco: 85, duracao_minutos: 75 },
  ];
  const professionals = [{ barbeiro_id: 9, barbeiro_nome: "Lucas · teste" }, { barbeiro_id: 10, barbeiro_nome: "Rafael · teste" }];
  const appointments = [
    { id: 71, user_id: 5, service_id: 1, barbeiro_id: 9, data_hora: slots(3)[0].data_hora, status: "confirmado", preco: 55, duracao_minutos: 40 },
    { id: 72, user_id: 5, service_id: 2, barbeiro_id: 10, data_hora: day(-2) + "T14:00:00", status: "concluido", preco: 40, duracao_minutos: 30 },
  ];
  const contexts = [];
  async function session({ width = 1440, role = "cliente", signedIn = true, reducedMotion = "reduce" } = {}) {
    const context = await browser.newContext({ viewport: { width, height: width < 720 ? 844 : 1000 }, reducedMotion, isMobile: width < 720, hasTouch: width < 720 });
    contexts.push(context);
    const state = { role, calls: [], bookingFailures: 0, loginFailure: false, calendarFailure: false, emptyAppointments: false, unsafeService: false };
    const user = { id: 5, nome: "Alex · teste", email: "alex@example.test", role };
    await context.addInitScript(({ base, signedIn, user }) => {
      window.BARBEARIA_API_URL = base + "/__fixtures";
      if (signedIn && !sessionStorage.getItem('product-fixture-seeded')) {
        localStorage.setItem("token", "local-ui-fixture");
        localStorage.setItem("user", JSON.stringify(user));
        sessionStorage.setItem('product-fixture-seeded', 'true');
      }
    }, { base, signedIn, user });
    await context.route("**/*", async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin !== base) { unexpected.push(url.origin); return route.abort(); }
      if (!url.pathname.startsWith("/__fixtures")) return route.continue();
      const path = url.pathname.replace("/__fixtures", "");
      const method = request.method();
      state.calls.push({ path, method, query: url.search, body: request.postDataJSON() });
      const reply = (body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
      if (path === "/auth/login") return state.loginFailure ? reply({ detail: "E-mail ou senha incorretos." }, 401) : reply({ access_token: "local-ui-fixture", user });
      if (path === "/auth/me") return reply(user);
      if (path === "/auth/esqueci-senha") return reply({ mensagem: "Se o e-mail estiver cadastrado, as instruções serão enviadas." });
      if (path.startsWith("/auth/")) return reply({ mensagem: "Solicitação concluída." });
      if (path === "/services/") return reply(state.unsafeService ? [{ ...services[0], nome: '<img src=x onerror="window.xss=1">', descricao: '<script>window.xss=1</script>' }] : services);
      if (/^\/services\/\d+$/.test(path)) return reply(services.find(s => s.id === Number(path.split("/").pop())) || services[0]);
      if (/^\/barbeiro-servico\/servico\//.test(path)) return reply(professionals);
      if (path === "/appointments/calendario") {
        if (state.calendarFailure) return reply({ detail: "Não foi possível consultar a agenda. Tente atualizar." }, 503);
        return reply({ days: Array.from({ length: 12 }, (_, i) => {
          const n = i + 1;
          const status = n === 1 ? "off" : n === 2 ? "full" : n === 5 ? "blocked" : "available";
          return { date: day(n), status, slots: status === "available" ? slots(n) : [] };
        }) });
      }
      if (path === "/appointments/disponiveis") {
        const n = Math.round((new Date(url.searchParams.get("data") + "T12:00:00Z") - new Date(today + "T12:00:00Z")) / 86400000);
        return reply(n === 2 ? [] : slots(n));
      }
      if (path === "/appointments/" && method === "GET") return reply(state.emptyAppointments ? [] : appointments);
      if (path === "/appointments/" && method === "POST") {
        await new Promise(resolve => setTimeout(resolve, 150));
        if (state.bookingFailures-- > 0) return reply({ detail: "Agenda temporariamente indisponível. Tente novamente." }, 503);
        return reply({ ...appointments[0], id: 73 }, 201);
      }
      if (/^\/appointments\/\d+$/.test(path)) return reply(appointments.find(a => a.id === Number(path.split("/").pop())) || appointments[0]);
      if (path.endsWith("/avaliacao")) return reply({ id: 1 }, 201);
      if (path === "/users/barbeiros") return reply(professionals.map(p => ({ id: p.barbeiro_id, nome: p.barbeiro_nome, role: "barbeiro" })));
      if (path === "/users/") return reply([user]);
      if (path === "/informacoes/") return reply({ nome: "Barbearia · demonstração local", endereco: "Dados fictícios para teste" });
      if (path === "/admin/agenda" || path === "/admin/me/agenda") return reply(appointments);
      if (path === "/admin/auditoria") return reply([]);
      if (/^\/(horario|barbeiro-servico)\//.test(path) || path === "/admin/avaliacoes") return reply([]);
      unexpected.push(`${method} ${path}`);
      return reply({ detail: "Fixture missing" }, 404);
    });
    const p = await context.newPage();
    p.setDefaultTimeout(5000);
    p.on("pageerror", error => errors.push(error.message));
    return { p, context, state };
  }
  async function goto(p, name) { await p.goto(`${base}/pages/${name}`); await p.evaluate(() => document.fonts.ready); }
  async function shot(p, name) {
    if (!options.screenshotDir) return;
    const path = `${options.screenshotDir}/product-${name}.png`;
    await p.screenshot({ path, fullPage: !name.startsWith("admin") }); screenshots.push(path);
  }
  async function layout(p, name) {
    const info = await p.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
      h1: document.querySelectorAll("h1").length,
      main: !!document.querySelector("main#main-content"),
      font: getComputedStyle(document.body).fontFamily,
      missingLabels: [...document.querySelectorAll('input:not([type=hidden]), select, textarea')].filter(el => !el.labels?.length && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')).map(el => el.id),
    }));
    check(!info.overflow, `${name}: no horizontal overflow`);
    if (info.overflow) layoutDiagnostics.push({ name, elements: await p.evaluate(() => [...document.querySelectorAll('main *, header *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1 && !el.closest('.agenda-table-wrapper, .date-roll, .admin-nav')).slice(0, 12).map(el => ({ tag: el.tagName, id: el.id, className: el.className, width: el.getBoundingClientRect().width }))) });
    check(info.h1 === 1 && info.main && info.font.includes("HomeSpace"), `${name}: heading, skip target and typography`);
    check(info.missingLabels.length === 0, `${name}: controls have labels (${info.missingLabels.join(',')})`);
  }
  try {
    const desktop = await session();
    const p = desktop.p;
    const confirm = `client-confirm.html?service_id=1&barbeiro_id=9&date_time=${encodeURIComponent(slots(3)[0].data_hora)}`;
    const pages = ["login.html", "cadastro.html", "forgot.html", "reset.html", "catalog.html", "client-services.html", "client-profissional.html?service_id=1", "client-date.html?service_id=1&barbeiro_id=9", confirm, "client-dashboard.html", "client-appointments.html", "client-account.html", "client-evaluate.html?appointment_id=72"];
    for (const width of [1440, 390, 320]) {
      await p.setViewportSize({ width, height: width < 720 ? 844 : 1000 });
      for (const name of pages) {
        await goto(p, name);
        if (name.startsWith("client-date")) await p.locator(".booking-day").first().waitFor();
        if (name.startsWith("client-appointments")) await p.locator(".appointment-card").first().waitFor();
        if (name.startsWith("client-account")) await p.locator("#account-content").getByText("Alex · teste", { exact: false }).waitFor();
        if (name.startsWith("client-services") || name.startsWith("catalog")) await p.locator(".service-selection-card").first().waitFor();
        await layout(p, `${width}/${name.split('?')[0]}`);
        if (name === 'client-dashboard.html') {
          check(await p.locator('.dashboard-card:first-child h2').evaluate(el => getComputedStyle(el).color === 'rgb(48, 39, 29)'), `${width}: booking heading uses contrasting ink on paper`);
        }
        if (width !== 320 && /^(login|client-date|client-dashboard|client-appointments|client-account)\./.test(name)) await shot(p, `${name.split('.')[0]}-${width}`);
      }
    }
    await p.setViewportSize({ width: 390, height: 844 });
    await goto(p, "client-services.html");
    check(await p.locator('.booking-progress [aria-current=step]').count() === 1, "service step marked current");
    await p.locator(".service-selection-card .btn").first().click();
    await p.locator(".professional-card .btn").first().click();
    await p.locator(".booking-day").first().waitFor();
    check(await p.locator('[data-status=off]').first().isDisabled(), "off day disabled");
    check(await p.locator('[data-status=blocked]').first().isDisabled(), "blocked day disabled");
    await p.locator('[data-status=full]').click();
    await p.locator("[data-suggestion]").first().waitFor();
    check(await p.locator("[data-suggestion]").count() === 3, "full day has three real fixture suggestions");
    await p.locator("[data-suggestion]").first().click();
    await p.locator(".slot-button").first().waitFor();
    check(await p.locator('[aria-pressed=true].booking-day').count() === 1, "suggestion selects one calendar day");
    await p.selectOption("#booking-barber", "10");
    await p.waitForFunction(() => document.querySelector('#booking-calendar').getAttribute('aria-busy') === 'false');
    check(await p.locator('[aria-pressed=true].booking-day').count() === 0, "professional change clears previous day");
    await p.selectOption("#booking-service", "3");
    await p.waitForFunction(() => location.search.includes('service_id=3') && document.querySelector('#booking-calendar').getAttribute('aria-busy') === 'false');
    check((await p.locator('.booking-progress a').last().getAttribute('href')).includes('service_id=3'), "progress back link tracks changed service");
    check(desktop.state.calls.some(c => c.path === '/appointments/calendario' && c.query.includes('service_id=3')), "long service reloads real availability endpoint");
    await p.locator('[data-status=available]').first().click();
    await p.locator(".slot-button").first().click();
    await p.locator('#confirmation-content').getByText('Corte e barba', { exact: false }).waitFor();
    check((await p.locator('[data-booking-back]').getAttribute('href')).includes('service_id=3&barbeiro_id=10'), "review back preserves chosen context");

    // Regression: a failed submission must allow an intentional second attempt.
    desktop.state.bookingFailures = 1;
    await p.click('#confirm-btn');
    check(await p.locator('#confirm-btn').isDisabled(), "confirmation disables during request");
    await p.locator('#confirmation-content .alert-danger').waitFor();
    check(!await p.locator('#confirm-btn').isDisabled(), "confirmation re-enabled after failure");
    await p.click('#confirm-btn');
    await p.waitForURL('**/client-appointments.html', { timeout: 2500 }).catch(() => {});
    check(p.url().endsWith('client-appointments.html'), "confirmation retry succeeds after failure");
    check(desktop.state.calls.filter(c => c.path === '/appointments/' && c.method === 'POST').length === 2, "only one POST per confirmation attempt");

    await goto(p, confirm + '&appointment_id=71');
    check(await p.locator('.booking-progress a').count() === 1, "reschedule locks service/professional steps");
    await p.click('[data-booking-back]');
    await p.locator('.booking-day').first().waitFor();
    check(p.url().includes('appointment_id=71'), "review back retains reschedule ID");
    check(await p.locator('#booking-service').isDisabled() && await p.locator('#booking-barber').isDisabled(), "reschedule choices remain locked");
    check(await p.locator('#change-professional').getAttribute('href') === 'client-appointments.html', "reschedule header returns to reservations");

    desktop.state.calendarFailure = true;
    await goto(p, 'client-date.html?service_id=1&barbeiro_id=9');
    await p.locator('#calendar-status').getByText('Não foi possível', { exact: false }).waitFor();
    check(await p.locator('.booking-day').count() === 0, "failed availability displays no fake dates");
    desktop.state.calendarFailure = false;
    await p.click('#calendar-retry');
    await p.locator('.booking-day').first().waitFor();
    check(await p.locator('.booking-day').count() === 12, "availability retry restores calendar");

    desktop.state.unsafeService = true;
    await goto(p, 'client-services.html');
    await p.locator('.service-selection-card').first().waitFor();
    check(await p.locator('.service-selection-card img, .service-selection-card script').count() === 0 && await p.evaluate(() => !window.xss), "untrusted service content stays text");
    desktop.state.unsafeService = false;
    desktop.state.emptyAppointments = true;
    await goto(p, 'client-appointments.html');
    await p.getByText('Você ainda não tem agendamentos.').waitFor();
    check(await p.getByRole('link', { name: 'Agendar um horário', exact: true }).isVisible(), "empty appointments has booking action");
    await goto(p, 'client-account.html');
    await p.click('#delete-account');
    check(await p.locator('#delete-dialog').isVisible(), "privacy confirmation opens");
    await p.keyboard.press('Escape');
    check(!await p.locator('#delete-dialog').isVisible(), "privacy dialog closes with Escape");
    check(!desktop.state.calls.some(c => c.method === 'DELETE'), "dialog dismissal never deletes data");
    await goto(p, 'client-evaluate.html?appointment_id=72');
    await p.locator('#evaluate-content').getByText('Avalie o atendimento', { exact: false }).waitFor();
    await p.selectOption('#eval-nota', '5');
    await p.fill('#eval-comentario', 'Avaliação fictícia de interface.');
    await p.locator('#evaluate-form [type=submit]').click();
    await p.waitForURL('**/client-appointments.html');
    check(desktop.state.calls.some(c => c.path === '/appointments/72/avaliacao' && c.body.nota === 5), "evaluation form keeps existing contract");
    await goto(p, confirm + '&appointment_id=71');
    await p.locator('#confirm-btn:not([disabled])').waitFor();
    check(await p.locator('#confirm-btn').textContent() === 'Confirmar novo horário', "reschedule has explicit confirmation label");
    await p.click('#confirm-btn');
    await p.waitForURL('**/client-appointments.html');
    check(desktop.state.calls.some(c => c.path === '/appointments/71' && c.method === 'PUT' && c.body.data_hora === slots(3)[0].data_hora && !('service_id' in c.body)), "reschedule only changes time through existing endpoint");
    await p.click('#logout-link');
    await p.waitForURL('**/login.html');
    check(await p.evaluate(() => !localStorage.getItem('token')) && desktop.state.calls.some(c => c.path === '/auth/logout'), "logout revokes through API and clears local access token");

    const guest = await session({ signedIn: false, width: 390 });
    await goto(guest.p, 'login.html?redirect=client-date.html%3Fservice_id%3D1%26barbeiro_id%3D9');
    await guest.p.keyboard.press('Tab');
    check(await guest.p.locator('.product-skip-link').evaluate(el => el === document.activeElement), "skip link is first keyboard target");
    await guest.p.keyboard.press('Enter');
    check(await guest.p.locator('main').evaluate(el => el === document.activeElement), "skip link focuses main");
    await guest.p.fill('#login-email', 'alex@example.test');
    await guest.p.fill('#login-password', 'local-ui-only');
    await guest.p.getByRole('button', { name: 'Mostrar senha' }).click();
    check(await guest.p.locator('#login-password').getAttribute('type') === 'text', "password visibility retained");
    guest.state.loginFailure = true;
    await guest.p.locator('#login-form [type=submit]').click();
    await guest.p.locator('#form-message:not([hidden])').waitFor();
    check(await guest.p.locator('#form-message').evaluate(el => el === document.activeElement), "login error focuses message");
    guest.state.loginFailure = false;
    await guest.p.locator('#login-form [type=submit]').click();
    await guest.p.waitForURL('**/client-date.html?**');
    check(guest.p.url().includes('service_id=1') && guest.p.url().includes('barbeiro_id=9'), "login preserves booking redirect");
    await goto(guest.p, 'reset.html');
    await guest.p.fill('#reset-password', 'local-ui-only');
    await guest.p.locator('#reset-form [type=submit]').click();
    await guest.p.getByText('O link de redefinição está incompleto. Solicite um novo link.').waitFor();
    check(!guest.state.calls.some(c => c.path === '/auth/redefinir-senha'), "missing reset token causes no request");
    await goto(guest.p, 'forgot.html');
    await guest.p.fill('#forgot-email', 'alex@example.test');
    await guest.p.locator('#forgot-form [type=submit]').click();
    await guest.p.locator('.alert-success').waitFor();
    check(await guest.p.locator('.alert-success').isVisible(), "recovery keeps neutral feedback");
    check(await guest.p.locator('.btn').first().evaluate(el => getComputedStyle(el).transitionDuration === '0s'), "reduced motion suppresses transitions");
    await goto(guest.p, 'cadastro.html');
    await guest.p.fill('#register-name', 'Cliente fictício');
    await guest.p.fill('#register-email', 'cliente@example.test');
    await guest.p.fill('#register-password', 'local-ui-only');
    await guest.p.locator('#register-form [type=submit]').click();
    check(!guest.state.calls.some(c => c.path === '/auth/register'), "registration requires existing consent checkbox");
    await guest.p.locator('[name=consentimento_lgpd]').check();
    await guest.p.locator('#register-form [type=submit]').click();
    await guest.p.waitForURL('**/login.html');
    check(guest.state.calls.some(c => c.path === '/auth/register' && c.body.consentimento_lgpd === true), "registration submits consent and returns to login");
    await goto(guest.p, 'reset.html#token=local-reset-fixture');
    await guest.p.fill('#reset-password', 'local-ui-only');
    await guest.p.locator('#reset-form [type=submit]').click();
    await guest.p.locator('.alert-success').waitFor();
    const reset = guest.state.calls.find(c => c.path === '/auth/redefinir-senha');
    check(reset?.body.token === 'local-reset-fixture' && !reset.query, "reset token travels in request body, never query");
    await goto(guest.p, 'client-date.html?service_id=1&barbeiro_id=9');
    await guest.p.locator('[data-status=available]').first().tap();
    await guest.p.locator('.slot-button').first().waitFor();
    check(await guest.p.locator('[aria-pressed=true].booking-day').count() === 1, "touch selection loads times on mobile");

    for (const role of ['admin', 'barbeiro']) {
      const admin = await session({ role });
      for (const width of [1440, 390, 320]) {
        await admin.p.setViewportSize({ width, height: 1000 });
        await goto(admin.p, 'admin.html');
        await admin.p.locator('#userName').getByText('Alex · teste').waitFor();
        await admin.p.locator('.agenda-table').waitFor();
        await layout(admin.p, `${role}/${width}`);
        check(await admin.p.locator('.date-item.selected').evaluate(el => {
          const rail = el.closest('.date-roll').getBoundingClientRect(); const rect = el.getBoundingClientRect();
          return rect.left >= rail.left - 1 && rect.right <= rail.right + 1;
        }), `${role}/${width}: selected day visible in rail`);
        if (width < 720) check(await admin.p.locator('.agenda-row').first().evaluate(el => el.getBoundingClientRect().right <= innerWidth), `${role}/${width}: appointment actions contained on mobile`);
        if (width < 720) check(await admin.p.locator('.agenda-header').evaluate(el => {
          const title = el.querySelector('h2').getBoundingClientRect(); const date = el.querySelector('.agenda-day-label').getBoundingClientRect();
          return title.bottom <= date.top + 1;
        }), `${role}/${width}: date does not overlap agenda heading`);
        if (role === 'admin' && width !== 320) await shot(admin.p, `admin-${width}`);
        if (role === 'barbeiro') check(await admin.p.locator('.admin-only:visible, [data-admin-only]:visible').count() === 0, `barber ${width}: admin sections remain hidden`);
      }
      if (role === 'admin') {
        await admin.p.locator('a[href="#servicos"]').click();
        await admin.p.locator('[data-service-edit="1"]').click();
        check(await admin.p.locator('#service-name').inputValue() === 'Corte clássico', "admin service edit fills existing form");
        await admin.p.click('#service-cancel-edit');
        check(await admin.p.locator('#service-name').inputValue() === '', "admin cancel edit restores form");
      } else check(!admin.state.calls.some(c => c.path === '/users/' || c.path === '/admin/agenda'), "barber uses restricted agenda endpoint");
    }
  } catch (error) { errors.push(error.stack || error.message); }
  finally { for (const context of contexts) await context.close(); }
  check(errors.length === 0, 'no JavaScript or runner errors');
  check(unexpected.length === 0, 'only local static resources and declared API fixtures');
  return { total: checks.length, passed: checks.filter(c => c.ok).length, failures: checks.filter(c => !c.ok), errors, unexpected, layoutDiagnostics, screenshots };
}
