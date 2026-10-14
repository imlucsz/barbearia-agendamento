import { api, clearToken, getToken, logout } from "./api.js";

const params = new URLSearchParams(window.location.search);
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

document.addEventListener("DOMContentLoaded", () => {
  const year = document.getElementById("current-year");
  if (year) year.textContent = new Date().getFullYear();
  document.getElementById("logout-link")?.addEventListener("click", (event) => {
    event.preventDefault();
    logout();
  });

  const page = document.body.dataset.page;
  const actions = {
    services: loadServices,
    professionals: loadProfessionals,
    date: setupDatePicker,
    confirm: loadConfirmation,
    appointments: loadAppointments,
    dashboard: loadDashboard,
    account: loadAccount,
    evaluate: loadEvaluation,
  };
  if (actions[page]) actions[page]();
});

function requireLogin(destination = `${window.location.pathname.split("/").pop()}${window.location.search}`) {
  if (getToken()) return true;
  window.location.href = `login.html?redirect=${encodeURIComponent(destination)}`;
  return false;
}

async function loadServices() {
  const container = document.getElementById("services-list");
  try {
    const services = await api.get("/services/", { auth: false });
    const requestedService = params.get("service_id");
    if (requestedService) {
      if (!services.some((service) => String(service.id) === String(requestedService))) {
        throw new Error("O serviço selecionado não está disponível.");
      }
      const destination = `client-profissional.html?service_id=${encodeURIComponent(requestedService)}`;
      if (!getToken()) {
        requireLogin(destination);
        return;
      }
      window.location.href = destination;
      return;
    }
    container.replaceChildren();
    if (!services.length) return showEmpty(container, "Nenhum serviço disponível no momento.");
    services.forEach((service) => {
      const card = document.createElement("article");
      card.className = "card service-selection-card";
      const title = document.createElement("h2");
      title.textContent = service.nome;
      const price = document.createElement("strong");
      price.textContent = currency.format(Number(service.preco));
      const duration = document.createElement("p");
      duration.textContent = `${service.duracao_minutos} minutos`;
      const link = document.createElement("a");
      link.className = "btn";
      link.href = `client-profissional.html?service_id=${encodeURIComponent(service.id)}`;
      link.textContent = "Escolher profissional";
      link.addEventListener("click", (event) => {
        if (!getToken()) {
          event.preventDefault();
          requireLogin(link.getAttribute("href"));
        }
      });
      card.append(title, price, duration, link);
      container.append(card);
    });
  } catch (error) {
    console.error("Falha ao carregar catálogo:", error);
    showError(container, error.message);
  }
}

async function loadProfessionals() {
  const container = document.getElementById("profissional-content");
  const serviceId = params.get("service_id");
  if (!serviceId) {
    window.location.href = "client-services.html";
    return;
  }
  if (!requireLogin()) return;
  try {
    const professionals = await api.get(`/barbeiro-servico/servico/${encodeURIComponent(serviceId)}/barbeiros`);
    container.replaceChildren();
    if (!professionals.length) return showEmpty(container, "Ainda não há profissionais associados a este serviço.");
    professionals.forEach((item) => {
      const card = document.createElement("article");
      card.className = "card professional-card";
      const name = document.createElement("h2");
      name.textContent = item.barbeiro_nome || `Profissional ${item.barbeiro_id}`;
      const link = document.createElement("a");
      link.className = "btn";
      link.href = `client-date.html?service_id=${encodeURIComponent(serviceId)}&barbeiro_id=${encodeURIComponent(item.barbeiro_id)}`;
      link.textContent = "Ver horários";
      card.append(name, link);
      container.append(card);
    });
  } catch (error) {
    console.error("Falha ao carregar profissionais:", error);
    handleAuthError(error);
    showError(container, error.message);
  }
}

function setupDatePicker() {
  if (!requireLogin()) return;
  const serviceId = params.get("service_id");
  const barberId = params.get("barbeiro_id");
  const appointmentId = params.get("appointment_id");
  const dateInput = document.getElementById("date-input");
  const slots = document.getElementById("slots-container");
  if (!serviceId || !barberId) {
    window.location.href = "client-services.html";
    return;
  }

  const today = localDateString(new Date());
  const maxDate = new Date();
  maxDate.setDate(maxDate.getDate() + 14);
  dateInput.min = today;
  dateInput.max = localDateString(maxDate);
  dateInput.addEventListener("change", () => loadSlots(dateInput.value));

  async function loadSlots(day) {
    if (!day) {
      showEmpty(slots, "Selecione uma data para ver os horários disponíveis.");
      return;
    }
    slots.replaceChildren();
    const loading = document.createElement("p");
    loading.className = "text-muted";
    loading.textContent = "Buscando horários disponíveis…";
    slots.append(loading);
    try {
      const available = await api.get("/appointments/disponiveis", {
        params: { service_id: serviceId, data: day, barbeiro_id: barberId },
      });
      slots.replaceChildren();
      if (available.length === 0) return showEmpty(slots, "Nenhum horário disponível nesta data. Tente outro dia.");
      const list = document.createElement("div");
      list.className = "slot-grid";
      available.forEach((slot) => {
        const button = document.createElement("a");
        button.className = "btn btn-ghost slot-button";
        const time = slot.horario || new Date(slot.data_hora).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
        button.textContent = time;
        button.href = `client-confirm.html?service_id=${encodeURIComponent(serviceId)}&barbeiro_id=${encodeURIComponent(barberId)}&date_time=${encodeURIComponent(slot.data_hora)}${appointmentId ? `&appointment_id=${encodeURIComponent(appointmentId)}` : ""}`;
        list.append(button);
      });
      slots.append(list);
    } catch (error) {
      console.error("Falha ao carregar horários:", error);
      handleAuthError(error);
      showError(slots, error.message);
    }
  }
}

async function loadConfirmation() {
  if (!requireLogin()) return;
  const serviceId = params.get("service_id");
  const barberId = params.get("barbeiro_id");
  const dateTime = params.get("date_time");
  const appointmentId = params.get("appointment_id");
  const container = document.getElementById("confirmation-content");
  const button = document.getElementById("confirm-btn");
  if (!serviceId || !barberId || !dateTime) {
    window.location.href = "client-services.html";
    return;
  }

  try {
    const [service, professionals] = await Promise.all([
      api.get(`/services/${encodeURIComponent(serviceId)}`, { auth: false }),
      api.get(`/barbeiro-servico/servico/${encodeURIComponent(serviceId)}/barbeiros`),
    ]);
    const professional = professionals.find((item) => String(item.barbeiro_id) === String(barberId));
    if (!professional) throw new Error("O profissional não está disponível para esse serviço.");
    container.replaceChildren();
    [
      ["Serviço", service.nome],
      ["Profissional", professional.barbeiro_nome || `Profissional ${barberId}`],
      ["Data e hora", new Date(dateTime).toLocaleString("pt-BR")],
      ["Duração", `${service.duracao_minutos} minutos`],
      ["Valor", currency.format(Number(service.preco))],
    ].forEach(([label, value]) => {
      const row = document.createElement("p");
      const strong = document.createElement("strong");
      strong.textContent = `${label}: `;
      row.append(strong, document.createTextNode(value));
      container.append(row);
    });

    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        if (appointmentId) {
          const previous = await api.get(`/appointments/${encodeURIComponent(appointmentId)}`);
          if (
            String(previous.service_id) !== String(serviceId) ||
            String(previous.barbeiro_id) !== String(barberId)
          ) {
            throw new Error("Os dados do reagendamento não correspondem ao agendamento original.");
          }
          await api.put(`/appointments/${encodeURIComponent(appointmentId)}`, { data_hora: dateTime });
        } else {
          await api.post("/appointments/", {
            service_id: Number(serviceId),
            barbeiro_id: Number(barberId),
            data_hora: dateTime,
          });
        }
        window.location.href = "client-appointments.html";
      } catch (error) {
        console.error("Falha ao confirmar agendamento:", error);
        showMessage(container, error.message, "danger");
        handleAuthError(error);
        button.disabled = false;
      }
    }, { once: true });
  } catch (error) {
    console.error("Falha ao carregar confirmação:", error);
    handleAuthError(error);
    showError(container, error.message);
    button.disabled = true;
  }
}

async function loadAppointments() {
  if (!requireLogin()) return;
  const container = document.getElementById("appointments-list");
  try {
    const appointments = await api.get("/appointments/");
    container.replaceChildren();
    if (!appointments.length) return showEmpty(container, "Você ainda não tem agendamentos.");
    appointments.forEach((appointment) => {
      const card = document.createElement("article");
      card.className = "card appointment-card";
      const title = document.createElement("h2");
      title.textContent = `Atendimento #${appointment.id}`;
      const details = document.createElement("div");
      details.className = "appointment-details";
      [
        ["Status", appointment.status],
        ["Data e hora", new Date(appointment.data_hora).toLocaleString("pt-BR")],
        ["Duração", `${appointment.duracao_minutos} min`],
        ["Valor", currency.format(Number(appointment.preco))],
      ].forEach(([label, value]) => {
        const row = document.createElement("p");
        const strong = document.createElement("strong");
        strong.textContent = `${label}: `;
        row.append(strong, document.createTextNode(value));
        details.append(row);
      });
      const actions = document.createElement("div");
      actions.className = "appointment-actions";
      if (["pendente", "confirmado"].includes(appointment.status)) {
        const reschedule = document.createElement("a");
        reschedule.className = "btn btn-ghost";
        reschedule.href = `client-date.html?service_id=${appointment.service_id}&barbeiro_id=${appointment.barbeiro_id}&appointment_id=${appointment.id}`;
        reschedule.textContent = "Reagendar";
        const cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "btn btn-danger";
        cancel.textContent = "Cancelar";
        cancel.addEventListener("click", () => cancelAppointment(appointment.id, cancel));
        actions.append(reschedule, cancel);
      }
      if (appointment.status === "concluido") {
        const evaluate = document.createElement("a");
        evaluate.className = "btn";
        evaluate.href = `client-evaluate.html?appointment_id=${appointment.id}`;
        evaluate.textContent = "Avaliar atendimento";
        actions.append(evaluate);
      }
      card.append(title, details, actions);
      container.append(card);
    });
  } catch (error) {
    console.error("Falha ao carregar agendamentos:", error);
    handleAuthError(error);
    showError(container, error.message);
  }
}

async function cancelAppointment(id, button) {
  if (!window.confirm("Cancelar este agendamento? O cancelamento exige pelo menos 24 horas de antecedência.")) return;
  button.disabled = true;
  try {
    await api.put(`/appointments/${encodeURIComponent(id)}`, { status: "cancelado" });
    await loadAppointments();
  } catch (error) {
    console.error("Falha ao cancelar agendamento:", error);
    showMessage(document.getElementById("appointments-list"), error.message, "danger");
    handleAuthError(error);
    button.disabled = false;
  }
}

async function loadDashboard() {
  if (!requireLogin()) return;
  try {
    const user = await api.get("/auth/me");
    document.getElementById("user-name").textContent = user.nome;
  } catch (error) {
    console.error("Falha ao carregar perfil:", error);
    handleAuthError(error);
  }
}

async function loadAccount() {
  if (!requireLogin()) return;
  const container = document.getElementById("account-content");
  try {
    const user = await api.get("/auth/me");
    container.replaceChildren();
    const name = document.createElement("p");
    name.textContent = `Nome: ${user.nome}`;
    const email = document.createElement("p");
    email.textContent = `E-mail: ${user.email}`;
    container.append(name, email);
    document.getElementById("delete-account")?.addEventListener("click", async () => {
      if (!window.confirm("Excluir sua conta? Seus dados pessoais serão desativados/anonimizados.")) return;
      try {
        await api.delete("/users/me");
        clearToken();
        localStorage.removeItem("user");
        window.location.href = "index.html";
      } catch (error) {
        console.error("Falha ao excluir conta:", error);
        showMessage(container, error.message, "danger");
      }
    });
  } catch (error) {
    console.error("Falha ao carregar conta:", error);
    handleAuthError(error);
    showError(container, error.message);
  }
}

async function loadEvaluation() {
  if (!requireLogin()) return;
  const appointmentId = params.get("appointment_id");
  const details = document.getElementById("evaluate-content");
  const form = document.getElementById("evaluate-form");
  if (!appointmentId) {
    window.location.href = "client-appointments.html";
    return;
  }
  try {
    const appointment = await api.get(`/appointments/${encodeURIComponent(appointmentId)}`);
    if (appointment.status !== "concluido") {
      showError(details, "Só é possível avaliar atendimentos concluídos.");
      form.hidden = true;
      return;
    }
    details.replaceChildren();
    const message = document.createElement("p");
    message.textContent = `Avalie o atendimento #${appointment.id}, realizado em ${new Date(appointment.data_hora).toLocaleString("pt-BR")}.`;
    details.append(message);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector("[type=submit]");
      button.disabled = true;
      try {
        await api.post(`/appointments/${encodeURIComponent(appointmentId)}/avaliacao`, {
          nota: Number(form.elements.nota.value),
          comentario: form.elements.comentario.value.trim() || null,
        });
        window.location.href = "client-appointments.html";
      } catch (error) {
        console.error("Falha ao enviar avaliação:", error);
        showMessage(details, error.message, "danger");
        button.disabled = false;
      }
    });
  } catch (error) {
    console.error("Falha ao carregar avaliação:", error);
    handleAuthError(error);
    showError(details, error.message);
    form.hidden = true;
  }
}

function localDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function showEmpty(container, message) {
  container.replaceChildren();
  const text = document.createElement("p");
  text.className = "empty-state";
  text.textContent = message;
  container.append(text);
}

function showError(container, message) {
  showMessage(container, message || "Não foi possível carregar esta informação.", "danger");
}

function showMessage(container, message, kind) {
  const alert = document.createElement("p");
  alert.className = `alert alert-${kind}`;
  alert.setAttribute("role", "alert");
  alert.textContent = message;
  container.prepend(alert);
}

function handleAuthError(error) {
  if (error.status === 401) {
    clearToken();
    localStorage.removeItem("user");
    window.location.href = `login.html?redirect=${encodeURIComponent(`${window.location.pathname.split("/").pop()}${window.location.search}`)}`;
  }
}
