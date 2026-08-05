const state = { familyCode: null, family: null };

const el = {
  loginPanel: document.getElementById("login-panel"),
  loginForm: document.getElementById("login-form"),
  loginPassword: document.getElementById("login-password"),
  loginError: document.getElementById("login-error"),
  familyPicker: document.getElementById("admin-family-picker"),
  content: document.getElementById("admin-content"),
  licensePanel: document.getElementById("license-panel"),
  licenseCrtNotice: document.getElementById("license-crt-notice"),
  licenseWordsList: document.getElementById("license-words-list"),
  licenseWordAdd: document.getElementById("license-word-add"),
  licenseWordCreateForm: document.getElementById("license-word-create-form"),
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

function licenseOptions() {
  return allOptions().filter((o) => o.kind === "license");
}

// CRT (FEP) calcule sa licence directement dans le code (resolver.build_fep_license), pas
// via des mots/bits en base : créer un mot ici pour cette gamme n'aurait aucun effet.
const NO_LICENSE_WORDS_FAMILY = "CRT";

async function init() {
  el.loginForm.addEventListener("submit", onLogin);
  el.familyForm.addEventListener("submit", onSaveFamily);
  el.groupCreateForm.addEventListener("submit", onCreateGroup);
  el.articleCreateForm.addEventListener("submit", onCreateArticle);
  el.ruleCreateForm.addEventListener("submit", onCreateRule);
  el.licenseWordCreateForm.addEventListener("submit", onCreateLicenseWord);
}

async function onLogin(event) {
  event.preventDefault();
  setAdminPassword(el.loginPassword.value);
  el.loginError.hidden = true;
  try {
    const families = await adminApi.listFamilies();
    el.loginPanel.hidden = true;
    renderFamilyPicker(families);
  } catch (error) {
    clearAdminAuth();
    el.loginError.textContent = error.messages ? error.messages.join(" ") : String(error);
    el.loginError.hidden = false;
  }
}

function renderFamilyPicker(families) {
  el.familyPicker.innerHTML = "";
  el.familyPicker.hidden = false;
  for (const family of families) {
    const button = el_("button", null, family.label);
    button.type = "button";
    if (family.code === state.familyCode) button.classList.add("active");
    button.addEventListener("click", () => selectFamily(family.code, button));
    el.familyPicker.appendChild(button);
  }
}

async function selectFamily(code, button) {
  for (const child of el.familyPicker.children) child.classList.remove("active");
  if (button) button.classList.add("active");
  state.familyCode = code;
  await loadFamily();
  el.content.hidden = false;
}

async function loadFamily() {
  state.family = await adminApi.getFamily(state.familyCode);
  render();
}

function render() {
  el.familyLabel.value = state.family.label;
  el.familyDescription.value = state.family.description || "";
  renderLicensePanel();
  renderGroups();
  renderArticles();
  renderRules();
}

// --- Gamme -------------------------------------------------------------------------------

async function onSaveFamily(event) {
  event.preventDefault();
  await runOrAlert(() =>
    adminApi.updateFamily(state.familyCode, {
      label: el.familyLabel.value,
      description: el.familyDescription.value || null,
    })
  );
  await loadFamily();
}

// --- Licences (mots/bits, HDR et SATCORE — pas CRT, voir NO_LICENSE_WORDS_FAMILY) -------

function renderLicensePanel() {
  if (!state.family.has_license) {
    el.licensePanel.hidden = true;
    return;
  }
  el.licensePanel.hidden = false;

  const isCrt = state.familyCode === NO_LICENSE_WORDS_FAMILY;
  el.licenseCrtNotice.hidden = !isCrt;
  el.licenseWordAdd.hidden = isCrt;

  el.licenseWordsList.innerHTML = "";
  for (const word of state.family.license_words) {
    el.licenseWordsList.appendChild(renderLicenseWord(word));
  }
}

function renderLicenseWord(word) {
  const box = el_("div", "admin-group");

  const header = el_("div", "admin-group-header");
  header.appendChild(el_("span", "admin-group-code", word.code));
  const deleteBtn = el_("button", "danger", "Supprimer le mot");
  deleteBtn.type = "button";
  deleteBtn.addEventListener("click", () => onDeleteLicenseWord(word));
  header.appendChild(deleteBtn);
  box.appendChild(header);

  const form = document.createElement("form");
  form.appendChild(labeledInput("Libellé", "text", word.label, (v) => (word._label = v)));
  const saveBtn = el_("button", null, "Enregistrer le mot");
  saveBtn.type = "submit";
  form.appendChild(saveBtn);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    onSaveLicenseWord(word);
  });
  box.appendChild(form);

  for (const bit of word.bits) {
    box.appendChild(renderLicenseBitRow(word, bit));
  }
  box.appendChild(renderLicenseBitCreateForm(word));

  return box;
}

async function onSaveLicenseWord(word) {
  await runOrAlert(() =>
    adminApi.updateLicenseWord(word.id, {
      label: word._label ?? word.label,
      position: word.position,
    })
  );
  await loadFamily();
}

async function onDeleteLicenseWord(word) {
  if (!confirm(`Supprimer le mot de licence « ${word.label} » et tous ses bits ?`)) return;
  await runOrAlert(() => adminApi.deleteLicenseWord(word.id));
  await loadFamily();
}

async function onCreateLicenseWord(event) {
  event.preventDefault();
  await runOrAlert(() =>
    adminApi.createLicenseWord({
      family_code: state.familyCode,
      code: document.getElementById("new-word-code").value,
      label: document.getElementById("new-word-label").value,
      position: state.family.license_words.length,
    })
  );
  event.target.reset();
  await loadFamily();
}

// Un bit est soit piloté par une ou plusieurs options (OU), soit figé (VRAI/FAUX constant,
// ex. les bits toujours inclus de SATCORE), soit non calculable (raison expliquée plutôt
// que compté silencieusement à 0) — jamais deux à la fois, voir LicenseBit dans models.py.
function bitMode(bit) {
  if (bit.constant_value === true) return "constant_true";
  if (bit.constant_value === false) return "constant_false";
  if (bit.unmapped_reason) return "unmapped";
  return "options";
}

function renderLicenseBitRow(word, bit) {
  const row = el_("div", "admin-group");
  row.style.marginLeft = "1.5rem";

  const header = el_("div", "admin-group-header");
  header.appendChild(el_("span", "admin-group-code", `D${bit.position} — poids ${bit.weight}`));
  const deleteBtn = el_("button", "danger", "Supprimer");
  deleteBtn.type = "button";
  deleteBtn.addEventListener("click", () => onDeleteLicenseBit(bit));
  header.appendChild(deleteBtn);
  row.appendChild(header);

  const form = document.createElement("form");
  const fields = {};
  fields.position = numberInput("Position (Dn)", bit.position);
  fields.weight = numberInput("Poids", bit.weight);
  fields.label = textInput("Libellé", bit.label);
  fields.sourceCell = textInput("Cellule source (classeur)", bit.source_cell || "");
  form.appendChild(fields.position.label);
  form.appendChild(fields.weight.label);
  form.appendChild(fields.label.label);
  form.appendChild(fields.sourceCell.label);

  const modeSelect = document.createElement("select");
  for (const [value, text] of [
    ["options", "Piloté par une ou plusieurs options (OU)"],
    ["constant_true", "Toujours VRAI (constante)"],
    ["constant_false", "Toujours FAUX (constante)"],
    ["unmapped", "Non calculable (raison à expliquer)"],
  ]) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = text;
    modeSelect.appendChild(opt);
  }
  modeSelect.value = bitMode(bit);
  form.appendChild(wrapLabel("Mode", modeSelect));

  const optionsContainer = el_("div", "admin-checkboxes");
  renderOptionCheckboxes(optionsContainer, bit.option_ids, licenseOptions());
  const reasonInput = textInput("Raison (non calculable)", bit.unmapped_reason || "");

  function syncMode() {
    optionsContainer.hidden = modeSelect.value !== "options";
    reasonInput.label.hidden = modeSelect.value !== "unmapped";
  }
  modeSelect.addEventListener("change", syncMode);
  syncMode();

  form.appendChild(optionsContainer);
  form.appendChild(reasonInput.label);

  const saveBtn = el_("button", null, "Enregistrer le bit");
  saveBtn.type = "submit";
  form.appendChild(saveBtn);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const mode = modeSelect.value;
    onSaveLicenseBit(bit, {
      position: Number(fields.position.input.value),
      weight: Number(fields.weight.input.value),
      label: fields.label.input.value,
      source_cell: fields.sourceCell.input.value || null,
      constant_value: mode === "constant_true" ? true : mode === "constant_false" ? false : null,
      unmapped_reason: mode === "unmapped" ? reasonInput.input.value || null : null,
      option_ids: mode === "options" ? checkedIds(optionsContainer) : [],
    });
  });
  row.appendChild(form);

  return row;
}

function numberInput(labelText, value) {
  const input = document.createElement("input");
  input.type = "number";
  input.value = value;
  return { label: wrapLabel(labelText, input), input };
}

function textInput(labelText, value) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = value;
  return { label: wrapLabel(labelText, input), input };
}

async function onSaveLicenseBit(bit, payload) {
  await runOrAlert(() => adminApi.updateLicenseBit(bit.id, payload));
  await loadFamily();
}

async function onDeleteLicenseBit(bit) {
  if (!confirm(`Supprimer le bit « ${bit.label} » ?`)) return;
  await runOrAlert(() => adminApi.deleteLicenseBit(bit.id));
  await loadFamily();
}

function renderLicenseBitCreateForm(word) {
  const details = document.createElement("details");
  details.className = "admin-add";
  details.appendChild(el_("summary", null, "Ajouter un bit à ce mot"));

  const form = document.createElement("form");
  const position = numberInput("Position (Dn)", word.bits.length);
  const label = textInput("Libellé", "");
  form.appendChild(position.label);
  form.appendChild(label.label);

  const optionsContainer = el_("div", "admin-checkboxes");
  renderOptionCheckboxes(optionsContainer, [], licenseOptions());
  form.appendChild(optionsContainer);

  const submit = el_("button", null, "Créer");
  submit.type = "submit";
  form.appendChild(submit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const pos = Number(position.input.value);
    await runOrAlert(() =>
      adminApi.createLicenseBit({
        word_id: word.id,
        position: pos,
        weight: 2 ** pos,
        label: label.input.value,
        option_ids: checkedIds(optionsContainer),
      })
    );
    await loadFamily();
  });

  details.appendChild(form);
  return details;
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
      family_code: state.familyCode,
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

function renderOptionCheckboxes(container, checkedOptionIds, options = gridOptions()) {
  container.innerHTML = "";
  const checked = new Set(checkedOptionIds);
  for (const option of options) {
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
      family_code: state.familyCode,
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
      family_code: state.familyCode,
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
