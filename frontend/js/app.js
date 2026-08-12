const state = {
  families: [],
  currentFamily: null,
  selectedIds: new Set(),
  articlesById: new Map(),
};

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
  familyDesc: document.getElementById("family-desc"),
  productVisual: document.getElementById("product-visual"),
  productVisualImg: document.getElementById("product-visual-img"),
  productVisualBadge: document.getElementById("product-visual-badge"),
  articlePicker: document.getElementById("article-picker"),
  articlePickerSelect: document.getElementById("article-picker-select"),
  groups: document.getElementById("groups"),
  recapEmpty: document.getElementById("recap-empty"),
  recapContent: document.getElementById("recap-content"),
  recapStatusPill: document.getElementById("recap-status-pill"),
  recapStatusText: document.getElementById("recap-status-text"),
  designation: document.getElementById("recap-designation"),
  commercialRef: document.getElementById("recap-commercial-ref"),
  itemNumber: document.getElementById("recap-item-number"),
  price: document.getElementById("recap-price"),
  messages: document.getElementById("recap-messages"),
  license: document.getElementById("recap-license"),
  licenseCard: document.getElementById("recap-license-card"),
  closest: document.getElementById("recap-closest"),
  closestCard: document.getElementById("recap-closest-card"),
  exportButton: document.getElementById("export-button"),
  copyCommercialBtn: document.getElementById("copy-commercial-btn"),
  copyItemBtn: document.getElementById("copy-item-btn"),
  toastContainer: document.getElementById("toast-container"),
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

function showToast(message) {
  if (!el.toastContainer) return;
  const toast = el_("div", "toast", message);
  el.toastContainer.appendChild(toast);
  setTimeout(() => {
    if (toast.parentNode) toast.remove();
  }, 3000);
}

function copyToClipboard(text, label) {
  if (!text || text === "—") return;
  navigator.clipboard.writeText(text).then(() => {
    showToast(`${label} copié dans le presse-papier : ${text}`);
  }).catch(() => {
    showToast(`Erreur lors de la copie`);
  });
}

async function init() {
  el.exportButton?.addEventListener("click", () => window.print());
  el.tooltipClose?.addEventListener("click", hideTooltip);
  el.tooltipLayer?.addEventListener("click", (event) => {
    if (event.target === el.tooltipLayer) hideTooltip();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideTooltip();
  });

  el.copyCommercialBtn?.addEventListener("click", () => {
    copyToClipboard(el.commercialRef.textContent, "Référence commerciale");
  });
  el.copyItemBtn?.addEventListener("click", () => {
    copyToClipboard(el.itemNumber.textContent, "Code article Agile");
  });

  el.articlePickerSelect?.addEventListener("change", onArticlePicked);

  setup3DVisualTilt();

  try {
    state.families = await api.listFamilies();
    renderFamilyPicker();
  } catch (error) {
    if (el.recapEmpty) {
      el.recapEmpty.textContent =
        `Impossible de contacter l'API (${API_BASE || window.location.origin}) : ${error.message}. ` +
        "Vérifiez que le serveur backend est en cours d'exécution.";
    }
  }
}

function setup3DVisualTilt() {
  const card = el.productVisual;
  if (!card) return;

  card.addEventListener("mousemove", (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -10;
    const rotateY = ((x - centerX) / centerX) * 10;

    card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.02, 1.02, 1.02)`;
  });

  card.addEventListener("mouseleave", () => {
    card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)";
  });
}

function renderFamilyPicker() {
  el.familyPicker.innerHTML = "";
  for (const family of state.families) {
    const button = document.createElement("button");
    button.type = "button";

    const title = el_("span", "family-card-title", family.label);
    button.appendChild(title);

    if (family.has_license) {
      const badge = el_("span", "license-badge", "🔑 Licence active");
      button.appendChild(badge);
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

  if (el.familyTitle) el.familyTitle.textContent = state.currentFamily.label;
  if (el.familyDesc) el.familyDesc.textContent = state.currentFamily.description || "Sélectionnez les options ci-dessous pour configurer l'équipement.";
  if (el.recapEmpty) el.recapEmpty.hidden = true;
  el.configurator.hidden = false;

  updateProductVisual(code);
  renderGroups();
  await loadArticlePicker(code);
  await refreshConfiguration();
}

async function loadArticlePicker(code) {
  if (!el.articlePicker || !el.articlePickerSelect) return;

  state.articlesById = new Map();
  el.articlePickerSelect.innerHTML = "";
  el.articlePickerSelect.appendChild(el_("option", null, "— Choisir un code article —")).value = "";

  let articles = [];
  try {
    articles = await api.listFamilyArticles(code);
  } catch (error) {
    el.articlePicker.hidden = true;
    return;
  }

  if (!articles.length) {
    el.articlePicker.hidden = true;
    return;
  }

  for (const article of articles) {
    state.articlesById.set(String(article.id), article);
    const option = el_("option", null, `${article.item_number} — ${article.designation || "sans désignation"}`);
    option.value = String(article.id);
    el.articlePickerSelect.appendChild(option);
  }
  el.articlePicker.hidden = false;
}

function onArticlePicked() {
  const article = state.articlesById.get(el.articlePickerSelect.value);
  if (!article) return;

  for (const input of el.groups.querySelectorAll("input")) {
    input.checked = article.option_ids.includes(Number(input.dataset.optionId));
  }

  onSelectionChange();
}

function updateProductVisual(code) {
  const src = PRODUCT_IMAGES[code];
  if (!src) {
    el.productVisual.hidden = true;
    el.productVisualImg.removeAttribute("src");
    return;
  }
  el.productVisualImg.onload = () => {
    el.productVisual.hidden = false;
    if (el.productVisualBadge) el.productVisualBadge.textContent = `Gamme ${code} — Spécification`;
  };
  el.productVisualImg.onerror = () => { el.productVisual.hidden = true; };
  el.productVisualImg.alt = state.currentFamily ? state.currentFamily.label : code;
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
      const sectionTitle = el_("div", "section-title", sectionKey);
      sectionEl.appendChild(sectionTitle);
      el.groups.appendChild(sectionEl);
    }

    const groupEl = el_("div", "group");

    const groupLabelContainer = el_("div", "group-label");
    const groupName = el_("span", null, group.section ? group.label : "Options disponibles");
    const selectionBadge = el_(
      "span",
      "group-selection-badge",
      group.selection === "single" ? "Choix unique" : "Optionnel"
    );
    groupLabelContainer.appendChild(groupName);
    groupLabelContainer.appendChild(selectionBadge);
    groupEl.appendChild(groupLabelContainer);

    const optionsContainer = el_("div", "options-container");
    for (const option of group.options) {
      optionsContainer.appendChild(renderOption(group, option));
    }
    groupEl.appendChild(optionsContainer);
    sectionEl.appendChild(groupEl);
  }
}

function optionText(option) {
  return option.technical_label
    ? `${option.label} / ${option.technical_label}`
    : option.label;
}

function renderOption(group, option) {
  const row = el_("div", "option-row");

  const input = document.createElement("input");
  input.type = group.selection === "single" ? "radio" : "checkbox";
  input.name = group.selection === "single" ? `group-${group.id}` : `option-${option.id}`;
  input.id = `option-input-${option.id}`;
  input.dataset.optionId = String(option.id);
  input.addEventListener("change", onSelectionChange);

  const label = document.createElement("label");
  label.htmlFor = input.id;

  if (option.technical_label) {
    label.innerHTML = `${option.label} <span class="option-tech-tag">— ${option.technical_label}</span>`;
  } else {
    label.textContent = option.label;
  }

  row.appendChild(input);
  row.appendChild(label);

  if (option.help_text || option.technical_label) {
    const info = el_("button", "info-button", "i");
    info.type = "button";
    info.setAttribute("aria-label", `Détails techniques de ${option.label}`);
    const helpContent = option.help_text || `${option.label} : ${option.technical_label}`;
    info.addEventListener("click", (e) => {
      e.stopPropagation();
      showTooltip(helpContent);
    });
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

  for (const input of el.groups.querySelectorAll("input")) {
    const row = input.closest(".option-row");
    if (row) {
      row.classList.toggle("active-row", input.checked);
    }
  }

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
  el.recapContent.hidden = false;

  el.designation.textContent = result.designation || "—";
  el.commercialRef.textContent = result.commercial_ref || "—";
  el.itemNumber.textContent = result.item_number || "—";
  el.price.textContent = formatPrice(result.price);

  if (el.recapStatusPill && el.recapStatusText) {
    if (result.found) {
      el.recapStatusPill.className = "status-indicator standard";
      el.recapStatusText.textContent = "Article Standard Qualifié";
    } else {
      el.recapStatusPill.className = "status-indicator custom";
      el.recapStatusText.textContent = "Configuration Sur-Mesure";
    }
  }

  el.messages.innerHTML = "";
  for (const warning of result.warnings || []) {
    el.messages.appendChild(el_("div", result.found ? "message message-warning" : "message message-error", warning));
  }

  renderLicense(result.license);
  renderClosest(result.closest);
  buildExportSheet(result);
}

function renderViolations(messages) {
  el.recapContent.hidden = false;

  el.designation.textContent = "—";
  el.commercialRef.textContent = "—";
  el.itemNumber.textContent = "—";
  el.price.textContent = "—";

  if (el.recapStatusPill && el.recapStatusText) {
    el.recapStatusPill.className = "status-indicator custom";
    el.recapStatusText.textContent = "Combinaison Incompatible";
  }

  el.messages.innerHTML = "";
  for (const message of messages) {
    el.messages.appendChild(el_("div", "message message-error", message));
  }
  if (el.licenseCard) el.licenseCard.hidden = true;
  if (el.closestCard) el.closestCard.hidden = true;
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
    if (el.licenseCard) el.licenseCard.hidden = true;
    return;
  }
  if (el.licenseCard) el.licenseCard.hidden = false;

  if (license.kind === "fep") {
    renderFepLicense(license);
    return;
  }
  for (const [code, word] of Object.entries(license)) {
    const item = el_("div", "license-word");
    item.appendChild(el_("span", "license-word-label", `${word.label} (${code})`));
    item.appendChild(el_("b", null, word.hex));
    el.license.appendChild(item);
  }
}

function renderFepLicense(license) {
  const part = el_("div", "license-word");
  part.appendChild(el_("span", "license-word-label", "Dongle FEP"));
  part.appendChild(el_("b", null, license.dongle_part_number));
  el.license.appendChild(part);

  const active = license.functions.filter((f) => f.active);
  const activeWord = el_("div", "license-word");
  activeWord.appendChild(el_("span", "license-word-label", "Fonctions"));
  activeWord.appendChild(el_("b", null, active.length ? active.map((f) => f.label).join(", ") : "Aucune"));
  el.license.appendChild(activeWord);

  const counters = license.counters.filter((c) => c.count > 0);
  if (counters.length) {
    const countWord = el_("div", "license-word");
    countWord.appendChild(el_("span", "license-word-label", "Compteurs"));
    countWord.appendChild(el_("b", null, counters.map((c) => `${c.code}=${c.hex}`).join(", ")));
    el.license.appendChild(countWord);
  }
}

function renderClosest(closest) {
  el.closest.innerHTML = "";
  if (!closest || closest.length === 0) {
    if (el.closestCard) el.closestCard.hidden = true;
    return;
  }
  if (el.closestCard) el.closestCard.hidden = false;

  for (const neighbour of closest) {
    const item = el_("div", "closest-article-item");

    const header = el_("div", "closest-article-header");
    header.appendChild(el_("span", "closest-item-number", neighbour.item_number || "Article standard"));
    if (neighbour.designation) {
      header.appendChild(el_("span", "closest-designation", neighbour.designation));
    }
    item.appendChild(header);

    const diffContainer = el_("div", "closest-diff-tags");
    for (const m of neighbour.missing || []) {
      diffContainer.appendChild(el_("span", "diff-tag-missing", `+ ${m}`));
    }
    for (const x of neighbour.extra || []) {
      diffContainer.appendChild(el_("span", "diff-tag-extra", `- ${x}`));
    }
    item.appendChild(diffContainer);

    el.closest.appendChild(item);
  }
}

function buildExportSheet(result) {
  if (!el.exportDate) return;
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

function buildExportConfigTable() {
  if (!el.exportConfigTable || !state.currentFamily) return;
  el.exportConfigTable.innerHTML = "";

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
      td.appendChild(el_("div", null, optionText(option)));
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
  if (!el.exportLicense) return;
  el.exportLicense.innerHTML = "";
  if (!license || Object.keys(license).length === 0) {
    if (el.exportLicenseBlock) el.exportLicenseBlock.hidden = true;
    return;
  }
  if (el.exportLicenseBlock) el.exportLicenseBlock.hidden = false;

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
  if (!el.tooltipLayer) return;
  el.tooltipText.textContent = text;
  el.tooltipLayer.hidden = false;
}

function hideTooltip() {
  if (!el.tooltipLayer) return;
  el.tooltipLayer.hidden = true;
}

init();
