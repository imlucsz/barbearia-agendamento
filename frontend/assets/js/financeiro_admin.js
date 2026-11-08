import { api, getToken } from "./api.js";

const form = document.getElementById("finance-form");

document.addEventListener("DOMContentLoaded", () => {
  if (!form) return;
  if (!getToken()) {
    window.location.href = "login.html?redirect=admin.html";
    return;
  }
  const today = new Date();
  const start = new Date(today.getFullYear(), today.getMonth(), 1);
  form.elements.inicio.value = localDateString(start);
  form.elements.fim.value = localDateString(today);
  form.addEventListener("submit", generateReport);
  document.getElementById("finance-export")?.addEventListener("click", exportReport);
});

async function generateReport(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("[type=submit]");
  const result = document.getElementById("finance-result");
  if (form.elements.inicio.value > form.elements.fim.value) {
    showError(result, "A data inicial deve ser anterior ou igual à data final.");
    return;
  }
  button.disabled = true;
  try {
    const report = await api.get("/admin/relatorio", {
      params: { inicio: form.elements.inicio.value, fim: form.elements.fim.value },
    });
    result.replaceChildren();
    [
      ["Atendimentos concluídos", report.total_agendamentos],
      ["Receita estimada", currency.format(Number(report.total_receita))],
      ["Ticket médio", currency.format(Number(report.ticket_medio))],
    ].forEach(([label, value]) => {
      const card = document.createElement("article");
      card.className = "finance-metric";
      const title = document.createElement("span");
      title.textContent = label;
      const metric = document.createElement("strong");
      metric.textContent = String(value);
      card.append(title, metric);
      result.append(card);
    });
    renderBreakdownTable(result, report);
    document.getElementById("finance-export").disabled = false;
  } catch (error) {
    console.error("Falha ao gerar relatório financeiro:", error);
    showError(result, error.message || "Não foi possível gerar o relatório.");
    if (error.status === 401) window.location.href = "login.html?redirect=admin.html";
  } finally {
    button.disabled = false;
  }
}

function renderBreakdownTable(container, report) {
  const rows = [
    ...(report.por_barbeiro || []).map((row) => ["Barbeiro", row.barbeiro, row.total_agendamentos, row.receita]),
    ...(report.por_servico || []).map((row) => ["Serviço", row.servico, row.total_agendamentos, row.receita]),
    ...(report.por_dia || []).map((row) => ["Dia", row.dia, row.total_agendamentos, row.receita]),
    ...Object.entries(report.contagem_status || {}).map(([status, count]) => ["Status", status, count, "—"]),
  ];
  const wrapper = document.createElement("div");
  wrapper.className = "finance-table-wrapper";
  const table = document.createElement("table");
  table.className = "finance-table";
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");
  ["Grupo", "Item", "Atendimentos", "Receita"].forEach((label) => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    headerRow.append(cell);
  });
  head.append(headerRow);
  const body = document.createElement("tbody");
  rows.forEach(([group, label, count, revenue]) => {
    const row = document.createElement("tr");
    [group, label, String(count), revenue === "—" ? revenue : currency.format(Number(revenue))].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = String(value ?? "");
      row.append(cell);
    });
    body.append(row);
  });
  table.append(head, body);
  wrapper.append(table);
  container.append(wrapper);
}

async function exportReport() {
  const start = form.elements.inicio.value;
  const end = form.elements.fim.value;
  if (!start || !end || start > end) return;
  try {
    const blob = await api.get("/admin/relatorio/csv", {
      params: { inicio: start, fim: end },
      responseType: "blob",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `relatorio-financeiro-${start}-${end}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    showError(document.getElementById("finance-result"), error.message || "Não foi possível exportar o relatório.");
  }
}

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function localDateString(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function showError(container, message) {
  container.replaceChildren();
  const error = document.createElement("p");
  error.className = "alert alert-danger";
  error.setAttribute("role", "alert");
  error.textContent = message;
  container.append(error);
}
