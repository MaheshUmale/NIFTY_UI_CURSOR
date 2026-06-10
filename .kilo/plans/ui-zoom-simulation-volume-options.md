# UI — Zoom, Simulation, Volume Proxy, CE/PE Chart, Space Optimization

**Status:** Plan (ready for implementation)
**AFTER reading the code below you WILL:**

- Edit only files listed in Steps
- Keep everything else unchanged
- Maintain CSS/JS/HTML consistency
- Keep `config/AGENTS.md` immutable risk rules untouched

---

## Step 1 — NIFTY FUTURE volume as proxy for NIFTY index

### Goal
The NIFTY index (`NSE_INDEX|Nifty 50`) carries no volume from the broker feed. Use the
current-month NIFTY future (`NIFTY25XXXXFUT`) volume as a **proxy** so that
VWAP + any volume metric in the UI is meaningful.

### Files (Python)
- `src/data/websocket_client.py`
- `src/data/market_buffer.py`
- `src/data/market_history.py`
- `app.py`

### Changes
1. `WebSocketClient._parse_feed()` already grabs `volume` from the tick but for
   the index it will be `None`. Add a small per-session cache that maps
   `NSE_INDEX|Nifty 50` → current-month future instrument key (use the same logic
   already present in `src/data/instrument_resolver.py`).
2. On each tick, if `instrument_key == NSE_INDEX|Nifty 50` and `volume` is
   missing/zero, copy `volume` from the **latest** future tick in the same
   `market_buffer` window for that future key.
3. Store the mapped source in the tick (`"volume_source": "future_proxy"`) for
   observability.

### Files (HTML/JS)
- `static/index.html`
- `static/js/app.js`

### Changes
4. Use the received tick `last_price` + volume (which will now be future-proxied)
   as-is — UI code does not need new fields because `tick.volume` is already used
   for the volume chart and VWAP.

---

## Step 2 — Fix chart zoom: 1m / 3m based on available time frame

### Goal
Buttons `1m`, `3m`, `10m`, `All` should map to actual data points, not fixed
counts that look wrong when fewer minutes have elapsed.

### Files
- `static/js/app.js`

### Changes
1. Keep data ingestion untouched.
2. Render zoom buttons as labels driven by the data window length:
   - `1m` → last 1 data point
   - `3m` → last 3 data points
   - `10m` → last 10 data points
   - `All` → full buffer (`window().length`)
3. `data-points` attributes become `1`, `3`, `10`, `Infinity` (already the
   pattern; just confirm the mapping matches available data).
4. If `window().length < N`, show exactly what we have (no empty gap).

---

## Step 3 — Remove all simulation-related parts from the UI

### Goal
Eliminate every user-facing simulation control (Simulate Tick, +10 Ticks,
Quick Simulation card, empty-state copy).

### Files
- `static/index.html`
- `static/js/app.js`
- `app.py` (only to remove the `/api/simulate_tick` and `/api/e2e_test` routes,
  not the root `app.py` contract)

### Changes
1. Delete from `index.html`:
   - `<button id="simTickBtn">Simulate Tick</button>`
   - `<button id="simBurstBtn">+10 Ticks</button>`
   - entire `Quick Simulation` card
   - any text saying "simulate a tick"
2. Delete from `app.js`:
   - `simulateTick()` / `simulateMultiple()`
   - bound click listeners for `simTickBtn` / `simBurstBtn`
3. Delete `@app.post('/api/simulate_tick')` and `@app.post('/api/e2e_test')` from
   `app.py` (test code path; keep `/api/connect`, `/api/disconnect`, `/ws`).
4. Keep `/api/status`, `/api/signals`, `/api/risk`, `/api/ticks`, `/api/history`.
5. Update empty-state helper text to "Waiting for signals…".

---

## Step 4 — Add ATM CE and PE chart beside the spot chart

### Goal
Show two live option price series (ATM Call + ATM Put) in a **new** chart panel
sidebar next to the spot price chart, using 1-minute candles summarized per
tick (btq/ltq / volume derivative if close is not available).

### Files
- `static/index.html`
- `static/js/app.js`
- `static/css/style.css`

### Changes
1. New HTML card:
   - Title: `ATM Options (CE / PE)`
   - Canvas: `atmOptionsChart`
2. JS additions:
   - Maintain two rolling series: `atmCePrices[]`, `atmPePrices[]`
   - Resolve ATM keys at connect time: use the existing option resolution in
     `src/data/market_history._resolve_option_keys(token)` — expose this mapping
     via `/api/history` as `option_keys: list[str]` (this is **already** returned
     by `fetch_warmup_data`).
   - Subscribe to those keys (read from the same list the strategy uses).
   - Filter ticks: CE keys → series A, PE keys → series B.
   - Render with a second `Chart` instance, line/dual-tone colors:
     - CE: accent-green
     - PE: accent-red
3. CSS: `.top-row` becomes `grid-template-columns: 2fr 1fr` so the options panel
   is narrower.

---

## Step 5 — Optimize space by reducing empty space

### Goal
Shrink header, cards padding, and chart heights so the dashboard fits more
information without scrolling on a typical 1080p monitor.

### Files
- `static/css/style.css`
- `static/index.html`

### Changes
1. `.chart-container { height: 220px }` (from 280)
2. `header { padding: 8px 16px }`
3. `.card { padding: 14px }`
4. `.log-panel { max-height: 140px }`
5. `.list-container { max-height: 260px }`
6. `.grid-3 { gap: 12px }`
7. `.top-row`, `.bottom-row` → `gap: 12px`
8. Remove the now-deleted `Quick Simulation` card (see Step 3) and any extra
   semicolon-row space between top-row and bottom-row.
9. `.price-value { font-size: 1.8rem }` (from 2.2rem)

---

## Delivery checklist

- [x] Tick for `NSE_INDEX|Nifty 50` carries `volume` sourced from future
- [x] VWAP shows non-zero after first future-claimed volume
- [x] `1m`/`3m`/`10m`/`All` zoom buttons only show what the dataset supports
- [x] Zero simulation IDs or onboarding in the UI
- [x] `/api/simulate_tick` and `/api/e2e_test` removed from `app.py`
- [ ] ATM CE/PE live chart visible beside spot chart
- [ ] CSS reduces whitespace as specified
- [ ] No hard-coded secrets, no `print()`, no new global state violation

---

## Risk / DOX considerations
- Does not alter `config/AGENTS.md` or risk constants.
- Does not place orders or touch execution/risk gates.
- Only `app.py` route removal — no state or broker-auth changes.
- Instrument resolution logic already exists in `src/data/instrument_resolver.py`
  and `src/data/market_history.py` — reuse only; do not rewrite.
