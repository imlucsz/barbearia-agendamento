import { INSTALLATION_CONFIG } from "./installation-config.mjs";

export function installationFeatureEnabled(name, features = INSTALLATION_CONFIG.features) {
  return features?.[name] !== false;
}

export async function initializeOptionalFeatures({
  documentRef = globalThis.document,
  features = INSTALLATION_CONFIG.features,
  loadWidget = () => import("./estrelinha/cinematic.mjs"),
} = {}) {
  if (!documentRef) return { widgetEnabled: false };
  const mount = documentRef.querySelector("[data-estrelinha-barbeiro]");
  if (!installationFeatureEnabled("estrelinhaWidget", features)) {
    const mounts = documentRef.querySelectorAll?.("[data-estrelinha-cameo]") ?? (mount ? [mount] : []);
    mounts.forEach(node => node.remove());
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
    document.querySelectorAll("[data-estrelinha-cameo]").forEach(node => node.remove());
    console.warn("Widget Estrelinha indisponível nesta instalação.", error);
  });
}
