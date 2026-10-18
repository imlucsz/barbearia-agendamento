const API_BASE_URL = (window.BARBEARIA_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

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
  window.location.href = "login.html";
}

async function request(endpoint, options = {}) {
  const { method = "GET", body, auth = true, params, headers = {}, ...rest } = options;
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

  const response = await fetch(url, {
    method,
    headers: requestHeaders,
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    ...rest,
  });

  if (!response.ok) {
    const responseText = await response.text();
    let detail = "";
    try {
      const data = JSON.parse(responseText);
      detail = data.detail || data.message || "";
    } catch {
      detail = responseText.trim();
    }
    const error = new Error(detail ? `Erro ${response.status}: ${detail}` : `Erro ${response.status}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  if (response.status === 205) return null;
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
