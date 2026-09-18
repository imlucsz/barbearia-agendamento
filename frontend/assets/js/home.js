import { apiGet, getCurrentUser, getToken, logout } from "./api.js";



document.addEventListener("DOMContentLoaded", () => { setupAuthArea(); setupBookingButtons(); setupMobileNav(); loadServices(); document.getElementById("btn-retry-services").addEventListener("click", loadServices); });


function setupAuthArea() {
  const authArea = document.getElementById("auth-area");
  const user = getCurrentUser();
  if (getToken() && user) {
    authArea.innerHTML = `<div class="user-area"><span class="user-name">${escapeHtml(user.name || user.nome || "Cliente")}</span><a href="appointments.html" class="link-entrar">Meus agendamentos</a><a href="#" class="link-logout" id="link-logout">Sair</a></div>`;
    document.getElementById("link-logout").addEventListener("click", (event) => { event.preventDefault(); logout(); });
  }
}

function setupBookingButtons() { [document.getElementById("btn-agendar-header"), document.getElementById("btn-agendar-hero")].forEach((button) => { if (button) button.addEventListener("click", () => { window.location.href = getToken() ? "schedule.html" : "login.html?redirect=schedule.html"; }); }); }
function goToSchedule(serviceId) { const destination = `schedule.html?service_id=${encodeURIComponent(serviceId)}`; window.location.href = getToken() ? destination : `login.html?redirect=${encodeURIComponent(destination)}`; }
function setupMobileNav() { const toggle = document.getElementById("nav-toggle"); const nav = document.getElementById("main-nav"); toggle.addEventListener("click", () => { const isOpen = nav.classList.toggle("main-nav--open"); toggle.setAttribute("aria-expanded", String(isOpen)); }); }

async function loadServices() {
  const skeleton = document.getElementById("services-skeleton"); const list = document.getElementById("services-list"); const errorBox = document.getElementById("services-error");
  skeleton.hidden = false; list.hidden = true; errorBox.hidden = true;
  try { renderServices(await apiGet("/services")); skeleton.hidden = true; list.hidden = false; } catch (error) { console.error("Falha ao carregar serviços:", error); skeleton.hidden = true; errorBox.hidden = false; }
}

function renderServices(services) {
  const list = document.getElementById("services-list"); list.innerHTML = "";
  if (!services || services.length === 0) { list.innerHTML = "<li class=\"service-row\"><span>Nenhum serviço disponível no momento.</span></li>"; return; }
  services.forEach((service) => {
    const row = document.createElement("li"); row.className = "service-row";
    const name = service.name ?? service.nome; const duration = service.duration_minutes ?? service.duracao_minutos ?? service.duration; const price = service.price ?? service.preco;
    row.innerHTML = `<span class="service-name">${escapeHtml(name)}</span><span class="service-duration mono">${escapeHtml(String(duration ?? ""))} min</span><span class="service-price mono">${formatPrice(price)}</span><button class="btn btn-ghost btn-sm" data-service-id="${service.id}">Selecionar</button>`;
    row.querySelector("button").addEventListener("click", () => goToSchedule(service.id)); list.appendChild(row);
  });
}

function formatPrice(value) { const number = Number(value); return Number.isNaN(number) ? "-" : number.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }
function escapeHtml(value) { const div = document.createElement("div"); div.textContent = value ?? ""; return div.innerHTML; }