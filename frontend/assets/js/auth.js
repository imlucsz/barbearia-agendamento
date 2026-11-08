import { api, setToken } from "./api.js";
import { readPasswordResetToken } from "./reset-token.mjs";

const moneySafeDestinations = {
  cliente: "client-dashboard.html",
  barbeiro: "admin.html",
  admin: "admin.html",
};
let recoveryInFlight = false;
let recoveryAvailableAt = 0;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("current-year").textContent = new Date().getFullYear();
  document.getElementById("login-form")?.addEventListener("submit", login);
  document.getElementById("register-form")?.addEventListener("submit", register);
  document.getElementById("forgot-form")?.addEventListener("submit", forgotPassword);
  document.getElementById("reset-form")?.addEventListener("submit", resetPassword);
});

async function login(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("[type=submit]");
  setBusy(button, true);
  try {
    const data = await api.post("/auth/login", {
      email: form.elements.email.value.trim(),
      senha: form.elements.senha.value,
    }, { auth: false });
    if (!data.access_token || !data.user) throw new Error("Não foi possível entrar na sua conta. Tente novamente.");
    setToken(data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    const redirect = new URLSearchParams(window.location.search).get("redirect");
    window.location.href = safeDestination(redirect, data.user.role);
  } catch (error) {
    showMessage(error.message, "danger");
  } finally {
    setBusy(button, false);
  }
}

async function register(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("[type=submit]");
  setBusy(button, true);
  try {
    await api.post("/auth/register", {
      nome: form.elements.nome.value.trim(),
      email: form.elements.email.value.trim(),
      senha: form.elements.senha.value,
      consentimento_lgpd: form.elements.consentimento_lgpd.checked,
    }, { auth: false });
    showMessage("Cadastro realizado. Entre com seu e-mail e senha para continuar.", "success");
    form.reset();
    window.setTimeout(() => { window.location.href = "login.html"; }, 1200);
  } catch (error) {
    showMessage(error.message, "danger");
  } finally {
    setBusy(button, false);
  }
}

async function forgotPassword(event) {
  event.preventDefault();
  if (recoveryInFlight || Date.now() < recoveryAvailableAt) return;
  recoveryInFlight = true;
  const form = event.currentTarget;
  const button = form.querySelector("[type=submit]");
  setBusy(button, true);
  form.setAttribute("aria-busy", "true");
  try {
    const result = await api.post("/auth/esqueci-senha", {
      email: form.elements.email.value.trim(),
    }, { auth: false });
    showMessage(result.mensagem || "Se o e-mail estiver cadastrado, as instruções serão enviadas.", "success");
  } catch (error) {
    showMessage(error.message, "danger");
  } finally {
    recoveryInFlight = false;
    form.removeAttribute("aria-busy");
    recoveryAvailableAt = Date.now() + 60000;
    const updateCountdown = () => {
      const seconds = Math.max(0, Math.ceil((recoveryAvailableAt - Date.now()) / 1000));
      button.disabled = seconds > 0;
      button.textContent = seconds ? `Solicitar novamente em ${seconds}s` : button.dataset.label;
      if (!seconds) window.clearInterval(timer);
    };
    const timer = window.setInterval(updateCountdown, 1000);
    updateCountdown();
  }
}

async function resetPassword(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const token = readPasswordResetToken(window.location);
  if (!token) {
    showMessage("O link de redefinição está incompleto. Solicite um novo link.", "danger");
    return;
  }
  const button = form.querySelector("[type=submit]");
  setBusy(button, true);
  try {
    const result = await api.post("/auth/redefinir-senha", {
      token,
      nova_senha: form.elements.senha.value,
    }, { auth: false });
    showMessage(result.mensagem || "Senha atualizada. Faça login para continuar.", "success");
    form.reset();
  } catch (error) {
    showMessage(error.message, "danger");
  } finally {
    setBusy(button, false);
  }
}

function safeDestination(value, role) {
  if (value) {
    const target = new URL(value, window.location.href);
    if (target.origin === window.location.origin && target.pathname.startsWith("/")) {
      const file = target.pathname.split("/").pop();
      const allowed = [
        "client-services.html", "client-profissional.html", "client-date.html",
        "client-confirm.html", "client-dashboard.html", "client-appointments.html",
        "client-evaluate.html", "client-account.html", "admin.html",
      ];
      if (allowed.includes(file)) return `${file}${target.search}${target.hash}`;
    }
  }
  return moneySafeDestinations[role] || "client-dashboard.html";
}

function showMessage(message, kind = "info") {
  const box = document.getElementById("form-message");
  box.className = `alert alert-${kind}`;
  box.textContent = message;
  box.hidden = false;
  box.focus();
}

function setBusy(button, busy) {
  button.disabled = busy;
  if (!button.dataset.label) button.dataset.label = button.textContent;
  button.textContent = busy ? "Aguarde…" : button.dataset.label;
}
