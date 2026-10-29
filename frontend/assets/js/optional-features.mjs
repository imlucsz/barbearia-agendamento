import { INSTALLATION_CONFIG } from "./installation-config.mjs";

export function installationFeatureEnabled(name, features = INSTALLATION_CONFIG.features) {
  return features?.[name] !== false;
}

export async function initializeOptionalFeatures({
  documentRef = globalThis.document,
  features = INSTALLATION_CONFIG.features,
  loadWidget = () => import("./estrelinha/widget.js"),
} = {}) {
  if (!documentRef) return { widgetEnabled: false };
  const mount = documentRef.querySelector("[data-estrelinha-barbeiro]");
  if (!installationFeatureEnabled("estrelinhaWidget", features)) {
    mount?.remove();
    return { widgetEnabled: false };
  }
  if (!mount) return { widgetEnabled: true };

  const stylesheet = documentRef.createElement("link");
  stylesheet.rel = "stylesheet";
  stylesheet.href = new URL("../css/estrelinha.css", import.meta.url).href;
  documentRef.head.append(stylesheet);
  await loadWidget();
  return { widgetEnabled: true };
}

if (typeof document !== "undefined") {
  initializeOptionalFeatures().catch((error) => {
    document.querySelector("[data-estrelinha-barbeiro]")?.remove();
    console.warn("Widget Estrelinha indisponível nesta instalação.", error);
  });
}
