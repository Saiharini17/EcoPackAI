/**
 * EcoPackAI — Main Recommender Frontend Logic
 * Features: AI recommendations, prediction history (localStorage), PDF/Excel export
 */

'use strict';

/* ── Constants ──────────────────────────────────────────────── */
const HISTORY_KEY = 'ecopackai_history';
const MAX_HISTORY  = 20;

/* ── State ──────────────────────────────────────────────────── */
let lastRecommendations = [];
let lastProfile = {};

/* ── DOM helpers ────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
function show(id) { const el = $(id); if (el) el.classList.remove('d-none'); }
function hide(id) { const el = $(id); if (el) el.classList.add('d-none'); }

/* ── On Load ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  $('weight').addEventListener('keydown', e => {
    if (e.key === 'Enter') getRecommendations();
  });
  renderHistory();
});

/* ═══════════════════════════════════════════════════════════════
   RECOMMENDATIONS
═══════════════════════════════════════════════════════════════ */

async function getRecommendations() {
  const btn    = $('btn-recommend');
  const weight = parseInt($('weight').value);

  if (!weight || weight < 1) {
    showError('Please enter a valid product weight (≥ 1g).');
    return;
  }

  const profile = {
    product_weight_g : weight,
    material_type    : $('material').value,
    fragility        : $('fragility').value,
    recyclable       : $('recyclable').value,
    transport_mode   : $('transport').value,
    product_category : $('category').value,
    top_n            : 3
  };

  lastProfile = { ...profile };
  delete lastProfile.top_n;

  // optional product name
  const name = $('product-name') ? $('product-name').value.trim() : '';
  if (name) lastProfile.product_name = name;

  btn.disabled = true;
  hide('placeholder');
  hide('results');
  hide('error-box');
  show('loading');

  try {
    const res  = await fetch('/api/recommend', {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify(profile)
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Server error');

    lastRecommendations = data.recommendations;
    renderRecommendations(data.recommendations);
    saveToHistory(lastProfile, data.recommendations);
  } catch (err) {
    showError(err.message || 'Failed to get recommendations. Is the server running?');
    show('placeholder');
  } finally {
    hide('loading');
    btn.disabled = false;
  }
}

/* ── Render Recommendation Cards ────────────────────────────── */
function renderRecommendations(recs) {
  const container = $('rec-cards');
  container.innerHTML = '';

  recs.forEach((r, idx) => {
    const card     = document.createElement('div');
    card.className = `rec-card rank-${r.rank}`;
    card.style.animationDelay = `${idx * 0.12}s`;

    const rankIcon  = r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : '🥉';
    const confPct   = Math.min(100, Math.max(0, r.confidence));
    const suit      = r.suitability_score.toFixed(1);
    const co2       = r.predicted_co2_kg;
    const co2Style  = co2 < 1.5 ? 'color:var(--eco-green);font-weight:700'
                    : co2 < 3.0 ? 'color:var(--eco-gold);font-weight:700'
                    :             'color:#f88;font-weight:700';
    const co2Label  = co2 < 1.5 ? 'Low impact' : co2 < 3.0 ? 'Moderate' : 'High impact';
    const ecoRating = Math.round(suit / 10);
    const stars     = '★'.repeat(ecoRating) + '☆'.repeat(10 - ecoRating);

    card.innerHTML = `
      <div class="d-flex align-items-start gap-3">
        <div class="rank-badge rank-${r.rank}" title="Rank #${r.rank}">${rankIcon}</div>
        <div class="flex-grow-1 min-w-0">

          <!-- Header row -->
          <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
            <div>
              <div class="rec-pkg-name">${escHtml(r.packaging_option)}</div>
              <div class="rec-eco-stars" title="Eco Rating ${ecoRating}/10">${stars}</div>
            </div>
            <div class="text-end">
              <div class="suit-score">${suit}<span style="font-size:.55em;font-weight:500;color:var(--eco-text-muted)">/100</span></div>
              <div class="suit-label">Suitability Score</div>
            </div>
          </div>

          <!-- Metrics grid -->
          <div class="rec-metrics-grid mt-2">
            <div class="rec-metric-box">
              <i class="fas fa-dollar-sign rec-metric-icon"></i>
              <div class="rec-metric-val">$${r.predicted_cost_usd.toFixed(2)}</div>
              <div class="rec-metric-lbl">Est. Cost / Unit</div>
            </div>
            <div class="rec-metric-box">
              <i class="fas fa-cloud rec-metric-icon"></i>
              <div class="rec-metric-val" style="${co2Style}">${co2.toFixed(3)} kg</div>
              <div class="rec-metric-lbl">CO₂ Emission · <span style="color:var(--eco-text-muted)">${co2Label}</span></div>
            </div>
            <div class="rec-metric-box">
              <i class="fas fa-brain rec-metric-icon"></i>
              <div class="rec-metric-val">${confPct.toFixed(1)}%</div>
              <div class="rec-metric-lbl">AI Confidence</div>
            </div>
          </div>

          <!-- Confidence bar -->
          <div class="confidence-bar-wrap mt-2">
            <div class="confidence-label">
              <span>Model Confidence</span><span>${confPct.toFixed(1)}%</span>
            </div>
            <div class="confidence-bar">
              <div class="confidence-fill" data-width="${confPct}"></div>
            </div>
          </div>

        </div>
      </div>
    `;
    container.appendChild(card);
  });

  // animate bars
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.querySelectorAll('#rec-cards .confidence-fill').forEach(el => {
      el.style.width = el.dataset.width + '%';
    });
  }));

  // subtitle
  const top = recs[0];
  const subtitle = $('results-subtitle');
  if (subtitle && top) {
    const name = lastProfile.product_name ? `"${escHtml(lastProfile.product_name)}" · ` : '';
    subtitle.innerHTML = `${name}${lastProfile.material_type} · ${lastProfile.product_weight_g}g · Best: <strong style="color:var(--eco-green)">${escHtml(top.packaging_option)}</strong>`;
  }

  // eco summary bar
  renderEcoSummary(recs);

  show('results');
}

/* ── Eco Impact Summary Bar ──────────────────────────────────── */
function renderEcoSummary(recs) {
  const el = $('eco-summary');
  if (!el || !recs.length) return;
  const top = recs[0];
  const avgCo2  = (recs.reduce((s, r) => s + r.predicted_co2_kg, 0) / recs.length).toFixed(3);
  const avgCost = (recs.reduce((s, r) => s + r.predicted_cost_usd, 0) / recs.length).toFixed(2);
  el.innerHTML = `
    <div class="eco-summary-inner">
      <div class="eco-summary-item">
        <i class="fas fa-trophy" style="color:var(--eco-gold)"></i>
        <span>Best Pick: <strong>${escHtml(top.packaging_option)}</strong></span>
      </div>
      <div class="eco-summary-sep"></div>
      <div class="eco-summary-item">
        <i class="fas fa-leaf" style="color:var(--eco-green)"></i>
        <span>Avg CO₂: <strong>${avgCo2} kg</strong></span>
      </div>
      <div class="eco-summary-sep"></div>
      <div class="eco-summary-item">
        <i class="fas fa-dollar-sign" style="color:var(--eco-teal)"></i>
        <span>Avg Cost: <strong>$${avgCost}</strong></span>
      </div>
    </div>
  `;
}

/* ═══════════════════════════════════════════════════════════════
   HISTORY (localStorage)
═══════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════════
   HISTORY (SQLite & localStorage)
   ═══════════════════════════════════════════════════════════════ */

let predictionHistory = [];

function getHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

async function saveToHistory(profile, recs) {
  // 1. Fallback / local storage save
  const localHistory = getHistory();
  localHistory.unshift({
    id        : Date.now(),
    timestamp : new Date().toISOString(),
    profile,
    topRec    : recs[0],
    allRecs   : recs
  });
  if (localHistory.length > MAX_HISTORY) localHistory.length = MAX_HISTORY;
  localStorage.setItem(HISTORY_KEY, JSON.stringify(localHistory));

  // 2. Server save (SQLite)
  try {
    const res = await fetch('/api/history/save', {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({ profile, recommendations: recs })
    });
    if (!res.ok) console.warn('Database save failed');
  } catch (err) {
    console.warn('Network error saving prediction to db:', err);
  }

  await renderHistory();
}

async function clearHistory() {
  // 1. Clear local
  localStorage.removeItem(HISTORY_KEY);

  // 2. Clear server
  try {
    const res = await fetch('/api/history/clear', {
      method: 'DELETE'
    });
    if (!res.ok) console.warn('Database clear failed');
  } catch (err) {
    console.warn('Network error clearing prediction db:', err);
  }

  await renderHistory();
}

async function renderHistory() {
  const cards   = $('history-cards');
  if (!cards) return;

  try {
    const res = await fetch('/api/history');
    if (!res.ok) throw new Error('API failure');
    const data = await res.json();
    predictionHistory = data.history || [];
  } catch (err) {
    console.warn('Falling back to local storage history:', err);
    // Normalize local storage objects to match DB format for rendering
    const local = getHistory();
    predictionHistory = local.map(item => ({
      id: item.id,
      created_at: item.timestamp,
      product_name: item.profile.product_name || '',
      product_weight_g: item.profile.product_weight_g,
      material_type: item.profile.material_type,
      fragility: item.profile.fragility,
      recyclable: item.profile.recyclable,
      transport_mode: item.profile.transport_mode,
      product_category: item.profile.product_category,
      top_packaging: item.topRec.packaging_option,
      confidence: item.topRec.confidence,
      predicted_cost: item.topRec.predicted_cost_usd,
      predicted_co2: item.topRec.predicted_co2_kg,
      suitability_score: item.topRec.suitability_score,
      all_recs: item.allRecs
    }));
  }

  const section = $('history-section');
  const countEl = $('history-count');
  const navBadge = $('history-count-badge');
  const navCount = $('history-nav-count');

  if (!predictionHistory.length) {
    if (section) section.classList.add('d-none');
    if (navBadge) navBadge.classList.add('d-none');
    return;
  }

  if (section) section.classList.remove('d-none');
  if (navBadge) navBadge.classList.remove('d-none');
  if (countEl) countEl.textContent = predictionHistory.length;
  if (navCount) navCount.textContent = predictionHistory.length;

  cards.innerHTML = '';

  predictionHistory.forEach(entry => {
    const col  = document.createElement('div');
    col.className = 'col-md-6 col-lg-4';

    // Normalize values
    const p = {
      product_name: entry.product_name || '',
      product_weight_g: entry.product_weight_g,
      material_type: entry.material_type,
      fragility: entry.fragility,
      recyclable: entry.recyclable,
      transport_mode: entry.transport_mode,
      product_category: entry.product_category
    };

    const top = {
      packaging_option: entry.top_packaging || '',
      confidence: entry.confidence || 0,
      predicted_cost_usd: entry.predicted_cost || 0,
      predicted_co2_kg: entry.predicted_co2 || 0,
      suitability_score: entry.suitability_score || 0
    };

    // Parse date safely
    let date;
    if (entry.created_at) {
      if (entry.created_at.includes('-') && entry.created_at.includes(' ')) {
        // SQLite timestamp 'YYYY-MM-DD HH:MM:SS' in UTC
        const iso = entry.created_at.trim().replace(' ', 'T') + 'Z';
        date = new Date(iso);
      } else {
        date = new Date(entry.created_at);
      }
    } else {
      date = new Date();
    }

    const timeStr = isNaN(date.getTime()) 
                  ? (entry.created_at || 'Just now')
                  : date.toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' })
                    + ' · ' + date.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' });

    const name = p.product_name ? `<div class="hist-product-name">${escHtml(p.product_name)}</div>` : '';
    const co2Color = top.predicted_co2_kg < 1.5 ? 'var(--eco-green)' : top.predicted_co2_kg < 3 ? 'var(--eco-gold)' : '#f88';

    col.innerHTML = `
      <div class="hist-card">
        <div class="hist-card-top">
          <div>
            ${name}
            <div class="hist-material-badge">
              <i class="fas fa-cube me-1"></i>${escHtml(p.material_type)}
            </div>
            <div class="hist-time">${timeStr}</div>
          </div>
          <button class="hist-rerun-btn" onclick="rerunPrediction(${entry.id})" title="Re-run this prediction">
            <i class="fas fa-redo"></i>
          </button>
        </div>

        <div class="hist-profile-chips">
          <span class="hist-chip"><i class="fas fa-weight-hanging me-1"></i>${p.product_weight_g}g</span>
          <span class="hist-chip"><i class="fas fa-wind me-1"></i>${p.fragility}</span>
          <span class="hist-chip"><i class="fas fa-recycle me-1"></i>${p.recyclable}</span>
          <span class="hist-chip"><i class="fas fa-truck me-1"></i>${p.transport_mode}</span>
        </div>

        <div class="hist-best-rec">
          <div class="hist-best-label">Best Recommendation</div>
          <div class="hist-best-name">🥇 ${escHtml(top.packaging_option)}</div>
          <div class="hist-metrics-row">
            <span class="hist-metric"><i class="fas fa-cloud me-1" style="color:${co2Color}"></i>${top.predicted_co2_kg.toFixed(3)} kg CO₂</span>
            <span class="hist-metric"><i class="fas fa-dollar-sign me-1" style="color:var(--eco-teal)"></i>$${top.predicted_cost_usd.toFixed(2)}</span>
            <span class="hist-metric"><i class="fas fa-star me-1" style="color:var(--eco-gold)"></i>${top.suitability_score.toFixed(1)}</span>
          </div>
        </div>
      </div>
    `;
    cards.appendChild(col);
  });
}

function rerunPrediction(id) {
  const entry = predictionHistory.find(h => h.id === id);
  if (!entry) return;
  const p = entry.profile;
  // Fill form fields
  if ($('product-name') && p.product_name) $('product-name').value = p.product_name;
  if ($('weight'))    $('weight').value    = p.product_weight_g;
  if ($('material'))  $('material').value  = p.material_type;
  if ($('fragility')) $('fragility').value = p.fragility;
  if ($('recyclable'))$('recyclable').value= p.recyclable;
  if ($('transport')) $('transport').value = p.transport_mode;
  if ($('category'))  $('category').value  = p.product_category;
  // Scroll to top and run
  window.scrollTo({ top: 0, behavior: 'smooth' });
  setTimeout(getRecommendations, 400);
}

/* ═══════════════════════════════════════════════════════════════
   EXPORT
═══════════════════════════════════════════════════════════════ */

async function exportExcel() {
  if (!lastRecommendations.length) return;
  try {
    const res = await fetch('/api/export/excel', {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({ recommendations: lastRecommendations, profile: lastProfile })
    });
    if (!res.ok) throw new Error('Export failed');
    downloadBlob(await res.blob(), 'ecopackai_report.xlsx');
  } catch (err) {
    showError('Excel export failed: ' + err.message);
  }
}

async function exportPDF() {
  if (!lastRecommendations.length) return;
  try {
    const res = await fetch('/api/export/pdf', {
      method  : 'POST',
      headers : { 'Content-Type': 'application/json' },
      body    : JSON.stringify({ recommendations: lastRecommendations, profile: lastProfile })
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.error || 'Export failed');
    }
    downloadBlob(await res.blob(), 'ecopackai_report.pdf');
  } catch (err) {
    showError('PDF export failed: ' + err.message);
  }
}

/* ═══════════════════════════════════════════════════════════════
   HELPERS
═══════════════════════════════════════════════════════════════ */

function showError(msg) {
  $('error-msg').textContent = msg;
  show('error-box');
  hide('loading');
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a   = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 200);
}

function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}
