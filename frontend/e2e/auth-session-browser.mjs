// Real Chromium regression. Run against auth-session-server.py with a disposable fixture DB.
export async function runAuthSessionChecks(browser, base = "https://127.0.0.1:4197", evil = "https://127.0.0.1:4198") {
  const results = [];
  const check = (value, name) => { if (!value) throw new Error(name); results.push({ name, passed: true }); };
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCookieControls", { enableThirdPartyCookieRestriction: true, disableThirdPartyCookieMetadata: true, disableThirdPartyCookieHeuristics: true });
  const statuses = [];
  page.on("response", response => { if (/\/auth\/(login|refresh|logout|me)$/.test(new URL(response.url()).pathname)) statuses.push({ path: new URL(response.url()).pathname, status: response.status() }); });
  const login = async () => {
    await page.goto(`${base}/pages/login.html`);
    await page.locator('#login-email').fill('browser-f1@example.com');
    await page.locator('#login-password').fill('fixture-browser-password');
    await Promise.all([page.waitForURL('**/client-dashboard.html'), page.getByRole('button', { name: 'Entrar na minha conta' }).click()]);
  };
  const expire = () => page.evaluate(async () => {
    const data = await (await fetch('/__qa__/expired-access')).json();
    localStorage.setItem('token', data.access_token);
  });
  const state = async () => (await context.request.get(`${base}/__qa__/state`)).json();
  try {
    await context.request.post(`${base}/__qa__/revoke-fixture-sessions`);
    await login();
    check(await page.title() !== '', 'real frontend login and dashboard');
    let cookie = (await context.cookies(`${base}/auth`)).find(c => c.name === 'refresh_token');
    check(cookie && cookie.secure && cookie.httpOnly && cookie.sameSite === 'Lax' && cookie.path === '/auth' && cookie.domain === '127.0.0.1', 'secure host-only HttpOnly Lax cookie persisted');
    check(!(await page.evaluate(() => document.cookie)).includes('refresh_token'), 'refresh unavailable to JavaScript');
    const initial = cookie.value;
    await expire();
    const first = await page.evaluate(async () => (await (await import('/assets/js/api.js')).api.get('/auth/me')).id);
    check(Number.isInteger(first), 'expired signed JWT causes refresh then successful retry');
    cookie = (await context.cookies(`${base}/auth`)).find(c => c.name === 'refresh_token');
    check(cookie.value !== initial, 'refresh rotates cookie');
    await expire();
    const beforeRefresh = statuses.filter(s => s.path === '/auth/refresh').length;
    const ids = await page.evaluate(async () => {
      const { api } = await import('/assets/js/api.js');
      return Promise.all(Array.from({ length: 3 }, () => api.get('/auth/me').then(user => user.id)));
    });
    check(ids.every(id => id === first), 'three simultaneous requests recover correctly');
    check(statuses.filter(s => s.path === '/auth/refresh').length - beforeRefresh === 1, 'refresh is single-flight per page');
    const beforeCsrf = await state();
    const foreign = await context.newPage();
    await foreign.goto(evil);
    const foreignNetwork = await context.newCDPSession(foreign);
    await foreignNetwork.send('Network.enable');
    const rejected = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('No browser network 403 observed')), 6000);
      foreignNetwork.on('Network.responseReceivedExtraInfo', event => {
        if (event.statusCode === 403) { clearTimeout(timeout); resolve(event.headers); }
      });
    });
    const corsBlocked = await foreign.evaluate(async target => { try { await fetch(target + '/auth/refresh', { method: 'POST', credentials: 'include' }); return false; } catch { return true; } }, base);
    const rejectHeaders = await rejected;
    check(corsBlocked && !Object.keys(rejectHeaders).some(k => k.toLowerCase() === 'access-control-allow-origin'), 'foreign browser origin has no credentialed CORS grant; real HTTP 403');
    check(JSON.stringify(await state()) === JSON.stringify(beforeCsrf), 'same-site foreign-origin CSRF blocked without rotation');
    await foreign.close();
    const missingOrigin = await context.request.post(`${base}/auth/refresh`);
    check(missingOrigin.status() === 403, 'refresh without Origin rejected');
    const old = initial;
    const replay = await context.request.post(`${base}/auth/refresh`, { headers: { Origin: base, Cookie: `refresh_token=${old}` } });
    check(replay.status() === 401, 'reuse rejects old refresh');
    check((await state()).active === 0, 'reuse revokes active family');
    await login();
    const { active } = await state();
    check(active === 1, 'fresh login after revocation creates one active session');
    await page.locator('#logout-link').click();
    await page.waitForURL('**/login.html');
    check(!(await context.cookies(`${base}/auth`)).some(c => c.name === 'refresh_token'), 'logout clears cookie with matching scope');
    check((await state()).active === 0, 'logout revokes family');
    await page.evaluate(id => localStorage.setItem('user', JSON.stringify({ id, nome: 'Conta F1 Ficticia', role: 'cliente' })), first);
    await expire();
    await page.goto(`${base}/pages/client-dashboard.html`);
    await page.waitForURL('**/login.html?**');
    check(await page.evaluate(() => localStorage.getItem('token') === null), 'missing cookie after 401 clears session and returns to login');
    const legacyEntry = await context.newPage();
    await legacyEntry.goto(evil + '/pages/reset.html?source=email#token=fixture-fragment');
    await legacyEntry.waitForURL(base + '/pages/reset.html?source=email#token=fixture-fragment');
    check(await legacyEntry.locator('#reset-form').count() === 1, 'real legacy redirect preserves path, query and reset fragment into the canonical frontend');
    await legacyEntry.close();
    // Negative control: allowed CORS alone cannot make a cross-site Lax cookie work.
    const legacy = await browser.newContext({ ignoreHTTPSErrors: true });
    try {
      const legacyPage = await legacy.newPage();
      const network = await legacy.newCDPSession(legacyPage);
      const blocked = [];
      await network.send('Network.enable');
      await network.send('Network.setCookieControls', { enableThirdPartyCookieRestriction: true, disableThirdPartyCookieMetadata: true, disableThirdPartyCookieHeuristics: true });
      network.on('Network.responseReceivedExtraInfo', event => { for (const cookie of event.blockedCookies || []) blocked.push(...cookie.blockedReasons); });
      await legacyPage.goto(base.replace('127.0.0.1', 'localhost') + '/pages/login.html');
      const control = await legacyPage.evaluate(async target => {
        const login = await fetch(target + '/auth/login', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'browser-f1@example.com', senha: 'fixture-browser-password' }) });
        const refresh = await fetch(target + '/auth/refresh', { method: 'POST', credentials: 'include' });
        return { login: login.status, refresh: refresh.status };
      }, base);
      check(control.login === 200 && control.refresh === 401, 'cross-site negative control fails refresh despite allowed CORS');
      check(!(await legacy.cookies(`${base}/auth`)).some(c => c.name === 'refresh_token'), 'Chromium actually rejects third-party refresh cookie');
      results.push({ name: 'cookie rejection diagnostics', reasons: [...new Set(blocked)] });
    } finally { await legacy.close(); }
    await context.request.post(`${base}/__qa__/revoke-fixture-sessions`);
    const finalState = await state();
    check(finalState.active === 0, 'fixture ends with every session revoked');
    const runtime = await (await context.request.get(`${base}/__qa__/runtime`)).json();
    return { chromium: browser.version(), runtime, thirdPartyRestrictionEnabled: true, results, statuses, finalState };
  } finally { await context.close(); }
}
