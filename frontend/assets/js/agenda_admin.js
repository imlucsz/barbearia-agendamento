// agenda_admin.js
// Lógica do painel administrativo: gera os dias da semana atual (domingo a sábado)
// e busca na API (FastAPI) os agendamentos do dia selecionado.
//
// Por enquanto o admin só pode ver/gerenciar a semana atual — navegar para
// outras semanas fica desativado até vocês decidirem liberar isso.

const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_KEY = "token";
const USER_KEY = "usuario";

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

// --- Helpers de data -------------------------------------------------

// Retorna o domingo (00:00) da semana em que "date" está
function getStartOfWeek(date) {
    const copy = new Date(date);
    const day = copy.getDay();
    copy.setDate(copy.getDate() - day);
    copy.setHours(0, 0, 0, 0);
    return copy;
}

// Gera um array com os 7 dias (domingo a sábado) da semana de "referenceDate"
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

// Formata a data no padrão que a API espera (YYYY-MM-DD)
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

function getToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
}

function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

function setUserName() {
    if (!userNameEl) return;

    const userRaw = localStorage.getItem(USER_KEY);
    if (!userRaw) {
        userNameEl.textContent = "Administrador";
        return;
    }

    try {
        const user = JSON.parse(userRaw);
        const nome = user?.nome || user?.name || user?.username || "Administrador";
        userNameEl.textContent = toTitleCase(nome);
    } catch (error) {
        userNameEl.textContent = "Administrador";
    }
}

// --- Renderização do carrossel ---------------------------------------

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

// --- Comunicação com a API --------------------------------------------

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
    const customer = item?.cliente?.nome || item?.cliente_nome || item?.cliente || item?.customer?.nome || item?.customer_name || "Cliente";
    const service = item?.servico?.nome || item?.servico_nome || item?.servico || item?.service?.nome || item?.service_name || "Serviço";
    const professional = item?.profissional?.nome || item?.profissional_nome || item?.profissional || item?.barbeiro?.nome || item?.barbeiro || item?.employee?.nome || item?.employee_name || "Equipe";

    return {
        id: item?.id ?? `${item?.horario ?? "agenda"}-${Math.random().toString(16).slice(2)}`,
        horario: normalizeTime(item?.horario ?? item?.hora ?? item?.time ?? item?.inicio ?? item?.start_time ?? item?.agenda_hora),
        cliente: String(customer),
        servico: String(service),
        profissional: String(professional),
        status: String(item?.status ?? item?.estado ?? "pendente").toLowerCase()
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

        return `
            <tr class="agenda-row">
                <td data-label="Horário"><span class="time-pill">${escapeHtml(item.horario)}</span></td>
                <td data-label="Cliente">${escapeHtml(item.cliente)}</td>
                <td data-label="Serviço">${escapeHtml(item.servico)}</td>
                <td data-label="Profissional">${escapeHtml(item.profissional)}</td>
                <td data-label="Status"><span class="status-badge status-${statusKey}">${escapeHtml(statusLabel)}</span></td>
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
                    </tr>
                </thead>
                <tbody>
                    ${linhas}
                </tbody>
            </table>
        </div>
    `;
}

async function carregarAgendaDoDia(date) {
    if (!agendaDayLabel) return;

    const dataFormatada = formatDateForAPI(date);
    agendaDayLabel.textContent = formatDateForDisplay(date);

    const token = getToken();
    if (!token) {
        renderAgendaMessage("Sessão expirada. Faça login novamente.", "error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/admin/agenda?data=${dataFormatada}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            }
        });

        if (!response.ok) {
            let message = "Não foi possível carregar a agenda do dia.";

            if (response.status === 401) {
                message = "Sessão expirada ou token inválido. Faça login novamente.";
            } else if (response.status === 404) {
                message = "Rota da agenda indisponível no backend.";
            } else if (response.status === 500) {
                message = "Erro interno do servidor. Tente novamente em alguns instantes.";
            }

            renderAgendaMessage(message, "error");
            return;
        }

        const responseBody = await response.json();
        const agendamentos = normalizeAgendaResponse(responseBody);
        renderizarAgendamentos(agendamentos);
    } catch (error) {
        console.error("Falha ao carregar agenda do dia:", error);
        renderAgendaMessage("Não foi possível conectar com o backend. Verifique a API e tente novamente.", "error");
    }
}

// --- Inicialização ------------------------------------------------------

function init() {
    setUserName();
    if (logoutLink) logoutLink.addEventListener("click", clearSession);
    weekDays = generateWeekDays(selectedDate);
    renderDateRoll();
    carregarAgendaDoDia(selectedDate);
}

document.addEventListener("DOMContentLoaded", init);
