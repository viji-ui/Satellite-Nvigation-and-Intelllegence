/* ══════════════════════════════════════════════════════════════════════
   app.js — Satellite & Navigation Intelligence Hub
   Starfield · All Charts (Chart.js) · Word Clouds · Top 10 Table
   · Satellite Search with Autocomplete
   ══════════════════════════════════════════════════════════════════════ */

/* ── Colour palette (mirrors CSS variables) ─────────────────────────── */
const CLR = {
  cyan:    "#00d4ff",
  orange:  "#ff6b00",
  green:   "#39ff14",
  gold:    "#ffd700",
  violet:  "#8b5cf6",
  red:     "#ff3366",
  neutral: "#7aa3cc",
  bg:      "#000510",
  panel:   "rgba(7,20,40,0.82)",
};

/* ── Chart.js global defaults ───────────────────────────────────────── */
Chart.defaults.color          = "#7aa3cc";
Chart.defaults.borderColor    = "rgba(0,212,255,0.08)";
Chart.defaults.font.family    = "'Space Mono', monospace";
Chart.defaults.font.size      = 11;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.padding  = 16;
Chart.defaults.plugins.tooltip.backgroundColor = "rgba(3,13,31,0.95)";
Chart.defaults.plugins.tooltip.borderColor     = "rgba(0,212,255,0.3)";
Chart.defaults.plugins.tooltip.borderWidth     = 1;
Chart.defaults.plugins.tooltip.titleFont       = { family: "'Orbitron', monospace", size: 11 };
Chart.defaults.plugins.tooltip.bodyFont        = { family: "'Space Mono', monospace", size: 11 };
Chart.defaults.plugins.tooltip.padding         = 12;

/* ══════════════════════════════════════════════════════════════════════
   STARFIELD  (animated canvas background with orbit ring)
   ══════════════════════════════════════════════════════════════════════ */
(function initStarfield() {
  const canvas = document.getElementById("starfield");
  const ctx    = canvas.getContext("2d");
  let   W, H, stars = [], orbitAngle = 0;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    stars = Array.from({ length: 280 }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      r: Math.random() * 1.4 + 0.3,
      a: Math.random(),
      da: (Math.random() - 0.5) * 0.004,
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // Stars
    stars.forEach(s => {
      s.a = Math.max(0.05, Math.min(1, s.a + s.da));
      if (s.a <= 0.05 || s.a >= 1) s.da *= -1;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(180,210,255,${s.a * 0.55})`;
      ctx.fill();
    });

    // Subtle orbit ring
    orbitAngle += 0.003;
    const cx = W / 2, cy = H * 0.28;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(orbitAngle);
    ctx.beginPath();
    ctx.ellipse(0, 0, W * 0.3, W * 0.08, 0, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(0,212,255,0.04)";
    ctx.lineWidth   = 1;
    ctx.setLineDash([6, 8]);
    ctx.stroke();
    ctx.restore();

    // Occasional shooting star
    if (Math.random() < 0.003) {
      const sx = Math.random() * W, sy = Math.random() * H * 0.4;
      const len = Math.random() * 100 + 60;
      const grad = ctx.createLinearGradient(sx, sy, sx + len, sy + len * 0.35);
      grad.addColorStop(0, "rgba(0,212,255,0)");
      grad.addColorStop(0.5, "rgba(0,212,255,0.8)");
      grad.addColorStop(1, "rgba(0,212,255,0)");
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx + len, sy + len * 0.35);
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([]);
      ctx.stroke();
    }

    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);
  resize();
  draw();
})();

/* ══════════════════════════════════════════════════════════════════════
   DATA LOADING
   ══════════════════════════════════════════════════════════════════════ */
let _data = null;

async function loadData() {
  const res = await fetch("outputs/satellite_data.json");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ══════════════════════════════════════════════════════════════════════
   HELPERS
   ══════════════════════════════════════════════════════════════════════ */
function hexAlpha(hex, alpha) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

const ORBIT_COLORS = {
  "LEO":        CLR.cyan,
  "MEO":        CLR.violet,
  "GEO":        CLR.gold,
  "HEO":        CLR.orange,
  "Elliptical": CLR.green,
  "Unknown":    CLR.neutral,
};

const CAP_COLORS = {
  "Strategic Tier":    CLR.gold,
  "Operational Tier":  CLR.cyan,
  "Support Tier":      CLR.green,
  "Experimental Tier": CLR.violet,
};

const SENT_COLORS = {
  "Positive": CLR.cyan,
  "Neutral":  CLR.gold,
  "Negative": CLR.red,
};

function capPillClass(label) {
  if (!label) return "cap-support";
  const l = label.toLowerCase();
  if (l.includes("strategic"))    return "cap-strategic";
  if (l.includes("operational"))  return "cap-operational";
  if (l.includes("experimental")) return "cap-experimental";
  return "cap-support";
}

/* ══════════════════════════════════════════════════════════════════════
   STAT CARDS
   ══════════════════════════════════════════════════════════════════════ */
function buildStatCards(data) {
  const sent  = data.sent_counts || {};
  const total = data.total || 0;
  const pos   = sent["Positive"] || 0;
  const orbit = data.orbit_counts || {};
  const topOp = (data.top_operators || [])[0];
  const countries = Object.keys(data.country_counts || {}).length;

  const pct = v => total ? ((v / total) * 100).toFixed(1) + "%" : "–";

  const cards = [
    { icon: "🛰️", value: total.toLocaleString(), label: "Active Satellites",       sub: "Global Orbital Fleet" },
    { icon: "🌐", value: Object.keys(orbit).length, label: "Orbit Classes",         sub: "LEO · MEO · GEO · HEO" },
    { icon: "🌍", value: countries,               label: "Countries & Operators",   sub: "Spacefaring nations" },
    { icon: "✅", value: pct(pos),                label: "Positive Missions",       sub: `${pos.toLocaleString()} satellites` },
    { icon: "🚀", value: topOp ? topOp[0].split(" ")[0] : "–", label: "Top Operator", sub: topOp ? `${topOp[1]} satellites` : "" },
    { icon: "⭐", value: (data.cap_counts?.["Strategic Tier"] || 0), label: "Strategic Tier", sub: "Highest capability score" },
  ];

  const grid = document.getElementById("stat-grid");
  grid.innerHTML = cards.map((c, i) =>
    `<div class="stat-card" style="animation-delay:${i * 0.08}s">
       <span class="stat-icon">${c.icon}</span>
       <span class="stat-value">${c.value}</span>
       <div class="stat-label">${c.label}</div>
       <div class="stat-sub">${c.sub}</div>
     </div>`
  ).join("");
}

/* ══════════════════════════════════════════════════════════════════════
   CHART BUILDERS
   ══════════════════════════════════════════════════════════════════════ */

/* 1 ── Sentiment by orbit class (horizontal bar) */
function buildOrbitSentChart(data) {
  const orbitSent = data.orbit_avg_sent || {};
  const labels = Object.keys(orbitSent);
  const values = Object.values(orbitSent);
  const colors = labels.map(l => ORBIT_COLORS[l] || CLR.neutral);

  new Chart(document.getElementById("chart-orbit-sent"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Avg Sentiment",
        data: values,
        backgroundColor: colors.map(c => hexAlpha(c, 0.55)),
        borderColor:     colors,
        borderWidth: 1.5,
        borderRadius: 6,
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: "rgba(0,212,255,0.07)" },
          ticks: { callback: v => v.toFixed(2) },
        },
        y: { grid: { display: false } },
      },
    }
  });
}

/* 2 ── Sentiment distribution (doughnut) */
function buildSentDistChart(data) {
  const sentC = data.sent_counts || {};
  const labels = Object.keys(sentC);
  const values = Object.values(sentC);
  const colors = labels.map(l => SENT_COLORS[l] || CLR.neutral);
  const total  = values.reduce((a, b) => a + b, 0);

  new Chart(document.getElementById("chart-sent-dist"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.map(c => hexAlpha(c, 0.55)),
        borderColor: colors,
        borderWidth: 2,
        hoverOffset: 10,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: "65%",
      plugins: {
        legend: { position: "bottom" },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed.toLocaleString()} (${((ctx.parsed/total)*100).toFixed(1)}%)` } }
      }
    }
  });

  // Insight box
  const dominant = labels[values.indexOf(Math.max(...values))];
  const domPct   = total ? ((Math.max(...values) / total) * 100).toFixed(1) : 0;
  document.getElementById("sent-insight").innerHTML =
    `<strong>${dominant}</strong> missions dominate at <strong>${domPct}%</strong> of all satellite profiles — 
     reflecting the precision-critical and enabling language used in most navigation, communications and 
     Earth observation mission descriptions.`;
}

/* 3 ── Orbit class counts (doughnut) */
function buildOrbitCountChart(data) {
  const orbitC = data.orbit_counts || {};
  const labels = Object.keys(orbitC);
  const values = Object.values(orbitC);
  const colors = labels.map(l => ORBIT_COLORS[l] || CLR.neutral);

  new Chart(document.getElementById("chart-orbit-counts"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors.map(c => hexAlpha(c, 0.5)),
        borderColor: colors,
        borderWidth: 2,
        hoverOffset: 12,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: "60%",
      plugins: {
        legend: { position: "bottom" },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed.toLocaleString()}` } }
      }
    }
  });
}

/* 4 ── Purpose breakdown (polar area) */
function buildPurposeChart(data) {
  const purposeC = data.purpose_counts || {};
  const labels   = Object.keys(purposeC);
  const values   = Object.values(purposeC);
  const palette  = [CLR.cyan, CLR.orange, CLR.violet, CLR.green,
                    CLR.gold, CLR.red, CLR.neutral, "#4fc3f7"];

  new Chart(document.getElementById("chart-purpose"), {
    type: "polarArea",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: palette.slice(0, labels.length).map(c => hexAlpha(c, 0.45)),
        borderColor:     palette.slice(0, labels.length),
        borderWidth: 1.5,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        r: { grid: { color: "rgba(0,212,255,0.08)" }, ticks: { display: false } }
      },
      plugins: {
        legend: { position: "bottom", labels: { font: { size: 9 } } }
      }
    }
  });
}

/* 5 ── Capability tier (bar) */
function buildCapChart(data) {
  const capC   = data.cap_counts || {};
  const labels = Object.keys(capC);
  const values = Object.values(capC);
  const colors = labels.map(l => CAP_COLORS[l] || CLR.neutral);

  new Chart(document.getElementById("chart-cap"), {
    type: "bar",
    data: {
      labels: labels.map(l => l.replace(" Tier", "")),
      datasets: [{
        label: "Satellites",
        data: values,
        backgroundColor: colors.map(c => hexAlpha(c, 0.5)),
        borderColor: colors,
        borderWidth: 1.5,
        borderRadius: 8,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: "rgba(0,212,255,0.07)" } },
        x: { grid: { display: false } },
      }
    }
  });
}

/* 6 ── Launch trend (area line) */
function buildLaunchTrendChart(data) {
  const trend  = data.launch_trend || [];
  const labels = trend.map(d => d.year);
  const values = trend.map(d => d.count);

  new Chart(document.getElementById("chart-launch-trend"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Launches",
        data: values,
        borderColor: CLR.cyan,
        backgroundColor: (ctx) => {
          const chart = ctx.chart;
          const { ctx: c2d, chartArea } = chart;
          if (!chartArea) return hexAlpha(CLR.cyan, 0.1);
          const grad = c2d.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
          grad.addColorStop(0, hexAlpha(CLR.cyan, 0.35));
          grad.addColorStop(1, hexAlpha(CLR.cyan, 0.02));
          return grad;
        },
        fill: true,
        tension: 0.45,
        pointRadius: 3,
        pointHoverRadius: 7,
        pointBackgroundColor: CLR.cyan,
        borderWidth: 2.5,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: "rgba(0,212,255,0.07)" }, beginAtZero: true },
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } }
      }
    }
  });
}

/* 7 ── Top operators (horizontal bar) */
function buildOperatorsChart(data) {
  const ops    = (data.top_operators || []).slice(0, 10);
  const labels = ops.map(o => o[0].length > 22 ? o[0].slice(0, 22) + "…" : o[0]);
  const values = ops.map(o => o[1]);
  const palette = [CLR.cyan, CLR.violet, CLR.orange, CLR.green,
                   CLR.gold, CLR.red, "#4fc3f7", "#b89af0", "#aaffaa", "#ffaa44"];

  new Chart(document.getElementById("chart-operators"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Satellites",
        data: values,
        backgroundColor: palette.map(c => hexAlpha(c, 0.52)),
        borderColor:     palette,
        borderWidth: 1.5,
        borderRadius: 5,
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: "rgba(0,212,255,0.07)" } },
        y: { grid: { display: false }, ticks: { font: { size: 10 } } },
      }
    }
  });
}

/* 8 ── User sector (doughnut) */
function buildUsersChart(data) {
  const userC  = data.user_counts || {};
  const labels = Object.keys(userC);
  const values = Object.values(userC);
  const palette = [CLR.cyan, CLR.orange, CLR.violet, CLR.green, CLR.gold, CLR.red];

  new Chart(document.getElementById("chart-users"), {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: palette.slice(0, labels.length).map(c => hexAlpha(c, 0.5)),
        borderColor: palette.slice(0, labels.length),
        borderWidth: 2,
        hoverOffset: 10,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: "62%",
      plugins: { legend: { position: "bottom" } }
    }
  });
}

/* 9 ── Countries (bar) */
function buildCountriesChart(data) {
  const countryC = data.country_counts || {};
  const labels   = Object.keys(countryC).slice(0, 12);
  const values   = labels.map(l => countryC[l]);
  const palette  = [CLR.cyan, CLR.orange, CLR.violet, CLR.green,
                    CLR.gold, CLR.red, CLR.neutral, "#4fc3f7",
                    "#b89af0", "#aaffaa", "#ffaa44", "#ff88aa"];

  new Chart(document.getElementById("chart-countries"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Satellites",
        data: values,
        backgroundColor: palette.map(c => hexAlpha(c, 0.5)),
        borderColor: palette,
        borderWidth: 1.5,
        borderRadius: 5,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: "rgba(0,212,255,0.07)" } },
        x: { grid: { display: false }, ticks: { maxRotation: 35, font: { size: 10 } } }
      }
    }
  });
}

/* 10 ── Perigee vs Apogee scatter (bubble) */
function buildScatterChart(data) {
  const scatter = data.scatter_data || [];

  const capGroups = {};
  scatter.forEach(pt => {
    const cap = pt.cap || "Support Tier";
    if (!capGroups[cap]) capGroups[cap] = [];
    capGroups[cap].push({
      x:     Math.log10(Math.max(pt.perigee, 1)),
      y:     Math.log10(Math.max(pt.apogee,  1)),
      r:     Math.sqrt(Math.max(pt.mass, 1)) * 0.18 + 3,
      name:  pt.name,
      orbit: pt.orbit,
    });
  });

  const datasets = Object.entries(capGroups).map(([cap, pts]) => ({
    label: cap,
    data: pts,
    backgroundColor: hexAlpha(CAP_COLORS[cap] || CLR.neutral, 0.45),
    borderColor:     CAP_COLORS[cap] || CLR.neutral,
    borderWidth: 0.8,
  }));

  new Chart(document.getElementById("chart-scatter"), {
    type: "bubble",
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            label: ctx => {
              const d = ctx.raw;
              return [
                ` ${d.name}`,
                ` Orbit: ${d.orbit}`,
                ` Perigee: ${Math.round(Math.pow(10, d.x))} km`,
                ` Apogee: ${Math.round(Math.pow(10, d.y))} km`,
              ];
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(0,212,255,0.07)" },
          title: { display: true, text: "log₁₀ Perigee (km)", color: CLR.neutral },
          ticks: { callback: v => `10^${v.toFixed(1)}` }
        },
        y: {
          grid: { color: "rgba(0,212,255,0.07)" },
          title: { display: true, text: "log₁₀ Apogee (km)", color: CLR.neutral },
          ticks: { callback: v => `10^${v.toFixed(1)}` }
        }
      }
    }
  });

  const strat = scatter.filter(s => s.cap === "Strategic Tier").length;
  document.getElementById("scatter-insight").innerHTML =
    `The scatter reveals clear orbital clustering: <strong>LEO constellations</strong> (300–1400 km) dominate by count, 
     while <strong>GEO payloads</strong> cluster at ~35,786 km with the heaviest launch masses. 
     <strong>${strat}</strong> satellites are classified as Strategic Tier based on orbit + mission criticality + mass.`;
}

/* ══════════════════════════════════════════════════════════════════════
   WORD CLOUDS
   ══════════════════════════════════════════════════════════════════════ */
function buildWordCloud(containerId, words, posColor, negColor) {
  const container = document.getElementById(containerId);
  if (!container || !words || !words.length) return;

  const max  = words[0][1];
  const isPos = containerId === "wc-pos";

  container.innerHTML = words.map(([word, count]) => {
    const size  = 10 + (count / max) * 22;
    const alpha = 0.45 + (count / max) * 0.55;
    const color = isPos ? CLR.cyan : CLR.orange;
    const alt   = isPos ? CLR.violet : CLR.red;
    const use   = Math.random() > 0.65 ? alt : color;
    return `<span class="wc-word"
      style="font-size:${size.toFixed(1)}px;color:${use};opacity:${alpha.toFixed(2)};
             transform:rotate(${(Math.random()-0.5)*18}deg);display:inline-block;"
      title="${count} occurrences">${word}</span>`;
  }).join("");
}

/* ══════════════════════════════════════════════════════════════════════
   TOP 10 TABLE
   ══════════════════════════════════════════════════════════════════════ */
function buildTop10Table(data) {
  const top10 = data.top10 || [];
  const panel = document.getElementById("top10-table");

  const rankClass = r => r === 1 ? "rank-1" : r === 2 ? "rank-2" : r === 3 ? "rank-3" : "rank-other";

  panel.innerHTML =
    `<div class="sat-row header">
       <div>#</div>
       <div>Satellite / Orbit</div>
       <div>Capability</div>
       <div>Purpose</div>
       <div>Sentiment</div>
       <div>Score</div>
     </div>` +
    top10.map((sat, i) => {
      const pct    = ((sat.combined_score || 0) * 100).toFixed(0);
      const capCls = capPillClass(sat.capability_label);
      const sentColor = sat.sentiment_label === "Positive" ? CLR.cyan :
                        sat.sentiment_label === "Negative" ? CLR.red : CLR.gold;
      return `
        <div class="sat-row" onclick="searchFor('${sat.name.replace(/'/g, "\\'")}')">
          <div class="rank-badge ${rankClass(i + 1)}">${i + 1}</div>
          <div>
            <div class="sat-name-cell">${sat.name}</div>
            <span class="sat-orbit-badge">${sat.orbit_class}</span>
          </div>
          <div><span class="cap-pill ${capCls}">${sat.capability_label}</span></div>
          <div style="font-size:11px;color:#7aa3cc;font-family:'Space Mono',monospace">
            ${(sat.purpose || "–").split("/")[0].trim().slice(0, 20)}
          </div>
          <div style="font-size:12px;color:${sentColor};font-family:'Space Mono',monospace">
            ${sat.sentiment_compound >= 0 ? "+" : ""}${(sat.sentiment_compound || 0).toFixed(3)}
          </div>
          <div class="score-bar-wrap">
            <div class="score-bar"><div class="score-fill" style="width:${pct}%"></div></div>
            <span class="score-val">${pct}%</span>
          </div>
        </div>`;
    }).join("");
}

/* ══════════════════════════════════════════════════════════════════════
   SATELLITE SEARCH
   ══════════════════════════════════════════════════════════════════════ */
let _searchIndex = [];
let _acActive    = -1;

function initSearch(data) {
  _searchIndex = data.search_index || [];
  const input = document.getElementById("sat-search");
  const acList = document.getElementById("autocomplete");
  const results = document.getElementById("search-results");

  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    if (q.length < 2) { acList.style.display = "none"; return; }

    const matches = _searchIndex
      .filter(s =>
        (s.name  || "").toLowerCase().includes(q) ||
        (s.purpose || "").toLowerCase().includes(q) ||
        (s.orbit_class || "").toLowerCase().includes(q) ||
        (s.operator || "").toLowerCase().includes(q) ||
        (s.country || "").toLowerCase().includes(q)
      )
      .slice(0, 8);

    if (!matches.length) { acList.style.display = "none"; return; }

    acList.innerHTML = matches
      .map(s => `<div class="autocomplete-item" data-name="${s.name}">${s.name} · <span style="opacity:0.6;font-size:10px">${s.orbit_class} · ${(s.purpose || "").split("/")[0].trim().slice(0,30)}</span></div>`)
      .join("");
    acList.style.display = "block";
    _acActive = -1;

    acList.querySelectorAll(".autocomplete-item").forEach(item => {
      item.addEventListener("click", () => {
        input.value = item.dataset.name;
        acList.style.display = "none";
        showResults(item.dataset.name);
      });
    });
  });

  input.addEventListener("keydown", e => {
    const items = acList.querySelectorAll(".autocomplete-item");
    if (!items.length) return;
    if (e.key === "ArrowDown") { _acActive = Math.min(_acActive + 1, items.length - 1); }
    else if (e.key === "ArrowUp") { _acActive = Math.max(_acActive - 1, -1); }
    else if (e.key === "Enter") {
      if (_acActive >= 0) {
        input.value = items[_acActive].dataset.name;
        acList.style.display = "none";
        showResults(items[_acActive].dataset.name);
        return;
      }
      acList.style.display = "none";
      showResults(input.value.trim());
      return;
    } else return;
    items.forEach((it, i) => it.classList.toggle("active", i === _acActive));
  });

  document.addEventListener("click", e => {
    if (!acList.contains(e.target) && e.target !== input) acList.style.display = "none";
  });
}

function searchFor(name) {
  const input = document.getElementById("sat-search");
  input.value = name;
  document.getElementById("autocomplete").style.display = "none";
  showResults(name);
  document.querySelector(".search-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}

function showResults(query) {
  if (!query) return;
  const q = query.toLowerCase();
  const matches = _searchIndex
    .filter(s =>
      (s.name || "").toLowerCase().includes(q) ||
      (s.purpose || "").toLowerCase().includes(q) ||
      (s.orbit_class || "").toLowerCase().includes(q) ||
      (s.operator || "").toLowerCase().includes(q)
    )
    .slice(0, 6);

  const container = document.getElementById("search-results");
  if (!matches.length) {
    container.innerHTML = `<div class="no-results">No satellites found matching "<em>${query}</em>"</div>`;
    return;
  }

  container.innerHTML = matches.map(sat => {
    const sentColor = sat.sentiment_label === "Positive" ? CLR.cyan :
                      sat.sentiment_label === "Negative" ? CLR.red : CLR.gold;
    const capCls    = capPillClass(sat.capability_label);
    const scores    = [
      { label: "Sentiment", val: (sat.sentiment >= 0 ? "+" : "") + (sat.sentiment || 0).toFixed(3) },
      { label: "Capability Score", val: sat.capability_score ?? "–" },
      { label: "Combined", val: ((sat.combined_score || 0) * 100).toFixed(0) + "%" },
    ];
    return `
      <div class="search-result-card">
        <div class="search-result-name">🛰️ ${sat.name}</div>
        <div class="search-result-desc">${sat.description || "Mission profile not available."}</div>
        <div class="search-meta">
          <span class="meta-chip">🌐 ${sat.orbit_class}</span>
          <span class="meta-chip">🎯 ${(sat.purpose || "–").split("/")[0].trim()}</span>
          <span class="meta-chip">🚀 ${sat.launch_year || "–"}</span>
          <span class="cap-pill ${capCls}" style="font-size:10px;padding:6px 15px">${sat.capability_label}</span>
          ${scores.map(s => `<span class="meta-chip">${s.label}: <strong style="color:${CLR.cyan}">${s.val}</strong></span>`).join("")}
          <span class="meta-chip" style="color:${sentColor}">Sentiment: <strong>${sat.sentiment_label}</strong></span>
        </div>
      </div>`;
  }).join("");
}

/* ══════════════════════════════════════════════════════════════════════
   MAIN INIT
   ══════════════════════════════════════════════════════════════════════ */
async function init() {
  try {
    const data = await loadData();
    _data = data;

    document.getElementById("loading-state").style.display = "none";
    document.getElementById("main-content").style.display  = "block";

    // Update badge count
    const badge = document.querySelector(".header-badge");
    if (badge && data.total) {
      badge.textContent = `UCS Satellite Database · NLP Analysis · ${data.total.toLocaleString()} Active Satellites`;
    }

    buildStatCards(data);
    buildOrbitSentChart(data);
    buildSentDistChart(data);
    buildOrbitCountChart(data);
    buildPurposeChart(data);
    buildCapChart(data);
    buildLaunchTrendChart(data);
    buildOperatorsChart(data);
    buildUsersChart(data);
    buildCountriesChart(data);
    buildScatterChart(data);
    buildWordCloud("wc-pos", data.top_pos_words || [], CLR.cyan, CLR.violet);
    buildWordCloud("wc-neg", data.top_neg_words || [], CLR.orange, CLR.red);
    buildTop10Table(data);
    initSearch(data);

  } catch (err) {
    console.error(err);
    document.getElementById("loading-state").innerHTML =
      `<div style="color:#ff3366;font-family:'Space Mono',monospace;font-size:12px;text-align:center;padding:60px 20px">
        <div style="font-size:32px;margin-bottom:16px">⚠️</div>
        <strong>Could not load satellite_data.json</strong><br><br>
        Run <code style="background:rgba(0,212,255,0.1);padding:4px 10px;border-radius:4px">python nlp_pipeline.py</code>
        in the project directory, then serve with<br>
        <code style="background:rgba(0,212,255,0.1);padding:4px 10px;border-radius:4px">python -m http.server 8000</code>
      </div>`;
  }
}

document.addEventListener("DOMContentLoaded", init);
