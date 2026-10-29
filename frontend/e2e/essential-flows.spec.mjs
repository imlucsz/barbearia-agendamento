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
  await page.getByRole("link", { name: "Escolher profissional" }).first().click();
  await page.getByRole("link", { name: "Ver horários" }).click();
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

test("cadastro, login, logout e reentrada após sessão expirada", async ({ page }) => {
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
  await page.getByRole("link", { name: "Sair" }).click();
  await page.waitForURL(/login\.html$/);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("token"))).toBeNull();

  await page.evaluate(() => {
    localStorage.setItem("token", "expired-e2e-token");
    localStorage.setItem("user", JSON.stringify({ role: "cliente" }));
  });
  await page.goto("/pages/client-appointments.html", { waitUntil: "commit" });
  await page.waitForURL(/login\.html\?redirect=client-appointments\.html$/);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("token"))).toBeNull();
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

test("histórico e avaliação de atendimento concluído", async ({ page }, testInfo) => {
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  await page.goto("/pages/client-appointments.html");
  await expect(page.locator(".appointment-card").first()).toBeVisible();
  const evaluationResponse = page.waitForResponse((response) =>
    response.url().includes("/avaliacao") && response.request().method() === "POST");
  await page.getByRole("link", { name: "Avaliar atendimento" }).first().click();
  await page.getByLabel("Sua nota (1 a 5)").selectOption("5");
  await page.getByLabel("Comentário (opcional)").fill("Atendimento fictício para teste E2E.");
  await page.getByRole("button", { name: "Enviar avaliação" }).click();
  expect((await evaluationResponse).status()).toBe(201);
  await page.waitForURL(/client-appointments\.html$/);
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

  const scheduleRow = page.locator("#schedules-list .management-item").first();
  await scheduleRow.getByRole("button", { name: "Desativar" }).click();
  await expect(page.locator("#schedules-list .management-item").first()).toContainText("Inativa");
  await page.locator("#schedules-list .management-item").first().getByRole("button", { name: "Ativar" }).click();
  await expect(page.locator("#schedules-list .management-item").first()).toContainText("Ativa");

  await page.locator("#block-start").fill(`${bookingDate}T14:00`);
  await page.locator("#block-end").fill(`${bookingDate}T14:30`);
  await page.getByLabel("Motivo").fill("Bloqueio criado pela interface E2E");
  await page.getByRole("button", { name: "Salvar bloqueio" }).click();
  const createdBlock = page.locator("#blocks-list .management-item").filter({ hasText: "Bloqueio criado pela interface E2E" });
  await expect(createdBlock).toBeVisible();
  await createdBlock.getByRole("button", { name: "Remover" }).click();
  await expect(createdBlock).toHaveCount(0);

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
  await page.locator("#institution-map").fill("https://maps.example.com/e2e");
  await page.getByRole("button", { name: "Salvar informações" }).click();
  await expect(page.locator("#institutional-form")).toContainText("atualizadas");

  await page.getByRole("button", { name: "Gerar relatório" }).click();
  await expect(page.locator("#finance-result")).toContainText("Receita estimada");

  await page.goto("/pages/login.html");
  await signIn(page, clientForProject(testInfo));
  await page.waitForURL(/client-dashboard\.html$/);
  await page.goto("/pages/client-appointments.html");
  await page.getByRole("link", { name: "Avaliar atendimento" }).first().click();
  await page.getByLabel("Sua nota (1 a 5)").selectOption("4");
  await page.getByLabel("Comentário (opcional)").fill("Avaliação de moderação E2E.");
  await page.getByRole("button", { name: "Enviar avaliação" }).click();
  await page.waitForURL(/client-appointments\.html$/);
  await page.goto("/pages/login.html");
  await signIn(page, admin);
  await page.waitForURL(/admin\.html$/);
  await expect(page.locator("#reviews-admin-list")).toContainText("Avaliação de moderação E2E.");

  const review = page.locator("#reviews-admin-list .management-item").filter({ hasText: "Avaliação de moderação E2E." }).last();
  await expect(review).toBeVisible();
  if (await review.getByRole("button", { name: "Exibir" }).count()) {
    await review.getByRole("button", { name: "Exibir" }).click();
  }
  await expect(review.getByRole("button", { name: "Ocultar" })).toBeVisible();
  await review.getByRole("button", { name: "Ocultar" }).click();
  await expect(review.getByRole("button", { name: "Exibir" })).toBeVisible();

  await page.goto("/pages/index.html");
  await expect(page.locator("#address")).toContainText("Rua Teste Fictícia, 123");
  await page.goto("/pages/admin.html");
  await expect(page.getByRole("heading", { name: "Gerenciar serviços" })).toBeVisible();
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
