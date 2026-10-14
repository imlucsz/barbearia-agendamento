import { api, getToken } from "./api.js";

const byId = (id) => document.getElementById(id);
const dayNames = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];
let services = [];
let barbers = [];
let clients = [];
let institutionalInfoExists = true;

document.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  if (!getToken()) {
    window.location.href = "login.html?redirect=admin.html";
    return;
  }
  try {
    const currentUser = await api.get("/auth/me");
    if (currentUser.role !== "admin") {
      document.querySelectorAll(".admin-only, [data-admin-only]").forEach((element) => { element.hidden = true; });
      if (currentUser.role !== "barbeiro") {
        window.location.href = "client-dashboard.html";
        return;
      }
    }
    byId("userName").textContent = currentUser.nome;
    if (currentUser.role === "admin") {
      await loadReferenceData();
      bindAdminForms();
      await Promise.all([
        loadServices(),
        loadClients(),
        loadBarberServices(),
        loadSchedules(),
        loadBlocks(),
        loadInstitutionalInfo(),
        loadReviews(),
      ]);
    }
  } catch (error) {
    console.error("Falha ao inicializar o painel:", error);
    showMessage(byId("agendaList"), error.message, "danger");
    if (error.status === 401) window.location.href = "login.html?redirect=admin.html";
  }
}

async function loadReferenceData() {
  [services, barbers, clients] = await Promise.all([
    api.get("/services/"),
    api.get("/users/barbeiros"),
    api.get("/users/"),
  ]);
  fillSelect("manual-client", clients, (client) => `${client.nome} · ${client.email}`, "Selecione um cliente cadastrado");
  fillSelect("manual-service", services, (service) => service.nome);
  fillSelect("manual-barber", barbers, (barber) => barber.nome);
  fillSelect("barber-service-barber", barbers, (barber) => barber.nome);
  fillSelect("barber-service-service", services, (service) => service.nome);
  ["schedule-barber", "block-barber"].forEach((id) => fillSelect(id, barbers, (barber) => barber.nome));
  if (barbers.length) {
    byId("schedule-barber").value = String(barbers[0].id);
    byId("block-barber").value = String(barbers[0].id);
  }
}

function bindAdminForms() {
  byId("manual-appointment-form").addEventListener("submit", createManualAppointment);
  byId("service-form").addEventListener("submit", saveService);
  byId("service-cancel-edit").addEventListener("click", resetServiceForm);
  byId("barber-service-form").addEventListener("submit", assignService);
  byId("schedule-form").addEventListener("submit", createSchedule);
  byId("block-form").addEventListener("submit", createBlock);
  byId("institutional-form").addEventListener("submit", saveInstitutionalInfo);
  byId("schedule-barber").addEventListener("change", loadSchedules);
  byId("block-barber").addEventListener("change", loadBlocks);
}

async function loadServices() {
  try {
    services = await api.get("/services/");
    fillSelect("manual-service", services, (service) => service.nome);
    fillSelect("barber-service-service", services, (service) => service.nome);
    const container = byId("services-admin-list");
    container.innerHTML = services.map((service) => `
      <article class="management-item">
        <div><strong>${escapeHtml(service.nome)}</strong><p>${formatCurrency(service.preco)} · ${service.duracao_minutos} min</p></div>
        <div class="management-actions">
          <button type="button" class="btn btn-ghost" data-service-edit="${service.id}">Editar</button>
          <button type="button" class="btn btn-danger" data-service-delete="${service.id}">Excluir</button>
        </div>
      </article>
    `).join("") || emptyHtml("Nenhum serviço cadastrado.");
    container.querySelectorAll("[data-service-edit]").forEach((button) => button.addEventListener("click", () => editService(button.dataset.serviceEdit)));
    container.querySelectorAll("[data-service-delete]").forEach((button) => button.addEventListener("click", () => deleteService(button.dataset.serviceDelete)));
  } catch (error) {
    report("services-admin-list", error);
  }
}

function editService(id) {
  const service = services.find((item) => String(item.id) === String(id));
  if (!service) return;
  const form = byId("service-form");
  form.elements.id.value = service.id;
  form.elements.nome.value = service.nome;
  form.elements.preco.value = service.preco;
  form.elements.duracao_minutos.value = service.duracao_minutos;
  form.querySelector("[type=submit]").textContent = "Atualizar serviço";
  byId("service-cancel-edit").hidden = false;
  form.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function saveService(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const id = form.elements.id.value;
  const body = {
    nome: form.elements.nome.value.trim(),
    preco: Number(form.elements.preco.value),
    duracao_minutos: Number(form.elements.duracao_minutos.value),
  };
  try {
    if (id) await api.put(`/services/${encodeURIComponent(id)}`, body);
    else await api.post("/services/", body);
    resetServiceForm();
    await loadServices();
    await loadBarberServices();
    showMessage(byId("services-admin-list"), "Serviço salvo.", "success");
  } catch (error) {
    report("services-admin-list", error);
  }
}

async function deleteService(id) {
  if (!window.confirm("Excluir este serviço? Agendamentos existentes mantêm o preço e a duração registrados.")) return;
  try {
    await api.delete(`/services/${encodeURIComponent(id)}`);
    await loadServices();
    await loadBarberServices();
  } catch (error) {
    report("services-admin-list", error);
  }
}

function resetServiceForm() {
  const form = byId("service-form");
  form.reset();
  form.elements.id.value = "";
  form.querySelector("[type=submit]").textContent = "Salvar serviço";
  byId("service-cancel-edit").hidden = true;
}

async function loadClients() {
  try {
    clients = await api.get("/users/");
    const container = byId("clients-list");
    container.innerHTML = clients.map((client) => `
      <article class="management-item">
        <div><strong>${escapeHtml(client.nome)}</strong><p>${escapeHtml(client.email)} · ${client.bloqueado ? "Bloqueado" : "Ativo"}</p></div>
        <div class="management-actions">
          <button type="button" class="btn btn-ghost" data-client-edit="${client.id}">Editar dados</button>
          <button type="button" class="btn ${client.bloqueado ? "btn-primary" : "btn-danger"}" data-client-toggle="${client.id}">${client.bloqueado ? "Desbloquear" : "Bloquear"}</button>
        </div>
      </article>
    `).join("") || emptyHtml("Nenhum cliente cadastrado.");
    container.querySelectorAll("[data-client-edit]").forEach((button) => button.addEventListener("click", () => editClient(button.dataset.clientEdit)));
    container.querySelectorAll("[data-client-toggle]").forEach((button) => button.addEventListener("click", () => toggleClient(button.dataset.clientToggle)));
  } catch (error) {
    report("clients-list", error);
  }
}

async function editClient(id) {
  const client = clients.find((item) => String(item.id) === String(id));
  if (!client) return;
  const nome = window.prompt("Nome do cliente:", client.nome);
  if (nome === null) return;
  const email = window.prompt("E-mail do cliente:", client.email);
  if (email === null) return;
  try {
    await api.put(`/users/${encodeURIComponent(id)}`, { nome: nome.trim(), email: email.trim() });
    await loadClients();
  } catch (error) {
    report("clients-list", error);
  }
}

async function toggleClient(id) {
  const client = clients.find((item) => String(item.id) === String(id));
  if (!client) return;
  try {
    await api.put(`/users/${encodeURIComponent(id)}`, { bloqueado: !client.bloqueado });
    await loadClients();
  } catch (error) {
    report("clients-list", error);
  }
}

async function assignService(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api.post("/barbeiro-servico/", {
      barbeiro_id: Number(form.elements.barbeiro_id.value),
      service_id: Number(form.elements.service_id.value),
    });
    await loadBarberServices();
  } catch (error) {
    report("barber-services-list", error);
  }
}

async function loadBarberServices() {
  try {
    const records = (await Promise.all(barbers.map((barber) =>
      api.get(`/barbeiro-servico/barbeiro/${encodeURIComponent(barber.id)}`)
    ))).flat();
    const container = byId("barber-services-list");
    container.innerHTML = records.map((record) => {
      const barber = barbers.find((item) => item.id === record.barbeiro_id);
      const service = services.find((item) => item.id === record.service_id);
      return `
        <article class="management-item">
          <div><strong>${escapeHtml(barber?.nome || `Barbeiro ${record.barbeiro_id}`)}</strong><p>${escapeHtml(service?.nome || `Serviço ${record.service_id}`)}</p></div>
          <button type="button" class="btn btn-danger" data-association-delete="${record.barbeiro_id}:${record.service_id}">Remover</button>
        </article>
      `;
    }).join("") || emptyHtml("Nenhum serviço associado à equipe.");
    container.querySelectorAll("[data-association-delete]").forEach((button) => {
      button.addEventListener("click", () => removeAssociation(button.dataset.associationDelete));
    });
  } catch (error) {
    report("barber-services-list", error);
  }
}

async function removeAssociation(key) {
  const [barberId, serviceId] = key.split(":");
  try {
    await api.delete("/barbeiro-servico/", { params: { barbeiro_id: barberId, service_id: serviceId } });
    await loadBarberServices();
  } catch (error) {
    report("barber-services-list", error);
  }
}

async function createSchedule(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const body = {
    barbeiro_id: Number(form.elements.barbeiro_id.value),
    dia_semana: Number(form.elements.dia_semana.value),
    hora_inicio: form.elements.hora_inicio.value,
    hora_fim: form.elements.hora_fim.value,
    ativo: true,
  };
  if (body.hora_inicio >= body.hora_fim) {
    return showMessage(byId("schedules-list"), "O horário de término deve ser posterior ao início.", "danger");
  }
  try {
    await api.post("/horario/jornadas", body);
    form.elements.hora_inicio.value = "";
    form.elements.hora_fim.value = "";
    await loadSchedules();
  } catch (error) {
    report("schedules-list", error);
  }
}

async function loadSchedules() {
  const barberId = byId("schedule-barber")?.value;
  if (!barberId) return;
  try {
    const records = await api.get(`/horario/jornadas/${encodeURIComponent(barberId)}`);
    const container = byId("schedules-list");
    container.innerHTML = records.map((record) => `
      <article class="management-item">
        <div><strong>${dayNames[record.dia_semana] || "Dia"} · ${escapeHtml(record.hora_inicio)}–${escapeHtml(record.hora_fim)}</strong><p>${record.ativo ? "Ativa" : "Inativa"}</p></div>
        <button type="button" class="btn btn-ghost" data-schedule-toggle="${record.id}" data-active="${record.ativo}">${record.ativo ? "Desativar" : "Ativar"}</button>
      </article>
    `).join("") || emptyHtml("Nenhuma jornada cadastrada para este barbeiro.");
    container.querySelectorAll("[data-schedule-toggle]").forEach((button) => button.addEventListener("click", async () => {
      try {
        await api.put(`/horario/jornadas/${encodeURIComponent(button.dataset.scheduleToggle)}`, { ativo: button.dataset.active !== "true" });
        await loadSchedules();
      } catch (error) {
        report("schedules-list", error);
      }
    }));
  } catch (error) {
    report("schedules-list", error);
  }
}

async function createBlock(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const body = {
    barbeiro_id: Number(form.elements.barbeiro_id.value),
    inicio: form.elements.inicio.value,
    fim: form.elements.fim.value,
    tipo: form.elements.tipo.value,
    motivo: form.elements.motivo.value.trim() || null,
    ativo: true,
  };
  if (body.inicio >= body.fim) {
    return showMessage(byId("blocks-list"), "O fim do bloqueio deve ser posterior ao início.", "danger");
  }
  try {
    await api.post("/horario/bloqueios", body);
    form.elements.inicio.value = "";
    form.elements.fim.value = "";
    form.elements.motivo.value = "";
    await loadBlocks();
  } catch (error) {
    report("blocks-list", error);
  }
}

async function loadBlocks() {
  const barberId = byId("block-barber")?.value;
  if (!barberId) return;
  try {
    const records = await api.get(`/horario/bloqueios/${encodeURIComponent(barberId)}`);
    const container = byId("blocks-list");
    container.innerHTML = records.map((record) => `
      <article class="management-item">
        <div><strong>${escapeHtml(record.tipo)}</strong><p>${escapeHtml(record.motivo || "Sem motivo")} · ${new Date(record.inicio).toLocaleString("pt-BR")}–${new Date(record.fim).toLocaleString("pt-BR")}</p></div>
        <button type="button" class="btn btn-danger" data-block-delete="${record.id}">Remover</button>
      </article>
    `).join("") || emptyHtml("Nenhum bloqueio cadastrado.");
    container.querySelectorAll("[data-block-delete]").forEach((button) => button.addEventListener("click", async () => {
      try {
        await api.delete(`/horario/bloqueios/${encodeURIComponent(button.dataset.blockDelete)}`);
        await loadBlocks();
      } catch (error) {
        report("blocks-list", error);
      }
    }));
  } catch (error) {
    report("blocks-list", error);
  }
}

async function createManualAppointment(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const userId = form.elements.user_id.value;
  const customerName = form.elements.nome_cliente.value.trim();
  if (Boolean(userId) === Boolean(customerName)) {
    showMessage(byId("manual-message"), "Selecione um cliente cadastrado ou informe o nome de um cliente avulso.", "danger");
    return;
  }
  const body = {
    service_id: Number(form.elements.service_id.value),
    barbeiro_id: Number(form.elements.barbeiro_id.value),
    data_hora: form.elements.data_hora.value,
  };
  if (userId) body.user_id = Number(userId);
  else body.nome_cliente = customerName;
  try {
    await api.post("/admin/agendamentos", body);
    form.reset();
    showMessage(byId("manual-message"), "Agendamento manual criado.", "success");
  } catch (error) {
    report("manual-message", error);
  }
}

async function loadInstitutionalInfo() {
  try {
    const info = await api.get("/informacoes/", { auth: false });
    institutionalInfoExists = true;
    const form = byId("institutional-form");
    Object.entries({
      nome: info.nome,
      endereco: info.endereco,
      telefone: info.telefone,
      email: info.email,
      site: info.site,
      dias_atendimento: info.dias_atendimento,
      horario_funcionamento: info.horario_funcionamento,
      endereco_maps: info.endereco_maps,
    }).forEach(([field, value]) => { form.elements[field].value = value || ""; });
  } catch (error) {
    if (error.status === 404) {
      institutionalInfoExists = false;
      return;
    }
    report("institutional-form", error);
  }
}

async function saveInstitutionalInfo(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const body = Object.fromEntries(new FormData(form).entries());
  ["site", "email", "endereco_maps"].forEach((key) => { if (!body[key]) body[key] = null; });
  try {
    if (institutionalInfoExists) await api.put("/informacoes/", body);
    else {
      await api.post("/informacoes/", body);
      institutionalInfoExists = true;
    }
    showMessage(form, "Informações institucionais atualizadas.", "success");
  } catch (error) {
    report("institutional-form", error);
  }
}

async function loadReviews() {
  try {
    const reviews = await api.get("/admin/avaliacoes");
    const container = byId("reviews-admin-list");
    container.innerHTML = reviews.map((review) => `
      <article class="management-item">
        <div><strong>${"★".repeat(review.nota)}${"☆".repeat(5 - review.nota)}</strong><p>${escapeHtml(review.comentario || "Sem comentário")} · ${new Date(review.criada_em).toLocaleDateString("pt-BR")}</p></div>
        <button type="button" class="btn ${review.oculta ? "btn-primary" : "btn-danger"}" data-review-toggle="${review.id}" data-hidden="${review.oculta}">${review.oculta ? "Exibir" : "Ocultar"}</button>
      </article>
    `).join("") || emptyHtml("Nenhuma avaliação cadastrada.");
    container.querySelectorAll("[data-review-toggle]").forEach((button) => button.addEventListener("click", async () => {
      try {
        await api.patch(`/admin/avaliacoes/${encodeURIComponent(button.dataset.reviewToggle)}/ocultar`, undefined, {
          params: { ocultar: button.dataset.hidden !== "true" },
        });
        await loadReviews();
      } catch (error) {
        report("reviews-admin-list", error);
      }
    }));
  } catch (error) {
    report("reviews-admin-list", error);
  }
}

function fillSelect(id, items, label, placeholder = null) {
  const select = byId(id);
  if (!select) return;
  select.replaceChildren();
  if (placeholder) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    option.selected = true;
    select.append(option);
  }
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = label(item);
    select.append(option);
  });
  select.disabled = items.length === 0 && !placeholder;
}

function report(id, error) {
  console.error(`Erro ao atualizar ${id}:`, error);
  showMessage(byId(id), error.message || "Não foi possível concluir a operação.", "danger");
}

function showMessage(container, message, kind) {
  if (!container) return;
  const alert = document.createElement("p");
  alert.className = `alert alert-${kind}`;
  alert.setAttribute("role", "status");
  alert.textContent = message;
  container.prepend(alert);
}

function emptyHtml(message) {
  return `<p class="text-muted">${escapeHtml(message)}</p>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value));
}
