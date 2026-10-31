const messages = new Map([
  ["Email ou senha incorretos", "E-mail ou senha incorretos."],
  ["Email já registrado", "Este e-mail já está cadastrado."],
  ["E-mail já cadastrado", "Este e-mail já está cadastrado."],
  ["Conta bloqueada", "Sua conta está bloqueada. Entre em contato com a barbearia."],
  ["Conta inativa", "Sua conta está inativa. Entre em contato com a barbearia."],
  ["Sessão expirada", "Sua sessão expirou. Entre novamente."],
  ["Sessão revogada", "Sua sessão expirou. Entre novamente."],
  ["Token inválido ou expirado", "O link é inválido ou expirou. Solicite um novo link."],
]);
for (const message of [
  "Acesso negado", "A senha atual está incorreta", "O consentimento para tratamento de dados é obrigatório",
  "O horário foi reservado por outra pessoa. Escolha outro horário.",
  "O agendamento conflita com outro agendamento", "Serviço não encontrado", "Usuário não encontrado",
  "O horário selecionado conflita com outro agendamento", "O horário selecionado está bloqueado",
  "Não é possível agendar em um horário passado", "O barbeiro não atende nesta data",
  "O horário não comporta a duração do serviço dentro da jornada",
  "Seus dados contêm caracteres não suportados neste PDF. Use a exportação JSON para preservá-los integralmente.",
  "A exclusão não é permitida porque esta é a última conta administradora ativa.",
]) messages.set(message, message);

export function formatApiError(status, responseText) {
  let detail = "";
  let validation = false;
  try {
    const data = JSON.parse(responseText);
    if (typeof data.detail === "string") {
      detail = data.detail;
    } else if (status === 422 && Array.isArray(data.detail)) {
      validation = true;
      detail = data.detail
        .map((item) => item?.type === "missing" ? "Preencha este campo."
          : item?.loc?.at(-1) === "email" ? "Digite um endereço de e-mail válido."
            : "Confira os dados informados.")
        .filter(Boolean)
        .join("; ");
    }
    if (!detail && typeof data.message === "string") detail = data.message;
  } catch {
    detail = "";
  }

  const message = validation && detail ? detail
    : status >= 400 && status < 500 && messages.has(detail) ? messages.get(detail)
      : "Não foi possível concluir a operação. Tente novamente.";
  const error = new Error(message);
  error.status = status;
  // Retain validation locations/types for developer inspection, never inputs.
  try {
    const data = JSON.parse(responseText);
    if (Array.isArray(data.detail)) error.validation = data.detail.map(item => ({
      location: item.loc, type: item.type,
    }));
  } catch { /* Non-JSON gateway responses are intentionally not exposed. */ }
  return error;
}
