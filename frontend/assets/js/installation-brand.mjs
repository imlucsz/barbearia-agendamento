import { INSTALLATION_CONFIG } from "./installation-config.mjs";

export const DEFAULT_BRAND_NAME = "Barbearia";
export const DEFAULT_THEME_COLOR = "#15120f";

const MAX_BRAND_NAME_LENGTH = 80;
const RASTER_IMAGE_EXTENSION = /\.(?:png|jpe?g|webp|avif)$/i;
const RELATIVE_BRAND_PATH = /^\.\.\/assets\/branding\/[A-Za-z0-9][A-Za-z0-9._-]*\.(?:png|jpe?g|webp|avif)$/i;

export function normalizeBrandConfiguration(brand = {}, pageUrl = "http://localhost/pages/index.html") {
  const configuredName = typeof brand?.name === "string"
    ? brand.name.replace(/[\u0000-\u001f\u007f]/g, "").trim()
    : "";
  const name = configuredName && configuredName.length <= MAX_BRAND_NAME_LENGTH
    ? configuredName
    : DEFAULT_BRAND_NAME;

  const color = typeof brand?.themeColor === "string" ? brand.themeColor.trim() : "";
  const themeColor = /^#[\da-f]{6}$/i.test(color) ? color.toLowerCase() : DEFAULT_THEME_COLOR;

  return Object.freeze({
    name,
    logoUrl: validateBrandLogoUrl(brand?.logoUrl, pageUrl),
    themeColor,
  });
}

export function validateBrandLogoUrl(value, pageUrl = "http://localhost/pages/index.html") {
  if (typeof value !== "string" || !value.trim()) return null;
  const configuredUrl = value.trim();

  if (RELATIVE_BRAND_PATH.test(configuredUrl)) {
    try {
      const base = new URL(pageUrl);
      const resolved = new URL(configuredUrl, base);
      if (resolved.origin !== base.origin || !resolved.pathname.includes("/assets/branding/")) return null;
      return resolved.href;
    } catch {
      return null;
    }
  }

  if (!/^https:\/\//i.test(configuredUrl)) return null;
  try {
    const parsed = new URL(configuredUrl);
    if (
      parsed.protocol !== "https:" ||
      parsed.username ||
      parsed.password ||
      parsed.search ||
      parsed.hash ||
      parsed.pathname.split("/").includes("..") ||
      !RASTER_IMAGE_EXTENSION.test(parsed.pathname)
    ) return null;
    return parsed.href;
  } catch {
    return null;
  }
}

function replaceConfiguredName(value, name) {
  return value.replace(/Barbearia Agendamento|Barbearia/g, name);
}

export function applyInstallationBrand(brand = INSTALLATION_CONFIG.brand, documentRef = globalThis.document) {
  if (!documentRef?.location?.href) return normalizeBrandConfiguration(brand);

  const configured = normalizeBrandConfiguration(brand, documentRef.location.href);
  const useDefaultName = configured.name === DEFAULT_BRAND_NAME;
  for (const lockup of documentRef.querySelectorAll(".brand-lockup")) {
    const name = lockup.querySelector(".brand-copy strong");
    if (name) name.textContent = configured.name;

    const accessibleName = lockup.getAttribute("aria-label");
    if (accessibleName && !useDefaultName) {
      lockup.setAttribute("aria-label", replaceConfiguredName(accessibleName, configured.name));
    }

    const mark = lockup.querySelector(".brand-mark");
    if (mark) {
      mark.setAttribute("aria-hidden", "true");
      if (configured.logoUrl) {
        const image = documentRef.createElement("img");
        image.className = "brand-logo-image";
        image.alt = "";
        image.setAttribute("aria-hidden", "true");
        image.referrerPolicy = "no-referrer";
        image.addEventListener("error", () => mark.replaceChildren("B."), { once: true });
        image.src = configured.logoUrl;
        mark.replaceChildren(image);
      }
    }
  }

  const themeColor = documentRef.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.setAttribute("content", configured.themeColor);

  if (!useDefaultName) {
    documentRef.title = replaceConfiguredName(documentRef.title, configured.name);
    const description = documentRef.querySelector('meta[name="description"]');
    if (description) {
      description.setAttribute("content", replaceConfiguredName(description.getAttribute("content") || "", configured.name));
    }
    for (const footer of documentRef.querySelectorAll(".auth-footer p, .footer-inner > p")) {
      const walker = documentRef.createTreeWalker(footer, 4);
      let textNode = walker.nextNode();
      while (textNode) {
        textNode.nodeValue = replaceConfiguredName(textNode.nodeValue, configured.name);
        textNode = walker.nextNode();
      }
    }
  }

  return configured;
}
