const state = {
  symbol: "EUR/USD",
  timeframe: "1h",
  mode: "SMART",
  symbolTv: "FX:EURUSD",
  bootstrap: null,
  mouseX: 0,
  mouseY: 0,
};

const els = {
  symbolSelect: document.getElementById("symbolSelect"),
  timeframeSelect: document.getElementById("timeframeSelect"),
  analyzeButton: document.getElementById("analyzeButton"),
  modePills: [...document.querySelectorAll(".mode-pill")],
  navButtons: [...document.querySelectorAll(".topnav-link")],
  pages: {
    dashboard: document.getElementById("dashboardPage"),
    news: document.getElementById("newsPage"),
    chart: document.getElementById("chartPage"),
  },
  heroSymbol: document.getElementById("heroSymbol"),
  heroInterval: document.getElementById("heroInterval"),
  heroMode: document.getElementById("heroMode"),
  newsBiasValue: document.getElementById("newsBiasValue"),
  newsImpactValue: document.getElementById("newsImpactValue"),
  overviewTitle: document.getElementById("overviewTitle"),
  overviewTradingView: document.getElementById("overviewTradingView"),
  overviewTimeframe: document.getElementById("overviewTimeframe"),
  overviewMode: document.getElementById("overviewMode"),
  overviewNewsBias: document.getElementById("overviewNewsBias"),
  overviewEvents: document.getElementById("overviewEvents"),
  analysisState: document.getElementById("analysisState"),
  analysisContent: document.getElementById("analysisContent"),
  newsPreview: document.getElementById("newsPreview"),
  newsDeskList: document.getElementById("newsDeskList"),
  eventDeskList: document.getElementById("eventDeskList"),
  tiltCards: [...document.querySelectorAll(".tilt-card")],
  revealItems: [...document.querySelectorAll(".reveal")],
  heroPanel: document.querySelector(".hero-panel"),
  petCompanion: document.getElementById("petCompanion"),
  petSummon: document.getElementById("petSummon"),
};

function setPage(page) {
  Object.entries(els.pages).forEach(([key, el]) => el.classList.toggle("active", key === page));
  els.navButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.page === page));
}

function updateHero(modeLabel) {
  if (els.heroSymbol) els.heroSymbol.textContent = state.symbol;
  if (els.heroInterval) els.heroInterval.textContent = state.timeframe;
  if (els.heroMode) els.heroMode.textContent = modeLabel;
  if (els.overviewTitle) els.overviewTitle.textContent = state.symbol;
  if (els.overviewTradingView) els.overviewTradingView.textContent = state.symbolTv;
  if (els.overviewTimeframe) els.overviewTimeframe.textContent = state.timeframe;
  if (els.overviewMode) els.overviewMode.textContent = modeLabel;
}

function badgeColor(sentiment) {
  if (sentiment === "positive") return "var(--green)";
  if (sentiment === "negative") return "var(--red)";
  return "var(--amber)";
}

function renderNewsCard(item) {
  const color = badgeColor(item.sentiment);
  return `
    <article class="news-card">
      <div class="news-top">
        <div class="news-badges">
          <span style="border-color:${color}55;color:${color};">${(item.sentiment || "neutral").toUpperCase()}</span>
          <span>${item.impact_label || "Low"} Impact</span>
        </div>
        <div class="news-meta">${item.published || "Recent"}</div>
      </div>
      <h4>${item.title || ""}</h4>
      <p>${(item.description || "").slice(0, 220)}</p>
      <div class="news-bottom">
        <span>${item.source || "News"}</span>
        <a href="${item.url || "#"}" target="_blank" rel="noreferrer">Open Source</a>
      </div>
    </article>
  `;
}

function renderEventCard(item) {
  const color = item.impact_label === "High" ? "var(--red)" : item.impact_label === "Medium" ? "var(--amber)" : "var(--cyan)";
  return `
    <article class="event-card">
      <div class="event-top">
        <div>
          <div class="eyebrow">${item.country || ""} · ${item.currency || ""}</div>
          <h4>${item.title || ""}</h4>
        </div>
        <div class="countdown-chip" style="border-color:${color};color:${color};">${item.countdown || ""}</div>
      </div>
      <div class="event-grid">
        <div><span>Impact</span><strong>${item.impact_label || ""}</strong></div>
        <div><span>Time</span><strong>${item.time_label || ""}</strong></div>
        <div><span>Forecast</span><strong>${item.forecast || "N/A"}</strong></div>
        <div><span>Previous</span><strong>${item.previous || "N/A"}</strong></div>
      </div>
      <p>${item.effect_on_symbol || ""}</p>
    </article>
  `;
}

function renderMarketIntel(payload) {
  const news = payload.news || [];
  const events = payload.events || [];
  const summary = payload.news_summary || {};
  state.symbolTv = payload.symbol_tv || state.symbolTv;
  els.newsBiasValue.textContent = (summary.sentiment || "neutral").toUpperCase();
  els.newsImpactValue.textContent = summary.impact_label || "Unknown";
  els.overviewNewsBias.textContent = (summary.sentiment || "neutral").toUpperCase();
  els.overviewEvents.textContent = String(events.length);
  els.newsPreview.innerHTML = news.slice(0, 3).map(renderNewsCard).join("") || `<div class="placeholder-state">لا توجد أخبار موثوقة الآن.</div>`;
  els.newsDeskList.innerHTML = news.map(renderNewsCard).join("") || `<div class="placeholder-state">لا توجد أخبار موثوقة الآن.</div>`;
  els.eventDeskList.innerHTML = events.map(renderEventCard).join("") || `<div class="placeholder-state">لا توجد أحداث مهمة محملة الآن.</div>`;
  renderTradingView("tradingviewChart", state.symbolTv, window.innerWidth < 1100 ? 520 : 700);
  renderTradingView("fullTradingviewChart", state.symbolTv, window.innerWidth < 1100 ? 620 : 920);
}

function renderAnalysis(result) {
  const accent = result.decision === "BUY" ? "var(--green)" : result.decision === "SELL" ? "var(--red)" : "var(--amber)";
  const metrics = [
    ["Bias", result.bias],
    ["Entry", result.entry],
    ["Entry Zone", result.entry_zone],
    ["Stop Loss", result.sl],
    ["Take Profit", result.tp],
    ["Risk/Reward", `1:${result.rr}`],
    ["Confidence", `${result.confidence}%`],
    ["Confluence", result.confluence_score],
  ];
  const detailCards = (result.details || []).map((item) => {
    const color = item.direction === "bullish" ? "var(--green)" : item.direction === "bearish" ? "var(--red)" : "var(--amber)";
    return `
      <article class="detail-card">
        <div class="detail-top">
          <strong>${item.signal}</strong>
          <span class="detail-badge" style="border-color:${color};color:${color};">${item.direction}</span>
        </div>
        <p>${item.desc}</p>
        <div class="detail-meter"><span style="width:${Math.max(8, item.strength || 0)}%;background:${color};"></span></div>
      </article>
    `;
  }).join("");

  els.analysisState.classList.add("hidden");
  els.analysisContent.classList.remove("hidden");
  els.analysisContent.innerHTML = `
    <section class="analysis-header">
      <div class="signal-headline">
        <div class="eyebrow">${result.mode_title} Analysis</div>
        <div class="signal-action" style="color:${accent};">${result.decision}</div>
        <p>${result.strategy_focus || ""}</p>
      </div>
      <div class="signal-meta-grid">
        ${metrics.slice(0, 4).map(([label, value]) => `<div class="metric-card"><span>${label}</span><strong>${value}</strong></div>`).join("")}
      </div>
    </section>
    <section class="signal-summary">
      <div class="eyebrow">Trade Plan</div>
      <p>${result.reason}</p>
      <div class="signal-meta-grid" style="margin-top:12px;">
        ${metrics.slice(4).map(([label, value]) => `<div class="metric-card"><span>${label}</span><strong>${value}</strong></div>`).join("")}
      </div>
      <div class="metric-card" style="margin-top:12px;"><span>Invalidation</span><strong>${result.invalidations}</strong></div>
      <div class="metric-card" style="margin-top:12px;"><span>TP/SL Logic</span><strong>${result.tp_sl_rationale}</strong></div>
    </section>
    <section class="detail-list" style="margin-top:16px;">${detailCards}</section>
  `;
}

function initRevealAnimations() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    },
    { threshold: 0.15 }
  );

  els.revealItems.forEach((item) => observer.observe(item));
}

function initTiltCards() {
  els.tiltCards.forEach((card) => {
    card.addEventListener("mousemove", (event) => {
      const rect = card.getBoundingClientRect();
      const px = (event.clientX - rect.left) / rect.width;
      const py = (event.clientY - rect.top) / rect.height;
      const rotateY = (px - 0.5) * 12;
      const rotateX = (0.5 - py) * 10;
      card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg) translateY(0)";
    });
  });
}

function initHeroParallax() {
  document.addEventListener("mousemove", (event) => {
    state.mouseX = (event.clientX / window.innerWidth - 0.5) * 12;
    state.mouseY = (event.clientY / window.innerHeight - 0.5) * 12;
    if (els.heroPanel) {
      els.heroPanel.style.transform = `translate3d(${state.mouseX * 0.15}px, ${state.mouseY * 0.12}px, 0)`;
    }
  });
}

function initPetCompanion() {}

function renderTradingView(containerId, symbolTv, height) {
  const host = document.getElementById(containerId);
  if (!host) return;
  const interval = mapInterval(state.timeframe);
  const src = buildTradingViewEmbedUrl(symbolTv, interval, height);
  host.innerHTML = `
    <iframe
      src="${src}"
      title="TradingView Chart"
      loading="lazy"
      allowtransparency="true"
      frameborder="0"
      scrolling="no"
      style="width:100%;height:${height}px;border:0;display:block;"
    ></iframe>
  `;
}

function mapInterval(interval) {
  const map = { "1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1D": "D" };
  return map[interval] || "60";
}

function buildTradingViewEmbedUrl(symbolTv, interval, height) {
  const params = new URLSearchParams({
    symbol: symbolTv,
    interval,
    hidetoptoolbar: "0",
    hidelegend: "0",
    hidesidetoolbar: "0",
    symboledit: "1",
    saveimage: "1",
    toolbarbg: "0f170f",
    theme: "dark",
    style: "1",
    timezone: "Etc/UTC",
    withdateranges: "1",
    details: "1",
    hotlist: "0",
    calendar: "0",
    studies: '["RSI@tv-basicstudies","MACD@tv-basicstudies"]',
  });

  return `https://s.tradingview.com/widgetembed/?frameElementId=${encodeURIComponent(`tv_${symbolTv}_${interval}`)}&${params.toString()}`;
}

async function loadMarketIntel() {
  const url = `${window.APP_CONFIG.marketIntelUrl}?symbol=${encodeURIComponent(state.symbol)}`;
  const res = await fetch(url);
  const data = await res.json();
  renderMarketIntel(data);
}

async function analyzeNow() {
  els.analyzeButton.disabled = true;
  els.analyzeButton.textContent = "جاري التحليل...";
  try {
    const res = await fetch(window.APP_CONFIG.analyzeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: state.symbol, timeframe: state.timeframe, mode: state.mode }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Failed");
    renderAnalysis(data.result);
  } catch (err) {
    els.analysisState.classList.remove("hidden");
    els.analysisContent.classList.add("hidden");
    els.analysisState.textContent = err.message || "فشل تنفيذ التحليل.";
  } finally {
    els.analyzeButton.disabled = false;
    els.analyzeButton.textContent = "حلل الآن";
  }
}

async function bootstrap() {
  const res = await fetch(window.APP_CONFIG.bootstrapUrl);
  const data = await res.json();
  state.bootstrap = data;
  state.symbol = data.selected_symbol;
  state.timeframe = data.selected_timeframe;
  state.mode = data.selected_mode;
  state.symbolTv = data.symbol_tv;
  els.symbolSelect.value = state.symbol;
  els.timeframeSelect.value = state.timeframe;
  const modeLabel = data.modes[state.mode].label;
  updateHero(modeLabel);
  renderMarketIntel(data);
}

els.symbolSelect.addEventListener("change", async (e) => {
  state.symbol = e.target.value;
  updateHero(state.bootstrap?.modes?.[state.mode]?.label || state.mode);
  await loadMarketIntel();
});

els.timeframeSelect.addEventListener("change", (e) => {
  state.timeframe = e.target.value;
  updateHero(state.bootstrap?.modes?.[state.mode]?.label || state.mode);
  renderTradingView("tradingviewChart", state.symbolTv, window.innerWidth < 1100 ? 520 : 700);
  renderTradingView("fullTradingviewChart", state.symbolTv, window.innerWidth < 1100 ? 620 : 920);
});

els.modePills.forEach((btn) => {
  btn.addEventListener("click", () => {
    els.modePills.forEach((pill) => pill.classList.remove("active"));
    btn.classList.add("active");
    state.mode = btn.dataset.mode;
    const label = state.bootstrap?.modes?.[state.mode]?.label || state.mode;
    updateHero(label);
    els.overviewMode.textContent = label;
  });
});

els.navButtons.forEach((btn) => btn.addEventListener("click", () => setPage(btn.dataset.page)));
els.analyzeButton.addEventListener("click", analyzeNow);

(async function init() {
  initRevealAnimations();
  initTiltCards();
  initHeroParallax();
  initPetCompanion();
  await bootstrap();
})();
