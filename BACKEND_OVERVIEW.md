# NIFTY Trading System – Backend Overview

## Table of Contents
1. [Purpose](#purpose)
2. [Entry Point – `app.py`](#entry-point---apppy)
3. [Market Data Ingestion – `src/data/`](#market-data-ingestion---srcdata)
4. [Strategy Layer – `src/strategy/`](#strategy-layer---srcstrategy)
5. [Execution & Order Management – `src/execution/`](#execution--order-management---srcexecution)
6. [Risk Layer – `src/risk/`](#risk-layer---srcrisk)
7. [Configuration & Utilities – `config/` & `src/utils/`](#configuration--utilities---config--srcutils)
8. [Database / Persistence – `data/`](#database--persistence---data)
9. [Tests – `tests/`](#tests---tests)
10. [How to Run / Connect](#how-to-run-connect)
11. [External Interfaces Summary](#external-interfaces-summary)
12. [Sequence Diagrams (Textual)](#sequence-diagrams-textual)
13. [References to AGENTS.md Contracts](#references-to-agentsmd-contracts)
---

## Purpose

This document describes the **functions**, **features**, **interfaces**, and **connection patterns** of the NIFTY backend trading system.  
It is intended for developers, risk auditors, and DevOps who need to understand or extend the pipeline.

---

## Entry Point – `app.py`

| Aspect | Details |
|--------|---------|
| **Framework** | FastAPI (`app = FastAPI(...)`) |
| **Static assets** | Mounted at `/static` from `static/` directory |
| **Global state** | `AppState` dataclass (ticks, signals, positions, risk status, browser WebSocket clients) |
| **Lifecycle hooks** | `lifespan` context manager starts logger & ensures graceful shutdown |
| **REST endpoints** | `/api/status`, `/api/signals`, `/api/positions`, `/api/ticks`, `/api/risk`, `/api/token`, `/api/connect`, `/api/disconnect`, `/api/simulate_tick`, `/api/e2e_test` |
| **WebSocket endpoint** | `/ws` – pushes `tick`, `signal`, `status` messages to browsers |
| **External connections** | • Upstox WebSocket (`wss://ws.upstox.com/feed/market-data-feed/v3`)<br>• SQLite journal (`data/trade_journal.db`) |
| **Configuration** | Imports risk constants from `config/risk_constants.py` and strategy parameters from `config/strategy_config.py` |

---

## Market Data Ingestion – `src/data/`

### `websocket_client.py`

| Class / Function | Signature | Purpose |
|------------------|-----------|---------|
| `WebSocketClient` | `__init__(token, tick_handler, buffer)` | Async WS client for Upstox v3 feed |
| `connect()` | `async -> None` | Connects, handles exponential back-off (1→2→4→8→16→30s, max 5 attempts), re-subscribes on reconnect |
| `subscribe(instrument_keys)` | `async -> None` | Subscribes to symbols; queues if not yet connected |
| `disconnect()` | `async -> None` | Graceful close |
| `_on_message(raw)` | `async -> None` | Parses JSON, pushes to buffer, calls `tick_handler` |

**External Interface**
- **Token source**: `POST /api/token`
- **Instrument keys**: Default `NSE_INDEX|NIFTY 50`, `NSE_INDEX|NIFTY BANK`
- **Error handling**: Raises `IngestionFatalError` after 5 failed reconnects

### `market_buffer.py`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `push(tick)` | `None` | Adds tick to ring buffer; forward-fills missing OI |
| `latest()` | `dict \| None` | Returns most recent tick |
| `window(keys)` | `list[dict]` | Filters ticks by instrument keys |
| `shift_window(atm)` | `None` | Signals that a new ATM window should be subscribed |
| `is_window_shift_requested` | `bool` (clears flag) | Consumer checks this to trigger re-subscribe |
| `clear()` | `None` | Resets buffer and OI cache |

---

## Strategy Layer – `src/strategy/`

| Module | Key Class | Public Interface |
|--------|-----------|------------------|
| `signal_generator.py` | `SignalGenerator` | `on_tick(tick) -> Signal \| None` |
| `orb_strategy.py` | `ORBStrategy` | `update(tick)`, `check_breakout(tick, avg_volume) -> "LONG"/"SHORT"/None` |
| `vwap_engine.py` | `VWAPEngine` | `update(tick)`, `get_vwap(symbol) -> float` |
| `ema_filter.py` | `EMAFilter` | `update(symbol, price)`, `is_above_ema(symbol, price) -> bool` |
| `confluence.py` | `ConfluenceEngine` | `get_conviction(votes) -> "HIGH"/"MEDIUM"/"LOW"` |

**Signal dataclass**
```python
@dataclass
class Signal:
    symbol: str
    side: str                  # "LONG" or "SHORT"
    instrument_key: str
    entry_price: float
    stop_loss: float
    target: float
    qty: int                   # sized later by risk gate
    confidence: float
    timestamp: datetime
    metadata: dict[str, Any]
```

---

## Execution – Order Management – `src/execution/`

| File | Key Class / Function | Purpose |
|------|----------------------|---------|
| `order_manager.py` | `OrderManager.place_order(signal)`, `modify_order()`, `cancel_order()` | Wraps Upstox REST `/v2/orders`; enforces `ORDER_PRODUCT = "I"` (MIS) |
| `position_tracker.py` | `PositionTracker.add_position()`, `close_position()`, `get_open_positions()` | In-memory position book; updates daily P&L |
| `square_off.py` | `square_off_all()` | Flattens all positions at `FORCE_SQUARE_OFF_BY` (15:20 IST) |

**Error handling**
- Every `ApiException` is logged with `logger.exception(...)` and re-raised; never silently swallowed.

---

## Risk Layer – `src/risk/`

| Component | Responsibility |
|-----------|----------------|
| `risk_constants.py` (config) | Immutable rules: max daily loss 4 %, max risk/trade 2 %, max trades/day 3, entry cut 15:15, square-off 15:20, OI ≥ 50 k, slippage buffer 0.5 % |
| `risk_manager.py` (implied) | Receives `Signal`, checks against constants, returns `VETO` or `APPROVED` |
| `trade_journal.py` | SQLite insert of every order event |

---

## Configuration – `config/`

| File | Owner | Mutability |
|------|-------|------------|
| `risk_constants.py` | Risk Auditor | **IMMUTABLE** |
| `strategy_config.py` | Strategy Engineer | Tunable (weekly review) |
| `index_params.py` | Upstox API Architect | Hard-coded per broker contract |
| `.env` | Risk Auditor | Secrets only, git-ignored |

---

## Utilities – `src/utils/`

| Module | Purpose |
|--------|---------|
| `logger.py` | `get_logger(name)` – JSON-line formatted, rotating handlers |
| `time_utils.py` | `now_ist()`, `is_market_hours()` |
| `exception_handler.py` | `IngestionFatalError`, `wrap_requests_exception` |
| `constants.py` | Shared constants (e.g., `ORDER_PRODUCT`) |

---

## Database – `data/`

| Resource | Description |
|----------|-------------|
| `trade_journal.db` | SQLite (WAL mode) – schema in `data/schema_v1.sql`; stores order events for audit & back-test |
| `instrument_cache/` | Daily CSV download of Upstox instrument master (retained 7 days) |
| `cache/` | Optional Redis state (volatile) |

**Connection contract**
```python
conn = sqlite3.connect("data/trade_journal.db")
conn.execute("PRAGMA journal_mode = WAL")
```

---

## Tests – `tests/`

| Test File | Scope |
|-----------|-------|
| `test_risk_constants_invariants.py` | Asserts exact risk constant values |
| `test_risk_manager.py` | Risk gate logic |
| `test_trade_journal.py` | Journal DB operations |
| `test_logger.py` | Sensitive-field scrubbing, rotation |
| `test_e2e_live.py` | End-to-end pipeline via `TestClient` |
| `conftest.py` | Shared fixtures (`fake_access_token`, etc.) |

**Coverage gate**
```
pytest --cov=src --cov-fail-under=80
```

---

## How to Run / Connect

1. **Prerequisites**
   ```bash
   pip install -r requirements.txt
   ```
2. **Environment**
   ```bash
   cp config/.env.example config/.env
   # edit .env with UPSTOX_API_KEY, UPSTOX_API_SECRET, etc.
   ```
3. **Start server**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
4. **Set token**
   ```bash
   curl -X POST http://localhost:8000/api/token \
        -H "Content-Type: application/json" \
        -d '{"access_token":"<token>"}'
   ```
5. **Connect to Upstox**
   ```bash
   curl -X POST http://localhost:8000/api/connect
   ```
6. **Open dashboard**
   ```
   http://localhost:8000/
   ```
7. **Simulate tick (optional)**
   ```bash
   curl -X POST http://localhost:8000/api/simulate_tick \
        -H "Content-Type: application/json" \
        -d '{"symbol":"NIFTY","last_price":24500,"volume":1000,"oi":50000}'
   ```

---

## External Interfaces Summary

| Interface | Direction | Protocol | Endpoint |
|-----------|-----------|----------|----------|
| Upstox Market-Data WebSocket | Inbound | wss | `wss://ws.upstox.com/feed/market-data-feed/v3` |
| Upstox Order REST | Outbound | HTTPS/JSON | `https://api.upstox.com/v2/orders` |
| Front-end UI | Both | HTTP + WS | `http://localhost:8000/` & `/ws` |
| SQLite Journal | Local | File | `data/trade_journal.db` |
| Config / Secrets | Local | Files | `config/*.py`, `.env` |

---

## Sequence Diagrams (Textual)

### 1. Tick Flow
```
[Upstox WS] --> WebSocketClient.on_message --> MarketBuffer.push --> tick_handler --> SignalGenerator.on_tick
                                                                                     |
                                                                                     v
                                                                              ConfluenceEngine
                                                                                     |
                                                                                     v
                                                                    Signal --> RiskManager.check
                                                                                     |
                                                                                     v
                                                                               OrderManager.place_order
                                                                                     |
                                                                                     v
                                                                                 TradeJournal.log
```

### 2. EOD Square-Off
```
15:20 IST --> square_off_all() --> iterate open positions
                                           |
                                           v
                                  OrderManager.place_order("MARKET", EXIT)
                                           |
                                           v
                                  TradeJournal.update(closed_position)
```

---

## References to AGENTS.md Contracts

| Module | AGENTS.md Reference |
|--------|---------------------|
| `src/` | `src/AGENTS.md` – module-level contracts, logging, type hints |
| `src/data/` | `src/data/AGENTS.md` – WebSocket, buffer, back-pressure |
| `src/strategy/` | `src/strategy/AGENTS.md` – signal math, no risk overrides |
| `src/execution/` | `src/execution/AGENTS.md` – order routing, ApiException handling |
| `src/risk/` | `src/risk/AGENTS.md` – veto power, daily-loss guard |
| `config/` | `config/AGENTS.md` – immutable risk rules |
| `tests/` | `tests/AGENTS.md` – coverage, mock discipline |
| `data/` | `data/AGENTS.md` – WAL mode, retention, schema migrations |
| `logs/` | `logs/AGENTS.md` – JSON-line format, rotation, PII masking |

> Source citation:  
> `> src/AGENTS.md — Pipeline: Market Data -> Strategy -> Risk Gate -> Execution -> Trade Journal`  
> `> config/AGENTS.md — Immutable risk rules, tunable strategy parameters`  
> `> src/data/AGENTS.md — Async WebSocket, token subscription, reconnection with exponential backoff, backpressure via ring buffer.`

---

*Document last updated: 2026-06-09*