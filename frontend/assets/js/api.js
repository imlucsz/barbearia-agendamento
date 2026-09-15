const API_BASE = "http://localhost:8000";

function getToken() { return localStorage.getItem("token"); }

function getCurrentUser() {
  const raw = localStorage.getItem("user") || localStorage.getItem("usuario");
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  localStorage.removeItem("usuario");
  window.location.href = "index.html";
}

async function apiGet(path) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) throw new Error(`GET ${path} falhou com status ${response.status}`);
  return response.json();
}

async function apiPost(path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!response.ok) throw new Error(`POST ${path} falhou com status ${response.status}`);
  return response.json();
}