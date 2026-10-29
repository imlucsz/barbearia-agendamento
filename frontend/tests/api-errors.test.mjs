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

  assert.equal(error.message, "Erro 422: Input should be greater than 0; Field required");
  assert.doesNotMatch(error.message, /\[object Object\]|private-value/);
});

test("keeps string API error details and plain-text fallback", () => {
  assert.equal(
    formatApiError(403, JSON.stringify({ detail: "Acesso negado" })).message,
    "Erro 403: Acesso negado",
  );
  assert.equal(formatApiError(502, "upstream unavailable").message, "Erro 502: upstream unavailable");
});
