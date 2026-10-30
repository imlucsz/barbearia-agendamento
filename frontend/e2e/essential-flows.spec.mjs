import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

const client = {
  email: "cliente.e2e@example.com",
  password: "E2E-Test-Client-Only-2026!",
};
const admin = {
  email: "admin.e2e@example.com",
  password: "E2E-Test-Admin-Only-2026!",
};
const mobileClient = {
  email: "cliente.mobile.e2e@example.com",
  password: "E2E-Test-Client-Only-2026!",
};
const barber = {
  email: "barbeiro.e2e@example.com",
  password: "E2E-Test-Barber-Only-2026!",
};
const bookingDate = process.env.PW_E2E_BOOKING_DATE;
const agendaDate = process.env.PW_E2E_AGENDA_DATE;

function clientForProject(testInfo) {
  return testInfo.project.name.startsWith("mobile") ? mobileClient : client;
}

function otherClientForProject(testInfo) {
  return testInfo.project.name.startsWith("mobile") ? client : mobileClient;
}

async function signIn(page, account) {
  await page.goto("/pages/login.html");
  await page.getByLabel("E-mail").fill(account.email);
  await page.getByLabel("Senha", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Entrar na minha conta" }).click();
}

async function chooseSlot(page) {
  await page.goto("/pages/client-services.html");
  const service = page.locator(".service-selection-card").filter({
    has: page.getByRole("heading", { name: "Corte E2E", exact: true }),
  });
  await expect(service).toHaveCount(1);
  await service.getByRole("link", { name: "Escolher profissional", exact: true }).click();
  const professional = page.locator(".professional-card").filter({
    has: page.getByRole("heading", { name: "Barbeiro E2E Fictício", exact: true }),
  });
  await expect(professional).toHaveCount(1);
  await professional.getByRole("link", { name: "Ver horários", exact: true }).click();
  await page.getByLabel("Selecione a data").fill(bookingDate);
  await expect(page.locator(".slot-button").first()).toBeVisible();
  return page.locator(".slot-button").first();
}

async function currentAppointmentCount(page) {
  await page.goto("/pages/client-appointments.html");
  await expect(page.locator("#appointments-list")).not.toContainText("Carregando");
  return page.locator(".appointment-card").count();
}

test.afterEach(async ({ page }, testInfo) => {
  if (!page.isClosed()) {
    await page.screenshot({ path: testInfo.outputPath("evidence.png"), fullPage: true }).catch(() => {});
  }
});

test("cadastro, login, refresh silencioso após sessão expirada e logout", async ({ page, context }) => {
  const email = `cadastro-${Date.now()}@example.com`;
  await page.goto("/pages/cadastro.html");
  await page.getByLabel("Nome completo").fill("Cliente Cadastro E2E");
  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel(/Senha/).fill("E2E-Registration-Only-2026!");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Criar minha conta" }).click();
  await expect(page.getByRole("alert")).toContainText("Cadastro realizado");
  await page.waitForURL(/login\.html$/);

  await page.getByLabel("E-mail").fill(email);
  await page.getByLabel("Senha", { exact: true }).fill("E2E-Registration-Only-2026!");
  await page.getByRole("button", { name: "Entrar na minha conta" }).click();
  await page.waitForURL(/client-dashboard\.html$/);
  const refreshCookie = (await context.cookies("http://127.0.0.1:4174/auth/refresh")).find((cookie) => cookie.name === "refresh_token");
  expect(refreshCookie?.httpOnly).toBe(true);

  await page.evaluate(() => {
    localStorage.setItem("token", "expired-e2e-token");
    localStorage.setItem("user", JSON.stringify({ role: "cliente" }));
  });
  await page.goto("/pages/client-appointments.html");
  await expect(page.locator("#appointments-list")).not.toContainText("Carregando");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("token"))).not.toBe("expired-e2e-token");
  await expect(page).toHaveURL(/client-appointments\.html$/);

  await page.getByRole("link", { name: "Sair" }).click();
  await page.waitForURL(/login\.html$/);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("token"))).toBeNull();
  await expect.poll(async () => (await context.cookies("http://127.0.0.1:4174/auth/refresh")).some((cookie) => cookie.name === "refresh_token")).toBe(false);
});

test("identidade configurada aparece nas páginas sem interpretar conteúdo como HTML", async ({ page }) => {
  const maliciousName = '<svg onload="window.__brandXss=true">';
  const imageFixture = await readFile(new URL("../assets/images/navalha-recortada.png", import.meta.url));
  await page.addInitScript(() => { window.__brandXss = false; });
  await page.route("**/assets/js/installation-config.mjs", (route) => route.fulfill({
    status: 200,
    contentType: "text/javascript",
    body: `export const INSTALLATION_CONFIG = Object.freeze(${JSON.stringify({
      apiBaseUrl: "http://127.0.0.1:4174",
      brand: { name: maliciousName, logoUrl: "../assets/branding/e2e-logo.png", themeColor: "#1677aa" },
    })});`,
  }));
  await page.route("**/assets/branding/e2e-logo.png", (route) => route.fulfill({
    status: 200,
    contentType: "image/png",
    body: imageFixture,
  }));

  for (const path of ["index.html", "login.html", "forgot.html", "client-services.html"]) {
    await page.goto(`/pages/${path}`);
    const names = page.locator(".brand-copy strong");
    await expect(names.first()).toHaveText(maliciousName);
    await expect(names).toHaveCount(path === "index.html" ? 2 : 1);
    await expect(page.locator(".brand-mark img").first()).toBeVisible();
    await expect(page.locator(".brand-copy svg")).toHaveCount(0);
    await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute("content", "#1677aa");
    expect(await page.title()).toContain(maliciousName);
    expect(await page.evaluate(() => window.__brandXss)).toBe(false);
    if (path === "index.html") {
      await expect(page.locator(".brand-lockup").first()).toHaveAttribute("aria-label", `${maliciousName} - início`);
      await expect(page.locator(".footer-inner > p")).toContainText(maliciousName);
    }
  }

  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  await expect(page.locator(".brand-copy strong")).toHaveText(maliciousName);
  await expect(page.locator(".brand-mark img").first()).toBeVisible();
  await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute("content", "#1677aa");

  await page.unroute("**/assets/js/installation-config.mjs");
  await page.unroute("**/assets/branding/e2e-logo.png");
  await page.goto("/pages/index.html");
  await expect(page.locator(".brand-copy strong").first()).toHaveText("Barbearia");
  await expect(page.locator(".brand-mark").first()).toHaveText("B.");
  await expect(page.locator(".brand-mark img")).toHaveCount(0);
  await expect(page).toHaveTitle("Barbearia Agendamento | Seu estilo, no seu horário");
});

test("nota média pública considera somente avaliações visíveis", async ({ page }) => {
  await page.route("**/appointments/avaliacoes", (route) => route.fulfill({ json: [
    { nota: 5, comentario: "Avaliação pública", oculta: false, criada_em: "2026-10-01T12:00:00" },
    { nota: 3, comentario: "Outra pública", oculta: false, criada_em: "2026-10-02T12:00:00" },
    { nota: 1, comentario: "Avaliação oculta", oculta: true, criada_em: "2026-10-03T12:00:00" },
  ] }));
  await page.goto("/pages/index.html");
  await expect(page.locator("#review-average")).toContainText("4.0 / 5 · 2 avaliações");
  await expect(page.locator("#reviews-list")).toContainText("Avaliação pública");
  await expect(page.locator("#reviews-list")).toContainText("Outra pública");
  await expect(page.locator("#reviews-list")).not.toContainText("Avaliação oculta");
});

test("Estrelinha pode ser desligada por instalação sem quebrar a home", async ({ page }) => {
  let requestedMascotModule = false;
  page.on("request", (request) => {
    if (request.url().includes("cdn.jsdelivr.net/npm/three")) requestedMascotModule = true;
  });
  await page.route("**/assets/js/installation-config.mjs", (route) => route.fulfill({
    status: 200,
    contentType: "text/javascript",
    body: `export const INSTALLATION_CONFIG = Object.freeze(${JSON.stringify({
      apiBaseUrl: "http://127.0.0.1:4174",
      brand: { name: "Barbearia Horizonte", mark: "BH.", tagline: "CORTE COM IDENTIDADE", logoUrl: "", themeColor: "#1677aa" },
      content: { homeHeroEyebrow: "Seu jeito, seu corte", homeHeroTitleLead: "Cuidado de", homeHeroTitleAccent: "verdade.", homeHeroDescription: "Texto desta instalação.", homePrimaryAction: "Ver horários", homeSecondaryAction: "Conheça os serviços", homeFooterMessage: "Uma casa de bairro.", consentText: "Texto próprio do aceite." },
      features: { estrelinhaWidget: false },
    })});`,
  }));

  await page.goto("/pages/index.html");
  await expect(page.locator(".brand-copy strong").first()).toHaveText("Barbearia Horizonte");
  await expect(page.locator('[data-installation-copy="homeHeroDescription"]')).toHaveText("Texto desta instalação.");
  await expect(page.locator("#services-list li").first()).toBeVisible();
  await expect(page.locator("[data-estrelinha-barbeiro]")).toHaveCount(0);
  expect(requestedMascotModule).toBe(false);
});

test("nota média pública mostra estado vazio sem avaliações", async ({ page }) => {
  await page.route("**/appointments/avaliacoes", (route) => route.fulfill({ json: [] }));
  await page.goto("/pages/index.html");
  await expect(page.locator("#review-average")).toHaveText("Ainda sem avaliações");
  await expect(page.locator("#reviews-list")).toContainText("As primeiras avaliações aparecerão aqui.");
});

test("comentários, nomes e informações institucionais com XSS permanecem texto nas páginas pública e admin", async ({ page }) => {
  const payload = '<img src=x onerror="window.__apiXss=true">';
  await page.addInitScript(() => { window.__apiXss = false; });
  const institutional = {
    nome: payload, endereco: payload, telefone: "11999990000", email: "contato@example.com",
    site: "https://example.com", horario_funcionamento: payload, dias_atendimento: payload,
    endereco_maps: "javascript:window.__apiXss=true",
  };
  const review = { id: 501, appointment_id: 701, nota: 5, comentario: payload, oculta: false, criada_em: "2026-01-01T12:00:00" };
  await page.route("**/informacoes/", (route) => route.fulfill({ json: institutional }));
  await page.route("**/appointments/avaliacoes", (route) => route.fulfill({ json: [review] }));
  await page.goto("/pages/index.html");
  await expect(page.locator("#address")).toHaveText(payload);
  await expect(page.locator("#reviews-list")).toContainText(payload);
  await expect(page.locator("#reviews-list img")).toHaveCount(0);
  await expect(page.locator("#map-container iframe")).toHaveCount(0);
  await expect(page.locator("#map-link")).toHaveAttribute("hidden", "");

  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  await page.route("**/users/", (route) => route.fulfill({ json: [
    { id: 501, nome: payload, email: "xss-fixture@example.com", role: "cliente", bloqueado: false },
  ] }));
  await page.route("**/admin/agenda**", (route) => route.fulfill({ json: [
    { id: 701, user_id: 501, nome_cliente: payload, service_id: 1, barbeiro_id: 1,
      data_hora: "2026-01-01T12:00:00", status: `pendente"><img src=x onerror="window.__apiXss=true">`, preco: 35, duracao_minutos: 30 },
  ] }));
  await page.route("**/admin/avaliacoes", (route) => route.fulfill({ json: [review] }));
  await page.reload();
  await expect(page.locator("#clients-list")).toContainText(payload);
  await expect(page.locator("#agendaList .agenda-row")).toContainText(payload);
  await expect(page.locator("#reviews-admin-list")).toContainText(payload);
  await expect(page.locator("#clients-list img, #agendaList img, #reviews-admin-list img")).toHaveCount(0);
  expect(await page.evaluate(() => window.__apiXss)).toBe(false);
});

test("conta baixa a exportação JSON e pede a senha atual antes de excluir", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  await page.goto("/pages/client-account.html");
  await page.route("**/users/me/exportacao", (route) => route.fulfill({ json: {
    schema_version: "1.0", exported_at: "2026-01-01T00:00:00", usuario: { nome: "Titular QA" },
    consentimentos: [], agendamentos: [], avaliacoes: [],
  } }));
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar meus dados" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^meus-dados-\d{4}-\d{2}-\d{2}\.json$/);

  await page.route("**/users/me", async (route) => {
    expect(route.request().method()).toBe("DELETE");
    expect(route.request().postDataJSON()).toEqual({ senha_atual: "current-password-123" });
    await route.fulfill({ json: { mensagem: "Conta anonimizada" } });
  });
  page.on("dialog", async (dialog) => {
    if (dialog.type() === "prompt") await dialog.accept("current-password-123");
    else await dialog.accept();
  });
  await page.getByRole("button", { name: "Excluir minha conta" }).click();
  await expect(page).toHaveURL(/index\.html$/);
});

test("recuperação mantém resposta genérica e redefinição sem token não envia credenciais", async ({ page }, testInfo) => {
  await page.goto("/pages/forgot.html");
  await page.getByLabel("E-mail cadastrado").fill(clientForProject(testInfo).email);
  await page.getByRole("button", { name: "Enviar instruções" }).click();
  const knownMessage = await page.getByRole("alert").innerText();
  expect(knownMessage.toLowerCase()).not.toContain("token");

  await page.getByLabel("E-mail cadastrado").fill("inexistente.e2e@example.com");
  await page.getByRole("button", { name: "Enviar instruções" }).click();
  await expect(page.getByRole("alert")).toHaveText(knownMessage);

  let resetRequests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/auth/redefinir-senha")) resetRequests += 1;
  });
  await page.goto("/pages/reset.html");
  await page.getByLabel("Nova senha").fill("E2E-Reset-Password-Only!");
  await page.getByRole("button", { name: "Salvar nova senha" }).click();
  await expect(page.getByRole("alert")).toContainText("link de redefinição está incompleto");
  expect(resetRequests).toBe(0);
});

test("catálogo mostra carregamento e estado vazio", async ({ page }) => {
  await page.route("**/services/", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.goto("/pages/client-services.html");
  await expect(page.locator("#services-list")).toContainText("Carregando serviços");
  await expect(page.locator("#services-list")).toContainText("Nenhum serviço disponível");
});

test("catálogo público exibe descrição, preço e duração na home e na seleção", async ({ page }) => {
  await page.route("**/services/", (route) => route.fulfill({ json: [
    { id: 811, nome: "Corte executivo RF01", descricao: "Acabamento e lavagem incluídos", preco: 42.5, duracao_minutos: 45 },
  ] }));
  await page.goto("/pages/index.html");
  const homeCard = page.locator("#services-list .service-card").filter({ hasText: "Corte executivo RF01" });
  await expect(homeCard).toContainText("Acabamento e lavagem incluídos");
  await expect(homeCard).toContainText("R$");
  await expect(homeCard).toContainText("45 min");

  await page.goto("/pages/client-services.html");
  const selection = page.locator(".service-selection-card").filter({ hasText: "Corte executivo RF01" });
  await expect(selection).toContainText("Acabamento e lavagem incluídos");
  await expect(selection).toContainText("45 minutos");
  await expect(selection).toContainText("R$");
});

test("disponibilidade respeita duração longa, jornada e limites do bloqueio", async ({ page }) => {
  await signIn(page, client);
  await page.waitForURL(/client-dashboard\.html$/);
  await page.goto("/pages/client-services.html");
  const longService = page.locator(".service-selection-card").filter({ hasText: "Serviço Longo E2E" });
  await longService.getByRole("link", { name: "Escolher profissional" }).click();
  await page.getByRole("link", { name: "Ver horários" }).click();
  await page.getByLabel("Selecione a data").fill(bookingDate);
  await expect(page.locator(".slot-button").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "11:30", exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "12:30", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "16:30", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "17:00", exact: true })).toHaveCount(0);
});

test("catálogo, disponibilidade respeitando bloqueio, criação, reagendamento e cancelamento", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  const beforeBooking = await currentAppointmentCount(page);
  const slot = await chooseSlot(page);
  await expect(page.getByRole("link", { name: "12:00", exact: true })).toHaveCount(0);
  await slot.click();
  await page.getByRole("button", { name: "Confirmar agendamento" }).click();
  await page.waitForURL(/client-appointments\.html$/);
  await expect(page.locator(".appointment-card")).toHaveCount(beforeBooking + 1);

  const createdCard = page.locator(".appointment-card").filter({ hasText: "pendente" }).first();
  const createdHeading = await createdCard.locator("h2").innerText();
  await createdCard.getByRole("link", { name: "Reagendar" }).click();
  await page.getByLabel("Selecione a data").fill(bookingDate);
  await expect(page.locator(".slot-button").first()).toBeVisible();
  await page.locator(".slot-button").first().click();
  await page.getByRole("button", { name: "Confirmar agendamento" }).click();
  await page.waitForURL(/client-appointments\.html$/);
  await expect(page.locator(".appointment-card")).toHaveCount(beforeBooking + 1);

  page.once("dialog", (dialog) => dialog.accept());
  await page.locator(".appointment-card").filter({ hasText: createdHeading }).getByRole("button", { name: "Cancelar" }).click();
  await expect(page.locator(".appointment-card").filter({ hasText: createdHeading })).toContainText("cancelado");
});

test("duplo clique cria uma reserva; outro cliente recebe conflito no mesmo horário", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  const beforeBooking = await currentAppointmentCount(page);
  const slot = await chooseSlot(page);
  await slot.click();
  const bookingRequests = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/appointments/")) bookingRequests.push(request);
  });
  const bookingResponsePromise = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().endsWith("/appointments/"));
  await page.getByRole("button", { name: "Confirmar agendamento" }).dblclick();
  const bookingResponse = await bookingResponsePromise;
  expect(bookingResponse.status()).toBe(201);
  await page.waitForURL(/client-appointments\.html$/);
  await expect(page.locator(".appointment-card")).toHaveCount(beforeBooking + 1);
  expect(bookingRequests).toHaveLength(1);
  const ownerToken = await page.evaluate(() => localStorage.getItem("token"));
  const persistedAppointmentsResponse = await page.request.get("http://127.0.0.1:4174/appointments/", {
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  expect(persistedAppointmentsResponse.status()).toBe(200);
  const persistedAppointments = await persistedAppointmentsResponse.json();
  const created = persistedAppointments.find((appointment) =>
    appointment.data_hora.startsWith(bookingDate) && appointment.status !== "cancelado");
  expect(created).toBeTruthy();
  await signIn(page, otherClientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  const confirmation = new URLSearchParams({
    service_id: String(created.service_id),
    barbeiro_id: String(created.barbeiro_id),
    date_time: created.data_hora,
  });
  await page.goto(`/pages/client-confirm.html?${confirmation}`);
  await page.getByRole("button", { name: "Confirmar agendamento" }).click();
  await expect(page.locator("#confirmation-content")).toContainText(/409|conflita com outro agendamento/i);
});

test("cliente não lê nem altera agendamento de outra conta", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  const ownToken = await page.evaluate(() => localStorage.getItem("token"));
  const otherLogin = await page.request.post("http://127.0.0.1:4174/auth/login", {
    data: {
      email: otherClientForProject(testInfo).email,
      senha: otherClientForProject(testInfo).password,
    },
  });
  expect(otherLogin.status()).toBe(200);
  const otherToken = (await otherLogin.json()).access_token;
  const otherAppointmentsResponse = await page.request.get("http://127.0.0.1:4174/appointments/", {
    headers: { Authorization: `Bearer ${otherToken}` },
  });
  const otherAppointments = await otherAppointmentsResponse.json();
  expect(otherAppointments.length).toBeGreaterThan(0);
  const otherAppointmentId = otherAppointments[0].id;

  const forbiddenRead = await page.request.get(`http://127.0.0.1:4174/appointments/${otherAppointmentId}`, {
    headers: { Authorization: `Bearer ${ownToken}` },
  });
  const forbiddenUpdate = await page.request.put(`http://127.0.0.1:4174/appointments/${otherAppointmentId}`, {
    headers: { Authorization: `Bearer ${ownToken}` },
    data: { status: "cancelado" },
  });
  expect(forbiddenRead.status()).toBe(403);
  expect(forbiddenUpdate.status()).toBe(403);

  await page.goto("/pages/client-appointments.html");
  await expect(page.locator(".appointment-card").filter({ hasText: `Atendimento #${otherAppointmentId}` })).toHaveCount(0);
});

test("histórico completo mostra agendamentos passados e futuros em ordem", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  await page.route("**/appointments/", (route) => route.fulfill({ json: [
    { id: 912, user_id: 1, service_id: 2, barbeiro_id: 3, data_hora: "2032-05-12T12:00:00", status: "pendente", preco: 40, duracao_minutos: 30 },
    { id: 911, user_id: 1, service_id: 2, barbeiro_id: 3, data_hora: "2032-05-08T12:00:00", status: "concluido", preco: 40, duracao_minutos: 30 },
  ] }));
  await page.goto("/pages/client-appointments.html");
  const cards = page.locator(".appointment-card");
  await expect(cards).toHaveCount(2);
  await expect(cards.nth(0)).toContainText("#912");
  await expect(cards.nth(1)).toContainText("#911");
});

test("histórico e avaliação de atendimento concluído", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  await page.goto("/pages/client-appointments.html");
  await expect(page.locator(".appointment-card").first()).toBeVisible();
  const evaluationLink = page.getByRole("link", { name: "Avaliar atendimento" }).first();
  const appointmentId = new URL(await evaluationLink.getAttribute("href"), "http://test.local").searchParams.get("appointment_id");
  const evaluationResponse = page.waitForResponse((response) =>
    response.url().includes("/avaliacao") && response.request().method() === "POST");
  await evaluationLink.click();
  await page.getByLabel("Sua nota (1 a 5)").selectOption("5");
  await page.getByLabel("Comentário (opcional)").fill("Atendimento fictício para teste E2E.");
  await page.getByRole("button", { name: "Enviar avaliação" }).click();
  expect((await evaluationResponse).status()).toBe(201);
  await page.waitForURL(/client-appointments\.html$/);
  const ratedCard = page.locator(".appointment-card").filter({ hasText: `Atendimento #${appointmentId}` });
  await expect(ratedCard.getByRole("link", { name: "Avaliar atendimento" })).toHaveCount(0);
});

test("painel administrativo carrega e gerencia serviços, equipe, clientes, horários e informações", async ({ page }, testInfo) => {
  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  await expect(page.getByRole("heading", { name: "Gerenciar serviços" })).toBeVisible();
  await expect(page.locator("#schedules-list")).toContainText("08:00");
  await expect(page.locator("#blocks-list")).toContainText("Bloqueio E2E fictício");
  await expect(page.locator("#clients-list")).toContainText("Cliente E2E Fictício");

  const clientName = testInfo.project.name.startsWith("mobile") ? "Cliente Mobile E2E Fictício" : "Cliente E2E Fictício";
  await page.locator("#manual-client").selectOption({ label: `${clientName} · ${clientForProject(testInfo).email}` });
  await page.locator("#manual-service").selectOption({ label: "Corte E2E" });
  await page.locator("#manual-barber").selectOption({ label: "Barbeiro E2E Fictício" });
  const manualTime = testInfo.project.name.startsWith("mobile") ? "15:30" : "15:00";
  await page.locator("#manual-date").fill(`${bookingDate}T${manualTime}`);
  const manualBookingResponse = page.waitForResponse((response) =>
    response.url().endsWith("/admin/agendamentos") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Criar agendamento" }).click();
  const manualBooking = await manualBookingResponse;
  expect(manualBooking.status()).toBe(201);
  await expect(page.locator("#manual-message")).toContainText("Agendamento manual criado");

  await page.locator("#service-name").fill("Serviço criado pelo E2E");
  await page.getByLabel("Preço (R$)").fill("42.50");
  await page.getByLabel("Duração (minutos)").fill("45");
  await page.getByRole("button", { name: "Salvar serviço" }).click();
  await expect(page.locator("#services-admin-list")).toContainText("Serviço criado pelo E2E");

  await page.locator("#barber-service-service").selectOption({ label: "Serviço criado pelo E2E" });
  await page.getByRole("button", { name: "Associar serviço" }).click();
  const newAssociation = page.locator("#barber-services-list .management-item").filter({ hasText: "Serviço criado pelo E2E" });
  await expect(newAssociation).toBeVisible();
  await newAssociation.getByRole("button", { name: "Remover" }).click();
  await expect(newAssociation).toHaveCount(0);

  const serviceRow = page.locator("#services-admin-list .management-item").filter({ hasText: "Serviço criado pelo E2E" });
  await serviceRow.getByRole("button", { name: "Editar" }).click();
  await page.locator("#service-name").fill("RF16 service updated");
  await page.getByLabel("Preço (R$)").fill("47.25");
  await page.getByLabel("Duração (minutos)").fill("50");
  await page.locator("#service-form [type=submit]").click();
  const updatedServiceRow = page.locator("#services-admin-list .management-item").filter({ hasText: "RF16 service updated" });
  await expect(updatedServiceRow).toContainText("R$ 47,25");
  page.once("dialog", (dialog) => dialog.accept());
  await updatedServiceRow.getByRole("button", { name: "Excluir" }).click();
  await expect(updatedServiceRow).toHaveCount(0);

  const scheduleRow = page.locator("#schedules-list .management-item").first();
  await scheduleRow.getByRole("button", { name: "Desativar" }).click();
  await expect(page.locator("#schedules-list .management-item").first()).toContainText("Inativa");
  await page.locator("#schedules-list .management-item").first().getByRole("button", { name: "Ativar" }).click();
  await expect(page.locator("#schedules-list .management-item").first()).toContainText("Ativa");

  await page.locator("#schedule-barber").selectOption({ index: 0 });
  await page.locator("#schedule-day").selectOption("2");
  await page.locator("#schedule-start").fill("09:00");
  await page.locator("#schedule-end").fill("17:00");
  await page.getByRole("button", { name: "Adicionar jornada" }).click();
  const newSchedule = page.locator("#schedules-list .management-item").filter({ hasText: "09:00" }).last();
  await expect(newSchedule).toBeVisible();
  await expect(newSchedule).toContainText("17:00");
  await newSchedule.getByRole("button", { name: "Editar" }).click();
  await page.locator("#schedule-start").fill("10:00");
  await page.locator("#schedule-end").fill("16:00");
  await page.locator("#schedule-form [type=submit]").click();
  const updatedSchedule = page.locator("#schedules-list .management-item").filter({ hasText: "10:00" }).last();
  await expect(updatedSchedule).toContainText("16:00");
  await updatedSchedule.getByRole("button", { name: "Desativar" }).click();
  await expect(updatedSchedule).toContainText("Inativa");
  await updatedSchedule.getByRole("button", { name: "Ativar" }).click();
  await expect(updatedSchedule).toContainText("Ativa");
  await updatedSchedule.getByRole("button", { name: "Remover" }).click();
  await expect(updatedSchedule).toHaveCount(0);

  await page.locator("#block-start").fill(`${bookingDate}T14:00`);
  await page.locator("#block-end").fill(`${bookingDate}T14:30`);
  await page.locator("#block-type").selectOption("feriado");
  await page.getByLabel("Motivo").fill("Bloqueio criado pela interface E2E");
  await page.getByRole("button", { name: "Salvar bloqueio" }).click();
  const createdBlock = page.locator("#blocks-list .management-item").filter({ hasText: "Bloqueio criado pela interface E2E" });
  await expect(createdBlock).toBeVisible();
  await expect(createdBlock).toContainText("feriado");
  await createdBlock.getByRole("button", { name: "Editar" }).click();
  await page.locator("#block-reason").fill("Bloqueio E2E feriado atualizado");
  await page.locator("#block-form [type=submit]").click();
  const updatedBlock = page.locator("#blocks-list .management-item").filter({ hasText: "Bloqueio E2E feriado atualizado" });
  await expect(updatedBlock).toContainText("feriado");
  await updatedBlock.getByRole("button", { name: "Remover" }).click();
  await expect(updatedBlock).toHaveCount(0);

  const clientRow = page.locator("#clients-list .management-item").filter({ hasText: clientForProject(testInfo).email });
  await clientRow.getByRole("button", { name: "Bloquear" }).click();
  await expect(clientRow).toContainText("Bloqueado");
  await clientRow.getByRole("button", { name: "Desbloquear" }).click();
  await expect(clientRow).toContainText("Ativo");

  await page.locator("#institution-name").fill("Barbearia E2E Temporária");
  await page.getByLabel("Endereço").fill("Rua Teste Fictícia, 123");
  await page.getByLabel("Telefone").fill("11999990000");
  await page.locator("#institution-email").fill("contato-e2e@example.com");
  await page.locator("#institution-site").fill("https://e2e.example.com");
  await page.getByLabel("Dias de atendimento").fill("Todos os dias");
  await page.getByLabel("Horário de funcionamento").fill("08:00 às 18:00");
  await page.locator("#institution-map").fill("https://www.google.com/maps/place/e2e");
  await page.getByRole("button", { name: "Salvar informações" }).click();
  await expect(page.locator("#institutional-form")).toContainText("atualizadas");

  await page.goto("/pages/index.html");
  await expect(page.locator("#address")).toHaveText("Rua Teste Fictícia, 123");
  await expect(page.locator("#phone")).toContainText("11999990000");
  await expect(page.locator("#email")).toContainText("contato-e2e@example.com");
  await expect(page.locator("#operating-days")).toHaveText("Todos os dias");
  await expect(page.locator("#mon")).toHaveText("08:00 às 18:00");
  await expect(page.locator("#map-link")).toHaveAttribute("href", "https://www.google.com/maps/place/e2e");
  await page.goto("/pages/admin.html");
  await expect(page.locator("#institution-address")).toHaveValue("Rua Teste Fictícia, 123");

  await page.getByRole("button", { name: "Gerar relatório" }).click();
  await expect(page.locator("#finance-result")).toContainText("Receita estimada");

  await page.goto("/pages/login.html");
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  await page.goto("/pages/client-appointments.html");
  await page.getByRole("link", { name: "Avaliar atendimento" }).first().click();
  const moderationComment = `RF22 moderation ${testInfo.project.name}`;
  await page.getByLabel("Sua nota (1 a 5)").selectOption("4");
  await page.getByLabel("Comentário (opcional)").fill(moderationComment);
  await page.getByRole("button", { name: "Enviar avaliação" }).click();
  await page.waitForURL(/client-appointments\.html$/);
  await page.goto("/pages/login.html");
  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  await expect(page.locator("#reviews-admin-list")).toContainText(moderationComment);

  const review = page.locator("#reviews-admin-list .management-item").filter({ hasText: moderationComment }).last();
  await expect(review).toBeVisible();
  if (await review.getByRole("button", { name: "Exibir" }).count()) {
    await review.getByRole("button", { name: "Exibir" }).click();
  }
  await expect(review.getByRole("button", { name: "Ocultar" })).toBeVisible();
  await review.getByRole("button", { name: "Ocultar" }).click();
  await expect(review.getByRole("button", { name: "Exibir" })).toBeVisible();

  await page.goto("/pages/index.html");
  await expect(page.locator("#reviews-list")).not.toContainText(moderationComment);
  await expect(page.locator("#address")).toContainText("Rua Teste Fictícia, 123");
  await page.goto("/pages/admin.html");
  const reviewAgain = page.locator("#reviews-admin-list .management-item").filter({ hasText: moderationComment }).last();
  await reviewAgain.getByRole("button", { name: "Exibir" }).click();
  await expect(reviewAgain.getByRole("button", { name: "Ocultar" })).toBeVisible();
  await page.goto("/pages/index.html");
  await expect(page.locator("#reviews-list")).toContainText(moderationComment);
  await page.goto("/pages/admin.html");
  await expect(page.getByRole("heading", { name: "Gerenciar serviços" })).toBeVisible();
});

test("RF13 agenda diária respeita data, perfil, propriedade e estados em desktop e mobile", async ({ page }) => {
  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  await page.goto("/pages/admin.html");
  const adminDate = page.locator(`#dateRoll .date-item[data-date="${agendaDate}"]`);
  await expect(adminDate).toBeVisible();
  const adminResponse = page.waitForResponse((response) =>
    response.url().includes("/admin/agenda") && response.url().includes(`data=${agendaDate}`));
  await adminDate.click();
  expect((await adminResponse).status()).toBe(200);
  const adminRows = page.locator("#agendaList .agenda-row");
  await expect(adminRows).toHaveCount(6);
  for (const text of [
    "Cliente RF13 Pendente", "Cliente RF13 Confirmado", "Cliente RF13 Concluído",
    "Cliente RF13 Cancelado", "Cliente RF13 Falta", "Cliente RF13 Avaliado",
    "Corte E2E", "Barbeiro E2E Fictício", "Segundo Barbeiro RF13",
    "Pendente", "Confirmado", "Concluído", "Cancelado", "Falta", "Avaliado",
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
  ]) {
    await expect(page.locator("#agendaList")).toContainText(text);
  }

  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await signIn(page, barber);
  await page.waitForURL(/admin\.html$/);
  await expect(page.locator("#userName")).toHaveText("Barbeiro E2E Fictício");
  await page.goto("/pages/admin.html");
  const barberDate = page.locator(`#dateRoll .date-item[data-date="${agendaDate}"]`);
  await expect(barberDate).toBeVisible();
  const barberResponse = page.waitForResponse((response) =>
    response.url().includes("/admin/me/agenda") && response.url().includes(`data=${agendaDate}`));
  await barberDate.click();
  expect((await barberResponse).status()).toBe(200);
  const barberRows = page.locator("#agendaList .agenda-row");
  await expect(barberRows).toHaveCount(3);
  await expect(page.locator("#agendaList")).toContainText("Barbeiro E2E Fictício");
  await expect(page.locator("#agendaList")).toContainText("Corte E2E");
  await expect(page.locator("#agendaList")).not.toContainText("Segundo Barbeiro RF13");
  await expect(page.locator("#agendaList")).not.toContainText("Cliente RF13 Cancelado");

  const barberToken = await page.evaluate(() => localStorage.getItem("token"));
  const forgedFullAgenda = await page.request.get(
    `http://127.0.0.1:4174/admin/agenda?data=${agendaDate}&barbeiro_id=999999`,
    { headers: { Authorization: `Bearer ${barberToken}` } },
  );
  expect(forgedFullAgenda.status()).toBe(403);
  const forgedOwnAgenda = await page.request.get(
    `http://127.0.0.1:4174/admin/me/agenda?data=${agendaDate}&barbeiro_id=999999`,
    { headers: { Authorization: `Bearer ${barberToken}` } },
  );
  expect(forgedOwnAgenda.status()).toBe(200);
  expect(await forgedOwnAgenda.json()).toHaveLength(3);

  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await signIn(page, client);
  await page.waitForURL(/client-dashboard\.html$/);
  const clientToken = await page.evaluate(() => localStorage.getItem("token"));
  for (const endpoint of ["/admin/agenda", "/admin/me/agenda"]) {
    const response = await page.request.get(
      `http://127.0.0.1:4174${endpoint}?data=${agendaDate}`,
      { headers: { Authorization: `Bearer ${clientToken}` } },
    );
    expect(response.status()).toBe(403);
  }
});

test("agenda registra status da equipe e valor cobrado", async ({ page }) => {
  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  let appointmentStatus = "pendente";
  let updatePayload = null;
  await page.route("**/admin/agenda*", (route) => route.fulfill({ json: [{
    id: 501, user_id: 1, barbeiro_id: 2, nome_cliente: "Cliente RF14",
    servico_nome: "Corte RF14", profissional_nome: "Barbeiro RF14",
    horario: "10:00", status: appointmentStatus, preco: 45, valor_cobrado: null,
  }] }));
  await page.route("**/appointments/501", async (route) => {
    updatePayload = route.request().postDataJSON();
    appointmentStatus = updatePayload.status;
    await route.fulfill({ json: {
      id: 501, user_id: 1, barbeiro_id: 2, service_id: 3,
      data_hora: "2032-05-12T10:00:00", status: appointmentStatus,
      preco: 45, duracao_minutos: 30, valor_cobrado: updatePayload.valor_cobrado,
    } });
  });
  await page.goto("/pages/admin.html");
  const row = page.locator(".agenda-row").filter({ hasText: "Cliente RF14" });
  await expect(row).toBeVisible();
  await page.locator("#charged-501").fill("38.50");
  await row.getByRole("button", { name: "Concluído" }).click();
  await expect.poll(() => updatePayload).toEqual({ status: "concluido", valor_cobrado: 38.5 });
  await expect(row).toContainText("Concluído");
});

test("bloqueio e desbloqueio de cliente afetam a sessão ativa imediatamente", async ({ browser }, testInfo) => {
  const contextOptions = {
    baseURL: "http://127.0.0.1:4173",
    viewport: testInfo.project.use.viewport,
    isMobile: Boolean(testInfo.project.use.isMobile),
    hasTouch: Boolean(testInfo.project.use.hasTouch),
  };
  const clientContext = await browser.newContext(contextOptions);
  const adminContext = await browser.newContext(contextOptions);
  try {
    const clientPage = await clientContext.newPage();
    const adminPage = await adminContext.newPage();
    const account = clientForProject(testInfo);
    await signIn(clientPage, account);
    await clientPage.waitForURL(/client-dashboard\.html$/);
    await signIn(adminPage, admin);
    await adminPage.waitForURL(/admin\.html$/);

    const clientRow = adminPage.locator("#clients-list .management-item").filter({ hasText: account.email });
    await expect(clientRow).toBeVisible();
    await clientRow.getByRole("button", { name: "Bloquear" }).click();
    await expect(clientRow).toContainText("Bloqueado");
    await clientPage.reload();
    await expect(clientPage).toHaveURL(/login\.html/);
    await expect.poll(() => clientPage.evaluate(() => localStorage.getItem("token"))).toBeNull();

    await clientRow.getByRole("button", { name: "Desbloquear" }).click();
    await expect(clientRow).toContainText("Ativo");
    await signIn(clientPage, account);
    await clientPage.waitForURL(/client-dashboard\.html$/);
  } finally {
    await clientContext.close();
    await adminContext.close();
  }
});

test("relatório financeiro exibe quebras por período e exporta CSV", async ({ page }) => {
  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  await page.route("**/admin/relatorio**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/csv")) {
      return route.fulfill({ contentType: "text/csv; charset=utf-8", body: "data_hora,barbeiro,servico,status,valor_cobrado\n" });
    }
    return route.fulfill({ json: {
      periodo: { inicio: "2026-06-01", fim: "2026-06-03" },
      total_agendamentos: 3, total_receita: 100, ticket_medio: 100 / 3,
      por_barbeiro: [{ barbeiro_id: 7, barbeiro: "Barbeiro RF21", total_agendamentos: 3, receita: 100 }],
      por_servico: [{ servico_id: 8, servico: "Serviço RF21", total_agendamentos: 3, receita: 100 }],
      por_dia: [{ dia: "2026-06-02", total_agendamentos: 2, receita: 67.5 }],
      contagem_status: { concluido: 3, cancelado: 1, falta: 1 },
    } });
  });
  await page.locator("#finance-start").fill("2026-06-01");
  await page.locator("#finance-end").fill("2026-06-03");
  await page.getByRole("button", { name: "Gerar relatório" }).click();
  await expect(page.locator(".finance-table")).toContainText("Barbeiro RF21");
  await expect(page.locator(".finance-table")).toContainText("Serviço RF21");
  await expect(page.locator(".finance-table")).toContainText("2026-06-02");
  await expect(page.locator(".finance-table")).toContainText("cancelado");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar CSV" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("relatorio-financeiro-2026-06-01-2026-06-03.csv");
});

test("usuário comum recebe 403 na API e é retirado da tela administrativa", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  const token = await page.evaluate(() => localStorage.getItem("token"));
  const forbidden = await page.request.get(
    `http://127.0.0.1:4174/admin/agenda?data=${bookingDate}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  expect(forbidden.status()).toBe(403);

  const deniedUiResponse = page.waitForResponse((response) =>
    response.url().includes("/admin/agenda") && response.status() === 403);
  await page.goto("/pages/admin.html");
  expect((await deniedUiResponse).status()).toBe(403);
  await page.waitForURL(/client-dashboard\.html$/);
});

test("formulário é navegável por Tab, tem foco visível, rótulos e validação nativa", async ({ page }) => {
  await page.goto("/pages/login.html");
  const email = page.getByLabel("E-mail");
  const password = page.getByLabel("Senha", { exact: true });
  await expect(email).toBeVisible();
  await expect(password).toBeVisible();

  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  await expect(email).toBeFocused();
  expect(await email.evaluate((element) => getComputedStyle(element).outlineStyle)).toBe("solid");

  await page.getByRole("button", { name: "Entrar na minha conta" }).click();
  expect(await email.evaluate((element) => element.validity.valueMissing)).toBe(true);
  expect(await email.evaluate((element) => element.validationMessage.length > 0)).toBe(true);
});

test("falha de rede mostra estado de erro e ação de repetição", async ({ page }) => {
  await page.route("**/services/", (route) => route.abort("failed"));
  await page.goto("/pages/client-services.html");
  await expect(page.locator("#services-list")).toContainText(/Failed to fetch|conectar|Erro/i);
});

test("cliente não encontra mutações administrativas na tela", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  await page.goto("/pages/admin.html");
  await page.waitForURL(/client-dashboard\.html$/);
  await expect(page.locator(".admin-only")).toHaveCount(0);
});
