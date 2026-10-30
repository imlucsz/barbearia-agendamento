import { expireSessionOnUnauthorized, shouldRefreshSession } from "./session.mjs";
import { formatApiError } from "./api-errors.mjs";
import { INSTALLATION_CONFIG } from "./installation-config.mjs";
import { applyInstallationBrand } from "./installation-brand.mjs";

applyInstallationBrand();

const API_BASE_URL = (window.BARBEARIA_API_URL || INSTALLATION_CONFIG.apiBaseUrl).replace(/\/+$/, "");
let refreshInFlight = null;

export function getToken() {
  return localStorage.getItem("token");
}

export function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem("user") || "null");
  } catch (error) {
    console.error("Dados locais do usuário inválidos:", error);
    return null;
  }
}

export function setToken(token) {
  if (token) localStorage.setItem("token", token);
  else localStorage.removeItem("token");
}

export function clearToken() {
  localStorage.removeItem("token");
}

export function logout() {
  clearToken();
  localStorage.removeItem("user");
  fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", credentials: "include", keepalive: true })
    .catch(() => {})
    .finally(() => { window.location.href = "login.html"; });
}

async function refreshAccessToken() {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    }).then(async (response) => {
      if (!response.ok) throw new Error("Sessão expirada");
      const data = await response.json();
      if (!data.access_token) throw new Error("Refresh sem access token");
      setToken(data.access_token);
      return data.access_token;
    }).finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

async function request(endpoint, options = {}) {
  const { method = "GET", body, auth = true, params, headers = {}, responseType = "json", ...rest } = options;
  const url = new URL(`${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`);

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const requestHeaders = new Headers(headers);
  if (body !== undefined && !(body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const token = auth ? getToken() : null;
  if (token) requestHeaders.set("Authorization", `Bearer ${token}`);

  const fetchOptions = {
    method,
    headers: requestHeaders,
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    ...rest,
    credentials: "include",
  };
  let response = await fetch(url, fetchOptions);

  if (shouldRefreshSession(response.status, auth, endpoint)) {
    try {
      const refreshedToken = await refreshAccessToken();
      const retryHeaders = new Headers(requestHeaders);
      retryHeaders.set("Authorization", `Bearer ${refreshedToken}`);
      response = await fetch(url, { ...fetchOptions, headers: retryHeaders });
    } catch {
      // The regular unauthorized handler below clears local state and redirects.
    }
  }

  if (!response.ok) {
    const responseText = await response.text();
    expireSessionOnUnauthorized(response.status, auth, localStorage, window.location, responseText);
    const error = formatApiError(response.status, responseText);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  if (response.status === 205) return null;
  if (responseType === "blob") return response.blob();
  if (responseType === "text") return response.text();
  return response.json();
}

export const api = {
  get: (endpoint, options = {}) => request(endpoint, { method: "GET", ...options }),
  post: (endpoint, body, options = {}) => request(endpoint, { method: "POST", body, ...options }),
  put: (endpoint, body, options = {}) => request(endpoint, { method: "PUT", body, ...options }),
  patch: (endpoint, body, options = {}) => request(endpoint, { method: "PATCH", body, ...options }),
  delete: (endpoint, options = {}) => request(endpoint, { method: "DELETE", ...options }),
};

export const apiGet = (endpoint, options = {}) => api.get(endpoint, options);
export const apiPost = (endpoint, body, options = {}) => api.post(endpoint, body, options);
export const apiPut = (endpoint, body, options = {}) => api.put(endpoint, body, options);
export const apiPatch = (endpoint, body, options = {}) => api.patch(endpoint, body, options);
export const apiDelete = (endpoint, options = {}) => api.delete(endpoint, options);
