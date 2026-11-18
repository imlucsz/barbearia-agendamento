import { INSTALLATION_CONFIG } from "./installation-config.mjs";
import { normalizeBrandConfiguration } from "./installation-brand.mjs";

export const LEGAL_FIELDS = Object.freeze([
  "razaoSocial", "cnpj", "endereco", "email", "telefone",
  "encarregadoNome", "encarregadoEmail", "documentosAtualizadosEm", "versaoDocumentos",
]);
export const NOT_INFORMED = "Não informado";

const REQUIRED_FIELDS = Object.freeze(["razaoSocial", "cnpj", "endereco", "email"]);
const EMAIL_PATTERN = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;

export function isValidCnpj(value) {
  const digits = String(value || "").replace(/\D/g, "");
  if (digits.length !== 14 || /^(\d)\1{13}$/.test(digits)) return false;
  const check = (length) => {
    const weights = length === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const sum = weights.reduce((total, weight, index) => total + Number(digits[index]) * weight, 0);
    const rest = sum % 11;
    return rest < 2 ? 0 : 11 - rest;
  };
  return check(12) === Number(digits[12]) && check(13) === Number(digits[13]);
}

export function formatCnpj(value) {
  const digits = String(value || "").replace(/\D/g, "");
  return digits.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
}

function clean(value, maxLength = 200) {
  const text = String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim();
  return text.length <= maxLength ? text : "";
}

export function normalizeLegalConfiguration(legal = {}) {
  const source = legal && typeof legal === "object" ? legal : {};
  const result = Object.fromEntries(LEGAL_FIELDS.map((field) => [field, clean(source[field])]));
  result.cnpj = isValidCnpj(result.cnpj) ? formatCnpj(result.cnpj) : "";
  if (!EMAIL_PATTERN.test(result.email)) result.email = "";
  if (!EMAIL_PATTERN.test(result.encarregadoEmail)) result.encarregadoEmail = "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(result.documentosAtualizadosEm)) result.documentosAtualizadosEm = "";
  result.missing = Object.freeze(REQUIRED_FIELDS.filter((field) => !result[field]));
  return Object.freeze(result);
}

export function formatDocumentDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : NOT_INFORMED;
}

export function legalOwnerName(legal, brand = INSTALLATION_CONFIG.brand) {
  return legal.razaoSocial || normalizeBrandConfiguration(brand).name;
}

export function legalIdentificationLine(legal) {
  const parts = [];
  if (legal.razaoSocial) parts.push(legal.razaoSocial);
  if (legal.cnpj) parts.push(`CNPJ ${legal.cnpj}`);
  if (legal.endereco) parts.push(legal.endereco);
  return parts.join(" · ");
}

function link(documentRef, href, label) {
  const anchor = documentRef.createElement("a");
  anchor.href = href;
  anchor.textContent = label;
  return anchor;
}

export function applyLegalFooter(documentRef = globalThis.document, config = INSTALLATION_CONFIG) {
  const legal = normalizeLegalConfiguration(config.legal);
  if (!documentRef?.querySelectorAll) return legal;

  const owner = legalOwnerName(legal, config.brand);
  documentRef.querySelectorAll("[data-copyright-owner]").forEach((node) => { node.textContent = owner; });
  documentRef.querySelectorAll("#current-year").forEach((node) => {
    if (!node.textContent.trim()) node.textContent = String(new Date().getFullYear());
  });

  documentRef.querySelectorAll("footer.auth-footer, footer.site-footer").forEach((footer) => {
    if (footer.querySelector("[data-legal-footer]")) return;
    const block = documentRef.createElement("div");
    block.className = "legal-footer";
    block.dataset.legalFooter = "";
    const nav = documentRef.createElement("nav");
    nav.setAttribute("aria-label", "Informações legais");
    nav.append(
      link(documentRef, "privacidade.html", "Política de Privacidade"),
      link(documentRef, "termos.html", "Termos de Uso"),
      link(documentRef, "cookies.html", "Política de Cookies"),
    );
    const preferences = documentRef.createElement("button");
    preferences.type = "button";
    preferences.className = "legal-footer__button";
    preferences.dataset.cookiePreferences = "";
    preferences.textContent = "Preferências de cookies";
    nav.append(preferences);
    block.append(nav);
    const identification = legalIdentificationLine(legal);
    if (identification) {
      const line = documentRef.createElement("p");
      line.className = "legal-footer__identification";
      line.textContent = identification;
      block.append(line);
    }
    footer.append(block);
  });
  return legal;
}

export function fillLegalPlaceholders(documentRef = globalThis.document, config = INSTALLATION_CONFIG, fallback = {}) {
  const legal = normalizeLegalConfiguration(config.legal);
  const values = {
    ...legal,
    nomeFantasia: normalizeBrandConfiguration(config.brand).name,
    endereco: legal.endereco || clean(fallback.endereco),
    email: legal.email || (EMAIL_PATTERN.test(clean(fallback.email)) ? clean(fallback.email) : ""),
    telefone: legal.telefone || clean(fallback.telefone),
    documentosAtualizadosEm: formatDocumentDate(legal.documentosAtualizadosEm),
  };
  values.canalTitular = legal.encarregadoEmail || values.email;
  documentRef.querySelectorAll("[data-legal]").forEach((node) => {
    const value = values[node.dataset.legal] || "";
    node.replaceChildren();
    if (value && node.dataset.legalLink === "email") {
      node.append(link(documentRef, `mailto:${value}`, value));
    } else {
      node.textContent = value || NOT_INFORMED;
    }
  });
  return values;
}
