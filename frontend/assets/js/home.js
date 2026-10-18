import { api, getCurrentUser, getToken, logout } from "./api.js";

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
let allServices = [];
let activeFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("current-year").textContent = new Date().getFullYear();
  setupNavigation();
  setupAuthArea();
  setupFilters();
  document.getElementById("btn-retry-services").addEventListener("click", loadServices);
  loadServices();
  loadBusinessInfo();
  loadReviews();
});

function setupNavigation() {
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("main-nav");
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("main-nav--open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
  });
  nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
    nav.classList.remove("main-nav--open");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Abrir menu");
  }));
}

function setupAuthArea() {
  const area = document.getElementById("auth-area");
  const user = getCurrentUser();
  if (!getToken() || !user) return;

  const destination = user.role === "admin" || user.role === "barbeiro"
    ? "admin.html"
    : "client-dashboard.html";
  area.replaceChildren();

  const dashboard = document.createElement("a");
  dashboard.href = destination;
  dashboard.className = "btn btn-ghost";
  dashboard.textContent = "Minha área";

  const exit = document.createElement("button");
  exit.type = "button";
  exit.className = "btn";
  exit.textContent = "Sair";
  exit.addEventListener("click", logout);

  area.append(dashboard, exit);
}

function setupFilters() {
  document.querySelectorAll(".filter-btn").forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter;
      document.querySelectorAll(".filter-btn").forEach((item) => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      renderServices();
    });
  });
}

async function loadServices() {
  const skeleton = document.getElementById("services-skeleton");
  const list = document.getElementById("services-list");
  const error = document.getElementById("services-error");
  skeleton.hidden = false;
  list.hidden = true;
  error.hidden = true;

  try {
    allServices = await api.get("/services/", { auth: false });
    renderServices();
    skeleton.hidden = true;
    list.hidden = false;
  } catch (requestError) {
    console.error("Falha ao carregar serviços:", requestError);
    skeleton.hidden = true;
    error.hidden = false;
  }
}

function renderServices() {
  const list = document.getElementById("services-list");
  const filtered = allServices.filter((service) => {
    if (activeFilter === "all") return true;
    const searchable = `${service.nome || ""} ${service.descricao || ""}`.toLocaleLowerCase("pt-BR");
    return activeFilter === "corte"
      ? searchable.includes("corte") || searchable.includes("cabelo")
      : searchable.includes("barba");
  });
  list.replaceChildren();

  if (filtered.length === 0) {
    const empty = document.createElement("li");
    empty.className = "service-empty";
    empty.textContent = allServices.length
      ? "Não encontramos serviços nessa categoria."
      : "Nenhum serviço disponível no momento.";
    list.append(empty);
    return;
  }

  filtered.forEach((service, index) => {
    const item = document.createElement("li");
    item.className = "service-card";
    item.style.setProperty("--card-index", index);

    const top = document.createElement("div");
    top.className = "service-card-top";
    const tag = document.createElement("span");
    tag.className = "service-tag";
    tag.textContent = categorize(service.nome);
    const number = document.createElement("span");
    number.className = "service-index";
    number.textContent = String(index + 1).padStart(2, "0");
    top.append(tag, number);

    const title = document.createElement("h3");
    title.textContent = service.nome;
    const details = document.createElement("p");
    details.className = "service-details";
    details.textContent = "Atendimento feito com atenção ao acabamento.";
    const footer = document.createElement("div");
    footer.className = "service-card-footer";
    const meta = document.createElement("div");
    const price = document.createElement("strong");
    price.className = "service-price";
    price.textContent = money.format(Number(service.preco));
    const duration = document.createElement("span");
    duration.className = "service-duration";
    duration.textContent = `${service.duracao_minutos} min`;
    meta.append(price, duration);
    const book = document.createElement("a");
    book.className = "service-book";
    book.href = `client-services.html?service_id=${encodeURIComponent(service.id)}`;
    book.setAttribute("aria-label", `Agendar ${service.nome}`);
    book.textContent = "↗";
    footer.append(meta, book);
    item.append(top, title, details, footer);
    list.append(item);
  });
}

function categorize(name = "") {
  const normalized = name.toLocaleLowerCase("pt-BR");
  if (normalized.includes("barba")) return "Barba";
  if (normalized.includes("sobrancelha")) return "Detalhes";
  if (normalized.includes("cabelo") || normalized.includes("corte")) return "Cabelo";
  return "Cuidado";
}

async function loadBusinessInfo() {
  try {
    const data = await api.get("/informacoes/", { auth: false });
    text("address", data.endereco || "Endereço não informado");
    setTelephoneLink("phone", data.telefone);
    text("operating-days", data.dias_atendimento || "Dias não informados");
    if (data.email) {
      const email = document.createElement("a");
      email.href = `mailto:${data.email}`;
      email.textContent = data.email;
      document.getElementById("email").replaceChildren(email);
    } else {
      text("email", "E-mail não informado");
    }

    renderBusinessHours(data.dias_atendimento, data.horario_funcionamento);
    renderMap(data.endereco_maps);
  } catch (error) {
    console.error("Falha ao carregar informações institucionais:", error);
    ["address", "phone", "operating-days", "email", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]
      .forEach((id) => text(id, "Informação indisponível"));
  }
}

function renderBusinessHours(daysText = "", hoursText = "") {
  const dayIds = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
  const weekdays = ["domingo", "segunda", "terca", "quarta", "quinta", "sexta", "sabado"];
  const days = String(daysText).toLocaleLowerCase("pt-BR").normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").replace(/-feira/g, "");
  const hours = String(hoursText || "Horário não informado");
  const closed = /fechado|não atend|nao atend/i.test(days);
  const range = days.match(/(domingo|segunda|terca|quarta|quinta|sexta|sabado)\s*(?:a|ate|-)\s*(domingo|segunda|terca|quarta|quinta|sexta|sabado)/);
  const rangeStart = range ? weekdays.indexOf(range[1]) : -1;
  const rangeEnd = range ? weekdays.indexOf(range[2]) : -1;
  dayIds.forEach((id, dayIndex) => {
    const dayName = weekdays[dayIndex];
    const open = !closed && (
      days.includes(dayName) ||
      (range && (rangeStart <= rangeEnd
        ? dayIndex >= rangeStart && dayIndex <= rangeEnd
        : dayIndex >= rangeStart || dayIndex <= rangeEnd)) ||
      /todos os dias|diariamente/i.test(days)
    );
    text(id, open ? hours : "Fechado");
  });
}

function renderMap(value) {
  const container = document.getElementById("map-container");
  const link = document.getElementById("map-link");
  container.replaceChildren();
  link.hidden = true;
  if (!value) {
    const fallback = document.createElement("p");
    fallback.className = "text-muted";
    fallback.textContent = "Mapa não disponível.";
    container.append(fallback);
    return;
  }

  try {
    const mapUrl = new URL(value);
    if (mapUrl.protocol !== "https:" || !/(^|\.)google\.(com|com\.br)$/.test(mapUrl.hostname)) {
      throw new Error("Origem de mapa não permitida");
    }
    link.href = mapUrl.href;
    link.hidden = false;
    if (mapUrl.pathname.includes("/maps/embed")) {
      const iframe = document.createElement("iframe");
      iframe.src = mapUrl.href;
      iframe.title = "Mapa da barbearia";
      iframe.loading = "lazy";
      iframe.referrerPolicy = "no-referrer-when-downgrade";
      iframe.setAttribute("sandbox", "allow-scripts allow-same-origin allow-popups");
      container.append(iframe);
    } else {
      const hint = document.createElement("p");
      hint.className = "text-muted";
      hint.textContent = "Abra o mapa para ver como chegar.";
      container.append(hint);
    }
  } catch (error) {
    console.error("URL de mapa institucional inválida:", error);
    const fallback = document.createElement("p");
    fallback.className = "text-muted";
    fallback.textContent = "Mapa indisponível.";
    container.append(fallback);
  }
}

async function loadReviews() {
  const container = document.getElementById("reviews-list");
  try {
    const reviews = await api.get("/appointments/avaliacoes", { auth: false });
    const visible = reviews.filter((review) => !review.oculta);
    container.replaceChildren();
    if (visible.length === 0) {
      document.getElementById("review-average").textContent = "Ainda sem avaliações";
      const message = document.createElement("p");
      message.className = "text-muted";
      message.textContent = "As primeiras avaliações aparecerão aqui.";
      container.append(message);
      return;
    }

    const average = visible.reduce((sum, review) => sum + Number(review.nota), 0) / visible.length;
    document.getElementById("review-average").textContent = `${average.toFixed(1)} / 5 · ${visible.length} ${visible.length === 1 ? "avaliação" : "avaliações"}`;
    visible.slice(0, 6).forEach((review) => {
      const card = document.createElement("article");
      card.className = "review-card";
      const stars = document.createElement("div");
      stars.className = "review-rating";
      stars.setAttribute("aria-label", `Nota ${review.nota} de 5`);
      stars.textContent = `${"★".repeat(review.nota)}${"☆".repeat(5 - review.nota)}`;
      const quote = document.createElement("p");
      quote.textContent = review.comentario || "Atendimento avaliado pelo cliente.";
      const date = document.createElement("small");
      date.textContent = review.criada_em
        ? new Date(review.criada_em).toLocaleDateString("pt-BR")
        : "Cliente da casa";
      card.append(stars, quote, date);
      container.append(card);
    });
  } catch (error) {
    console.error("Falha ao carregar avaliações:", error);
    document.getElementById("review-average").textContent = "Avaliações indisponíveis";
    container.replaceChildren();
    const message = document.createElement("p");
    message.className = "text-muted";
    message.textContent = "Não foi possível carregar as avaliações agora.";
    container.append(message);
  }
}

function setTelephoneLink(id, value) {
  const node = document.getElementById(id);
  const phone = String(value || "").trim();
  if (!phone) {
    node.textContent = "Não informado";
    return;
  }
  const link = document.createElement("a");
  link.href = `tel:${phone.replace(/[^\d+]/g, "")}`;
  link.textContent = phone;
  node.replaceChildren(link);
}

function text(id, value) {
  document.getElementById(id).textContent = value;
}
