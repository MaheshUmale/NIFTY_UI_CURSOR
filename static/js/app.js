const tickHistory = { labels: [], prices: [], volumes: [], maxPoints: 200 };
const signals = [];
const MAX_SIGNALS = 50;
const logLines = [];
const MAX_LOG = 80;

let chart;

document.addEventListener('DOMContentLoaded', () => {
  initChart();
  bindControls();
  initWs();
  loadInitialStatus();
});

function bindControls() {
  document.getElementById('connectBtn').addEventListener('click', connectUpstox);
  document.getElementById('disconnectBtn').addEventListener('click', disconnectUpstox);
  document.getElementById('simTickBtn').addEventListener('click', simulateTick);
  document.getElementById('simBurstBtn').addEventListener('click', simulateMultiple);
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
    tickHistory.maxPoints = pts === Infinity ? 999999 : pts;
    if (tickHistory.labels.length > tickHistory.maxPoints) {
      const trim = tickHistory.labels.length - tickHistory.maxPoints;
      tickHistory.labels.splice(0, trim);
      tickHistory.prices.splice(0, trim);
      tickHistory.volumes.splice(0, trim);
    }
    updateChart();
  });
}

function initChart() {
  const ctx = document.getElementById('priceChart').getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 280);
  grad.addColorStop(0, 'rgba(59,130,246,0.18)');
  grad.addColorStop(1, 'rgba(59,130,246,0.0)');
  chart = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [{
      label: 'Price', data: [], borderColor: '#3b82f6', backgroundColor: grad,
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
  new Chart(document.getElementById('volumeChart').getContext('2d'), {
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

async function simulateTick() {
  const sym = document.getElementById('simSym').value || 'NSE_INDEX|NIFTY 50';
  const price = parseFloat(document.getElementById('simPrice').value) || 24500 + Math.random() * 200;
  const oi = parseInt(document.getElementById('simOI').value) || 50000 + Math.floor(Math.random() * 5000);
  try {
    const r = await fetch('/api/simulate_tick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instrument_key: sym, symbol: sym.split('|').pop(), last_price: price, volume: 1000 + Math.floor(Math.random() * 5000), oi }),
    });
    if (r.ok) addLog('info', `Simulated tick: ${sym.split('|').pop()} @ ${price.toFixed(2)}`);
  } catch (e) {
    addLog('error', 'Simulate error: ' + e.message);
  }
}

async function simulateMultiple() {
  const sym = 'NSE_INDEX|NIFTY 50';
  addLog('info', 'Simulating 10 ticks...');
  for (let i = 0; i < 10; i++) {
    const price = 24500 + (Math.random() - 0.5) * 400;
    const oi = 50000 + Math.floor(Math.random() * 10000);
    try {
      await fetch('/api/simulate_tick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instrument_key: sym, symbol: 'NIFTY', last_price: price, volume: 1000 + Math.floor(Math.random() * 5000), oi }),
      });
    } catch { /* ignore */ }
    await new Promise(r => setTimeout(r, 100));
  }
  addLog('info', '10 ticks simulated');
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
  const sym = tick.symbol || tick.instrument_key || 'UNKNOWN';
  const price = Number(tick.last_price);
  if (!isFinite(price)) {
    addLog('warn', `Bad tick skipped: missing last_price — ${JSON.stringify(tick).slice(0, 120)}`);
    return;
  }
  const prev = tickHistory.prices.length ? tickHistory.prices[tickHistory.prices.length - 1] : price;
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
  updateChart();
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
    list.innerHTML = `<div class="empty-state"><span class="big-icon">📡</span>No signals — simulate a tick or connect live data</div>`;
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

function updateChart() {
  if (!chart) return;
  chart.data.labels = tickHistory.labels;
  chart.data.datasets[0].data = tickHistory.prices;
  chart.data.datasets[1] && (chart.data.datasets[1].data = tickHistory.volumes);
  chart.update('none');
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
