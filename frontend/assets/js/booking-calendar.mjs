import { isBookableDate, isBookableDateTime } from "./booking-date.mjs";

export function nextAvailableDays(days, after) {
  return days.filter(day => day.date > after && day.slots.length).slice(0, 3);
}

// Both successes and failures belong to one context; stale responses never paint.
export function latestRequest() {
  let version = 0;
  const guarded = async task => {
    const own = ++version;
    try { const value = await task(); return { current: own === version, value }; }
    catch (error) { return { current: own === version, error }; }
  };
  guarded.invalidate = () => { version += 1; };
  return guarded;
}

const labels = { off: "Sem expediente", blocked: "Bloqueado / folga", full: "Sem vagas", available: "Com vagas" };
const dateLabel = day => new Intl.DateTimeFormat("pt-BR", {
  weekday: "short", day: "2-digit", month: "2-digit", timeZone: "UTC",
}).format(new Date(day + "T12:00:00Z"));
function element(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}

export async function mountBookingCalendar(api, params, onError) {
  const calendar = document.getElementById("booking-calendar");
  const slots = document.getElementById("slots-container");
  const dateInput = document.getElementById("date-input");
  const serviceSelect = document.getElementById("booking-service");
  const barberSelect = document.getElementById("booking-barber");
  const status = document.getElementById("calendar-status");
  const retry = document.getElementById("calendar-retry");
  const request = latestRequest();
  const slotRequest = latestRequest();
  let days = [];
  let initialized = false;
  const appointmentId = params.get("appointment_id");
  const context = () => ({ service_id: serviceSelect.value, barbeiro_id: barberSelect.value,
    ...(appointmentId ? { appointment_id: appointmentId } : {}) });
  const message = text => slots.replaceChildren(element("p", text, "empty-state"));
  const fail = error => { onError(error); status.textContent = error.message; };

  function render() {
    calendar.replaceChildren();
    days.forEach(day => {
      const button = element("button", "", "booking-day btn btn-ghost");
      button.type = "button";
      button.dataset.date = day.date;
      button.dataset.status = day.status;
      button.disabled = !isBookableDate(day.date) || ["off", "blocked"].includes(day.status);
      button.setAttribute("aria-pressed", String(dateInput.value === day.date));
      button.append(element("span", dateLabel(day.date)), element("small", labels[day.status]));
      button.addEventListener("click", () => selectDay(day.date));
      calendar.append(button);
    });
  }

  function suggest(after) {
    const future = nextAvailableDays(days, after).filter(day =>
      isBookableDate(day.date) && day.slots.some(slot => isBookableDateTime(slot.data_hora)));
    slots.append(element("p", future.length
      ? "Não encontramos horários disponíveis para este dia. Confira as próximas datas com vagas."
      : "Não há próximas datas com vagas na janela de agendamento permitida."));
    for (const day of future) {
      const button = element("button", dateLabel(day.date), "btn btn-ghost");
      button.type = "button";
      button.dataset.suggestion = day.date;
      button.addEventListener("click", () => selectDay(day.date));
      slots.append(button);
    }
  }

  async function selectDay(day) {
    const entry = days.find(item => item.date === day);
    if (!entry || !isBookableDate(day) || ["off", "blocked"].includes(entry.status)) return;
    if (dateInput.value === day && slots.getAttribute("aria-busy") === "true") return;
    dateInput.value = day;
    render();
    message("Buscando horários disponíveis…");
    slots.setAttribute("aria-busy", "true");
    const response = await slotRequest(() => api.get("/appointments/disponiveis", { params: { ...context(), data: day } }));
    if (!response.current) return;
    slots.setAttribute("aria-busy", "false");
    if (response.error) { message(response.error.message); onError(response.error); return; }
    slots.replaceChildren();
    const available = response.value.filter(slot => isBookableDateTime(slot.data_hora));
    // Keep suggestions consistent with a day that filled since the window read.
    entry.slots = available;
    entry.status = available.length ? "available" : "full";
    render();
    if (!available.length) { suggest(day); return; }
    const list = element("div", "", "slot-grid");
    for (const slot of available) {
      const link = element("a", slot.horario, "btn btn-ghost slot-button");
      const query = new URLSearchParams({ ...context(), date_time: slot.data_hora });
      if (appointmentId) query.set("appointment_id", appointmentId);
      link.href = "client-confirm.html?" + query;
      list.append(link);
    }
    slots.append(list);
  }

  async function loadContext(reloadBarbers = false) {
    slotRequest.invalidate();
    dateInput.value = "";
    days = [];
    render();
    message("Selecione uma data para consultar os horários.");
    slots.setAttribute("aria-busy", "false");
    calendar.setAttribute("aria-busy", "true");
    status.textContent = "Consultando expediente e disponibilidade…";
    retry.disabled = true;
    barberSelect.disabled = true;
    const response = await request(async () => {
      const serviceId = serviceSelect.value;
      const professionals = reloadBarbers
        ? await api.get(`/barbeiro-servico/servico/${encodeURIComponent(serviceId)}/barbeiros`) : null;
      const barberId = professionals
        ? (professionals.find(p => String(p.barbeiro_id) === barberSelect.value) || professionals[0])?.barbeiro_id
        : barberSelect.value;
      const data = barberId ? await api.get("/appointments/calendario", {
        params: { service_id: serviceId, barbeiro_id: barberId,
          ...(appointmentId ? { appointment_id: appointmentId } : {}) },
      }) : null;
      return { professionals, barberId, data };
    });
    if (!response.current) return;
    calendar.setAttribute("aria-busy", "false");
    retry.disabled = false;
    if (response.error) { fail(response.error); return; }
    const { professionals, barberId, data } = response.value;
    if (professionals) {
      barberSelect.replaceChildren(...professionals.map(p => {
        const option = element("option", p.barbeiro_nome || `Profissional ${p.barbeiro_id}`);
        option.value = p.barbeiro_id; return option;
      }));
    }
    if (barberId) barberSelect.value = barberId;
    barberSelect.disabled = Boolean(appointmentId) || !barberId;
    days = data?.days || [];
    status.textContent = data ? "Expediente individual. Datas sem expediente ou bloqueadas não podem ser selecionadas."
      : "Nenhum profissional disponível para este serviço.";
    render();
    if (data && !days.some(day => day.slots.length)) message("Não há vagas na janela de agendamento permitida.");
    // Keep direct links/back navigation aligned with the chosen service and professional.
    params.set("service_id", serviceSelect.value);
    params.set("barbeiro_id", barberSelect.value);
    history.replaceState(null, "", "?" + params);
    const back = document.getElementById("change-professional");
    back.href = appointmentId ? "client-appointments.html"
      : "client-profissional.html?service_id=" + encodeURIComponent(serviceSelect.value);
    if (appointmentId) back.textContent = "← Meus agendamentos";
  }

  retry.addEventListener("click", () => initialized ? loadContext(true) : window.location.reload());
  try {
    const services = await api.get("/services/", { auth: false });
    serviceSelect.replaceChildren(...services.map(service => {
      const option = element("option", service.nome);
      option.value = service.id; return option;
    }));
    if (!services.some(s => String(s.id) === params.get("service_id"))) throw new Error("Serviço indisponível.");
    serviceSelect.value = params.get("service_id");
    const initial = element("option", "Profissional selecionado");
    initial.value = params.get("barbeiro_id");
    barberSelect.append(initial);
    serviceSelect.disabled = Boolean(appointmentId);
    serviceSelect.addEventListener("change", () => loadContext(true));
    barberSelect.addEventListener("change", () => loadContext());
    initialized = true;
    await loadContext(true);
  } catch (error) { fail(error); }
}
