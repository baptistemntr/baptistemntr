// Gamme pilote de l'espace IMI (voir admin.py) : volontairement figée en V1 pour valider
// le modèle avant d'ouvrir les 18 autres gammes à l'édition directe.
const FAMILY_CODE = "DTR";

const state = { family: null };

const el = {
  loginPanel: document.getElementById("login-panel"),
  loginForm: document.getElementById("login-form"),
  loginPassword: document.getElementById("login-password"),
  loginError: document.getElementById("login-error"),
  content: document.getElementById("admin-content"),
  familyForm: document.getElementById("family-form"),
  familyLabel: document.getElementById("family-label"),
  familyDescription: document.getElementById("family-description"),
  groupsList: document.getElementById("groups-list"),
  groupCreateForm: document.getElementById("group-create-form"),
  articlesBody: document.getElementById("articles-body"),
  articleCreateForm: document.getElementById("article-create-form"),
  newArticleOptions: document.getElementById("new-article-options"),
  rulesBody: document.getElementById("rules-body"),
  ruleCreateForm: document.getElementById("rule-create-form"),
  newRuleSource: document.getElementById("new-rule-source"),
  newRuleTarget: document.getElementById("new-rule-target"),
};

function el_(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function allOptions() {
  return state.family.groups.flatMap((g) => g.options.map((o) => ({ ...o, groupLabel: g.label })));
}

function gridOptions() {
  return allOptions().filter((o) => o.kind === "grid");
}

async function init() {
  el.loginForm.addEventListener("submit", onLogin);
  el.familyForm.addEventListener("submit", onSaveFamily);
  el.groupCreateForm.addEventListener("submit", onCreateGroup);
  el.articleCreateForm.addEventListener("submit", onCreateArticle);
  el.ruleCreateForm.addEventListener("submit", onCreateRule);
}

async function onLogin(event) {
  event.preventDefault();
  setAdminPassword(el.loginPassword.value);
  el.loginError.hidden = true;
  try {
    await loadFamily();
    el.loginPanel.hidden = true;
    el.content.hidden = false;
  } catch (error) {
    clearAdminAuth();
    el.loginError.textContent = error.messages ? error.messages.join(" ") : String(error);
    el.loginError.hidden = false;
  }
}

async function loadFamily() {
  state.family = await adminApi.getFamily(FAMILY_CODE);
  render();
}

function render() {
  el.familyLabel.value = state.family.label;
  el.familyDescription.value = state.family.description || "";
  renderGroups();
  renderArticles();
  renderRules();
}

// --- Gamme -------------------------------------------------------------------------------

async function onSaveFamily(event) {
  event.preventDefault();
  await runOrAlert(() =>
    adminApi.updateFamily(FAMILY_CODE, {
      label: el.familyLabel.value,
      description: el.familyDescription.value || null,
    })
  );
  await loadFamily();
}

// --- Groupes et options --------------------------------------------------------------------

function renderGroups() {
  el.groupsList.innerHTML = "";
  for (const group of state.family.groups) {
    el.groupsList.appendChild(renderGroup(group));
  }
}

function renderGroup(group) {
  const box = el_("div", "admin-group");

  const header = el_("div", "admin-group-header");
  header.appendChild(el_("span", "admin-group-code", group.code));
  const deleteGroupBtn = el_("button", "danger", "Supprimer le groupe");
  deleteGroupBtn.type = "button";
  deleteGroupBtn.addEventListener("click", () => onDeleteGroup(group));
  header.appendChild(deleteGroupBtn);
  box.appendChild(header);

  const form = document.createElement("form");
  form.appendChild(labeledInput("Libellé", "text", group.label, (v) => (group._label = v)));
  form.appendChild(labeledInput("Section", "text", group.section || "", (v) => (group._section = v)));
  form.appendChild(labeledInput("Aide (survol)", "text", group.help_text || "", (v) => (group._help = v)));
  const saveBtn = el_("button", null, "Enregistrer le groupe");
  saveBtn.type = "submit";
  form.appendChild(saveBtn);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSaveGroup(group);
  });
  box.appendChild(form);

  for (const option of group.options) {
    box.appendChild(renderOptionRow(group, option));
  }
  box.appendChild(renderOptionCreateForm(group));

  return box;
}

function labeledInput(labelText, type, value, onChange) {
  const label = el_("label", null, labelText);
  const input = document.createElement("input");
  input.type = type;
  input.value = value;
  input.addEventListener("input", () => onChange(input.value));
  label.appendChild(input);
  return label;
}

async function onSaveGroup(group) {
  await runOrAlert(() =>
    adminApi.updateGroup(group.id, {
      label: group._label ?? group.label,
      section: (group._section ?? group.section) || null,
      help_text: (group._help ?? group.help_text) || null,
      selection: group.selection,
      required: group.required,
      position: group.position,
    })
  );
  await loadFamily();
}

async function onDeleteGroup(group) {
  if (!confirm(`Supprimer le groupe « ${group.label} » et ses options ?`)) return;
  await runOrAlert(() => adminApi.deleteGroup(group.id));
  await loadFamily();
}

async function onCreateGroup(event) {
  event.preventDefault();
  await runOrAlert(() =>
    adminApi.createGroup({
      family_code: FAMILY_CODE,
      code: document.getElementById("new-group-code").value,
      label: document.getElementById("new-group-label").value,
      section: document.getElementById("new-group-section").value || null,
      selection: document.getElementById("new-group-selection").value,
      position: state.family.groups.length,
    })
  );
  event.target.reset();
  await loadFamily();
}

function renderOptionRow(group, option) {
  const row = el_("div", "admin-option-row");
  row.appendChild(el_("span", "admin-option-caption", option.caption));

  const label = document.createElement("input");
  label.type = "text";
  label.value = option.label;
  row.appendChild(label);

  const technical = document.createElement("input");
  technical.type = "text";
  technical.placeholder = "Définition technique (infobulle)";
  technical.value = option.technical_label || "";
  row.appendChild(technical);

  const actions = el_("span");
  const saveBtn = el_("button", null, "Enregistrer");
  saveBtn.type = "button";
  saveBtn.addEventListener("click", () => onSaveOption(option, label.value, technical.value));
  actions.appendChild(saveBtn);
  const deleteBtn = el_("button", "danger", "Supprimer");
  deleteBtn.type = "button";
  deleteBtn.addEventListener("click", () => onDeleteOption(option));
  actions.appendChild(deleteBtn);
  row.appendChild(actions);

  return row;
}

async function onSaveOption(option, label, technicalLabel) {
  await runOrAlert(() =>
    adminApi.updateOption(option.id, {
      label,
      technical_label: technicalLabel || null,
      help_text: option.help_text,
      kind: option.kind,
      component_item_number: option.component_item_number,
      unit_price: option.unit_price,
      position: option.position,
    })
  );
  await loadFamily();
}

async function onDeleteOption(option) {
  if (!confirm(`Supprimer l'option « ${option.label} » ? Toute ligne de grille qui l'utilise perdra cette option.`)) return;
  await runOrAlert(() => adminApi.deleteOption(option.id));
  await loadFamily();
}

function renderOptionCreateForm(group) {
  const details = document.createElement("details");
  details.className = "admin-add";
  const summary = el_("summary", null, "Ajouter une option à ce groupe");
  details.appendChild(summary);

  const form = document.createElement("form");
  const caption = document.createElement("input");
  caption.type = "text";
  caption.placeholder = "Nom technique (fixe une fois créé — relie l'option à la grille)";
  caption.required = true;
  form.appendChild(wrapLabel("Nom technique (caption)", caption));

  const label = document.createElement("input");
  label.type = "text";
  label.placeholder = "Libellé commercial";
  label.required = true;
  form.appendChild(wrapLabel("Libellé commercial", label));

  const kind = document.createElement("select");
  for (const [value, text] of [["grid", "grid (détermine l'article)"], ["commercial", "commercial (informatif)"]]) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = text;
    kind.appendChild(opt);
  }
  form.appendChild(wrapLabel("Type", kind));

  const submit = el_("button", null, "Créer");
  submit.type = "submit";
  form.appendChild(submit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await runOrAlert(() =>
      adminApi.createOption({
        group_id: group.id,
        caption: caption.value,
        label: label.value,
        kind: kind.value,
        position: group.options.length,
      })
    );
    await loadFamily();
  });

  details.appendChild(form);
  return details;
}

function wrapLabel(text, inputEl) {
  const label = el_("label", null, text);
  label.appendChild(inputEl);
  return label;
}

// --- Grille (articles) ---------------------------------------------------------------------

function renderArticles() {
  el.articlesBody.innerHTML = "";
  for (const article of state.family.articles) {
    el.articlesBody.appendChild(renderArticleRow(article));
  }
  renderOptionCheckboxes(el.newArticleOptions, []);
}

function renderArticleRow(article) {
  const row = document.createElement("tr");

  const itemInput = tableInput(article.item_number || "");
  const designationInput = tableInput(article.designation || "");
  const refInput = tableInput(article.commercial_ref || "");
  const priceInput = tableInput(article.standard_price ?? "", "number");

  row.appendChild(wrapCell(itemInput));
  row.appendChild(wrapCell(designationInput));
  row.appendChild(wrapCell(refInput));
  row.appendChild(wrapCell(priceInput));

  const optionsCell = document.createElement("td");
  const checkboxContainer = el_("div", "admin-checkboxes");
  optionsCell.appendChild(checkboxContainer);
  renderOptionCheckboxes(checkboxContainer, article.option_ids);
  row.appendChild(optionsCell);

  const actionsCell = document.createElement("td");
  const saveBtn = el_("button", null, "Enregistrer");
  saveBtn.type = "button";
  saveBtn.addEventListener("click", () =>
    onSaveArticle(article, {
      item_number: itemInput.value || null,
      designation: designationInput.value || null,
      commercial_ref: refInput.value || null,
      standard_price: priceInput.value === "" ? null : Number(priceInput.value),
      option_ids: checkedIds(checkboxContainer),
    })
  );
  actionsCell.appendChild(saveBtn);
  const deleteBtn = el_("button", "danger", "Supprimer");
  deleteBtn.type = "button";
  deleteBtn.addEventListener("click", () => onDeleteArticle(article));
  actionsCell.appendChild(deleteBtn);
  row.appendChild(actionsCell);

  return row;
}

function tableInput(value, type = "text") {
  const input = document.createElement("input");
  input.type = type;
  if (type === "number") input.step = "0.01";
  input.value = value;
  return input;
}

function wrapCell(inputEl) {
  const cell = document.createElement("td");
  cell.appendChild(inputEl);
  return cell;
}

function renderOptionCheckboxes(container, checkedOptionIds) {
  container.innerHTML = "";
  const checked = new Set(checkedOptionIds);
  for (const option of gridOptions()) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = String(option.id);
    input.checked = checked.has(option.id);
    label.appendChild(input);
    label.appendChild(document.createTextNode(` ${option.groupLabel} : ${option.label}`));
    container.appendChild(label);
  }
}

function checkedIds(container) {
  return Array.from(container.querySelectorAll("input:checked"), (input) => Number(input.value));
}

async function onSaveArticle(article, payload) {
  await runOrAlert(() => adminApi.updateArticle(article.id, payload));
  await loadFamily();
}

async function onDeleteArticle(article) {
  if (!confirm(`Supprimer la ligne de grille ${article.item_number || "(sans code article)"} ?`)) return;
  await runOrAlert(() => adminApi.deleteArticle(article.id));
  await loadFamily();
}

async function onCreateArticle(event) {
  event.preventDefault();
  await runOrAlert(() =>
    adminApi.createArticle({
      family_code: FAMILY_CODE,
      item_number: document.getElementById("new-article-item").value || null,
      designation: document.getElementById("new-article-designation").value || null,
      commercial_ref: document.getElementById("new-article-ref").value || null,
      standard_price: document.getElementById("new-article-price").value
        ? Number(document.getElementById("new-article-price").value)
        : null,
      option_ids: checkedIds(el.newArticleOptions),
    })
  );
  event.target.reset();
  await loadFamily();
}

// --- Règles de compatibilité -----------------------------------------------------------

function renderRules() {
  el.rulesBody.innerHTML = "";
  const optionsById = new Map(allOptions().map((o) => [o.id, o]));
  for (const rule of state.family.rules) {
    const row = document.createElement("tr");
    const source = optionsById.get(rule.source_option_id);
    const target = optionsById.get(rule.target_option_id);
    row.appendChild(el_("td", null, source ? source.label : `#${rule.source_option_id}`));
    row.appendChild(el_("td", null, rule.kind === "requires" ? "nécessite" : "exclut"));
    row.appendChild(el_("td", null, target ? target.label : `#${rule.target_option_id}`));
    row.appendChild(el_("td", null, rule.message || ""));
    const actionsCell = document.createElement("td");
    const deleteBtn = el_("button", "danger", "Supprimer");
    deleteBtn.type = "button";
    deleteBtn.addEventListener("click", () => onDeleteRule(rule));
    actionsCell.appendChild(deleteBtn);
    row.appendChild(actionsCell);
    el.rulesBody.appendChild(row);
  }

  el.newRuleSource.innerHTML = "";
  el.newRuleTarget.innerHTML = "";
  for (const option of allOptions()) {
    const text = `${option.groupLabel} : ${option.label}`;
    el.newRuleSource.appendChild(new Option(text, option.id));
    el.newRuleTarget.appendChild(new Option(text, option.id));
  }
}

async function onDeleteRule(rule) {
  if (!confirm("Supprimer cette règle ?")) return;
  await runOrAlert(() => adminApi.deleteRule(rule.id));
  await loadFamily();
}

async function onCreateRule(event) {
  event.preventDefault();
  await runOrAlert(() =>
    adminApi.createRule({
      family_code: FAMILY_CODE,
      kind: document.getElementById("new-rule-kind").value,
      source_option_id: Number(el.newRuleSource.value),
      target_option_id: Number(el.newRuleTarget.value),
      message: document.getElementById("new-rule-message").value || null,
    })
  );
  event.target.reset();
  await loadFamily();
}

// --- Utilitaire ---------------------------------------------------------------------------

async function runOrAlert(action) {
  try {
    return await action();
  } catch (error) {
    alert(error.messages ? error.messages.join(" ") : String(error));
    throw error;
  }
}

init();
