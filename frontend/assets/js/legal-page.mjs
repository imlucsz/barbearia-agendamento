import { api } from "./api.js";
import { fillLegalPlaceholders } from "./legal.mjs";

async function loadInstitutionalFallback() {
  try {
    return await api.get("/informacoes/", { auth: false });
  } catch (error) {
    console.error("Falha ao carregar informações institucionais:", error);
    return {};
  }
}

fillLegalPlaceholders();
loadInstitutionalFallback().then((info) => fillLegalPlaceholders(document, undefined, info || {}));
