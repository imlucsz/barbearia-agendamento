import test from "node:test";
import assert from "node:assert/strict";
import { formatApiError } from "../assets/js/api-errors.mjs";

test("formats structured FastAPI validation errors without object coercion or submitted input", () => {
  const error = formatApiError(422, JSON.stringify({
    detail: [
      { loc: ["body", "duracao_minutos"], msg: "Input should be greater than 0", type: "greater_than", input: 0 },
      { loc: ["body", "nome"], msg: "Field required", type: "missing", input: "private-value" },
    ],
  }));

  assert.equal(error.message, "Confira os dados informados.; Preencha este campo.");
  assert.doesNotMatch(error.message, /\[object Object\]|private-value/);
});

test("keeps string API error details and plain-text fallback", () => {
  assert.equal(
    formatApiError(403, JSON.stringify({ detail: "Acesso negado" })).message,
    "Acesso negado",
  );
  assert.equal(formatApiError(502, "upstream unavailable").message, "Não foi possível concluir a operação. Tente novamente.");
});

test("email validation is Portuguese and does not expose Pydantic internals", () => {
  assert.equal(formatApiError(422, JSON.stringify({detail:[{loc:['body','email'],type:'value_error',msg:'value is not a valid email address'}]})).message, 'Digite um endereço de e-mail válido.');
});

test("known account states are mapped; arbitrary technical prose is never trusted", () => {
  for (const text of ["Erro de configuração: permission denied", "Falha com acentuação SELECT private", "Traceback", "Acesso negado: detalhe privado"]) {
    assert.equal(formatApiError(400, JSON.stringify({detail:text})).message, "Não foi possível concluir a operação. Tente novamente.");
  }
  assert.match(formatApiError(403, JSON.stringify({detail:"Conta bloqueada"})).message, /conta está bloqueada/);
  assert.match(formatApiError(403, JSON.stringify({detail:"Conta inativa"})).message, /conta está inativa/);
  const error = formatApiError(422, JSON.stringify({detail:[{loc:["body","email"],type:"missing",input:"private"}]}));
  assert.equal(error.message, "Preencha este campo.");
  assert.deepEqual(error.validation, [{location:["body","email"],type:"missing"}]);
  assert.doesNotMatch(JSON.stringify(error), /private/);
});
