export const CONSENT_STORAGE_KEY = "barbearia.consent.v1";
export const CONSENT_EVENT = "barbearia:consent-change";
export const CONSENT_MAX_AGE_DAYS = 365;

function storageOf(windowRef) {
  try {
    return windowRef?.localStorage || null;
  } catch {
    return null;
  }
}

export function readConsent(storage, now = new Date()) {
  try {
    const parsed = JSON.parse(storage?.getItem(CONSENT_STORAGE_KEY) || "null");
    if (!parsed || parsed.version !== 1 || typeof parsed.terceiros !== "boolean") return null;
    const decided = new Date(parsed.decididoEm);
    if (Number.isNaN(decided.getTime())) return null;
    const ageDays = (now.getTime() - decided.getTime()) / 86400000;
    if (ageDays < 0 || ageDays > CONSENT_MAX_AGE_DAYS) return null;
    return Object.freeze({ terceiros: parsed.terceiros, decididoEm: parsed.decididoEm });
  } catch {
    return null;
  }
}

export function saveConsent(storage, terceiros, now = new Date()) {
  const record = { version: 1, terceiros: Boolean(terceiros), decididoEm: now.toISOString() };
  try {
    storage?.setItem(CONSENT_STORAGE_KEY, JSON.stringify(record));
  } catch {
    // Sem gravação, a escolha vale só para esta página; uma permissão antiga não pode prevalecer.
    try {
      storage?.removeItem(CONSENT_STORAGE_KEY);
    } catch {
      // Armazenamento indisponível: nada a remover.
    }
  }
  return Object.freeze({ terceiros: record.terceiros, decididoEm: record.decididoEm });
}

const pageChoices = new WeakMap();

// O mapa do Google é exibido por padrão (legítimo interesse); o visitante pode desativá-lo.
export function isThirdPartyContentEnabled(windowRef = globalThis.window) {
  if (windowRef && pageChoices.has(windowRef)) return pageChoices.get(windowRef);
  return readConsent(storageOf(windowRef))?.terceiros ?? true;
}

export function setThirdPartyConsent(terceiros, windowRef = globalThis.window) {
  const record = saveConsent(storageOf(windowRef), terceiros);
  if (windowRef) pageChoices.set(windowRef, record.terceiros);
  windowRef?.document?.querySelector?.("[data-consent-banner]")?.remove();
  windowRef?.dispatchEvent?.(new CustomEvent(CONSENT_EVENT, { detail: record }));
  return record;
}

function closeBanner(documentRef, banner, returnFocus) {
  banner.remove();
  const target = returnFocus?.isConnected ? returnFocus : documentRef.getElementById("main-content");
  target?.focus?.();
}

export function showConsentBanner(documentRef = globalThis.document, { returnFocus = null } = {}) {
  const windowRef = documentRef?.defaultView;
  if (!documentRef?.body || !windowRef) return null;
  documentRef.querySelector("[data-consent-banner]")?.remove();

  const banner = documentRef.createElement("section");
  banner.className = "consent-banner";
  banner.dataset.consentBanner = "";
  banner.setAttribute("aria-labelledby", "consent-banner-title");

  const title = documentRef.createElement("h2");
  title.id = "consent-banner-title";
  title.className = "consent-banner__title";
  title.textContent = "Preferências de cookies";

  const text = documentRef.createElement("p");
  text.textContent = "Usamos apenas cookies e armazenamento local essenciais para login, segurança e funcionamento do agendamento. Não usamos cookies de publicidade nem ferramentas de análise, como Google Analytics. A página inicial exibe o mapa do Google para mostrar a localização da barbearia; ao carregá-lo, o Google recebe seu endereço IP e pode usar cookies próprios. Você pode desativar o mapa aqui.";

  const more = documentRef.createElement("a");
  more.href = "cookies.html";
  more.textContent = "Ver Política de Cookies";

  const actions = documentRef.createElement("div");
  actions.className = "consent-banner__actions";
  const accept = documentRef.createElement("button");
  accept.type = "button";
  accept.className = "btn";
  accept.dataset.consentChoice = "accept";
  accept.textContent = "Permitir conteúdo de terceiros";
  const reject = documentRef.createElement("button");
  reject.type = "button";
  reject.className = "btn";
  reject.dataset.consentChoice = "reject";
  reject.textContent = "Usar somente essenciais";
  actions.append(reject, accept);

  const current = readConsent(storageOf(windowRef));
  banner.append(title, text);
  const status = documentRef.createElement("p");
  status.className = "consent-banner__status";
  status.textContent = !current
    ? "Escolha atual: mapa do Google exibido (padrão)."
    : current.terceiros
      ? "Escolha atual: conteúdo de terceiros permitido."
      : "Escolha atual: somente essenciais.";
  banner.append(status, more, actions);

  banner.addEventListener("click", (event) => {
    const choice = event.target.closest?.("[data-consent-choice]")?.dataset.consentChoice;
    if (!choice) return;
    setThirdPartyConsent(choice === "accept", windowRef);
    closeBanner(documentRef, banner, returnFocus);
  });
  banner.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    closeBanner(documentRef, banner, returnFocus);
  });

  const footer = returnFocus?.closest?.("footer");
  const container = returnFocus?.closest?.("p, div");
  if (footer) footer.before(banner);
  else if (container) container.after(banner);
  else documentRef.body.append(banner);
  return banner;
}

// Sem cookies opcionais, não há aviso automático: a permissão é pedida no ponto
// em que o conteúdo de terceiros seria carregado e pode ser revista no rodapé.
export function initCookieConsent(documentRef = globalThis.document) {
  if (!documentRef?.body || !documentRef.defaultView) return;
  documentRef.addEventListener("click", (event) => {
    const trigger = event.target.closest?.("[data-cookie-preferences]");
    if (!trigger) return;
    const banner = showConsentBanner(documentRef, { returnFocus: trigger });
    banner?.querySelector("[data-consent-choice]")?.focus();
  });
}
