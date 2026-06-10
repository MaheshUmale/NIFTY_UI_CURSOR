# Purpose

Market data ingestion: Upstox daily instrument CSV loader, async WebSocket V3 client, and thread-safe ring buffer for the 7-strike ATM ± 3 window.

# Ownership

| File | Owner |
|------|-------|
| `__init__.py` | Upstox API Architect |
| `instrument_loader.py` | Upstox API Architect |
| `websocket_client.py` | Upstox API Architect |
| `market_buffer.py` | Strategy & Core Logic Engineer (consumer-facing) |

# Local Contracts

- **Strict zero-computation:** The ingestion module must execute ZERO math, ZERO averaging, ZERO indicator generation. Its sole responsibility is serialization, network transport, and ring-buffer writes.
- **Source of truth:** `ALL_DOCS/UPSTOX-api-docs.json` and `ALL_DOCS/deep-research-report_UPSTOX.md`.
- **Cache invariants:** Instrument CSV must be cached per UTC day. Re-download only on date change or cache miss.
- **7-strike window rule:** The buffer always exposes the strikes around ATM (configurable via `ATM_STRIKE_WINDOW`, default ±3 = 7 strikes) per subscribed instrument. Out-of-window strikes are dropped silently.
- **Forward-fill OI:** When the exchange OI packet is null (3–5 min lag), the buffer must forward-fill the last known OI rather than emit 0. The analyst engine relies on this to avoid divide-by-zero noise.
- **Async only:** The WebSocket client is `asyncio` based. It must register a single async tick handler. No blocking I/O on the event loop.

# Work Guidance

- **Token subscription at startup:** On boot, the module subscribes to:
  - `NSE_INDEX|Nifty 50` (spot)
  - `NSE_INDEX|Nifty Bank` (spot)
  - `NSE_FO|<atm-3>..<atm+3>` (options, dynamic)
- **Dynamic window shift:** When the analyst engine calls `buffer.shift_window(new_atm)`, the data module must request a re-subscribe to the new strike set. No silent drift.
- **Reconnection:** Exponential backoff: 1s → 2s → 4s → … → 30s. After 5 consecutive failures, raise `IngestionFatalError` and exit non-zero.
- **Backpressure:** If the ring buffer is full, drop the oldest tick and log a warning. Never block the WebSocket receive loop.

# Verification

- `test_instrument_loader.py` must cover:
  - Symbol → instrument_key resolution for NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY.
  - Nearest weekly/monthly expiry selection.
  - Cache hit/miss path.
- `test_market_buffer.py` must cover:
  - Forward-fill when OI is null.
  - Ring buffer overflow drops oldest.
  - Dynamic window shift preserves continuity.
- Latency SLO: WebSocket → buffer push must complete < 50 ms p99.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-modules are documented in the Ownership table above.
