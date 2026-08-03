const state = {
  families: [],
  currentFamily: null, // détail complet (avec groups) de la gamme sélectionnée
  selectedIds: new Set(),
};

const el = {
  familyPicker: document.getElementById("family-picker"),
  configurator: document.getElementById("configurator"),
  familyTitle: document.getElementById("family-title"),
  groups: document.getElementById("groups"),
  recapEmpty: document.getElementById("recap-empty"),
  recapContent: document.getElementById("recap-content"),
  designation: document.getElementById("recap-designation"),
  commercialRef: document.getElementById("recap-commercial-ref"),
  itemNumber: document.getElementById("recap-item-number"),
  price: document.getElementById("recap-price"),
  messages: document.getElementById("recap-messages"),
  license: document.getElementById("recap-license"),
  closest: document.getElementById("recap-closest"),
  exportButton: document.getElementById("export-button"),
  tooltipLayer: document.getElementById("tooltip-layer"),
  tooltipText: document.getElementById("tooltip-text"),
  tooltipClose: document.getElementById("tooltip-close"),
};

function el_(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function init() {
  el.exportButton.addEventListener("click", () => window.print());
  el.tooltipClose.addEventListener("click", hideTooltip);
  el.tooltipLayer.addEventListener("click", (event) => {
    if (event.target === el.tooltipLayer) hideTooltip();
  });

  try {
    state.families = await api.listFamilies();
    renderFamilyPicker();
  } catch (error) {
    el.recapEmpty.textContent =
      `Impossible de contacter l'API (${API_BASE}) : ${error.message}. ` +
      "Vérifiez que le backend tourne et qu'il est joignable depuis ce navigateur.";
  }
}

function renderFamilyPicker() {
  el.familyPicker.innerHTML = "";
  for (const family of state.families) {
    const button = el_("button", null, family.label);
    button.type = "button";
    if (family.has_license) {
      button.appendChild(el_("span", "license-badge", "🔑 licence"));
    }
    button.addEventListener("click", () => selectFamily(family.code, button));
    el.familyPicker.appendChild(button);
  }
}

async function selectFamily(code, button) {
  for (const child of el.familyPicker.children) child.classList.remove("active");
  button.classList.add("active");

  state.currentFamily = await api.getFamily(code);
  state.selectedIds = new Set();

  el.familyTitle.textContent = state.currentFamily.label;
  el.configurator.hidden = false;
  renderGroups();
  await refreshConfiguration();
}

function renderGroups() {
  el.groups.innerHTML = "";
  let currentSection = null;
  let sectionEl = null;

  for (const group of state.currentFamily.groups) {
    const sectionKey = group.section || group.label;
    if (sectionKey !== currentSection) {
      currentSection = sectionKey;
      sectionEl = el_("section", "section");
      sectionEl.appendChild(el_("div", "section-title", sectionKey));
      el.groups.appendChild(sectionEl);
    }

    const groupEl = el_("div", "group");
    // Les groupes issus des licences/attributs commerciaux portent déjà leur nom dans le
    // titre de section : répéter le libellé ici serait redondant.
    if (group.section) {
      groupEl.appendChild(el_("span", "group-label", group.label));
    }

    for (const option of group.options) {
      groupEl.appendChild(renderOption(group, option));
    }
    sectionEl.appendChild(groupEl);
  }
}

function renderOption(group, option) {
  const row = el_("div", "option-row");

  const input = document.createElement("input");
  input.type = group.selection === "single" ? "radio" : "checkbox";
  input.name = group.selection === "single" ? `group-${group.id}` : `option-${option.id}`;
  input.id = `option-input-${option.id}`;
  input.dataset.optionId = String(option.id);
  input.addEventListener("change", onSelectionChange);

  const label = el_("label", null, option.label);
  label.htmlFor = input.id;

  row.appendChild(input);
  row.appendChild(label);

  if (option.technical_label) {
    const info = el_("button", "info-button", "i");
    info.type = "button";
    info.setAttribute("aria-label", `Définition de ${option.label}`);
    info.addEventListener("click", () => showTooltip(option.technical_label));
    row.appendChild(info);
  }

  return row;
}

function onSelectionChange() {
  state.selectedIds = new Set(
    Array.from(el.groups.querySelectorAll("input:checked"), (input) =>
      Number(input.dataset.optionId)
    )
  );
  refreshConfiguration();
}

async function refreshConfiguration() {
  try {
    const result = await api.configure(state.currentFamily.code, Array.from(state.selectedIds));
    renderResult(result);
  } catch (error) {
    renderViolations(error.messages || [error.message]);
  }
}

function renderResult(result) {
  el.recapEmpty.hidden = true;
  el.recapContent.hidden = false;

  el.designation.textContent = result.designation || "—";
  el.commercialRef.textContent = result.commercial_ref || "—";
  el.itemNumber.textContent = result.item_number || "—";
  el.price.textContent = formatPrice(result.price);

  el.messages.innerHTML = "";
  for (const warning of result.warnings || []) {
    el.messages.appendChild(el_("div", result.found ? "message message-warning" : "message message-error", warning));
  }

  renderLicense(result.license);
  renderClosest(result.closest);
}

function renderViolations(messages) {
  el.recapEmpty.hidden = true;
  el.recapContent.hidden = false;

  el.designation.textContent = "—";
  el.commercialRef.textContent = "—";
  el.itemNumber.textContent = "—";
  el.price.textContent = "—";

  el.messages.innerHTML = "";
  for (const message of messages) {
    el.messages.appendChild(el_("div", "message message-error", message));
  }
  el.license.hidden = true;
  el.closest.hidden = true;
}

function formatPrice(price) {
  if (!price || price.amount === null || price.amount === undefined) {
    const missing = (price && price.missing_prices) || [];
    return missing.length ? `Indisponible (manque : ${missing.join(", ")})` : "Indisponible";
  }
  const amount = price.amount.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return price.kind === "estimate" ? `≈ ${amount} € (estimation)` : `${amount} €`;
}

function renderLicense(license) {
  el.license.innerHTML = "";
  if (!license || Object.keys(license).length === 0) {
    el.license.hidden = true;
    return;
  }
  el.license.hidden = false;
  for (const [code, word] of Object.entries(license)) {
    const item = el_("div", "license-word");
    item.appendChild(el_("b", null, word.hex));
    item.appendChild(document.createTextNode(` — ${word.label} (${code})`));
    el.license.appendChild(item);
  }
}

function renderClosest(closest) {
  el.closest.innerHTML = "";
  if (!closest || closest.length === 0) {
    el.closest.hidden = true;
    return;
  }
  el.closest.hidden = false;
  el.closest.appendChild(el_("div", null, "Configurations les plus proches dans la grille :"));
  const list = document.createElement("ul");
  for (const neighbour of closest) {
    const parts = [];
    if (neighbour.missing.length) parts.push(`manque : ${neighbour.missing.join(", ")}`);
    if (neighbour.extra.length) parts.push(`en trop : ${neighbour.extra.join(", ")}`);
    list.appendChild(
      el_("li", null, `${neighbour.item_number || "?"} (${neighbour.designation || "—"}) — ${parts.join(" / ")}`)
    );
  }
  el.closest.appendChild(list);
}

function showTooltip(text) {
  el.tooltipText.textContent = text;
  el.tooltipLayer.hidden = false;
}

function hideTooltip() {
  el.tooltipLayer.hidden = true;
}

init();
