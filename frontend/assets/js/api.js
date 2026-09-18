// api.js
// Camada única de comunicação com o backend (FastAPI).
// Nenhum outro .js deve chamar fetch() diretamente nem conhecer API_BASE.

const API_BASE = "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getToken() {
  return localStorage.getItem("token");
}

function getCurrentUser() {
  const raw = localStorage.getItem("user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.location.href = "index.html";
}

function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function apiRequest(path, { method = "GET", body } = {}) {
  const headers = authHeaders(body ? { "Content-Type": "application/json" } : {});

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });

  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      // corpo não era JSON ou veio vazio, usa mensagem padrão
    }
    throw new ApiError(detail || `${method} ${path} falhou com status ${response.status}`, response.status);
  }

  if (response.status === 204) return null; // DELETE geralmente não   retorna corpo
  return response.json();
}

const apiGet    = (path)       => apiRequest(path);
const apiPost   = (path, body) => apiRequest(path, { method: "POST", body });
const apiPut    = (path, body) => apiRequest(path, { method: "PUT", body });
const apiPatch  = (path, body) => apiRequest(path, { method: "PATCH", body });
const apiDelete = (path)       => apiRequest(path, { method: "DELETE" });
// ... mantêm-se as funções apiGet, apiPost, etc. ...

export { apiGet, apiPost, apiPut, apiPatch, apiDelete, logout, getCurrentUser, getToken, ApiError };