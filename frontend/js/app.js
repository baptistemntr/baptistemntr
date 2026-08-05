const state = {
  families: [],
  currentFamily: null, // détail complet (avec groups) de la gamme sélectionnée
  selectedIds: new Set(),
};

// Visuel produit dans l'en-tête du configurateur (frontend/img/products/) : seules ces
// gammes ont une illustration pour l'instant, les autres masquent simplement le cadre
// (voir updateProductVisual).
const PRODUCT_IMAGES = {
  CRT: "img/products/crt.webp",
  DTR: "img/products/dtr.webp",
  HDR: "img/products/hdr.webp",
  SATCORE: "img/products/satcore.webp",
  RTR: "img/products/rtr.webp",
  BSS: "img/products/bss.webp",
  "RSR-RF": "img/products/rsr-rf.webp",
};

const el = {
  familyPicker: document.getElementById("family-picker"),
  configurator: document.getElementById("configurator"),
  familyTitle: document.getElementById("family-title"),
  productVisual: document.getElementById("product-visual"),
  productVisualImg: document.getElementById("product-visual-img"),
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
  exportDate: document.getElementById("export-date"),
  exportFamily: document.getElementById("export-family"),
  exportDesignation: document.getElementById("export-designation"),
  exportCommercialRef: document.getElementById("export-commercial-ref"),
  exportItemNumber: document.getElementById("export-item-number"),
  exportPrice: document.getElementById("export-price"),
  exportMessages: document.getElementById("export-messages"),
  exportConfigTable: document.getElementById("export-config-table"),
  exportLicenseBlock: document.getElementById("export-license-block"),
  exportLicense: document.getElementById("export-license"),
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
      `Impossible de contacter l'API (${API_BASE || window.location.origin}) : ${error.message}. ` +
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

  try {
    state.currentFamily = await api.getFamily(code);
  } catch (error) {
    renderViolations(error.messages || [error.message]);
    return;
  }
  state.selectedIds = new Set();

  el.familyTitle.textContent = state.currentFamily.label;
  el.configurator.hidden = false;
  updateProductVisual(code);
  renderGroups();
  await refreshConfiguration();
}

// Cadre masqué par défaut (index.html) : on ne le montre qu'une fois l'image chargée avec
// succès, jamais entre-temps ni en cas d'échec — même logique que le logo Safran (onerror),
// pour ne jamais laisser une icône d'image cassée à l'écran devant un client.
function updateProductVisual(code) {
  const src = PRODUCT_IMAGES[code];
  if (!src) {
    el.productVisual.hidden = true;
    el.productVisualImg.removeAttribute("src");
    return;
  }
  el.productVisualImg.onload = () => { el.productVisual.hidden = false; };
  el.productVisualImg.onerror = () => { el.productVisual.hidden = true; };
  el.productVisualImg.alt = state.currentFamily.label;
  el.productVisualImg.src = src;
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
  buildExportSheet(result);
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
  if (license.kind === "fep") {
    renderFepLicense(license);
    return;
  }
  for (const [code, word] of Object.entries(license)) {
    const item = el_("div", "license-word");
    item.appendChild(el_("b", null, word.hex));
    item.appendChild(document.createTextNode(` — ${word.label} (${code})`));
    el.license.appendChild(item);
  }
}

// CRT (dongle FEP) : pas un mot en somme pondérée comme HDR, mais une table de fonctions
// actives et de compteurs matériels — reflet direct de la section « 9 - Dongle FEP » du
// classeur, à charge pour l'IMI de la reporter dans l'outil de programmation du dongle.
function renderFepLicense(license) {
  const part = el_("div", "license-word");
  part.appendChild(document.createTextNode("Dongle FEP : "));
  part.appendChild(el_("b", null, license.dongle_part_number));
  el.license.appendChild(part);

  const active = license.functions.filter((f) => f.active);
  el.license.appendChild(el_(
    "div", "license-word",
    active.length
      ? `Fonctions actives : ${active.map((f) => f.label).join(", ")}`
      : "Aucune fonction active"
  ));

  const counters = license.counters.filter((c) => c.count > 0);
  if (counters.length) {
    el.license.appendChild(el_(
      "div", "license-word",
      `Compteurs : ${counters.map((c) => `${c.code}=${c.hex}`).join(", ")}`
    ));
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

// --- Fiche imprimable (export PDF via Ctrl+P) --------------------------------------------
//
// Reconstruite à chaque configuration valide (appelée depuis renderResult), pas seulement
// au clic sur « Exporter » : la fiche est toujours à jour quand l'impression système
// s'ouvre, sans dépendre d'un second calcul juste avant impression.

function buildExportSheet(result) {
  el.exportDate.textContent = new Date().toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
  el.exportFamily.textContent = state.currentFamily ? state.currentFamily.label : "";

  el.exportDesignation.textContent = result.designation || "—";
  el.exportCommercialRef.textContent = result.commercial_ref || "—";
  el.exportItemNumber.textContent = result.item_number || "—";
  el.exportPrice.textContent = formatPrice(result.price);

  el.exportMessages.innerHTML = "";
  for (const warning of result.warnings || []) {
    el.exportMessages.appendChild(
      el_("div", result.found ? "message message-warning" : "message message-error", warning)
    );
  }

  buildExportConfigTable();
  buildExportLicense(result.license);
}

// Une ligne par groupe où au moins une option est cochée (les groupes vides — « None »,
// options commerciales non cochées — n'ont rien à montrer sur une fiche de commande) ;
// une ligne d'en-tête par section, pour retrouver le découpage vu à l'écran.
function buildExportConfigTable() {
  el.exportConfigTable.innerHTML = "";
  if (!state.currentFamily) return;

  let currentSection = null;
  for (const group of state.currentFamily.groups) {
    const selected = group.options.filter((o) => state.selectedIds.has(o.id));
    if (!selected.length) continue;

    const sectionKey = group.section || group.label;
    if (sectionKey !== currentSection) {
      currentSection = sectionKey;
      const sectionRow = el_("tr", "export-section-row");
      const sectionTh = el_("th", null, sectionKey);
      sectionTh.colSpan = 2;
      sectionRow.appendChild(sectionTh);
      el.exportConfigTable.appendChild(sectionRow);
    }

    const row = document.createElement("tr");
    row.appendChild(el_("th", null, group.section ? group.label : ""));
    const td = document.createElement("td");
    for (const option of selected) {
      const line = document.createElement("div");
      line.textContent = option.label;
      if (option.technical_label) {
        line.appendChild(el_("span", "export-option-technical", option.technical_label));
      }
      td.appendChild(line);
    }
    row.appendChild(td);
    el.exportConfigTable.appendChild(row);
  }

  if (!el.exportConfigTable.children.length) {
    const row = document.createElement("tr");
    const td = el_("td", null, "Aucune option sélectionnée.");
    td.colSpan = 2;
    row.appendChild(td);
    el.exportConfigTable.appendChild(row);
  }
}

function buildExportLicense(license) {
  el.exportLicense.innerHTML = "";
  if (!license || Object.keys(license).length === 0) {
    el.exportLicenseBlock.hidden = true;
    return;
  }
  el.exportLicenseBlock.hidden = false;

  if (license.kind === "fep") {
    buildExportFepLicense(license);
    return;
  }

  const table = el_("table", "export-license-table");
  const head = document.createElement("tr");
  head.appendChild(el_("th", null, "Mot"));
  head.appendChild(el_("th", null, "Valeur"));
  table.appendChild(head);
  for (const [code, word] of Object.entries(license)) {
    const row = document.createElement("tr");
    row.appendChild(el_("th", null, `${word.label} (${code})`));
    row.appendChild(el_("td", "export-hex", word.hex));
    table.appendChild(row);
  }
  el.exportLicense.appendChild(table);
}

// CRT (dongle FEP) : même table que le récapitulatif à l'écran (renderFepLicense), mise en
// forme pour l'impression plutôt que reconstruite depuis zéro.
function buildExportFepLicense(license) {
  const table = el_("table", "export-license-table");

  let row = document.createElement("tr");
  row.appendChild(el_("th", null, "Dongle FEP"));
  row.appendChild(el_("td", "export-hex", license.dongle_part_number));
  table.appendChild(row);

  const active = license.functions.filter((f) => f.active);
  row = document.createElement("tr");
  row.appendChild(el_("th", null, "Fonctions actives"));
  row.appendChild(el_("td", null, active.length ? active.map((f) => f.label).join(", ") : "Aucune"));
  table.appendChild(row);

  const counters = license.counters.filter((c) => c.count > 0);
  if (counters.length) {
    row = document.createElement("tr");
    row.appendChild(el_("th", null, "Compteurs"));
    row.appendChild(el_("td", "export-hex", counters.map((c) => `${c.code}=${c.hex}`).join(", ")));
    table.appendChild(row);
  }

  el.exportLicense.appendChild(table);
}

function showTooltip(text) {
  el.tooltipText.textContent = text;
  el.tooltipLayer.hidden = false;
}

function hideTooltip() {
  el.tooltipLayer.hidden = true;
}

init();
