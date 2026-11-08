// agenda_admin.js
// Lógica do painel administrativo: gera os dias da semana atual (domingo a sábado)
// e busca na API (FastAPI) os agendamentos do dia selecionado.
//
// Navegação semanal com seleção de dias e proteção contra respostas antigas.
//
// Toda comunicação com o backend passa por api.js (apiGet/apiPost/...).
// Este arquivo não conhece API_BASE nem faz fetch() diretamente.

import { api, getCurrentUser, getToken, logout } from "./api.js";
import { escapeHtml } from "./escape-html.mjs";
import { summarizeDay } from "./staff-summary.mjs";
import { openStaffAction } from "./staff-action.mjs";

const USER_KEY = "user";

const dateRoll = document.getElementById("dateRoll");
const prevBtn = document.getElementById("prevDates");
const nextBtn = document.getElementById("nextDates");
const agendaList = document.getElementById("agendaList");
const agendaDayLabel = document.getElementById("agendaDayLabel");
const userNameEl = document.getElementById("userName");
const logoutLink = document.querySelector(".btn-logout");

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

let weekDays = [];
let selectedDate = new Date();
let currentUser = null;
let referenceMaps = { services: new Map(), clients: new Map(), barbers: new Map() };
let agendaRequestId = 0;
let displayedAppointments = null;




function getStartOfWeek(date) {
    const copy = new Date(date);
    const day = copy.getDay();
    copy.setDate(copy.getDate() - day);
    copy.setHours(0, 0, 0, 0);
    return copy;
}


function generateWeekDays(referenceDate) {
    const start = getStartOfWeek(referenceDate);
    return Array.from({ length: 7 }, (_, index) => {
        const date = new Date(start);
        date.setDate(start.getDate() + index);
        return date;
    });
}

function sameDay(a, b) {
    return a.getFullYear() === b.getFullYear() &&
        a.getMonth() === b.getMonth() &&
        a.getDate() === b.getDate();
}


function formatDateForAPI(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function formatDateForDisplay(date) {
    return new Intl.DateTimeFormat("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "2-digit",
        year: "numeric"
    }).format(date);
}

function toTitleCase(value) {
    return String(value ?? "")
        .trim()
        .replace(/\s+/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

function clearSession() {
    logout();
}

function setUserName() {
    if (!userNameEl) return;
    currentUser = getCurrentUser();
    userNameEl.textContent = toTitleCase(currentUser?.nome || currentUser?.name || "Equipe");
}



function renderDateRoll() {
    if (!dateRoll) return;

    dateRoll.innerHTML = "";

    weekDays.forEach((date) => {
        const item = document.createElement("button");
        item.type = "button";
        item.classList.add("date-item");
        item.dataset.date = formatDateForAPI(date);

        if (sameDay(date, selectedDate)) {
            item.classList.add("selected");
        }

        if (sameDay(date, new Date())) {
            item.classList.add("today");
        }

        item.setAttribute("aria-pressed", String(sameDay(date, selectedDate)));
        item.setAttribute("aria-label", formatDateForDisplay(date));
        item.innerHTML = `
            <span class="date-weekday">${DIAS_SEMANA[date.getDay()]}</span>
            <span class="date-number">${String(date.getDate()).padStart(2, "0")}</span>
        `;

        item.addEventListener("click", () => {
            selecionarDia(date);
            focusSelectedDate();
        });
        item.addEventListener("keydown", (event) => {
            const offsets = { ArrowLeft: -1, ArrowRight: 1, PageUp: -7, PageDown: 7 };
            let offset = offsets[event.key];
            if (event.key === "Home") offset = -date.getDay();
            if (event.key === "End") offset = 6 - date.getDay();
            if (offset == null) return;
            event.preventDefault();
            const target = new Date(date);
            target.setDate(target.getDate() + offset);
            selecionarDia(target);
            focusSelectedDate();
        });
        dateRoll.appendChild(item);
    });

    if (prevBtn) prevBtn.disabled = false;
    if (nextBtn) nextBtn.disabled = false;
    revealSelectedDate();
}

function revealSelectedDate() {
    // Reveal the selected day within the rail without moving page scroll/focus.
    const selected = dateRoll.querySelector(".selected");
    if (selected) {
        dateRoll.scrollLeft += selected.getBoundingClientRect().left - dateRoll.getBoundingClientRect().left
            - (dateRoll.clientWidth - selected.clientWidth) / 2;
    }
}

function focusSelectedDate() {
    const selected = Array.from(dateRoll.children).find(button => button.dataset.date === formatDateForAPI(selectedDate));
    selected?.focus();
}

function selecionarDia(date) {
    selectedDate = new Date(date);
    weekDays = generateWeekDays(selectedDate);
    renderDateRoll();
    carregarAgendaDoDia(selectedDate);
}

function navegarSemana(offset) {
    const target = new Date(selectedDate);
    target.setDate(target.getDate() + offset * 7);
    selecionarDia(target);
}



function normalizeTime(value) {
    if (!value) return "--:--";

    if (typeof value === "string") {
        if (/^\d{2}:\d{2}$/.test(value)) return value;

        const isoMatch = value.match(/T?(\d{1,2}):(\d{2})/);
        if (isoMatch) {
            const hour = String(Number(isoMatch[1])).padStart(2, "0");
            const minutes = isoMatch[2];
            return `${hour}:${minutes}`;
        }

        return value.substring(0, 5);
    }

    return "--:--";
}

function normalizeAppointment(item) {
    const customer = item?.cliente?.nome || item?.nome_cliente || item?.cliente_nome || item?.cliente || item?.customer?.nome || item?.customer_name || referenceMaps.clients.get(item?.user_id) || `Cliente #${item?.user_id ?? ""}`;
    const service = item?.servico?.nome || item?.servico_nome || item?.servico || item?.service?.nome || item?.service_name || referenceMaps.services.get(item?.service_id) || `Serviço #${item?.service_id ?? ""}`;
    const professional = item?.profissional?.nome || item?.profissional_nome || item?.profissional || item?.barbeiro?.nome || item?.barbeiro || item?.employee?.nome || item?.employee_name || referenceMaps.barbers.get(item?.barbeiro_id) || `Equipe #${item?.barbeiro_id ?? ""}`;

    return {
        id: item?.id ?? `${item?.horario ?? "agenda"}-${Math.random().toString(16).slice(2)}`,
        horario: normalizeTime(item?.horario ?? item?.hora ?? item?.time ?? item?.inicio ?? item?.start_time ?? item?.agenda_hora ?? item?.data_hora),
        cliente: String(customer),
        servico: String(service),
        profissional: String(professional),
        status: String(item?.status ?? item?.estado ?? "pendente").toLowerCase(),
        preco: Number(item?.preco ?? 0),
        valorCobrado: item?.valor_cobrado == null ? null : Number(item.valor_cobrado)
    };
}

function normalizeAgendaResponse(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.agendamentos)) return payload.agendamentos;
    if (payload && Array.isArray(payload.appointments)) return payload.appointments;
    if (payload && Array.isArray(payload.items)) return payload.items;
    if (payload && Array.isArray(payload.data)) return payload.data;
    return [];
}

function getStatusLabel(status) {
    const labels = {
        confirmado: "Confirmado",
        pendente: "Pendente",
        cancelado: "Cancelado",
        cancelada: "Cancelado",
        falta: "Falta",
        avaliado: "Avaliado",
        concluido: "Concluído",
        finalizado: "Finalizado"
    };

    return labels[String(status || "").toLowerCase()] || toTitleCase(status || "Pendente");
}

function renderAgendaMessage(message, type = "info") {
    if (!agendaList) return;

    agendaList.innerHTML = `
        <div class="agenda-empty ${type}">
            <span>${escapeHtml(message)}</span>
        </div>
    `;
}

function renderizarAgendamentos(agendamentos) {
    if (!agendaList) return;

    const lista = [...agendamentos]
        .map(normalizeAppointment)
        .sort((a, b) => {
            const primeiraHora = a.horario === "--:--" ? 24 * 60 : Number(a.horario.split(":")[0]) * 60 + Number(a.horario.split(":")[1]);
            const segundaHora = b.horario === "--:--" ? 24 * 60 : Number(b.horario.split(":")[0]) * 60 + Number(b.horario.split(":")[1]);
            return primeiraHora - segundaHora;
        });

    const summary = document.getElementById('agenda-summary');
    if (summary) {
        const day = summarizeDay(lista, formatDateForAPI(selectedDate));
        summary.innerHTML = `<div><span>Reservas na data</span><strong>${day.total}</strong></div><div><span>Pendentes de conclusão</span><strong>${day.pending}</strong></div><div><span>Concluídos</span><strong>${day.completed}</strong></div><div class="staff-next"><span>Próximo horário reservado na data</span><strong>${escapeHtml(day.next ? `${day.next.horario} · ${day.next.cliente} · ${day.next.servico}` : 'Nenhum horário futuro nesta data')}</strong></div>`;
    }
    if (!lista.length) {
        renderAgendaMessage("Nenhuma reserva nesta data. Consulte o expediente e os bloqueios antes de marcar um horário.");
        return;
    }

    const linhas = lista.map((item) => {
        const statusKey = String(item.status || "pendente").toLowerCase();
        const statusLabel = getStatusLabel(statusKey);
        const isActive = ["pendente", "confirmado"].includes(statusKey);
        const actions = isActive && (currentUser?.role === "admin" || currentUser?.role === "barbeiro")
            ? `<div class="agenda-actions">
                <button type="button" class="btn btn-sm" data-appointment-status="concluido" data-appointment-id="${escapeHtml(item.id)}">Concluir atendimento</button>
                <button type="button" class="btn btn-sm btn-ghost" data-appointment-status="falta" data-appointment-id="${escapeHtml(item.id)}">Marcar ausência</button>
                <button type="button" class="btn btn-sm btn-danger" data-appointment-status="cancelado" data-appointment-id="${escapeHtml(item.id)}">Cancelar agendamento</button>
            </div>`
            : "";

        return `
            <tr class="agenda-row" role="row">
                <td role="cell" data-label="Horário"><span class="time-pill">${escapeHtml(item.horario)}</span></td>
                <td role="cell" data-label="Cliente">${escapeHtml(item.cliente)}</td>
                <td role="cell" data-label="Serviço">${escapeHtml(item.servico)}</td>
                <td role="cell" data-label="Profissional">${escapeHtml(item.profissional)}</td>
                <td role="cell" data-label="Status"><span class="status-badge status-${escapeHtml(statusKey)}">${escapeHtml(statusLabel)}</span></td>
                <td role="cell" data-label="Ações">${actions}</td>
            </tr>
        `;
    }).join("");

    agendaList.innerHTML = `
        <div class="agenda-table-wrapper">
            <table class="agenda-table" role="table" aria-label="Atendimentos do dia">
                <thead role="rowgroup">
                    <tr role="row">
                        <th role="columnheader" scope="col">Horário</th>
                        <th role="columnheader" scope="col">Cliente</th>
                        <th role="columnheader" scope="col">Serviço</th>
                        <th role="columnheader" scope="col">Profissional</th>
                        <th role="columnheader" scope="col">Status</th>
                        <th role="columnheader" scope="col">Ações</th>
                    </tr>
                </thead>
                <tbody role="rowgroup">
                    ${linhas}
                </tbody>
            </table>
        </div>
    `;
    agendaList.querySelectorAll("[data-appointment-status]").forEach((button) => {
        button.addEventListener("click", () => {
            const requestId = agendaRequestId;
            displayedAppointments = null;
            const appointment = lista.find(item => String(item.id) === button.dataset.appointmentId);
            if (!appointment) return;
            return openStaffAction({ appointment, status: button.dataset.appointmentStatus,
                dateLabel: formatDateForDisplay(selectedDate), opener: button,
                isCurrent: () => requestId === agendaRequestId,
                submit: async update => {
                    await api.put(`/appointments/${encodeURIComponent(appointment.id)}`, update);
                    if (requestId !== agendaRequestId) return;
                    await carregarAgendaDoDia(selectedDate);
                    const feedback = document.getElementById('agenda-feedback');
                    if (feedback) { feedback.textContent = `Atendimento de ${appointment.cliente}: ${getStatusLabel(update.status)}. Alteração salva.`; feedback.hidden = false; }
                },
            });
        });
    });
}


async function carregarAgendaDoDia(date) {
    if (!agendaDayLabel) return;

    const requestId = ++agendaRequestId;
    displayedAppointments = null;
    const summary = document.getElementById('agenda-summary');
    if (summary) summary.innerHTML = '';
    const feedback = document.getElementById('agenda-feedback');
    if (feedback) feedback.hidden = true;
    const picker = document.getElementById('agenda-date');
    if (picker) picker.value = formatDateForAPI(date);
    const dataFormatada = formatDateForAPI(date);
    agendaDayLabel.textContent = formatDateForDisplay(date);
    renderAgendaMessage("Carregando agenda…");

    if (!getToken()) {
        renderAgendaMessage("Sessão expirada. Faça login novamente.", "error");
        return;
    }

    try {
        const endpoint = currentUser?.role === "barbeiro" ? "/admin/me/agenda" : "/admin/agenda";
        const responseBody = await api.get(endpoint, { params: { data: dataFormatada } });
        if (requestId !== agendaRequestId) return;
        const agendamentos = normalizeAgendaResponse(responseBody);
        displayedAppointments = agendamentos;
        renderizarAgendamentos(agendamentos);
    } catch (error) {
        if (requestId !== agendaRequestId) return;
        console.error("Falha ao carregar agenda do dia:", error);

        let message = "Não foi possível carregar a agenda do dia.";
        if (error.status === 401) {
            message = "Sessão expirada ou token inválido. Faça login novamente.";
        } else if (error.status === 404) {
            message = "Rota da agenda indisponível no backend.";
        } else if (error.status === 500) {
            message = "Erro interno do servidor. Tente novamente em alguns instantes.";
        } else if (!error.status) {
            message = "Não foi possível conectar com o backend. Verifique a API e tente novamente.";
        }

        renderAgendaMessage(message, "error");
    }
}

// --- Inicialização ------------------------------------------------------

function init() {
    if (!getToken()) {
        window.location.href = "login.html?redirect=admin.html";
        return;
    }
    setUserName();
    if (logoutLink) logoutLink.addEventListener("click", clearSession);
    // Once the user interacts with the table, keep their input and focus intact.
    // Reference names will be used normally on the next agenda load.
    agendaList?.addEventListener("focusin", () => { displayedAppointments = null; });
    agendaList?.addEventListener("input", () => { displayedAppointments = null; });
    prevBtn?.addEventListener("click", () => navegarSemana(-1));
    nextBtn?.addEventListener("click", () => navegarSemana(1));
    window.addEventListener('resize', revealSelectedDate, { passive: true });
    document.getElementById('agenda-today')?.addEventListener('click', () => selecionarDia(new Date()));
    document.getElementById('agenda-retry')?.addEventListener('click', () => carregarAgendaDoDia(selectedDate));
    document.getElementById('agenda-date')?.addEventListener('change', event => {
        const value = event.target.value;
        if (/^\d{4}-\d{2}-\d{2}$/.test(value)) selecionarDia(new Date(value + 'T12:00:00'));
    });
    weekDays = generateWeekDays(selectedDate);
    renderDateRoll();
    carregarAgendaDoDia(selectedDate);

    const references = currentUser?.role === "admin"
        ? [["services", "/services/"], ["clients", "/users/"], ["barbers", "/users/barbeiros"]]
        : currentUser?.role === "barbeiro" ? [["services", "/services/"]] : [];
    if (currentUser?.role === "barbeiro" && currentUser.id != null) {
        referenceMaps.barbers = new Map([[currentUser.id, currentUser.nome || currentUser.name || "Você"]]);
    }
    references.forEach(([key, endpoint]) => {
        api.get(endpoint).then((items) => {
            referenceMaps[key] = new Map(items.map((item) => [item.id, item.nome]));
            // Only enrich the currently displayed successful response, never a
            // pending day or an agenda error with an earlier day's appointments.
            if (displayedAppointments !== null) renderizarAgendamentos(displayedAppointments);
        }).catch((error) => {
            console.error(`Falha ao carregar referência da agenda (${endpoint}):`, error);
        });
    });
}

document.addEventListener("DOMContentLoaded", init);
