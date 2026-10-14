// agenda_admin.js
// Lógica do painel administrativo: gera os dias da semana atual (domingo a sábado)
// e busca na API (FastAPI) os agendamentos do dia selecionado.
//
// Por enquanto o admin só pode ver/gerenciar a semana atual — navegar para
// outras semanas fica desativado até vocês decidirem liberar isso.
//
// Toda comunicação com o backend passa por api.js (apiGet/apiPost/...).
// Este arquivo não conhece API_BASE nem faz fetch() diretamente.

import { api, getCurrentUser, getToken, logout } from "./api.js";

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

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
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

        if (sameDay(date, selectedDate)) {
            item.classList.add("selected");
        }

        if (sameDay(date, new Date())) {
            item.classList.add("today");
        }

        item.setAttribute("aria-pressed", String(sameDay(date, selectedDate)));
        item.innerHTML = `
            <span class="date-weekday">${DIAS_SEMANA[date.getDay()]}</span>
            <span class="date-number">${String(date.getDate()).padStart(2, "0")}</span>
        `;

        item.addEventListener("click", () => selecionarDia(date));
        dateRoll.appendChild(item);
    });

    if (prevBtn) prevBtn.disabled = true;
    if (nextBtn) nextBtn.disabled = true;
}

function selecionarDia(date) {
    selectedDate = new Date(date);
    renderDateRoll();
    carregarAgendaDoDia(selectedDate);
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
        horario: normalizeTime(item?.horario ?? item?.hora ?? item?.time ?? item?.inicio ?? item?.start_time ?? item?.agenda_hora),
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

    if (!lista.length) {
        renderAgendaMessage("Todas as vagas livres — nenhum horário marcado");
        return;
    }

    const linhas = lista.map((item) => {
        const statusKey = String(item.status || "pendente").toLowerCase();
        const statusLabel = getStatusLabel(statusKey);
        const isActive = ["pendente", "confirmado"].includes(statusKey);
        const actions = isActive && (currentUser?.role === "admin" || currentUser?.role === "barbeiro")
            ? `<div class="agenda-actions">
                <label class="visually-hidden" for="charged-${escapeHtml(item.id)}">Valor cobrado em reais</label>
                <input class="agenda-price-input" id="charged-${escapeHtml(item.id)}" type="number" min="0" step="0.01" value="${escapeHtml(item.valorCobrado ?? item.preco)}">
                <button type="button" class="btn btn-sm btn-ghost" data-appointment-status="concluido" data-appointment-id="${escapeHtml(item.id)}">Concluído</button>
                <button type="button" class="btn btn-sm btn-ghost" data-appointment-status="falta" data-appointment-id="${escapeHtml(item.id)}">Falta</button>
                <button type="button" class="btn btn-sm btn-danger" data-appointment-status="cancelado" data-appointment-id="${escapeHtml(item.id)}">Cancelar</button>
            </div>`
            : "";

        return `
            <tr class="agenda-row">
                <td data-label="Horário"><span class="time-pill">${escapeHtml(item.horario)}</span></td>
                <td data-label="Cliente">${escapeHtml(item.cliente)}</td>
                <td data-label="Serviço">${escapeHtml(item.servico)}</td>
                <td data-label="Profissional">${escapeHtml(item.profissional)}</td>
                <td data-label="Status"><span class="status-badge status-${statusKey}">${escapeHtml(statusLabel)}</span></td>
                <td data-label="Ações">${actions}</td>
            </tr>
        `;
    }).join("");

    agendaList.innerHTML = `
        <div class="agenda-table-wrapper">
            <table class="agenda-table">
                <thead>
                    <tr>
                        <th>Horário</th>
                        <th>Cliente</th>
                        <th>Serviço</th>
                        <th>Profissional</th>
                        <th>Status</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    ${linhas}
                </tbody>
            </table>
        </div>
    `;
    agendaList.querySelectorAll("[data-appointment-status]").forEach((button) => {
        button.addEventListener("click", async () => {
            button.disabled = true;
            try {
                const update = { status: button.dataset.appointmentStatus };
                if (update.status === "concluido") {
                    const amount = Number(agendaList.querySelector(`#charged-${CSS.escape(button.dataset.appointmentId)}`)?.value);
                    if (!Number.isFinite(amount) || amount < 0) throw new Error("Informe um valor cobrado válido.");
                    update.valor_cobrado = amount;
                }
                await api.put(`/appointments/${encodeURIComponent(button.dataset.appointmentId)}`, update);
                await carregarAgendaDoDia(selectedDate);
            } catch (error) {
                console.error("Falha ao atualizar status do atendimento:", error);
                renderAgendaMessage(error.message || "Não foi possível atualizar o atendimento.", "error");
                button.disabled = false;
            }
        });
    });
}


async function carregarAgendaDoDia(date) {
    if (!agendaDayLabel) return;

    const dataFormatada = formatDateForAPI(date);
    agendaDayLabel.textContent = formatDateForDisplay(date);

    if (!getToken()) {
        renderAgendaMessage("Sessão expirada. Faça login novamente.", "error");
        return;
    }

    try {
        const endpoint = currentUser?.role === "barbeiro" ? "/admin/me/agenda" : "/admin/agenda";
        const responseBody = await api.get(endpoint, { params: { data: dataFormatada } });
        const agendamentos = normalizeAgendaResponse(responseBody);
        renderizarAgendamentos(agendamentos);
    } catch (error) {
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
    if (currentUser?.role === "admin") {
        Promise.all([
            api.get("/services/"),
            api.get("/users/"),
            api.get("/users/barbeiros"),
        ]).then(([services, clients, barbers]) => {
            referenceMaps.services = new Map(services.map((item) => [item.id, item.nome]));
            referenceMaps.clients = new Map(clients.map((item) => [item.id, item.nome]));
            referenceMaps.barbers = new Map(barbers.map((item) => [item.id, item.nome]));
            return carregarAgendaDoDia(selectedDate);
        }).catch((error) => {
            console.error("Falha ao carregar dados de referência da agenda:", error);
            renderAgendaMessage(error.message || "Não foi possível carregar os dados da agenda.", "error");
        });
    }
    weekDays = generateWeekDays(selectedDate);
    renderDateRoll();
    if (currentUser?.role !== "admin") carregarAgendaDoDia(selectedDate);
}

document.addEventListener("DOMContentLoaded", init);
