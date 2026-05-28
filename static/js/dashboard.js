/**
 * EcoPackAI — BI Dashboard Frontend Logic
 * Renders KPIs, ML metrics, and 6 Plotly charts
 */

'use strict';

/* ── Design tokens (matches style.css) ──────────────────────── */
const COLORS = {
  green:      '#1dd275',
  greenLight: '#4ade9f',
  teal:       '#0ff0b3',
  greenDark:  '#0d8a48',
  text:       '#e8f5ee',
  textMuted:  '#7a9e8a',
  surface:    'rgba(255,255,255,0.04)',
  gold:       '#f5c542',
  silver:     '#b0bec5',
  bronze:     '#cd8a5a',
};

const PALETTE = [
  '#1dd275', '#0ff0b3', '#4ade9f', '#16b862', '#0d8a48',
  '#f5c542', '#cd8a5a', '#b0bec5', '#5bc8f5', '#c97af5'
];

const PLOTLY_BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  font:          { family: 'Outfit, system-ui, sans-serif', color: COLORS.textMuted, size: 12 },
  margin:        { t: 20, r: 10, b: 50, l: 50 },
  xaxis: {
    gridcolor:    'rgba(255,255,255,0.05)',
    linecolor:    'rgba(255,255,255,0.07)',
    tickfont:     { color: COLORS.textMuted, size: 11 },
    title:        { font: { color: COLORS.textMuted } }
  },
  yaxis: {
    gridcolor:    'rgba(255,255,255,0.05)',
    linecolor:    'rgba(255,255,255,0.07)',
    tickfont:     { color: COLORS.textMuted, size: 11 },
    title:        { font: { color: COLORS.textMuted } }
  },
  legend: {
    font:         { color: COLORS.textMuted },
    bgcolor:      'rgba(0,0,0,0)'
  }
};

const PLOTLY_CONFIG = {
  displayModeBar: false,
  responsive:     true
};

/* ── DOM helper ─────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

/* ── On load: fetch all data ─────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const [dashRes, metricsRes] = await Promise.all([
      fetch('/api/dashboard-data'),
      fetch('/api/model-metrics')
    ]);

    const dash    = await dashRes.json();
    const metrics = await metricsRes.json();

    if (dash.status === 'success')    renderDashboard(dash);
    if (metrics.status === 'success') renderMetrics(metrics.metrics);
  } catch (err) {
    console.error('Dashboard load error:', err);
  }
});

/* ── KPI Stats ───────────────────────────────────────────────── */
function renderDashboard(data) {
  const s = data.stats;

  animateNumber('k-products',  s.total_products,   0,  800);
  animateNumber('k-materials', s.total_materials,   0,  600);
  animateNumber('k-co2',       s.avg_co2,           3,  700);
  animateNumber('k-savings',   s.co2_savings_vs_plastic, 1, 900, '%');

  // Charts
  chartCO2ByPackaging(data.co2_by_packaging);
  chartCostByPackaging(data.cost_by_packaging);
  chartRecyclability(data.recyclability);
  chartTransport(data.transport_distribution);
  chartBiodeg(data.biodegradability);
  chartCategory(data.category_distribution);
}

/* ── ML Metrics ──────────────────────────────────────────────── */
function renderMetrics(m) {
  animateNumber('m-rf-r2',  m.cost.r2,                    4, 600);
  animateNumber('m-xgb-r2', m.co2.r2,                     4, 700);
  animateNumber('m-acc',    m.classifier_accuracy * 100,   1, 800, '%');
}

/* ── Animate number count-up ─────────────────────────────────── */
function animateNumber(id, target, decimals, duration, suffix = '') {
  const el = $(id);
  if (!el) return;
  const start   = 0;
  const startTs = performance.now();

  function step(ts) {
    const progress = Math.min((ts - startTs) / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    const value    = start + (target - start) * eased;
    el.textContent = value.toFixed(decimals) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* ── Chart 1: Avg CO₂ by Packaging Option ───────────────────── */
function chartCO2ByPackaging(data) {
  const labels = data.map(d => d.Packaging_Option);
  const values = data.map(d => d.avg_co2);

  Plotly.newPlot('chart-co2', [{
    type: 'bar',
    x: labels,
    y: values,
    marker: {
      color: values.map((v, i) => PALETTE[i % PALETTE.length]),
      opacity: 0.85,
      line: { color: 'rgba(255,255,255,0.1)', width: 1 }
    },
    hovertemplate: '<b>%{x}</b><br>Avg CO₂: %{y:.3f} kg<extra></extra>',
    text: values.map(v => v.toFixed(3)),
    textposition: 'outside',
    textfont: { color: COLORS.textMuted, size: 10 }
  }], {
    ...PLOTLY_BASE,
    yaxis: { ...PLOTLY_BASE.yaxis, title: { text: 'kg CO₂', font: { color: COLORS.textMuted } } }
  }, PLOTLY_CONFIG);
}

/* ── Chart 2: Avg Cost by Packaging Option ──────────────────── */
function chartCostByPackaging(data) {
  const labels = data.map(d => d.Packaging_Option);
  const values = data.map(d => d.avg_cost);

  Plotly.newPlot('chart-cost', [{
    type: 'bar',
    x: labels,
    y: values,
    marker: {
      color: values.map((v, i) => PALETTE[(i + 2) % PALETTE.length]),
      opacity: 0.85,
      line: { color: 'rgba(255,255,255,0.1)', width: 1 }
    },
    hovertemplate: '<b>%{x}</b><br>Avg Cost: $%{y:.2f}<extra></extra>',
    text: values.map(v => '$' + v.toFixed(2)),
    textposition: 'outside',
    textfont: { color: COLORS.textMuted, size: 10 }
  }], {
    ...PLOTLY_BASE,
    yaxis: { ...PLOTLY_BASE.yaxis, title: { text: 'USD', font: { color: COLORS.textMuted } } }
  }, PLOTLY_CONFIG);
}

/* ── Chart 3: Recyclability % by Material ───────────────────── */
function chartRecyclability(data) {
  const labels = data.map(d => d.Material_Type);
  const values = data.map(d => d.recyclable_pct);

  Plotly.newPlot('chart-recyc', [{
    type: 'bar',
    x: labels,
    y: values,
    orientation: 'v',
    marker: {
      color: values.map(v => v >= 80 ? COLORS.green : v >= 50 ? COLORS.gold : '#e05c5c'),
      opacity: 0.85,
      line: { color: 'rgba(255,255,255,0.1)', width: 1 }
    },
    hovertemplate: '<b>%{x}</b><br>Recyclable: %{y:.1f}%<extra></extra>',
    text: values.map(v => v.toFixed(1) + '%'),
    textposition: 'outside',
    textfont: { color: COLORS.textMuted, size: 10 }
  }], {
    ...PLOTLY_BASE,
    margin: { t: 20, r: 10, b: 60, l: 50 },
    yaxis: { ...PLOTLY_BASE.yaxis, range: [0, 110], title: { text: '%', font: { color: COLORS.textMuted } } }
  }, PLOTLY_CONFIG);
}

/* ── Chart 4: Transport Mode — Donut ────────────────────────── */
function chartTransport(data) {
  const labels = data.map(d => d.mode);
  const values = data.map(d => d.count);

  Plotly.newPlot('chart-transport', [{
    type: 'pie',
    hole: 0.55,
    labels,
    values,
    marker: {
      colors: [COLORS.green, COLORS.gold, COLORS.teal, COLORS.silver],
      line: { color: 'rgba(11,26,20,1)', width: 2 }
    },
    textinfo: 'label+percent',
    hovertemplate: '<b>%{label}</b><br>%{value} products (%{percent})<extra></extra>',
    textfont: { size: 11, color: COLORS.text }
  }], {
    ...PLOTLY_BASE,
    margin:    { t: 10, r: 10, b: 10, l: 10 },
    showlegend: false
  }, PLOTLY_CONFIG);
}

/* ── Chart 5: Biodegradability by Material ───────────────────── */
function chartBiodeg(data) {
  const sorted = [...data].sort((a, b) => b.Biodegradability_Score - a.Biodegradability_Score);
  const labels = sorted.map(d => d.Material_Type);
  const values = sorted.map(d => d.Biodegradability_Score);

  Plotly.newPlot('chart-biodeg', [{
    type: 'bar',
    x: labels,
    y: values,
    marker: {
      color: values.map(v =>
        v >= 75 ? COLORS.green : v >= 40 ? COLORS.gold : '#e05c5c'),
      opacity: 0.85,
      line: { color: 'rgba(255,255,255,0.1)', width: 1 }
    },
    hovertemplate: '<b>%{x}</b><br>Biodegradability: %{y}<extra></extra>',
    text: values.map(v => v.toFixed(0)),
    textposition: 'outside',
    textfont: { color: COLORS.textMuted, size: 10 }
  }], {
    ...PLOTLY_BASE,
    margin: { t: 20, r: 10, b: 60, l: 50 },
    yaxis: { ...PLOTLY_BASE.yaxis, range: [0, 110], title: { text: 'Score (0-100)', font: { color: COLORS.textMuted } } }
  }, PLOTLY_CONFIG);
}

/* ── Chart 6: Product Category Distribution ─────────────────── */
function chartCategory(data) {
  const sorted = [...data].sort((a, b) => b.count - a.count);
  const labels = sorted.map(d => d.category);
  const values = sorted.map(d => d.count);

  Plotly.newPlot('chart-category', [{
    type: 'bar',
    x: labels,
    y: values,
    marker: {
      color: values.map((v, i) => PALETTE[i % PALETTE.length]),
      opacity: 0.85,
      line: { color: 'rgba(255,255,255,0.1)', width: 1 }
    },
    hovertemplate: '<b>%{x}</b><br>Products: %{value}<extra></extra>',
    text: values,
    textposition: 'outside',
    textfont: { color: COLORS.textMuted, size: 10 }
  }], {
    ...PLOTLY_BASE,
    margin: { t: 20, r: 10, b: 100, l: 60 },
    xaxis: {
      ...PLOTLY_BASE.xaxis,
      tickangle: -30,
    },
    yaxis: { ...PLOTLY_BASE.yaxis, title: { text: 'Count', font: { color: COLORS.textMuted } } }
  }, PLOTLY_CONFIG);
}
