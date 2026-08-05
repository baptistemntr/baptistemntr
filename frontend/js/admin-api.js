// Auth HTTP Basic gérée explicitement en JS plutôt que via la boîte de dialogue native du
// navigateur : plus prévisible (la boîte native ne se déclenche pas de façon fiable sur un
// fetch()), et permet un formulaire cohérent avec le reste de l'appli. Le mot de passe ne
// vit qu'en mémoire de page : pas de session persistée, conforme au périmètre V1 (un seul
// mot de passe partagé, pas de gestion d'utilisateurs).
let adminAuthHeader = null;

function setAdminPassword(password) {
  adminAuthHeader = "Basic " + btoa("imi:" + password);
}

function clearAdminAuth() {
  adminAuthHeader = null;
}

async function adminRequest(path, options = {}) {
  if (!adminAuthHeader) {
    throw new ApiError(["Non connecté."], 401);
  }
  const headers = { ...(options.headers || {}), Authorization: adminAuthHeader };
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
  getFamily: (code) => adminRequest(`/api/admin/families/${encodeURIComponent(code)}`),
  updateFamily: (code, payload) =>
    adminRequest(`/api/admin/families/${encodeURIComponent(code)}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }),

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
};
