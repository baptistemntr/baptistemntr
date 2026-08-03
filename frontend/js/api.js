// Base de l'API catalogue. À adapter si le backend n'écoute pas sur ce port.
const API_BASE = window.CATALOGUE_API_BASE || "http://localhost:8010";

async function apiRequest(path, options) {
  const response = await fetch(API_BASE + path, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    // /api/configure renvoie les violations de règles dans `detail`, à afficher telles quelles.
    const detail = body && body.detail;
    const messages = Array.isArray(detail) ? detail : [detail || response.statusText];
    throw new ApiError(messages, response.status);
  }
  return body;
}

class ApiError extends Error {
  constructor(messages, status) {
    super(messages.join(" "));
    this.messages = messages;
    this.status = status;
  }
}

const api = {
  health: () => apiRequest("/api/health"),
  listFamilies: () => apiRequest("/api/families"),
  getFamily: (code) => apiRequest(`/api/families/${encodeURIComponent(code)}`),
  configure: (familyCode, optionIds) =>
    apiRequest("/api/configure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ family_code: familyCode, option_ids: optionIds }),
    }),
};
