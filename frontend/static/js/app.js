/**
 * MarketLens — Frontend Application
 * Handles tab navigation, API calls, and Chart.js visualisations.
 *
 * All data is fetched from the FastAPI backend.
 * No mock data is ever displayed — the app shows a clear empty state
 * until the data pipeline has been run.
 */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────
const API = "";   // Same-origin — FastAPI serves the frontend

const COLORS = {
  blue:   "#3b82f6",  teal:   "#14b8a6",
  green:  "#22c55e",  red:    "#ef4444",
  amber:  "#f59e0b",  purple: "#a855f7",
  sectors: [
    "#3b82f6","#14b8a6","#22c55e","#f59e0b",
    "#a855f7","#ef4444","#f97316","#06b6d4",
  ],
};

// Global chart instances (to allow clean destroy/re-draw)
const charts = {};
let assetData     = [];   // All assets metadata
let marketOverview = {};  // Cached overview response

// ══════════════════════════════════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════════════════════════════════

function switchTab(tab) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
  document.getElementById(`page-${tab}`).classList.add("active");
  document.getElementById(`tab-${tab}`).classList.add("active");

  // Lazy-load page data on first visit
  if (tab === "asset"     && !document.getElementById("asset-ticker-select").options.length > 1) populateAssetSelects();
  if (tab === "portfolio" && document.getElementById("weight-rows").children.length === 0)        initPortfolioBuilder();
  if (tab === "forecast"  && !document.getElementById("forecast-ticker").options.length > 1)      populateForecastSelect();
  if (tab === "regime"    && !document.getElementById("regime-ticker").options.length > 1)        populateRegimeSelect();
}

function toggleAIPanel() {
  document.getElementById("ai-panel").classList.toggle("open");
}

// ══════════════════════════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════════════════════════

async function apiFetch(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

function fmt(v, decimals = 2, suffix = "") {
  if (v == null || isNaN(v)) return "—";
  return Number(v).toFixed(decimals) + suffix;
}

function fmtPct(v, decimals = 2) {
  if (v == null || isNaN(v)) return "—";
  const pct = Number(v);
  return (pct >= 0 ? "+" : "") + pct.toFixed(decimals) + "%";
}

function colorClass(v) {
  if (v == null) return "";
  return Number(v) >= 0 ? "positive" : "negative";
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function chartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { labels: { color: "#8fa3c0", font: { size: 11 } } },
      tooltip: {
        backgroundColor: "#141d35",
        borderColor: "rgba(59,130,246,0.3)",
        borderWidth: 1,
        titleColor: "#f0f6ff",
        bodyColor: "#8fa3c0",
      },
    },
    scales: {
      x: {
        grid:  { color: "rgba(255,255,255,0.04)" },
        ticks: { color: "#4d6080", maxTicksLimit: 8, font: { size: 10 } },
      },
      y: {
        grid:  { color: "rgba(255,255,255,0.04)" },
        ticks: { color: "#4d6080", font: { size: 10 } },
      },
    },
  };
}

// ══════════════════════════════════════════════════════════════════════════
// INITIALISATION
// ══════════════════════════════════════════════════════════════════════════

async function init() {
  try {
    // Load asset list first
    const assetResp = await apiFetch("/api/market/assets");
    assetData = assetResp.assets;

    // Load market overview
    await loadMarketOverview();

    document.getElementById("loading-overlay").classList.add("hidden");
  } catch (err) {
    document.getElementById("loading-overlay").innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠</div>
        <p style="color:#ef4444;font-weight:600">Cannot connect to MarketLens API</p>
        <p style="color:#8fa3c0;margin-top:8px;font-size:0.8rem">
          Make sure the FastAPI backend is running:<br>
          <code style="color:#3b82f6">uvicorn backend.main:app --reload</code>
        </p>
        <p style="color:#4d6080;margin-top:8px;font-size:0.75rem">
          Also ensure the data pipeline has been run:<br>
          <code style="color:#14b8a6">python -m pipeline.run_pipeline</code>
        </p>
      </div>
    `;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE 1: MARKET OVERVIEW
// ══════════════════════════════════════════════════════════════════════════

async function loadMarketOverview() {
  const data = await apiFetch("/api/market/overview");
  marketOverview = data;

  // KPI cards
  const all = data.all_assets;
  const avgReturn = all.reduce((s, a) => s + (a.ann_return_pct || 0), 0) / all.length;
  const avgVol    = all.reduce((s, a) => s + (a.ann_vol_pct || 0), 0) / all.length;
  const avgSharpe = all.reduce((s, a) => s + (a.sharpe || 0), 0) / all.length;

  document.getElementById("kpi-overview").innerHTML = `
    ${kpiCard("Total Assets Tracked", all.length, "", "blue")}
    ${kpiCard("Avg Ann. Return", fmtPct(avgReturn), "Cross-asset average", avgReturn >= 0 ? "green" : "red")}
    ${kpiCard("Avg Volatility", fmt(avgVol) + "%", "Annualised 20-day", "amber")}
    ${kpiCard("Avg Sharpe Ratio", fmt(avgSharpe), "Historical, rf=5%", avgSharpe >= 1 ? "green" : "blue")}
    ${kpiCard("Sectors Covered", data.sector_breakdown.length, "Diversified universe", "teal")}
    ${kpiCard("Data Source", "Yahoo Finance", "yfinance · Adjusted Close", "purple")}
  `;

  // Performers
  renderPerformers("top-performers",   data.top_performers,   true);
  renderPerformers("worst-performers", data.worst_performers, false);

  // Asset table
  renderAssetTable(data.all_assets);

  // Sector bar chart
  renderSectorChart(data.sector_breakdown);

  // Scatter: vol vs return
  renderScatterChart(data.all_assets);
}

function kpiCard(label, value, sub, color = "blue") {
  return `
    <div class="kpi-card ${color}">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      ${sub ? `<div class="kpi-sub">${sub}</div>` : ""}
    </div>
  `;
}

function renderPerformers(containerId, items, positive) {
  const container = document.getElementById(containerId);
  container.innerHTML = items.map((a, i) => `
    <div class="performer-row">
      <span class="performer-rank">#${i + 1}</span>
      <div class="performer-info">
        <div class="performer-ticker">${a.ticker}</div>
        <div class="performer-name">${(a.company || "").substring(0, 25)}</div>
        <div class="performer-sector">${a.sector}</div>
      </div>
      <div class="performer-value ${positive ? "positive" : "negative"}">
        ${fmtPct(a.ann_return_pct)}
        <div style="font-size:0.68rem;color:#4d6080">Sharpe: ${fmt(a.sharpe)}</div>
      </div>
    </div>
  `).join("");
}

function renderAssetTable(assets) {
  window._allAssets = assets;
  document.getElementById("asset-tbody").innerHTML = assets.map(a => `
    <tr>
      <td style="font-weight:700;color:#3b82f6">${a.ticker}</td>
      <td style="font-family:var(--font-sans);color:#f0f6ff">${a.company}</td>
      <td style="color:#8fa3c0">${a.sector}</td>
      <td class="${colorClass(a.ann_return_pct)}">${fmtPct(a.ann_return_pct)}</td>
      <td>${fmt(a.ann_vol_pct)}%</td>
      <td class="${(a.sharpe || 0) >= 1 ? "positive" : ""}">${fmt(a.sharpe)}</td>
      <td class="negative">${fmtPct(a.max_drawdown_pct)}</td>
      <td style="color:#4d6080">${fmtVolume(a.avg_daily_volume)}</td>
    </tr>
  `).join("");
}

function filterTable() {
  const q = document.getElementById("asset-search").value.toLowerCase();
  const all = window._allAssets || [];
  renderAssetTable(all.filter(a =>
    a.ticker.toLowerCase().includes(q) ||
    (a.company || "").toLowerCase().includes(q) ||
    (a.sector  || "").toLowerCase().includes(q)
  ));
}

function fmtVolume(v) {
  if (!v) return "—";
  if (v >= 1e9) return (v / 1e9).toFixed(1) + "B";
  if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
  return v.toLocaleString();
}

function renderSectorChart(sectors) {
  destroyChart("chart-sector");
  const ctx = document.getElementById("chart-sector").getContext("2d");
  charts["chart-sector"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: sectors.map(s => s.sector),
      datasets: [{
        label: "Avg Ann. Return %",
        data:  sectors.map(s => s.avg_return_pct),
        backgroundColor: sectors.map((_, i) => COLORS.sectors[i % COLORS.sectors.length] + "99"),
        borderColor:     sectors.map((_, i) => COLORS.sectors[i % COLORS.sectors.length]),
        borderWidth: 1, borderRadius: 4,
      }],
    },
    options: {
      ...chartDefaults(),
      indexAxis: "y",
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
    },
  });
}

function renderScatterChart(assets) {
  destroyChart("chart-scatter");
  const ctx = document.getElementById("chart-scatter").getContext("2d");
  charts["chart-scatter"] = new Chart(ctx, {
    type: "scatter",
    data: {
      datasets: [{
        label: "Assets",
        data: assets.map(a => ({ x: a.ann_vol_pct, y: a.ann_return_pct, label: a.ticker })),
        backgroundColor: assets.map(a => a.ann_return_pct >= 0 ? COLORS.green + "99" : COLORS.red + "99"),
        borderColor:     assets.map(a => a.ann_return_pct >= 0 ? COLORS.green : COLORS.red),
        pointRadius: 6, pointHoverRadius: 8,
      }],
    },
    options: {
      ...chartDefaults(),
      plugins: {
        ...chartDefaults().plugins,
        tooltip: {
          ...chartDefaults().plugins.tooltip,
          callbacks: {
            label: ctx => {
              const d = ctx.raw;
              return `${d.label}: Vol ${fmt(d.x)}%, Ret ${fmtPct(d.y)}`;
            },
          },
        },
      },
      scales: {
        x: { ...chartDefaults().scales.x, title: { display: true, text: "Volatility (%)", color: "#4d6080" } },
        y: { ...chartDefaults().scales.y, title: { display: true, text: "Ann. Return (%)", color: "#4d6080" } },
      },
    },
  });
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE 2: ASSET ANALYSIS
// ══════════════════════════════════════════════════════════════════════════

function populateAssetSelects() {
  const sel = document.getElementById("asset-ticker-select");
  sel.innerHTML = `<option value="">— Select Asset —</option>` +
    assetData.map(a => `<option value="${a.ticker}">${a.ticker} — ${a.company}</option>`).join("");
}

async function loadAssetData() {
  const ticker = document.getElementById("asset-ticker-select").value;
  const days   = document.getElementById("asset-days-select").value;
  if (!ticker) return;

  try {
    const [priceData, monthlyData] = await Promise.all([
      apiFetch(`/api/market/prices/${ticker}?days=${days}`),
      apiFetch(`/api/market/monthly-returns/${ticker}`),
    ]);

    const d = priceData.data;
    const stat = marketOverview.all_assets?.find(a => a.ticker === ticker) || {};

    // KPIs
    const latestPrice = d[d.length - 1]?.adj_close || 0;
    const cumRet      = d[d.length - 1]?.cumulative_return_pct || 0;
    document.getElementById("kpi-asset").innerHTML = `
      ${kpiCard("Latest Price", "$" + fmt(latestPrice), priceData.company, "blue")}
      ${kpiCard("Period Return", fmtPct(cumRet), `Last ${days} trading days`, cumRet >= 0 ? "green" : "red")}
      ${kpiCard("Ann. Volatility", fmt(stat.ann_vol_pct) + "%", "Historical 20-day", "amber")}
      ${kpiCard("Sharpe Ratio", fmt(stat.sharpe), "Ann., rf=5%", (stat.sharpe||0) >= 1 ? "green" : "blue")}
      ${kpiCard("Max Drawdown", fmtPct(stat.max_drawdown_pct), "Peak-to-trough", "red")}
      ${kpiCard("Sector", priceData.sector, priceData.company, "teal")}
    `;

    document.getElementById("asset-chart-title").textContent = `${ticker} — Price & Moving Averages`;

    renderPriceChart(d);
    renderReturnsHistogram(d);
    renderVolatilityChart(d);
    renderDrawdownChart(d);
    renderMonthlyHeatmap(monthlyData.monthly_returns);

  } catch (err) {
    console.error(err);
    alert("Error loading asset data: " + err.message);
  }
}

function renderPriceChart(d) {
  destroyChart("chart-price");
  const ctx = document.getElementById("chart-price").getContext("2d");
  const labels = d.map(r => r.date);

  charts["chart-price"] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Adj. Close",
          data: d.map(r => r.adj_close),
          borderColor: COLORS.blue, borderWidth: 1.5,
          pointRadius: 0, fill: false, tension: 0.2,
        },
        {
          label: "MA-20",
          data: d.map(r => r.ma_20),
          borderColor: COLORS.teal, borderWidth: 1, borderDash: [4, 2],
          pointRadius: 0, fill: false,
        },
        {
          label: "MA-50",
          data: d.map(r => r.ma_50),
          borderColor: COLORS.amber, borderWidth: 1, borderDash: [4, 2],
          pointRadius: 0, fill: false,
        },
        {
          label: "MA-200",
          data: d.map(r => r.ma_200),
          borderColor: COLORS.purple, borderWidth: 1, borderDash: [6, 3],
          pointRadius: 0, fill: false,
        },
      ],
    },
    options: chartDefaults(),
  });
}

function renderReturnsHistogram(d) {
  destroyChart("chart-returns-hist");
  const ctx     = document.getElementById("chart-returns-hist").getContext("2d");
  const returns = d.map(r => r.daily_return_pct).filter(v => v != null);

  // Simple histogram: bucket into 30 bins
  const min = Math.min(...returns), max = Math.max(...returns);
  const bins = 30, step = (max - min) / bins;
  const buckets = Array.from({ length: bins }, (_, i) => ({ x: min + i * step, count: 0 }));
  returns.forEach(v => {
    const idx = Math.min(Math.floor((v - min) / step), bins - 1);
    buckets[idx].count++;
  });

  charts["chart-returns-hist"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: buckets.map(b => fmt(b.x, 1) + "%"),
      datasets: [{
        label: "Frequency",
        data:  buckets.map(b => b.count),
        backgroundColor: buckets.map(b => b.x >= 0 ? COLORS.green + "99" : COLORS.red + "99"),
        borderWidth: 0, barPercentage: 1, categoryPercentage: 1,
      }],
    },
    options: {
      ...chartDefaults(),
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
      scales: {
        x: { ...chartDefaults().scales.x, ticks: { maxTicksLimit: 6, color: "#4d6080", font: { size: 10 } } },
        y: { ...chartDefaults().scales.y, title: { display: true, text: "# Days", color: "#4d6080" } },
      },
    },
  });
}

function renderVolatilityChart(d) {
  destroyChart("chart-volatility");
  const ctx = document.getElementById("chart-volatility").getContext("2d");
  charts["chart-volatility"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: d.map(r => r.date),
      datasets: [{
        label: "20-day Rolling Vol (%)",
        data:  d.map(r => r.vol_20d_pct),
        borderColor: COLORS.amber, borderWidth: 1.5,
        pointRadius: 0, fill: true,
        backgroundColor: COLORS.amber + "18",
      }],
    },
    options: chartDefaults(),
  });
}

function renderDrawdownChart(d) {
  destroyChart("chart-drawdown");
  const ctx = document.getElementById("chart-drawdown").getContext("2d");
  charts["chart-drawdown"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: d.map(r => r.date),
      datasets: [{
        label: "Drawdown (%)",
        data:  d.map(r => r.drawdown_pct),
        borderColor: COLORS.red, borderWidth: 1.5,
        pointRadius: 0, fill: true,
        backgroundColor: COLORS.red + "22",
      }],
    },
    options: chartDefaults(),
  });
}

function renderMonthlyHeatmap(monthly) {
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const years  = [...new Set(monthly.map(m => m.year))].sort();

  function cellClass(v) {
    if (v == null) return "heatmap-cell--zero";
    if (v > 8)  return "heatmap-cell--pos-3";
    if (v > 3)  return "heatmap-cell--pos-2";
    if (v > 0)  return "heatmap-cell--pos-1";
    if (v > -3) return "heatmap-cell--neg-1";
    if (v > -8) return "heatmap-cell--neg-2";
    return "heatmap-cell--neg-3";
  }

  const byYearMonth = {};
  monthly.forEach(m => { byYearMonth[`${m.year}-${m.month}`] = m.monthly_return_pct; });

  const html = `
    <table class="heatmap-table">
      <thead><tr>
        <th>Year</th>${MONTHS.map(m => `<th>${m}</th>`).join("")}<th>Annual</th>
      </tr></thead>
      <tbody>
        ${years.map(year => {
          let annSum = 0, annCount = 0;
          const cells = MONTHS.map((_, mi) => {
            const v = byYearMonth[`${year}-${mi + 1}`];
            if (v != null) { annSum += v; annCount++; }
            return `<td class="${cellClass(v)}">${v != null ? fmtPct(v, 1) : "—"}</td>`;
          }).join("");
          const annAvg = annCount ? annSum : null;
          return `<tr>
            <td style="color:#8fa3c0;font-weight:600">${year}</td>
            ${cells}
            <td class="${cellClass(annAvg)}" style="font-weight:600">
              ${annAvg != null ? fmtPct(annAvg, 1) : "—"}
            </td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
  document.getElementById("monthly-heatmap").innerHTML = html;
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE 3: PORTFOLIO
// ══════════════════════════════════════════════════════════════════════════

function initPortfolioBuilder() {
  const container = document.getElementById("weight-rows");
  container.innerHTML = "";
  // Default: 4 equal-weight positions
  const defaults = [
    { ticker: "AAPL", w: "0.25" },
    { ticker: "MSFT", w: "0.25" },
    { ticker: "JPM",  w: "0.25" },
    { ticker: "JNJ",  w: "0.25" },
  ];
  defaults.forEach(d => addWeightRow(d.ticker, d.w));
  updateWeightTotal();
}

function addWeightRow(ticker = "", weight = "0.10") {
  const container = document.getElementById("weight-rows");
  const id = "wr-" + Date.now() + Math.random().toString(36).substr(2, 5);
  const options = assetData.map(a =>
    `<option value="${a.ticker}" ${a.ticker === ticker ? "selected" : ""}>${a.ticker} — ${a.company}</option>`
  ).join("");

  const div = document.createElement("div");
  div.className = "weight-row-item";
  div.id = id;
  div.innerHTML = `
    <select class="weight-ticker-select" onchange="updateWeightTotal()">${options}</select>
    <input class="weight-input" type="number" min="0" max="1" step="0.01"
           value="${weight}" oninput="updateWeightTotal()" placeholder="0.00" />
    <button class="remove-btn" onclick="removeWeightRow('${id}')" title="Remove">✕</button>
  `;
  container.appendChild(div);
  updateWeightTotal();
}

function removeWeightRow(id) {
  document.getElementById(id)?.remove();
  updateWeightTotal();
}

function updateWeightTotal() {
  const inputs = document.querySelectorAll(".weight-input");
  const total  = Array.from(inputs).reduce((s, i) => s + (parseFloat(i.value) || 0), 0);
  const el     = document.getElementById("weight-total");
  el.textContent = (total * 100).toFixed(1) + "%";
  el.className   = `weight-total-value ${Math.abs(total - 1) < 0.001 ? "valid" : total > 1 ? "invalid" : ""}`;
}

async function analysePortfolio() {
  const rows    = document.querySelectorAll(".weight-row-item");
  const weights = {};
  rows.forEach(row => {
    const ticker = row.querySelector(".weight-ticker-select").value;
    const w      = parseFloat(row.querySelector(".weight-input").value) || 0;
    if (ticker && w > 0) weights[ticker] = (weights[ticker] || 0) + w;
  });

  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  if (Math.abs(total - 1.0) > 0.001) {
    alert(`Portfolio weights must sum to 100%. Current total: ${(total * 100).toFixed(1)}%`);
    return;
  }

  const btn = document.getElementById("analyse-btn");
  btn.disabled = true; btn.textContent = "Analysing…";

  try {
    const name = document.getElementById("portfolio-name").value || "My Portfolio";
    const result = await apiPost("/api/portfolio/analyse", { weights, portfolio_name: name });

    document.getElementById("portfolio-results-card").style.display = "block";
    document.getElementById("portfolio-charts").style.display = "grid";
    document.getElementById("portfolio-equity-card").style.display = "block";

    // KPIs
    document.getElementById("kpi-portfolio").innerHTML = `
      ${kpiCard("Ann. Return",    fmtPct(result.annualised_return * 100),    "Historical", result.annualised_return >= 0 ? "green" : "red")}
      ${kpiCard("Ann. Volatility", fmt(result.annualised_volatility * 100) + "%", "Portfolio vol", "amber")}
      ${kpiCard("Sharpe Ratio",   fmt(result.sharpe_ratio), "Ann., rf=5%", (result.sharpe_ratio||0) >= 1 ? "green" : "blue")}
      ${kpiCard("Max Drawdown",   fmtPct(result.max_drawdown * 100), "Peak-to-trough", "red")}
      ${kpiCard("Total Return",   fmtPct(result.total_portfolio_return * 100), "Full period", result.total_portfolio_return >= 0 ? "green" : "red")}
      ${kpiCard("Trading Days",   result.n_trading_days, "Data coverage", "teal")}
    `;

    // Charts
    renderPieChart("chart-sector-alloc", result.sector_allocation, "Sector Allocation");
    renderBarChart("chart-risk-contrib", result.risk_contribution, "Risk Contribution", COLORS.red);
    renderBarChart("chart-return-contrib", result.return_contribution, "Return Contribution", COLORS.green);

    // Equity curve
    const eq = await apiPost("/api/portfolio/equity-curve", { weights, portfolio_name: name });
    renderEquityCurve(eq);

  } catch (err) {
    alert("Portfolio analysis failed: " + err.message);
  } finally {
    btn.disabled = false; btn.textContent = "Analyse Portfolio";
  }
}

function renderPieChart(id, data, label) {
  destroyChart(id);
  const ctx    = document.getElementById(id).getContext("2d");
  const labels = Object.keys(data);
  const values = Object.values(data).map(v => (v * 100).toFixed(1));
  charts[id] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: labels.map((_, i) => COLORS.sectors[i % COLORS.sectors.length] + "cc"),
        borderColor:     labels.map((_, i) => COLORS.sectors[i % COLORS.sectors.length]),
        borderWidth: 1,
      }],
    },
    options: {
      ...chartDefaults(),
      cutout: "55%",
      plugins: {
        ...chartDefaults().plugins,
        tooltip: {
          ...chartDefaults().plugins.tooltip,
          callbacks: { label: ctx => `${ctx.label}: ${ctx.raw}%` },
        },
      },
    },
  });
}

function renderBarChart(id, data, label, color) {
  destroyChart(id);
  const ctx    = document.getElementById(id).getContext("2d");
  const labels = Object.keys(data);
  const values = Object.values(data).map(v => (v * 100).toFixed(2));
  charts[id] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        backgroundColor: color + "88",
        borderColor:     color,
        borderWidth: 1, borderRadius: 4,
      }],
    },
    options: {
      ...chartDefaults(),
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
    },
  });
}

function renderEquityCurve(eq) {
  destroyChart("chart-equity");
  const ctx = document.getElementById("chart-equity").getContext("2d");
  charts["chart-equity"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: eq.dates,
      datasets: [{
        label: "Portfolio Value (Base=1.0)",
        data:  eq.equity_curve,
        borderColor: COLORS.blue, borderWidth: 2,
        pointRadius: 0, fill: true,
        backgroundColor: COLORS.blue + "18",
      }],
    },
    options: chartDefaults(),
  });
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE 4: FORECASTING
// ══════════════════════════════════════════════════════════════════════════

function populateForecastSelect() {
  const sel = document.getElementById("forecast-ticker");
  sel.innerHTML = `<option value="">— Select Asset —</option>` +
    assetData.map(a => `<option value="${a.ticker}">${a.ticker} — ${a.company}</option>`).join("");
}

async function loadForecast() {
  const ticker  = document.getElementById("forecast-ticker").value;
  const horizon = document.getElementById("forecast-horizon").value;
  if (!ticker) { alert("Please select an asset."); return; }

  try {
    const data = await apiFetch(`/api/forecast/${ticker}?horizon=${horizon}`);
    document.getElementById("forecast-title").textContent =
      `${ticker} — ${horizon}-Day Trend Estimate`;

    renderForecastChart(data);

    document.getElementById("forecast-meta").innerHTML = `
      <div class="forecast-meta-item">
        <div class="forecast-meta-label">Model</div>
        <div class="forecast-meta-value">${data.model_name}</div>
      </div>
      <div class="forecast-meta-item">
        <div class="forecast-meta-label">Smoothing Level</div>
        <div class="forecast-meta-value">${data.smoothing_level}</div>
      </div>
      <div class="forecast-meta-item">
        <div class="forecast-meta-label">Smoothing Trend</div>
        <div class="forecast-meta-value">${data.smoothing_trend}</div>
      </div>
      <div class="forecast-meta-item">
        <div class="forecast-meta-label">Residual Std Dev</div>
        <div class="forecast-meta-value">$${fmt(data.residual_std)}</div>
      </div>
      <div class="forecast-meta-item">
        <div class="forecast-meta-label">Confidence Level</div>
        <div class="forecast-meta-value">${(data.confidence_level * 100).toFixed(0)}%</div>
      </div>
    `;

    document.getElementById("forecast-disclaimer").textContent = data.disclaimer;

  } catch (err) {
    alert("Forecast failed: " + err.message);
  }
}

function renderForecastChart(data) {
  destroyChart("chart-forecast");
  const ctx = document.getElementById("chart-forecast").getContext("2d");

  const allDates  = [...data.historical_dates, ...data.forecast_dates];
  const histLen   = data.historical_dates.length;

  const histPrices    = [...data.historical_prices, ...Array(data.forecast_dates.length).fill(null)];
  const forecastPrices = [...Array(histLen - 1).fill(null),
                           data.historical_prices[histLen - 1],
                           ...data.forecast_values];
  const upperBound    = [...Array(histLen - 1).fill(null),
                          data.historical_prices[histLen - 1],
                          ...data.upper_bound];
  const lowerBound    = [...Array(histLen - 1).fill(null),
                          data.historical_prices[histLen - 1],
                          ...data.lower_bound];

  charts["chart-forecast"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: allDates,
      datasets: [
        {
          label: "Historical Price",
          data: histPrices,
          borderColor: COLORS.blue, borderWidth: 1.5,
          pointRadius: 0, fill: false,
        },
        {
          label: "Trend Forecast",
          data: forecastPrices,
          borderColor: COLORS.teal, borderWidth: 2, borderDash: [5, 3],
          pointRadius: 0, fill: false,
        },
        {
          label: "Upper Bound (90%)",
          data: upperBound,
          borderColor: COLORS.teal + "40", borderWidth: 1,
          pointRadius: 0, fill: "+1",
          backgroundColor: COLORS.teal + "18",
        },
        {
          label: "Lower Bound (90%)",
          data: lowerBound,
          borderColor: COLORS.teal + "40", borderWidth: 1,
          pointRadius: 0, fill: false,
        },
      ],
    },
    options: chartDefaults(),
  });
}

// ══════════════════════════════════════════════════════════════════════════
// PAGE 5: MARKET REGIME
// ══════════════════════════════════════════════════════════════════════════

function populateRegimeSelect() {
  const sel = document.getElementById("regime-ticker");
  sel.innerHTML = `<option value="">All Assets</option>` +
    assetData.map(a => `<option value="${a.ticker}">${a.ticker} — ${a.company}</option>`).join("");
}

async function trainModel() {
  const btn = document.querySelector(".regime-controls .btn--secondary");
  btn.disabled = true; btn.textContent = "Training…";
  try {
    const data = await apiPost("/api/regime/train", {});
    alert(`Model trained! CV Accuracy: ${(data.cv_accuracy * 100).toFixed(1)}%\n\n` +
          `Top features: ${Object.entries(data.feature_importance).sort(([,a],[,b]) => b - a).slice(0,3).map(([k,v]) => `${k}: ${(v*100).toFixed(1)}%`).join(", ")}`);
    loadRegime();
  } catch (err) {
    alert("Training failed: " + err.message);
  } finally {
    btn.disabled = false; btn.textContent = "Train / Retrain Model";
  }
}

async function loadRegime() {
  const ticker = document.getElementById("regime-ticker").value;
  const url    = "/api/regime/predict" + (ticker ? `?ticker=${ticker}` : "");
  try {
    const data = await apiFetch(url);
    const preds = data.predictions;

    const counts = { "Low Volatility": 0, "Medium Volatility": 0, "High Volatility": 0 };
    preds.forEach(p => { counts[p.regime_label] = (counts[p.regime_label] || 0) + 1; });

    document.getElementById("kpi-regime").innerHTML = `
      ${kpiCard("Observations", preds.length, "Last 90 days per asset", "blue")}
      ${kpiCard("Low Vol Days", counts["Low Volatility"], "Calm market periods", "green")}
      ${kpiCard("Medium Vol Days", counts["Medium Volatility"], "Normal market", "amber")}
      ${kpiCard("High Vol Days", counts["High Volatility"], "Turbulent periods", "red")}
    `;

    renderRegimeDistChart(counts);
    renderRegimeTimeChart(preds);

    document.getElementById("regime-methodology").innerHTML = `
      <p><strong>Model:</strong> Random Forest Classifier (scikit-learn, 200 trees)</p>
      <p><strong>Features:</strong> 20-day & 60-day rolling volatility, daily return, 5-day & 20-day
         return momentum, MA20-MA50 spread, 60-day volume z-score</p>
      <p><strong>Labels:</strong> Derived from historical vol_20d tertiles:
         Low (bottom 33%), Medium (middle 33%), High (top 33%)</p>
      <p><strong>Validation:</strong> 5-fold time-series cross-validation (no data leakage)</p>
      <p><strong>Disclaimer:</strong> ${data.disclaimer}</p>
    `;

  } catch (err) {
    if (err.message.includes("not found")) {
      alert("Please train the model first using the 'Train / Retrain Model' button.");
    } else {
      alert("Regime load failed: " + err.message);
    }
  }
}

function renderRegimeDistChart(counts) {
  destroyChart("chart-regime-dist");
  const ctx = document.getElementById("chart-regime-dist").getContext("2d");
  charts["chart-regime-dist"] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: Object.keys(counts),
      datasets: [{
        data: Object.values(counts),
        backgroundColor: [COLORS.green + "cc", COLORS.amber + "cc", COLORS.red + "cc"],
        borderColor:     [COLORS.green,         COLORS.amber,         COLORS.red],
        borderWidth: 1,
      }],
    },
    options: { ...chartDefaults(), cutout: "55%" },
  });
}

function renderRegimeTimeChart(preds) {
  destroyChart("chart-regime-time");
  const ctx = document.getElementById("chart-regime-time").getContext("2d");
  const byDate = {};
  preds.forEach(p => {
    byDate[p.date] = byDate[p.date] || { low: 0, med: 0, high: 0 };
    if (p.regime_label === "Low Volatility")    byDate[p.date].low++;
    if (p.regime_label === "Medium Volatility") byDate[p.date].med++;
    if (p.regime_label === "High Volatility")   byDate[p.date].high++;
  });
  const dates  = Object.keys(byDate).sort();
  charts["chart-regime-time"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: dates,
      datasets: [
        { label: "Low Vol",  data: dates.map(d => byDate[d].low),  backgroundColor: COLORS.green + "99", borderWidth: 0, stack: "s" },
        { label: "Med Vol",  data: dates.map(d => byDate[d].med),  backgroundColor: COLORS.amber + "99", borderWidth: 0, stack: "s" },
        { label: "High Vol", data: dates.map(d => byDate[d].high), backgroundColor: COLORS.red   + "99", borderWidth: 0, stack: "s" },
      ],
    },
    options: { ...chartDefaults(), scales: { x: { stacked: true, ...chartDefaults().scales.x }, y: { stacked: true, ...chartDefaults().scales.y } } },
  });
}

// ══════════════════════════════════════════════════════════════════════════
// AI INSIGHTS
// ══════════════════════════════════════════════════════════════════════════

async function generateInsights() {
  const context = document.getElementById("ai-context").value.trim();
  if (!context) { alert("Please enter some analytical context first."); return; }

  const btn = document.querySelector(".btn--ai");
  btn.disabled = true; btn.textContent = "Generating…";
  document.getElementById("ai-output").innerHTML = `<p style="color:#4d6080">Calling Gemini AI…</p>`;

  try {
    const data = await apiPost("/api/insights/generate", { context });
    // Convert basic markdown to HTML
    const html = data.insight
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g,   "<em>$1</em>")
      .replace(/### (.*)/g,    "<h3>$1</h3>")
      .replace(/## (.*)/g,     "<h3>$1</h3>")
      .replace(/\n- /g,        "\n<br>• ")
      .replace(/\n/g,          "<br>");
    document.getElementById("ai-output").innerHTML = html;
  } catch (err) {
    document.getElementById("ai-output").innerHTML = `<p style="color:#ef4444">Error: ${err.message}</p>`;
  } finally {
    btn.disabled = false; btn.textContent = "Generate Insights";
  }
}

// ══════════════════════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", init);
