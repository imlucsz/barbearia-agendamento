// api.js - Funções centralizadas para comunicação com o backend
// Base URL da API (ajustar conforme ambiente)
const API_BASE_URL = "http://127.0.0.1:8000";

// Função interna para obter o token de autenticação (ex: do localStorage)
function getAuthToken() {
  return localStorage.getItem('token');
}

// Função interna para configurar headers comuns
function getHeaders(includeAuth = true) {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (includeAuth) {
    const token = getAuthToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }
  return headers;
}

// Função genérica de requisição
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const { method = 'GET', body, auth = true, ...rest } = options;

  const config = {
    method,
    headers: getHeaders(auth),
    ...rest,
  };

  if (body && !(body instanceof FormData)) {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, config);
    // Tratamento de erros comuns
    if (!response.ok) {
      let errorMsg = `Erro ${response.status}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMsg += `: ${errorData.detail}`;
        } else if (errorData.message) {
          errorMsg += `: ${errorData.message}`;
        }
      } catch (e) {
        // Se não conseguir parsear o JSON, usa o texto da resposta
        errorMsg += `: ${await response.text()}`;
      }
      throw new Error(errorMsg);
    }
    // Se a resposta não tiver conteúdo (ex: 204), retorna null
    if (response.status === 204) {
      return null;
    }
    return await response.json();
  } catch (error) {
    // Re-throw para que o chamador possa tratar
    throw error;
  }
}

// Exporta métodos HTTP específicos
export const api = {
  get: (endpoint, opts = {}) => request(endpoint, { method: 'GET', ...opts }),
  post: (endpoint, data, opts = {}) => request(endpoint, { method: 'POST', body: data, ...opts }),
  put: (endpoint, data, opts = {}) => request(endpoint, { method: 'PUT', body: data, ...opts }),
  patch: (endpoint, data, opts = {}) => request(endpoint, { method: 'PATCH', body: data, ...opts }),
  delete: (endpoint, opts = {}) => request(endpoint, { method: 'DELETE', ...opts }),
};

// Função auxiliar para atualizar o token (ex: após login)
export function setToken(token) {
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
}

// Função auxiliar para limpar o token (logout)
export function clearToken() {
  localStorage.removeItem('token');
}