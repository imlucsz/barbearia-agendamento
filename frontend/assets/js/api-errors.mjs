export function formatApiError(status, responseText) {
  let detail = "";
  try {
    const data = JSON.parse(responseText);
    if (typeof data.detail === "string") {
      detail = data.detail;
    } else if (Array.isArray(data.detail)) {
      detail = data.detail
        .map((item) => (typeof item?.msg === "string" ? item.msg : ""))
        .filter(Boolean)
        .join("; ");
    }
    if (!detail && typeof data.message === "string") detail = data.message;
  } catch {
    detail = responseText.trim();
  }

  return new Error(detail ? `Erro ${status}: ${detail}` : `Erro ${status}`);
}
