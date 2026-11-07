// Reusable with any existing Playwright Page. Start booking-smart-server.py first.
export default async function verifyBooking(page) {
  const base = "http://127.0.0.1:4186";
  let checks = 0;
  const check = (ok, name) => { if (!ok) throw new Error(name); checks += 1; };
  async function login(email, destination = "**/client-dashboard.html") {
    await page.goto(base + "/pages/login.html");
    await page.getByLabel("E-mail").fill(email);
    await page.getByLabel("Senha", { exact: true }).fill("Booking-Test-Only-2026!");
    await page.getByRole("button", { name: "Entrar na minha conta" }).click();
    await page.waitForURL(destination);
  }
  await login("smart@example.com");
  check(page.url().endsWith("client-dashboard.html"), "real login");
  await page.goto(base + "/pages/client-date.html?service_id=1&barbeiro_id=2");
  await page.locator(".booking-day").first().waitFor();
  check(await page.locator(".booking-day").count() === 15, "bounded calendar");
  check(await page.locator('.booking-day[data-status="off"]:disabled').count() > 0, "days off disabled");
  check(await page.locator('.booking-day[data-status="blocked"]:disabled').count() > 0, "holiday disabled");
  check(await page.locator('#booking-service option').first().textContent().then(t => t.includes("<img")), "service literal text");
  check(await page.locator('#booking-barber option').first().textContent().then(t => t.includes("<img")), "professional literal text");
  check(await page.locator("#booking-calendar img, #booking-service img, #booking-barber img").count() === 0, "no injected markup");
  const full = page.locator('.booking-day[data-status="full"]').first();
  check(await full.isEnabled(), "working but full selectable for alternatives");
  const fullDay = await full.getAttribute("data-date");
  await full.click();
  await page.locator("[data-suggestion]").first().waitFor();
  const suggestions = await page.locator("[data-suggestion]").count();
  check(suggestions > 0 && suggestions <= 3, "at most three real suggestions");
  const suggestedDay = await page.locator("[data-suggestion]").first().getAttribute("data-suggestion");
  check(suggestedDay > fullDay, "suggestions are subsequent dates");
  await page.locator("[data-suggestion]").first().click();
  await page.locator(".slot-button").first().waitFor();
  check(await page.locator("#date-input").inputValue() === suggestedDay, "suggestion updates date");
  check(await page.locator(".slot-button").count() === 6, "short service duration respected");
  await page.selectOption("#booking-service", "2");
  await page.waitForFunction(() => document.querySelector("#booking-calendar").getAttribute("aria-busy") === "false");
  check(await page.locator("#date-input").inputValue() === "", "service change clears selection");
  await page.locator(`[data-date="${suggestedDay}"]`).click();
  await page.locator(".slot-button").first().waitFor();
  check(await page.locator(".slot-button").count() === 1, "long service occupies whole shift");
  await page.selectOption("#booking-barber", "3");
  await page.waitForFunction(() => document.querySelector("#booking-calendar").getAttribute("aria-busy") === "false");
  check(await page.locator("#date-input").inputValue() === "", "professional change clears date");
  check(await page.locator(`[data-date="${suggestedDay}"]`).isDisabled(), "previous date is off for other professional");
  await page.selectOption("#booking-service", "1");
  await page.waitForFunction(() => document.querySelector("#booking-calendar").getAttribute("aria-busy") === "false");
  await page.selectOption("#booking-barber", "2");
  await page.waitForFunction(() => document.querySelector("#booking-calendar").getAttribute("aria-busy") === "false");

  // Real HTTP requests, deliberately delivered in reverse order.
  let release, captured;
  const gotRoute = new Promise(resolve => { captured = resolve; });
  await page.route("**/appointments/calendario?**", async route => {
    captured();
    await new Promise(resolve => { release = resolve; });
    await route.continue();
  }, { times: 1 });
  await page.selectOption("#booking-service", "2");
  await gotRoute;
  await page.selectOption("#booking-service", "1");
  await page.waitForFunction(() => document.querySelectorAll(".booking-day").length === 15);
  release();
  await page.locator(`[data-date="${suggestedDay}"]`).click();
  await page.locator(".slot-button").first().waitFor();
  check(await page.locator(".slot-button").count() === 6, "stale service response ignored");
  await page.route("**/appointments/calendario?**", route => route.fulfill({ status: 503, json: { detail: "Consulta indisponível" } }), { times: 1 });
  await page.getByRole("button", { name: "Atualizar disponibilidade" }).click();
  await page.waitForFunction(() => document.querySelector("#booking-calendar").getAttribute("aria-busy") === "false");
  check(await page.locator(".slot-button").count() === 0, "failure clears stale slots");
  await page.getByRole("button", { name: "Atualizar disponibilidade" }).click();
  await page.locator(".booking-day").first().waitFor();
  check(await page.locator(".booking-day").count() === 15, "retry recovers");

  await page.goto(base + "/pages/client-services.html");
  await page.locator(".service-selection-card").first().waitFor();
  check(await page.locator(".service-selection-card").first().innerText().then(t => t.includes("<script>")), "description literal text");
  check(await page.locator(".service-selection-card img, .service-selection-card script").count() === 0, "catalog has no payload elements");
  await page.goto(base + "/pages/index.html");
  await page.waitForFunction(() => document.querySelector("#reviews-list")?.textContent.includes("<img") ||
    [...document.querySelectorAll(".review-card")].some(n => n.textContent.includes("<img")));
  check(await page.locator(".review-card img").count() === 0, "review remains text");
  check(await page.evaluate(() => !window.__xss), "no payload executed");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base + "/pages/client-date.html?service_id=1&barbeiro_id=2");
  await page.locator(".booking-day").first().waitFor();
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), "mobile no horizontal overflow");
  await page.locator('.booking-day[data-status="available"]').first().focus();
  await page.keyboard.press("Enter");
  await page.locator(".slot-button").first().waitFor();
  check(await page.locator('.booking-day[aria-pressed="true"]').count() === 1, "keyboard date selection");
  await page.route("**/informacoes/", route => route.fulfill({ json: {
    endereco: '<img src=x onerror="window.__xss=5">', telefone: "(11) 99999-0000",
    dias_atendimento: "Todos os dias", horario_funcionamento: "<svg onload=alert(1)>",
  } }));
  await page.goto(base + "/pages/index.html");
  await page.waitForFunction(() => document.querySelector("#address").textContent.includes("<img"));
  check(await page.locator("#address img, #mon svg").count() === 0, "institutional data literal text");
  await page.unroute("**/informacoes/");
  await login("admin@example.com", "**/admin.html");
  await page.waitForFunction(() => document.querySelector("#services-admin-list").textContent.includes("<img"));
  check(await page.locator("#services-admin-list img, #services-admin-list script").count() === 0, "admin service safe");
  await page.waitForFunction(() => document.querySelector("#clients-list").textContent.includes("<svg"));
  check(await page.locator("#clients-list svg").count() === 0, "admin client safe");
  check(await page.evaluate(() => !window.__xss), "no admin payload executed");
  return { chromium: page.context().browser().version(), checks };
}
