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
  } catch (error) {
    console.error("Falha ao gerar relatório financeiro:", error);
    showError(result, error.message || "Não foi possível gerar o relatório.");
    if (error.status === 401) window.location.href = "login.html?redirect=admin.html";
  } finally {
    button.disabled = false;
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
