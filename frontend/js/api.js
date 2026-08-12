// Chemin relatif par défaut : le backend sert désormais ce dossier lui-même (voir
// server.py), donc frontend et API partagent toujours la même origine. À ne renseigner
// que si ce fichier est servi séparément du backend (ex. déploiement statique distinct).
const API_BASE = window.CATALOGUE_API_BASE || "";

// Un proxy réseau peut intercepter une requête sans jamais répondre : sans limite, ça
// reste bloqué indéfiniment sans que l'utilisateur voie d'erreur.
const REQUEST_TIMEOUT_MS = 8000;

async function apiRequest(path, options) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(API_BASE + path, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new ApiError(
        [`Aucune réponse de ${API_BASE} après ${REQUEST_TIMEOUT_MS / 1000}s (proxy ou pare-feu ?).`],
        0
      );
    }
    throw new ApiError([`Connexion à ${API_BASE} impossible : ${error.message}`], 0);
  } finally {
    clearTimeout(timeout);
  }

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
  listFamilyArticles: (code) => apiRequest(`/api/families/${encodeURIComponent(code)}/articles`),
  configure: (familyCode, optionIds) =>
    apiRequest("/api/configure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ family_code: familyCode, option_ids: optionIds }),
    }),
};
