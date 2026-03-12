const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let currentSport = "all";
let currentView = "arbitrage";
let arbData = [];
let oddsData = [];
let kalshiData = [];

function apiBase() {
  const val = $("#api-url").value.replace(/\/+$/, "");
  if (val) return val;
  return window.location.origin;
}

function setStatus(msg, isError = false) {
  const el = $("#status");
  el.textContent = msg;
  el.style.color = isError ? "#e74c3c" : "#7a8ea0";
}

// --- Data fetching ---

async function fetchArbitrage() {
  const url = currentSport === "all"
    ? `${apiBase()}/api/arbitrage`
    : `${apiBase()}/api/arbitrage?sport=${currentSport}`;
  setStatus("Loading arbitrage data...");
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    arbData = await resp.json();
    setStatus(`Found ${arbData.length} arbitrage opportunities`);
    renderArbitrage();
  } catch (e) {
    setStatus(`Error: ${e.message}`, true);
    arbData = [];
    renderArbitrage();
  }
}

async function fetchOdds() {
  const url = currentSport === "all"
    ? `${apiBase()}/api/odds`
    : `${apiBase()}/api/odds?sport=${currentSport}`;
  setStatus("Loading odds data...");
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    oddsData = await resp.json();
    setStatus(`Loaded ${oddsData.length} games`);
    renderOdds();
  } catch (e) {
    setStatus(`Error: ${e.message}`, true);
    oddsData = [];
    renderOdds();
  }
}

async function fetchKalshi() {
  const url = currentSport === "all"
    ? `${apiBase()}/api/kalshi`
    : `${apiBase()}/api/kalshi?sport=${currentSport}`;
  setStatus("Loading Kalshi markets...");
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    kalshiData = await resp.json();
    setStatus(`Loaded ${kalshiData.length} Kalshi events`);
    renderKalshi();
  } catch (e) {
    setStatus(`Error: ${e.message}`, true);
    kalshiData = [];
    renderKalshi();
  }
}

function refreshData() {
  if (currentView === "arbitrage") fetchArbitrage();
  else if (currentView === "odds") fetchOdds();
  else if (currentView === "kalshi") fetchKalshi();
}

// --- Rendering ---

function renderArbitrage() {
  const container = $("#arb-list");
  if (arbData.length === 0) {
    container.innerHTML = '<div class="no-data">No arbitrage opportunities found. Try refreshing or selecting a different sport.</div>';
    return;
  }

  container.innerHTML = arbData.map((arb, i) => `
    <div class="arb-card">
      <div class="arb-header">
        <span class="arb-matchup">${arb.away_team} @ ${arb.home_team}</span>
        <span class="arb-profit">+${arb.profit_pct}% Profit</span>
      </div>
      <div class="arb-meta">${arb.sport_title} &middot; Market: ${formatMarket(arb.market)}</div>
      <div class="arb-outcomes">
        ${arb.outcomes.map(o => `
          <div class="outcome-card">
            <div class="outcome-name">${o.outcome_name}${o.point !== null && o.point !== undefined ? ` (${o.point > 0 ? "+" : ""}${o.point})` : ""}</div>
            <div class="outcome-book">${o.bookmaker}</div>
            <div class="outcome-odds">Line: ${o.american_odds > 0 ? "+" : ""}${o.american_odds} (${o.odds.toFixed(3)} decimal)</div>
            <div class="outcome-stake">Stake: ${o.stake_pct}% of bankroll</div>
          </div>
        `).join("")}
      </div>
      <div class="calc-section">
        <label>Total wager ($):
          <input type="number" class="wager-input" data-idx="${i}" placeholder="100" value="100" />
        </label>
        <div class="calc-result" id="calc-${i}">${calcProfit(arb, 100)}</div>
      </div>
    </div>
  `).join("");

  $$(".wager-input").forEach(input => {
    input.addEventListener("input", (e) => {
      const idx = parseInt(e.target.dataset.idx);
      const wager = parseFloat(e.target.value) || 0;
      $(`#calc-${idx}`).innerHTML = calcProfit(arbData[idx], wager);
    });
  });
}

function calcProfit(arb, totalWager) {
  if (!totalWager || totalWager <= 0) return "";
  const profit = (totalWager * arb.profit_pct / 100).toFixed(2);
  const stakes = arb.outcomes.map(o =>
    `${o.outcome_name} @ ${o.bookmaker}: $${(totalWager * o.stake_pct / 100).toFixed(2)}`
  ).join(" | ");
  return `Profit: <strong>$${profit}</strong> &mdash; ${stakes}`;
}

function renderOdds() {
  const container = $("#odds-list");
  if (oddsData.length === 0) {
    container.innerHTML = '<div class="no-data">No odds data available. Try refreshing or selecting a different sport.</div>';
    return;
  }

  container.innerHTML = oddsData.map(game => {
    const bookmakers = game.bookmakers || [];
    if (bookmakers.length === 0) return "";

    const marketKeys = [...new Set(bookmakers.flatMap(b => b.markets.map(m => m.key)))];

    return marketKeys.map(mk => {
      const bestOdds = {};
      const rows = [];

      bookmakers.forEach(bk => {
        const market = bk.markets.find(m => m.key === mk);
        if (!market) return;
        const row = { bookmaker: bk.title };
        market.outcomes.forEach(o => {
          row[o.name] = o.price;
          if (!bestOdds[o.name] || o.price > bestOdds[o.name]) {
            bestOdds[o.name] = o.price;
          }
        });
        rows.push(row);
      });

      if (rows.length === 0) return "";

      const outcomeNames = [...new Set(rows.flatMap(r => Object.keys(r).filter(k => k !== "bookmaker")))];

      return `
        <div class="game-card">
          <div class="game-header">
            <span>${game.away_team} @ ${game.home_team}</span>
            <span class="game-sport">${game.sport_title} &middot; ${formatMarket(mk)}</span>
          </div>
          <table class="odds-table">
            <thead>
              <tr>
                <th>Sportsbook</th>
                ${outcomeNames.map(n => `<th>${n}</th>`).join("")}
              </tr>
            </thead>
            <tbody>
              ${rows.map(r => `
                <tr>
                  <td>${r.bookmaker}</td>
                  ${outcomeNames.map(n => {
                    const val = r[n];
                    const isBest = val === bestOdds[n];
                    const display = val !== undefined ? (val > 0 ? `+${val}` : val) : "-";
                    return `<td class="${isBest ? "best-odds" : ""}">${display}</td>`;
                  }).join("")}
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }).join("");
  }).join("");
}

function renderKalshi() {
  const container = $("#kalshi-list");
  if (kalshiData.length === 0) {
    container.innerHTML = '<div class="no-data">No Kalshi markets available. Try refreshing or selecting a different sport.</div>';
    return;
  }

  container.innerHTML = kalshiData.map(event => {
    const outcomes = event.outcomes || [];
    const sportLabel = {
      "basketball_nba": "NBA", "baseball_mlb": "MLB",
      "icehockey_nhl": "NHL", "americanfootball_nfl": "NFL"
    }[event.sport_key] || event.sport_key;

    const marketLabel = {h2h: "Game Winner", spreads: "Spread", totals: "Totals"}[event.market_type] || event.market_type;

    return `<div class="game-card">
      <div class="game-header">
        <span>${event.title}</span>
        <span class="game-sport">${sportLabel} &middot; Kalshi &middot; ${marketLabel}</span>
      </div>
      <table class="odds-table">
        <thead><tr>
          <th>Outcome</th>
          <th>Yes Bid</th>
          <th>Yes Ask</th>
          <th>American</th>
          <th>Decimal</th>
        </tr></thead>
        <tbody>
        ${outcomes.map(o => `<tr>
          <td>${o.outcome_name}</td>
          <td>${fmtCents(o.yes_bid)}</td>
          <td>${fmtCents(o.yes_ask)}</td>
          <td class="${event.market_type === 'h2h' ? 'best-odds' : ''}">${o.american_odds !== null ? (o.american_odds > 0 ? "+" : "") + o.american_odds : "-"}</td>
          <td>${o.decimal_odds || "-"}</td>
        </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
  }).join("");
}

function fmtCents(val) {
  if (val === null || val === undefined) return "-";
  return `${(val * 100).toFixed(0)}¢`;
}

function formatMarket(key) {
  const labels = { h2h: "Moneyline", spreads: "Spread", totals: "Totals" };
  return labels[key] || key;
}

// --- Event listeners ---

$$(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    $$(".tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentSport = btn.dataset.sport;
    refreshData();
  });
});

$$(".view-tab").forEach(btn => {
  btn.addEventListener("click", () => {
    $$(".view-tab").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentView = btn.dataset.view;

    $("#arbitrage-view").classList.add("hidden");
    $("#odds-view").classList.add("hidden");
    $("#kalshi-view").classList.add("hidden");

    if (currentView === "arbitrage") {
      $("#arbitrage-view").classList.remove("hidden");
      fetchArbitrage();
    } else if (currentView === "odds") {
      $("#odds-view").classList.remove("hidden");
      fetchOdds();
    } else if (currentView === "kalshi") {
      $("#kalshi-view").classList.remove("hidden");
      fetchKalshi();
    }
  });
});

$("#refresh-btn").addEventListener("click", refreshData);

// Initial load
fetchArbitrage();
