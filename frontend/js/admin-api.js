// En-tête maison plutôt que `Authorization: Basic` : ce dernier fait entrer en jeu la
// gestion native des identifiants du navigateur (cache par origine, ré-essai automatique)
// dès qu'un 401 survient, ce qui entre en conflit avec ce formulaire de connexion —
// reproduit concrètement (un mauvais mot de passe suivi du bon reste bloqué). Le mot de
// passe ne vit qu'en mémoire de page : pas de session persistée, conforme au périmètre V1
// (un seul mot de passe partagé, pas de gestion d'utilisateurs).
let adminPassword = null;

function setAdminPassword(password) {
  adminPassword = password;
}

function clearAdminAuth() {
  adminPassword = null;
}

async function adminRequest(path, options = {}) {
  if (!adminPassword) {
    throw new ApiError(["Non connecté."], 401);
  }
  const headers = { ...(options.headers || {}), "X-Admin-Password": adminPassword };
  const response = await fetch(API_BASE + path, { ...options, headers });

  if (response.status === 401) {
    clearAdminAuth();
    throw new ApiError(["Mot de passe incorrect."], 401);
  }
  if (response.status === 204) return null;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body && body.detail;
    const messages = Array.isArray(detail) ? detail : [detail || response.statusText];
    throw new ApiError(messages, response.status);
  }
  return body;
}

const adminApi = {
  listFamilies: () => adminRequest("/api/admin/families"),
  getFamily: (code) => adminRequest(`/api/admin/families/${encodeURIComponent(code)}`),
  updateFamily: (code, payload) =>
    adminRequest(`/api/admin/families/${encodeURIComponent(code)}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  checkBom: (code) => adminRequest(`/api/admin/families/${encodeURIComponent(code)}/bom-check`),
  createFamily: (payload) =>
    adminRequest("/api/admin/families", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  deleteFamily: (code) =>
    adminRequest(`/api/admin/families/${encodeURIComponent(code)}`, { method: "DELETE" }),
  searchAgileArticles: (q, finishedOnly = false) =>
    adminRequest(
      `/api/admin/agile-articles?q=${encodeURIComponent(q)}` +
      (finishedOnly ? "&finished_only=true" : "")
    ),

  createGroup: (payload) =>
    adminRequest("/api/admin/groups", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  updateGroup: (id, payload) =>
    adminRequest(`/api/admin/groups/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  deleteGroup: (id) => adminRequest(`/api/admin/groups/${id}`, { method: "DELETE" }),

  createOption: (payload) =>
    adminRequest("/api/admin/options", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  updateOption: (id, payload) =>
    adminRequest(`/api/admin/options/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  deleteOption: (id) => adminRequest(`/api/admin/options/${id}`, { method: "DELETE" }),

  createArticle: (payload) =>
    adminRequest("/api/admin/articles", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  updateArticle: (id, payload) =>
    adminRequest(`/api/admin/articles/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  deleteArticle: (id) => adminRequest(`/api/admin/articles/${id}`, { method: "DELETE" }),

  createRule: (payload) =>
    adminRequest("/api/admin/rules", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  deleteRule: (id) => adminRequest(`/api/admin/rules/${id}`, { method: "DELETE" }),

  createLicenseWord: (payload) =>
    adminRequest("/api/admin/license-words", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  updateLicenseWord: (id, payload) =>
    adminRequest(`/api/admin/license-words/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  deleteLicenseWord: (id) => adminRequest(`/api/admin/license-words/${id}`, { method: "DELETE" }),

  createLicenseBit: (payload) =>
    adminRequest("/api/admin/license-bits", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  updateLicenseBit: (id, payload) =>
    adminRequest(`/api/admin/license-bits/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),
  deleteLicenseBit: (id) => adminRequest(`/api/admin/license-bits/${id}`, { method: "DELETE" }),
};
