const tickHistory = { labels: [], prices: [], volumes: [], maxPoints: 10 };
const atmHistory = { labels: [], ce: [], pe: [], maxPoints: 10 };
const signals = [];
const MAX_SIGNALS = 50;
const logLines = [];
const MAX_LOG = 80;

let priceChart;
let volumeChart;
let atmOptionsChart;

document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  bindControls();
  initWs();
  loadInitialStatus();
});

function bindControls() {
  document.getElementById('connectBtn').addEventListener('click', connectUpstox);
  document.getElementById('disconnectBtn').addEventListener('click', disconnectUpstox);
  document.getElementById('clearLogsBtn').addEventListener('click', clearLogs);
  document.getElementById('clearSignalsBtn').addEventListener('click', () => { signals.length = 0; renderSignals(); });
  document.getElementById('chartZoomControls').addEventListener('click', (e) => {
    if (!e.target.classList.contains('chart-zoom-btn')) return;
    document.querySelectorAll('.chart-zoom-btn').forEach(b => {
      b.style.color = ''; b.style.borderColor = ''; b.classList.remove('active');
    });
    e.target.style.color = 'var(--accent-blue)';
    e.target.style.borderColor = 'var(--accent-blue)';
    e.target.classList.add('active');
    const pts = parseInt(e.target.dataset.points);
    const maxPoints = Number.isFinite(pts) ? pts : null;
    trimChart(tickHistory, maxPoints);
    trimChart(atmHistory, maxPoints);
    updateCharts();
  });

  setZoomFromWindow(tickHistory);
  setZoomFromWindow(atmHistory);
  window.addEventListener('resize', () => {
    setZoomFromWindow(tickHistory);
    setZoomFromWindow(atmHistory);
    updateCharts();
  });
  loadInitialHistory();
}

function trimChart(history, maxPoints) {
  const len = history.labels.length;
  if (!Number.isFinite(maxPoints) || maxPoints <= 0) {
    return;
  }
  if (len > maxPoints) {
    const trim = len - maxPoints;
    history.labels.splice(0, trim);
    history.prices.splice(0, trim);
    history.volumes.splice(0, trim);
    history.ce.splice(0, trim);
    history.pe.splice(0, trim);
  }
}

function setZoomFromWindow(history) {
  const maxWidth = window.innerWidth || 1400;
  if (maxWidth <= 900) {
    history.maxPoints = 3;
  } else if (maxWidth <= 1100) {
    history.maxPoints = 5;
  } else {
    history.maxPoints = 10;
  }
  trimChart(history, history.maxPoints);
}

async function loadInitialHistory() {
  try {
    const r = await fetch('/api/history');
    const data = await r.json();
    const rows = Array.isArray(data?.ohlcv) ? data.ohlcv : [];
    if (!rows.length) return;
    const labels = [];
    const prices = [];
    const volumes = [];
    for (const row of rows) {
      const ts = row?.timestamp || '';
      const price = row?.close ?? row?.last_price ?? row?.open ?? 0;
      const vol = Number(row?.volume || 0);
      if (!ts || !price) continue;
      labels.push(ts);
      prices.push(price);
      volumes.push(vol);
    }
    tickHistory.labels = labels;
    tickHistory.prices = prices;
    tickHistory.volumes = volumes;
    setZoomFromWindow(tickHistory);
    updateCharts();
  } catch (e) {
    addLog('error', 'History load failed: ' + (e?.message || e));
  }
}

function initCharts() {
  const priceCtx = document.getElementById('priceChart').getContext('2d');
  const priceGrad = priceCtx.createLinearGradient(0, 0, 0, 220);
  priceGrad.addColorStop(0, 'rgba(59,130,246,0.18)');
  priceGrad.addColorStop(1, 'rgba(59,130,246,0.0)');
  priceChart = new Chart(priceCtx, {
    type: 'line',
    data: { labels: [], datasets: [{
      label: 'Price', data: [], borderColor: '#3b82f6', backgroundColor: priceGrad,
      borderWidth: 2, fill: true, tension: 0.25, pointRadius: 0, pointHitRadius: 8,
    }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1e2130', borderColor: '#2e3345', borderWidth: 1,
          titleColor: '#9aa0b2', bodyColor: '#e8eaed',
          bodyFont: { family: 'JetBrains Mono, monospace', size: 13 }, padding: 10,
          callbacks: { label: (c) => 'Price: ' + c.parsed.y.toFixed(2) },
        },
      },
      scales: {
        x: {
          display: true,
          ticks: { color: '#6b7280', font: { size: 10, family: 'JetBrains Mono' }, maxTicksLimit: 8, maxRotation: 0 },
          grid: { color: 'rgba(46,51,69,.5)' },
        },
        y: {
          display: true,
          ticks: { color: '#6b7280', font: { size: 10, family: 'JetBrains Mono' }, callback: v => v.toFixed(0) },
          grid: { color: 'rgba(46,51,69,.5)' },
        },
      },
    },
  });

  const volumeCtx = document.getElementById('volumeChart').getContext('2d');
  volumeChart = new Chart(volumeCtx, {
    type: 'bar',
    data: { labels: [], datasets: [{
      label: 'Volume', data: [], backgroundColor: 'rgba(139,92,246,.45)', borderColor: 'rgba(139,92,246,.7)', borderWidth: 1,
    }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          display: true,
          ticks: { color: '#6b7280', font: { size: 10, family: 'JetBrains Mono' }, maxTicksLimit: 8, maxRotation: 0 },
          grid: { color: 'rgba(46,51,69,.5)' },
        },
        y: {
          display: true,
          ticks: { color: '#6b7280', font: { size: 10, family: 'JetBrains Mono' }, callback: v => v >= 1000 ? (v/1000).toFixed(0)+'k' : v },
          grid: { color: 'rgba(46,51,69,.5)' },
        },
      },
    },
  });

  const atmCtx = document.getElementById('atmOptionsChart').getContext('2d');
  atmOptionsChart = new Chart(atmCtx, {
    type: 'line',
    data: { labels: [], datasets: [
      { label: 'ATM CE', data: [], borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,.12)', borderWidth: 2, fill: true, tension: 0.25, pointRadius: 0, pointHitRadius: 8 },
      { label: 'ATM PE', data: [], borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,.12)', borderWidth: 2, fill: true, tension: 0.25, pointRadius: 0, pointHitRadius: 8 },
    ] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: true, labels: { color: '#9aa0b2', font: { size: 11, family: 'JetBrains Mono' } } },
        tooltip: {
          backgroundColor: '#1e2130', borderColor: '#2e3345', borderWidth: 1,
          titleColor: '#9aa0b2', bodyColor: '#e8eaed',
          bodyFont: { family: 'JetBrains Mono, monospace', size: 13 }, padding: 10,
        },
      },
      scales: {
        x: {
          display: true,
          ticks: { color: '#6b7280', font: { size: 10, family: 'JetBrains Mono' }, maxTicksLimit: 8, maxRotation: 0 },
          grid: { color: 'rgba(46,51,69,.5)' },
        },
        y: {
          display: true,
          ticks: { color: '#6b7280', font: { size: 10, family: 'JetBrains Mono' }, callback: v => v.toFixed(0) },
          grid: { color: 'rgba(46,51,69,.5)' },
        },
      },
    },
  });
}

function updateCharts() {
  if (!priceChart || !volumeChart || !atmOptionsChart) return;
  priceChart.data.labels = tickHistory.labels;
  priceChart.data.datasets[0].data = tickHistory.prices;
  volumeChart.data.labels = tickHistory.labels;
  volumeChart.data.datasets[0].data = tickHistory.volumes;
  atmOptionsChart.data.labels = atmHistory.labels;
  atmOptionsChart.data.datasets[0].data = atmHistory.ce;
  atmOptionsChart.data.datasets[1].data = atmHistory.pe;
  priceChart.update('none');
  volumeChart.update('none');
  atmOptionsChart.update('none');
}

function initWs() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.onopen = () => addLog('info', 'WebSocket connected to server');
  ws.onclose = () => {
    addLog('warn', 'WebSocket closed');
    updateStatus('disconnected');
    document.getElementById('connectBtn').disabled = false;
    document.getElementById('disconnectBtn').disabled = true;
  };
  ws.onerror = () => { addLog('error', 'WebSocket error'); updateStatus('error'); };
  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    const ts = msg.ts ? new Date(msg.ts).toLocaleTimeString() : new Date().toLocaleTimeString();
    if (msg.type === 'status') handleStatus(msg.data);
    else if (msg.type === 'tick') handleTick(msg.data, ts);
    else if (msg.type === 'signal') handleSignal(msg.data, ts);
  };
}

async function loadInitialStatus() {
  try {
    const r = await fetch('/api/status');
    const data = await r.json();
    handleStatus(data);
  } catch (e) {
    addLog('error', 'Status load failed: ' + e.message);
  }
}

async function connectUpstox() {
  const token = document.getElementById('tokenInput').value.trim();
  if (!token) return addLog('error', 'Enter access token first');
  updateStatus('connecting');
  try {
    await fetch('/api/token', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ access_token: token }) });
    const conn = await fetch('/api/connect', { method: 'POST' });
    const data = await conn.json();
    if (!conn.ok) throw new Error(data.error || 'connect failed');
    addLog('info', 'Connection initiated...');
  } catch (e) {
    addLog('error', 'Connect error: ' + e.message);
    updateStatus('disconnected');
  }
}

async function disconnectUpstox() {
  try {
    await fetch('/api/disconnect', { method: 'POST' });
    addLog('warn', 'Disconnected');
    updateStatus('disconnected');
  } catch (e) {
    addLog('error', 'Disconnect error: ' + e.message);
  }
}

function updateStatus(state) {
  const badge = document.getElementById('statusBadge');
  badge.className = 'status-badge';
  if (state === 'connected') {
    badge.classList.add('status-connected');
    badge.innerHTML = '<span class="dot"></span>CONNECTED';
    document.getElementById('connectBtn').disabled = true;
    document.getElementById('disconnectBtn').disabled = false;
  } else if (state === 'connecting') {
    badge.innerHTML = '<span class="dot" style="animation-duration:.6s"></span>CONNECTING...';
    document.getElementById('connectBtn').disabled = true;
    document.getElementById('disconnectBtn').disabled = true;
    badge.style.cssText = 'background:rgba(59,130,246,.12);color:#3b82f6;border:1px solid rgba(59,130,246,.25)';
  } else if (state === 'error') {
    badge.classList.add('status-error');
    badge.innerHTML = '<span class="dot"></span>ERROR';
    document.getElementById('connectBtn').disabled = false;
    document.getElementById('disconnectBtn').disabled = true;
  } else {
    badge.classList.add('status-disconnected');
    badge.innerHTML = 'DISCONNECTED';
    document.getElementById('connectBtn').disabled = false;
    document.getElementById('disconnectBtn').disabled = true;
    badge.style.cssText = '';
  }
}

function handleStatus(data) {
  updateStatus(data.connected ? 'connected' : 'disconnected');
  const errEl = document.getElementById('errorBox');
  if (data.error_message) {
    errEl.style.display = 'block';
    errEl.textContent = data.error_message;
    updateStatus('error');
  } else {
    errEl.style.display = 'none';
  }
  document.getElementById('statTicks').textContent = formatNum(data.tick_count);
  document.getElementById('statTrades').textContent = data.daily_trades;
  const pnl = data.daily_pnl >= 0 ? '+' + data.daily_pnl.toFixed(2) : data.daily_pnl.toFixed(2);
  const pnlEl = document.getElementById('statPnl');
  pnlEl.textContent = pnl;
  pnlEl.className = 'risk-metric-value ' + (data.daily_pnl >= 0 ? 'price-up' : 'price-down');
  const ind = data.risk_status?.indicator || 'OK';
  document.getElementById('riskIndicator').textContent = ind;
  document.getElementById('riskIndicator').className = 'badge ' + (ind === 'OK' ? 'badge-ok' : ind === 'WARNING' ? 'badge-warn' : 'badge-crit');
  document.getElementById('riskDailyLoss').textContent = ((data.risk_status?.daily_loss_pct || 0) * 100).toFixed(2) + '%';
  document.getElementById('maxDailyLoss').textContent = ((data.risk_status?.max_daily_loss_pct || 0.04) * 100).toFixed(0) + '%';
  const tradeCt = data.risk_status?.trades_today ?? data.daily_trades ?? 0;
  document.getElementById('riskTrades').textContent = tradeCt + ' / ' + (data.risk_status?.max_trades_per_day || 3);
}

function handleTick(tick, ts) {
  const isNifty = tick.instrument_key === 'NSE_INDEX|Nifty 50';
  const isOption = tick.instrument_key.includes('CE') || tick.instrument_key.includes('PE');

  if (!isNifty && !isOption) return;

  const price = tick.last_price;
  if (!price) return;

  if (isNifty) {
    const sym = 'NIFTY 50';
    const closePrice = tick.close_price;
    const prev = closePrice || price;
    const diff = price - prev;
    const chgPct = prev ? ((diff / prev) * 100).toFixed(3) : '0.000';
    const sign = diff > 0 ? '+' : '';
    document.getElementById('lastSym').textContent = sym;
    const priceEl = document.getElementById('lastPrice');
    priceEl.textContent = price.toFixed(2);
    priceEl.previousElementSibling && (priceEl.previousElementSibling.textContent = sym);
    document.getElementById('priceChg').textContent = `${sign}${diff.toFixed(2)} (${sign}${chgPct}%)`;
    document.getElementById('priceChg').className = 'price-change ' + (diff > 0 ? 'price-up' : diff < 0 ? 'price-down' : 'price-flat');
    document.getElementById('lastOi').textContent = formatNum(tick.oi);
    document.getElementById('lastVol').textContent = formatNum(tick.volume);
    document.getElementById('lastTs').textContent = ts;
    const tickEl = document.getElementById('statTicks');
    tickEl.textContent = formatNum((parseInt(tickEl.textContent.replace(/,/g, '')) || 0) + 1);
    tickHistory.labels.push(ts);
    tickHistory.prices.push(price);
    tickHistory.volumes.push(tick.volume || 0);
    while (tickHistory.labels.length > tickHistory.maxPoints) {
      tickHistory.labels.shift();
      tickHistory.prices.shift();
      tickHistory.volumes.shift();
    }
  }

  if (isOption) {
    const side = tick.instrument_key.includes('CE') ? 'ce' : 'pe';
    atmHistory.labels.push(ts);
    atmHistory.ce.push(side === 'ce' ? price : (atmHistory.ce[atmHistory.ce.length - 1] || 0));
    atmHistory.pe.push(side === 'pe' ? price : (atmHistory.pe[atmHistory.pe.length - 1] || 0));
    while (atmHistory.labels.length > atmHistory.maxPoints) {
      atmHistory.labels.shift();
      atmHistory.ce.shift();
      atmHistory.pe.shift();
    }
    document.getElementById('atmBadge').textContent = tick.instrument_key.split('|').pop();
    document.getElementById('atmBadge').className = 'badge badge-neutral';
  }

  updateCharts();
}

function handleSignal(data, ts) {
  signals.unshift({
    symbol: data.symbol, side: data.side, entry_price: data.entry_price,
    target: data.target, stop_loss: data.stop_loss, confidence: data.confidence,
    bias: data.metadata?.window_status || data.tag || '', timestamp: ts, metadata: data.metadata,
  });
  if (signals.length > MAX_SIGNALS) signals.pop();
  renderSignals();
  addLog('signal', `⚡ ${data.side} ${data.symbol} @ ${data.entry_price.toFixed(2)} conf=${(data.confidence*100).toFixed(0)}%`);
}

function renderSignals() {
  const list = document.getElementById('signalList');
  if (!signals.length) {
    list.innerHTML = `<div class="empty-state"><span class="big-icon">📡</span>No signals — connect live data</div>`;
    return;
  }
  list.innerHTML = signals.map(s => {
    const cls = s.side === 'LONG' ? 'long' : 'short';
    const bg = s.confidence >= 0.8 ? 'rgba(16,185,129,.2);color:#10b981;border:1px solid rgba(16,185,129,.4)' :
               s.confidence >= 0.6 ? 'rgba(245,158,11,.2);color:#f59e0b;border:1px solid rgba(245,158,11,.4)' :
               'rgba(239,68,68,.2);color:#ef4444;border:1px solid rgba(239,68,68,.4)';
    return `<div class="signal-item">
      <div class="signal-badge ${cls}" style="background:${bg.split(';')[0]};color:${bg.split(';')[1]};border:${bg.split(';')[2]}">${s.side.charAt(0)}</div>
      <div class="signal-info">
        <div class="signal-symbol">${escapeHtml(s.symbol)}</div>
        <div class="signal-meta">
          ${s.bias ? `<span>${escapeHtml(s.bias)}</span>` : ''}
          ${s.metadata?.vwap ? `<span>vwap: ${s.metadata.vwap.toFixed(2)}</span>` : ''}
          ${s.metadata?.pcr ? `<span>pcr: ${s.metadata.pcr.toFixed(2)}</span>` : ''}
        </div>
      </div>
      <div class="signal-prices">
        <div class="signal-price entry">E: ${s.entry_price.toFixed(2)}</div>
        <div class="signal-price sl">SL: ${s.stop_loss.toFixed(2)}</div>
        <div class="signal-price tp">TP: ${s.target.toFixed(2)}</div>
      </div>
    </div>`;
  }).join('');
}

function addLog(level, msg) {
  const t = new Date().toLocaleTimeString();
  logLines.push({ t, level, msg });
  if (logLines.length > MAX_LOG) logLines.shift();
  const list = document.getElementById('logList');
  const el = document.createElement('div');
  el.className = 'log-entry';
  el.innerHTML = `<span class="log-time">${t}</span><span class="log-msg ${level}">${escapeHtml(msg)}</span>`;
  list.prepend(el);
  while (list.children.length > MAX_LOG) list.lastChild.remove();
}

function clearLogs() {
  logLines.length = 0;
  document.getElementById('logList').innerHTML = '';
}

function formatNum(n) {
  if (n == null) return '-';
  return Number(n).toLocaleString();
}

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
