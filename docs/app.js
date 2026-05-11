/* ── Configuración ─────────────────────────────────────────────────────────── */

// En GitHub Pages, los datos están en ../data/bills/
// Si corres local, podés cambiar esto a una ruta relativa
const DATA_BASE = "../data/bills";

const INTENTION_CONFIG = {
  favor:      { icon: "✅", label: "A favor",    cls: "favor" },
  contra:     { icon: "❌", label: "En contra",  cls: "contra" },
  abstencion: { icon: "⚠️", label: "Abstención", cls: "abstencion" },
  sin_info:   { icon: "❓", label: "Sin info",   cls: "sin_info" },
};

/* ── Estado ────────────────────────────────────────────────────────────────── */
let bills = [];
let currentBill = null;
let currentData = null;
let currentFilter = "all";
let currentSort = { col: "apellido", dir: 1 };

/* ── Bootstrap ─────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", async () => {
  await loadBillsList();
  setupFilters();
});

async function loadBillsList() {
  try {
    const resp = await fetch(`${DATA_BASE}/../bills.yaml`);
    if (!resp.ok) throw new Error("bills.yaml no encontrado");
    const text = await resp.text();
    bills = parseYamlBills(text).filter(b => b.active !== false);
  } catch {
    bills = await discoverBillsFromDirs();
  }

  renderTabs();
  if (bills.length > 0) {
    selectBill(bills[0]);
  } else {
    document.getElementById("no-bills").style.display = "block";
  }
}

// Parseo manual de YAML simple (sin librería externa)
function parseYamlBills(yaml) {
  const result = [];
  const billBlocks = yaml.split(/^  - /m).slice(1);
  for (const block of billBlocks) {
    const lines = block.split("\n");
    const bill = {};
    for (const line of lines) {
      const m = line.match(/^\s{0,4}(\w[\w_]*):\s*(.+)/);
      if (m) bill[m[1]] = m[2].replace(/^["']|["']$/g, "").trim();
    }
    if (bill.slug) result.push(bill);
  }
  return result;
}

// Fallback: intentar cargar bills conocidos leyendo latest.json
async function discoverBillsFromDirs() {
  return [];
}

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
function renderTabs() {
  const nav = document.getElementById("bill-tabs");
  nav.innerHTML = "";
  if (bills.length === 0) {
    nav.innerHTML = '<span class="tabs-loading">Sin proyectos activos</span>';
    return;
  }
  for (const bill of bills) {
    const btn = document.createElement("button");
    btn.className = "tab-btn";
    btn.textContent = bill.name;
    btn.dataset.slug = bill.slug;
    btn.addEventListener("click", () => selectBill(bill));
    nav.appendChild(btn);
  }
}

async function selectBill(bill) {
  currentBill = bill;

  // Marcar tab activo
  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.slug === bill.slug);
  });

  // Cargar datos
  try {
    const resp = await fetch(`${DATA_BASE}/${bill.slug}/latest.json`);
    if (!resp.ok) throw new Error("Sin datos aún");
    currentData = await resp.json();
  } catch {
    currentData = null;
  }

  renderBill();
}

/* ── Render ────────────────────────────────────────────────────────────────── */
function renderBill() {
  const header = document.getElementById("bill-header");
  const table  = document.getElementById("deputies-table");
  const noBills = document.getElementById("no-bills");

  noBills.style.display = "none";

  if (!currentData) {
    header.style.display = "none";
    table.style.display  = "none";
    noBills.style.display = "block";
    noBills.querySelector("p").textContent =
      "Aún no hay datos para este proyecto. El bot los cargará en el próximo ciclo.";
    return;
  }

  header.style.display = "block";
  table.style.display  = "table";

  // Meta
  document.getElementById("bill-title").textContent = currentData.bill_name;

  const updated = currentData.last_updated
    ? `Actualizado: ${formatDatetime(currentData.last_updated)}`
    : "";
  document.getElementById("last-updated").textContent = updated;

  // Summary
  const s = currentData.summary || {};
  document.getElementById("count-favor").textContent     = s.favor || 0;
  document.getElementById("count-contra").textContent    = s.contra || 0;
  document.getElementById("count-abstencion").textContent = s.abstencion || 0;
  document.getElementById("count-sin-info").textContent  = s.sin_info || 0;

  renderTable();
}

function renderTable() {
  if (!currentData) return;

  let deputies = [...currentData.deputies];

  // Filtrar por intención
  if (currentFilter !== "all") {
    deputies = deputies.filter(d => d.intention === currentFilter);
  }

  // Filtrar por búsqueda
  const q = document.getElementById("search-input").value.toLowerCase();
  if (q) {
    deputies = deputies.filter(d =>
      `${d.apellido} ${d.nombre} ${d.bloque}`.toLowerCase().includes(q)
    );
  }

  // Ordenar
  deputies.sort((a, b) => {
    const va = (a[currentSort.col] || "").toString().toLowerCase();
    const vb = (b[currentSort.col] || "").toString().toLowerCase();
    return va < vb ? -currentSort.dir : va > vb ? currentSort.dir : 0;
  });

  const tbody = document.getElementById("deputies-tbody");
  tbody.innerHTML = "";

  for (const d of deputies) {
    const cfg = INTENTION_CONFIG[d.intention] || INTENTION_CONFIG.sin_info;
    const conf = Math.round((d.confidence || 0) * 100);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${d.apellido}</strong>, ${d.nombre}</td>
      <td><span class="bloque-tag">${d.bloque}</span></td>
      <td>
        <span class="badge ${cfg.cls}">${cfg.icon} ${cfg.label}</span>
      </td>
      <td>
        <div class="confidence-wrap">
          <div class="confidence-bar">
            <div class="confidence-fill" style="width:${conf}%"></div>
          </div>
          <span class="confidence-pct">${conf}%</span>
        </div>
      </td>
      <td class="reasoning-cell">
        ${d.quote ? `<div class="quote-text">"${escHtml(d.quote)}"</div>` : ""}
        <div>${escHtml(d.reasoning || "")}</div>
      </td>
      <td class="sources-cell">${_renderSources(d.sources)}</td>
    `;
    tbody.appendChild(tr);
  }

  if (deputies.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="6" style="text-align:center;color:#9ca3af;padding:24px">Sin resultados para este filtro.</td>`;
    tbody.appendChild(tr);
  }
}

/* ── Filtros y búsqueda ────────────────────────────────────────────────────── */
function setupFilters() {
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      renderTable();
    });
  });

  document.getElementById("search-input").addEventListener("input", renderTable);

  document.querySelectorAll("th.sortable").forEach(th => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      if (currentSort.col === col) {
        currentSort.dir *= -1;
      } else {
        currentSort = { col, dir: 1 };
      }
      renderTable();
    });
  });
}

/* ── Helpers ───────────────────────────────────────────────────────────────── */
function _renderSources(sources) {
  if (!sources || sources.length === 0) return "<span style='color:#9ca3af'>—</span>";
  return sources.map(s => {
    const label = escHtml(s.source || s.title || "Ver nota");
    const title = escHtml(s.title || "");
    const url   = s.url || "#";
    return `<a class="source-link" href="${url}" target="_blank" rel="noopener" title="${title}">${label}</a>`;
  }).join("");
}

function formatDatetime(iso) {
  if (!iso) return "";
  const dt = new Date(iso);
  return dt.toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
