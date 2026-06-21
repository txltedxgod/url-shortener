"use strict";

const API = {
  shorten: "/api/shorten",
  links: "/api/links",
  link: (code) => `/api/links/${encodeURIComponent(code)}`,
  analytics: (code) => `/api/links/${encodeURIComponent(code)}/analytics`,
  deactivate: (code) => `/api/links/${encodeURIComponent(code)}/deactivate`,
  activate: (code) => `/api/links/${encodeURIComponent(code)}/activate`,
  qr: (code) => `/api/links/${encodeURIComponent(code)}/qr`,
};

const charts = {};
let activeCode = null;

// ---------- Theme ----------
const themeToggle = document.getElementById("theme-toggle");
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  themeToggle.querySelector(".theme-icon").textContent = theme === "dark" ? "\uD83C\uDF19" : "\u2600\uFE0F";
}
themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme");
  applyTheme(current === "dark" ? "light" : "dark");
  if (activeCode) loadAnalytics(activeCode); // re-render charts with new palette
});
applyTheme(localStorage.getItem("theme") || "dark");

// ---------- Helpers ----------
function toast(message, kind = "") {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = `toast ${kind}`;
  setTimeout(() => el.classList.add("hidden"), 2600);
}

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { const body = await res.json(); detail = body.detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function statusBadge(link) {
  if (!link.is_active) return '<span class="badge inactive">inactive</span>';
  if (link.expires_at && new Date(link.expires_at) <= new Date())
    return '<span class="badge expired">expired</span>';
  return '<span class="badge active">active</span>';
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function palette(n) {
  const base = ["#5b8cff", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#22d3ee", "#fb7185", "#4ade80", "#facc15", "#60a5fa"];
  return Array.from({ length: n }, (_, i) => base[i % base.length]);
}

// ---------- Create ----------
document.getElementById("shorten-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = document.getElementById("url").value.trim();
  const alias = document.getElementById("alias").value.trim();
  const ttl = document.getElementById("ttl").value;

  const payload = { url };
  if (alias) payload.alias = alias;
  if (ttl) payload.ttl_seconds = Number(ttl);

  try {
    const link = await api(API.shorten, { method: "POST", body: JSON.stringify(payload) });
    showCreateResult(link);
    document.getElementById("shorten-form").reset();
    toast("Short link created", "success");
    loadLinks();
  } catch (err) {
    toast(err.message, "error");
  }
});

function showCreateResult(link) {
  const box = document.getElementById("create-result");
  box.innerHTML = `
    <img src="${API.qr(link.code)}" alt="QR code" />
    <div class="grow">
      <div class="short-link">${link.short_url}</div>
      <div class="muted" style="margin-top:6px">→ ${escapeHtml(link.original_url)}</div>
    </div>
    <button class="btn ghost tiny" data-copy="${link.short_url}">Copy</button>`;
  box.classList.remove("hidden");
  box.querySelector("[data-copy]").addEventListener("click", (e) => copy(e.target.dataset.copy));
}

function copy(text) {
  navigator.clipboard.writeText(text).then(() => toast("Copied to clipboard", "success"));
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------- List ----------
async function loadLinks() {
  const body = document.getElementById("links-body");
  try {
    const data = await api(`${API.links}?limit=100&offset=0`);
    if (!data.items.length) {
      body.innerHTML = '<tr><td colspan="6" class="empty">No links yet — create your first one above.</td></tr>';
      return;
    }
    body.innerHTML = data.items.map(rowHtml).join("");
    bindRowActions();
  } catch (err) {
    body.innerHTML = `<tr><td colspan="6" class="empty">${escapeHtml(err.message)}</td></tr>`;
  }
}

function rowHtml(link) {
  return `
    <tr data-code="${link.code}">
      <td><a href="${link.short_url}" target="_blank" rel="noopener" class="mono">/${link.code}</a></td>
      <td class="dest" title="${escapeHtml(link.original_url)}">${escapeHtml(link.original_url)}</td>
      <td>${link.click_count}</td>
      <td>${statusBadge(link)}</td>
      <td>${fmtDate(link.created_at)}</td>
      <td>
        <div class="row-actions">
          <button class="btn ghost tiny" data-action="stats">Stats</button>
          <button class="btn ghost tiny" data-action="copy">Copy</button>
          <button class="btn ghost tiny" data-action="toggle">${link.is_active ? "Disable" : "Enable"}</button>
          <button class="btn ghost tiny danger" data-action="delete">Delete</button>
        </div>
      </td>
    </tr>`;
}

function bindRowActions() {
  document.querySelectorAll("#links-body tr").forEach((tr) => {
    const code = tr.dataset.code;
    const link = tr.querySelector('a').getAttribute('href');
    tr.querySelector('[data-action="stats"]').addEventListener("click", () => openAnalytics(code));
    tr.querySelector('[data-action="copy"]').addEventListener("click", () => copy(link));
    tr.querySelector('[data-action="toggle"]').addEventListener("click", () => toggleLink(code, tr));
    tr.querySelector('[data-action="delete"]').addEventListener("click", () => deleteLink(code));
  });
}

async function toggleLink(code, tr) {
  const isEnabling = tr.querySelector('[data-action="toggle"]').textContent === "Enable";
  try {
    await api(isEnabling ? API.activate(code) : API.deactivate(code), { method: "PATCH" });
    toast(isEnabling ? "Link enabled" : "Link disabled", "success");
    loadLinks();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function deleteLink(code) {
  if (!confirm(`Delete /${code}? This cannot be undone.`)) return;
  try {
    await api(API.link(code), { method: "DELETE" });
    toast("Link deleted", "success");
    if (activeCode === code) closeAnalytics();
    loadLinks();
  } catch (err) {
    toast(err.message, "error");
  }
}

// ---------- Analytics ----------
async function openAnalytics(code) {
  activeCode = code;
  document.getElementById("analytics").classList.remove("hidden");
  document.getElementById("analytics-code").textContent = `/${code}`;
  document.getElementById("analytics").scrollIntoView({ behavior: "smooth" });
  await loadAnalytics(code);
}

function closeAnalytics() {
  activeCode = null;
  document.getElementById("analytics").classList.add("hidden");
}
document.getElementById("close-analytics").addEventListener("click", closeAnalytics);

async function loadAnalytics(code) {
  try {
    const data = await api(API.analytics(code));
    document.getElementById("stat-total").textContent = data.total_clicks;
    document.getElementById("stat-unique").textContent = data.unique_visitors;

    const tick = cssVar("--text-muted");
    const grid = cssVar("--border");
    Chart.defaults.color = tick;
    Chart.defaults.borderColor = grid;

    renderLine("chart-timeseries", data.timeseries.map((p) => p.bucket), data.timeseries.map((p) => p.clicks));
    renderBar("chart-referrers", data.top_referrers);
    renderDoughnut("chart-devices", data.devices);
    renderBar("chart-countries", data.countries);
    renderDoughnut("chart-browsers", data.browsers);
  } catch (err) {
    toast(err.message, "error");
  }
}

function destroy(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function renderLine(id, labels, values) {
  destroy(id);
  const ctx = document.getElementById(id);
  charts[id] = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{ label: "Clicks", data: values, borderColor: "#5b8cff", backgroundColor: "rgba(91,140,255,0.15)", fill: true, tension: 0.35, pointRadius: 3 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}

function renderBar(id, items) {
  destroy(id);
  const ctx = document.getElementById(id);
  charts[id] = new Chart(ctx, {
    type: "bar",
    data: { labels: items.map((i) => i.label), datasets: [{ data: items.map((i) => i.count), backgroundColor: palette(items.length), borderRadius: 6 }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}

function renderDoughnut(id, items) {
  destroy(id);
  const ctx = document.getElementById(id);
  charts[id] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: items.map((i) => i.label), datasets: [{ data: items.map((i) => i.count), backgroundColor: palette(items.length), borderWidth: 0 }] },
    options: { responsive: true, plugins: { legend: { position: "bottom", labels: { boxWidth: 12, padding: 12 } } }, cutout: "60%" },
  });
}

// ---------- Init ----------
document.getElementById("refresh").addEventListener("click", loadLinks);
loadLinks();
