// agenda_admin.js
// Lógica do painel administrativo: gera os dias da semana atual (domingo a sábado)
// e busca na API (FastAPI) os agendamentos do dia selecionado.
//
// Por enquanto o admin só pode ver/gerenciar a semana atual — navegar para
// outras semanas fica desativado até vocês decidirem liberar isso.

const API_BASE_URL = "http://127.0.0.1:8000"; // ajustar para a URL real da API

const dateRoll = document.getElementById("dateRoll");
const prevBtn = document.getElementById("prevDates");
const nextBtn = document.getElementById("nextDates");

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

let weekDays = [];          // os 7 dias da semana atual (dom -> sáb)
let selectedDate = new Date(); // dia selecionado no carrossel

// --- Helpers de data -------------------------------------------------

// Retorna o domingo (00:00) da semana em que "date" está
function getStartOfWeek(date) {
    const d = new Date(date);
    d.setDate(d.getDate() - d.getDay()); // getDay(): 0 = domingo
    d.setHours(0, 0, 0, 0);
    return d;
}

// Gera um array com os 7 dias (domingo a sábado) da semana de "referenceDate"
function generateWeekDays(referenceDate) {
    const start = getStartOfWeek(referenceDate);
    const dias = [];
    for (let i = 0; i < 7; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        dias.push(d);
    }
    return dias;
}

function mesmoDia(a, b) {
    return a.toDateString() === b.toDateString();
}

// Formata a data no padrão que a API espera (YYYY-MM-DD)
function formatDateForAPI(date) {
    const ano = date.getFullYear();
    const mes = String(date.getMonth() + 1).padStart(2, "0");
    const dia = String(date.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
}

// --- Renderização do carrossel ---------------------------------------

function renderDateRoll() {
    dateRoll.innerHTML = "";

    weekDays.forEach((date) => {
        const item = document.createElement("button");
        item.type = "button";
        item.classList.add("date-item"); // ajustar para o nome de classe usado no admin.css

        if (mesmoDia(date, selectedDate)) {
            item.classList.add("selected");
        }
        if (mesmoDia(date, new Date())) {
            item.classList.add("today");
        }

        item.innerHTML = `
            <span class="date-weekday">${DIAS_SEMANA[date.getDay()]}</span>
            <span class="date-number">${String(date.getDate()).padStart(2, "0")}</span>
        `;

        item.addEventListener("click", () => selecionarDia(date));

        dateRoll.appendChild(item);
    });

    // Como por enquanto só existe a semana atual, os botões de navegação
    // ficam desativados. Quando vocês liberarem outras semanas, é só
    // trocar essa função para chamar generateWeekDays() com outra data
    // de referência e reativar os botões.
    prevBtn.disabled = true;
    nextBtn.disabled = true;
}

function selecionarDia(date) {
    selectedDate = date;
    renderDateRoll();
    carregarAgendaDoDia(date);
}

// --- Comunicação com a API --------------------------------------------

async function carregarAgendaDoDia(date) {
    const dataFormatada = formatDateForAPI(date);
    const token = localStorage.getItem("token"); // ajustar para onde o JWT é salvo no login

    try {
        const response = await fetch(
            `${API_BASE_URL}/admin/agenda?data=${dataFormatada}`,
            {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
            }
        );

        if (!response.ok) {
            throw new Error(`Erro ${response.status} ao buscar a agenda`);
        }

        const agendamentos = await response.json();
        renderizarAgendamentos(agendamentos);
    } catch (erro) {
        console.error("Falha ao carregar agenda do dia:", erro);
        // dá pra mostrar um aviso na tela aqui pro admin, tipo:
        // exibirErroNaTela("Não foi possível carregar a agenda desse dia.");
    }
}

// Placeholder: troca isso pelo elemento real da lista de agendamentos
function renderizarAgendamentos(agendamentos) {
    console.log("Agendamentos do dia:", agendamentos);

    // Formato esperado de cada item (alinhem isso com o schema do backend):
    // { id, horario, cliente, servico, profissional, status }
}

// --- Inicialização ------------------------------------------------------

function init() {
    weekDays = generateWeekDays(selectedDate);
    renderDateRoll();
    carregarAgendaDoDia(selectedDate);
}

init();
