# Follow-Up Task List — Verification & Enhancements

**Status:** A4 and A5 completed — ready to verify
**Created by:** Kilo session ending at 2026-06-10T15:33:36+05:30
**Base commit:** b218db4

---

## Section A — Hard Verification (blockers before calling UI complete)

### Task A1 — Prove option keys are being subscribed
**Owner:** backend/data
**Files:** `app.py`, `src/data/market_history.py`
**Steps:**
1. Restart server with fresh `.env` token.
2. Hit `/api/status` and confirm `connected=true`, `tick_count` increasing.
3. Hit `/api/ticks` and list instrument keys.
4. **Pass condition:** more than 2 keys appear (spot + future + >=2 option keys).
5. Run `tests/ExtractInstrumentKeys.py` manually with a fresh token and confirm it prints a non-empty instrument list.

### Task A2 — Prove ATM CE/PE ticks reach buffer and UI
**Owner:** backend/data + UI
**Files:** `src/data/market_buffer.py`, `static/js/app.js`
**Steps:**
1. Capture 30 seconds of ticks via `/api/ticks`.
2. Filter keys containing `|CE` or `|PE` and confirm they exist.
3. Open dashboard; confirm ATM Options chart renders (non-flat line) after a few seconds.
4. If no option ticks: check Upstox feed mode (`full` vs `ltpc`) and instrument-key casing in `src/data/websocket_client.py`.

### Task A3 — Prove volume proxy works for NIFTY index
**Owner:** backend/data
**Files:** `app.py`, `src/data/market_buffer.py`
**Steps:**
1. Subscribe with future + index keys.
2. On each `NSE_INDEX|Nifty 50` tick, assert `volume > 0` or `volume_source == "future_proxy"`.
3. In UI, confirm Volume / OI chart shows non-zero bars after first proxied tick.

### Task A4 — Prove zoom buttons behave correctly
**Owner:** UI
**Files:** `static/js/app.js`, `static/index.html`
**Status:** ✅ Completed
**Steps:**
1. With < 10 data points loaded, click `10m` and `All` — chart must render all points, no empty gap.
2. Resize window below 900px — default zoom must fall back to 3 points.
3. Log must not throw JS errors on these interactions.

### Task A5 — Prove simulation routes are gone
**Owner:** backend + UI
**Files:** `app.py`, `static/index.html`, `static/js/app.js`
**Status:** ✅ Completed
**Steps:**
1. `grep -r "simulate_tick|simulateTick|simulateMultiple|Quick Simulation" static/ app.py` → zero matches.
2. `grep -r "/api/e2e_test\|/api/simulate_tick" app.py` → zero matches.
3. `/api/status` and `/` must still return 200.

---

## Section B — Enhancements (ordered by value)

### Task B1 — Dynamic ATM roll-over at expiry
**Owner:** backend/data
**Files:** `src/data/market_history.py`
**Description:** When nearest expiry passes, automatically shift to next expiry. Add a cached `nearest_expiry_date` and a daily check at 09:15 IST.

### Task B2 — Strike width validation & config
**Owner:** backend/data
**Files:** `config/AGENTS.md` or new `config/strategy_params.yaml`
**Description:** Make ATM ± 3 a configurable parameter. Validate that selected strikes are evenly spaced and within trading bounds.

### Task B3 — Volume proxy metrics in UI
**Owner:** UI
**Files:** `static/index.html`, `static/js/app.js`
**Description:** Show `volume_source` badge (index vs future-proxy) and last-proxied volume timestamp for transparency.

### Task B4 — Option chain depth selector
**Owner:** UI + backend
**Files:** `static/js/app.js`, `app.py`
**Description:** Add a dropdown to switch between ATM ± 1, ± 2, ± 3 strikes on the ATM Options chart. Keep future volume proxy unchanged.

### Task B5 — Connection health indicator
**Owner:** UI
**Files:** `static/index.html`, `static/js/app.js`
**Description:** Show last tick age (seconds since last update). Turn status badge yellow if > 5s, red if > 15s. Uses existing WebSocket `ts` field.

### Task B6 — Error telemetry for failed ATM resolution
**Owner:** backend
**Files:** `app.py`, `src/data/market_history.py`
**Description:** When `resolve_option_keys_for_history()` fails, surface the error to the UI via `/api/status` `error_message` so the dashboard shows actionable feedback.

### Task B7 — Unit tests for volume proxy & option resolution
**Owner:** tests
**Files:** `tests/`
**Description:**
- `test_volume_proxy.py`: mock `MarketBuffer.latest_for()` and assert index tick gets volume copied.
- `test_option_resolution.py`: mock instrument master DataFrame and assert ATM ± 3 keys are returned.

---

## Section C — DOX / housekeeping (do after verification passes)

1. Do not update `config/AGENTS.md` unless a new config boundary is added (only needed if B2/B6 land).
2. Update `src/data/AGENTS.md` only if resolver ownership changes again.
3. Add new task list file under `.kilo/plans/` with naming convention:
   - `YYYY-MM-DD-slug.md`

---

## Execution rules for next session

- Read `.kilo/plans/ui-zoom-simulation-volume-options.md` and this file before editing.
- Work Section A tasks in order; each task is a commit-sized unit.
- Use `/local-review-uncommitted` after every non-trivial file change batch.
- Do not remove or rename existing tests without explicit confirmation.
- Keep `config/AGENTS.md` immutable risk rules untouched.
