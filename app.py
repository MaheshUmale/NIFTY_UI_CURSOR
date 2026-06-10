"""FastAPI application — main entry point for the trading system.

Serves the dashboard UI, provides WebSocket streaming to the browser,
connects to Upstox WebSocket for market data, runs strategy on ticks,
and exposes REST API for signals, positions, trades, and risk status.

Source citation:
    > src/AGENTS.md — Pipeline: Market Data -> Strategy -> Risk Gate -> Execution -> Trade Journal
    > config/AGENTS.md — Immutable risk rules, tunable strategy parameters
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.data.websocket_client import WebSocketClient
from src.data.market_history import fetch_warmup_data, resolve_option_keys_for_history
from src.data.instrument_resolver import resolve_current_month_future
from src.data.market_buffer import MarketBuffer
from src.strategy.signal_generator import Signal, SignalGenerator
from src.utils.logger import get_logger, configure_logging
from src.utils.time_utils import now_ist, is_market_hours

# ---------------------------------------------------------------------------
# Configure logging
# ---------------------------------------------------------------------------
configure_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Instrument cache: current-month future instrument keys for volume proxy
# ---------------------------------------------------------------------------
_current_future_cache: dict[str, str | None] = {}


def _get_nifty_future_key() -> str | None:
    if "nifty" not in _current_future_cache:
        _current_future_cache["nifty"] = resolve_current_month_future("NIFTY")
    return _current_future_cache["nifty"]


# ---------------------------------------------------------------------------
# In-memory state (shared across all connected clients)
# ---------------------------------------------------------------------------

@dataclass
class AppState:
    """Global application state — holds all live data."""
    # Market data
    buffer: MarketBuffer = field(default_factory=lambda: MarketBuffer(capacity=5000))
    ws_client: WebSocketClient | None = None
    latest_ticks: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Strategy
    signal_generator: SignalGenerator = field(default_factory=SignalGenerator)
    signals: list[dict[str, Any]] = field(default_factory=list)
    max_signals: int = 100

    # Positions (simulated for E2E testing)
    positions: list[dict[str, Any]] = field(default_factory=list)
    daily_pnl: float = 0.0
    daily_trades: int = 0

    # Risk status
    risk_status: dict[str, Any] = field(default_factory=lambda: {
        "indicator": "OK",
        "daily_loss_pct": 0.0,
        "trades_today": 0,
        "max_daily_loss_pct": 0.04,
        "max_trades_per_day": 3,
        "max_risk_per_trade_pct": 0.02,
    })

    # Connection status
    connected: bool = False
    access_token: str = ""
    error_message: str = ""

    # Browser WebSocket clients
    browser_clients: set[WebSocket] = field(default_factory=set)

    # Tick counter
    tick_count: int = 0
    start_time: float = 0.0


state = AppState()


def _proxy_index_volume(tick: dict[str, Any]) -> None:
    if tick.get("instrument_key") != "NSE_INDEX|Nifty 50":
        return
    if tick.get("volume"):
        return
    fut_key = _current_future_cache.get("nifty") or _get_nifty_future_key()
    if not fut_key:
        return
    ref = state.buffer.latest_for(fut_key) if state.buffer else None
    if ref and ref.get("volume"):
        tick["volume"] = ref["volume"]
        tick["volume_source"] = "future_proxy"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    load_dotenv(Path(__file__).parent / "config" / ".env", override=True)
    logger.info("Trading system starting up...")
    state.start_time = time.time()

    token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
    if token:
        state.access_token = token
        logger.info("Access token loaded from .env (length=%d)", len(token))
        try:
            _get_nifty_future_key()
            option_keys = resolve_option_keys_for_history(state.access_token, df=None)
            instrument_keys = [
                "NSE_INDEX|Nifty 50",
                "NSE_INDEX|Nifty Bank",
                _current_future_cache.get("nifty", ""),
            ]
            instrument_keys = [k for k in instrument_keys if k]
            instrument_keys.extend(option_keys)
            state.ws_client = WebSocketClient(
                token=state.access_token,
                tick_handler=tick_handler,
                buffer=state.buffer,
                instrument_keys=instrument_keys,
            )
            asyncio.create_task(_run_websocket(instrument_keys))
            state.connected = True
            state.error_message = ""
            logger.info("WebSocket auto-connect initiated with %d instruments", len(instrument_keys))
        except Exception as e:
            state.error_message = str(e)
            logger.exception("Failed to auto-connect on startup")
    else:
        logger.info("No UPSTOX_ACCESS_TOKEN in .env — waiting for manual connect")

    yield

    logger.info("Trading system shutting down...")
    if state.ws_client:
        await state.ws_client.disconnect()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NIFTY Trading System — Live Dashboard",
    description="End-to-end live streaming and UI for the NIFTY options trading system.",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)))


# ---------------------------------------------------------------------------
# WebSocket broadcast helpers
# ---------------------------------------------------------------------------

async def broadcast_to_browser(payload: dict[str, Any]) -> None:
    """Broadcast a message to all connected browser clients."""
    if not state.browser_clients:
        return

    message = json.dumps(payload)
    disconnected: list[WebSocket] = []
    for client in state.browser_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)

    for client in disconnected:
        state.browser_clients.discard(client)


async def broadcast_tick(tick: dict[str, Any]) -> None:
    """Broadcast a tick to all connected browser clients."""
    await broadcast_to_browser({
        "type": "tick",
        "data": tick,
        "ts": now_ist().isoformat(),
    })


async def broadcast_signal(signal: dict[str, Any]) -> None:
    """Broadcast a signal to all connected browser clients."""
    await broadcast_to_browser({
        "type": "signal",
        "data": signal,
        "ts": now_ist().isoformat(),
    })


async def broadcast_status() -> None:
    """Broadcast current status to all connected browser clients."""
    await broadcast_to_browser({
        "type": "status",
        "data": {
            "connected": state.connected,
            "tick_count": state.tick_count,
            "daily_pnl": state.daily_pnl,
            "daily_trades": state.daily_trades,
            "risk_status": state.risk_status,
            "positions": state.positions,
            "error_message": state.error_message,
        },
        "ts": now_ist().isoformat(),
    })


# ---------------------------------------------------------------------------
# Tick handler — called by WebSocketClient on each tick
# ---------------------------------------------------------------------------

_tick_handler_lock = asyncio.Lock()


async def tick_handler(tick: dict[str, Any]) -> None:
    """Process each tick: update state, run strategy, broadcast to browser."""
    async with _tick_handler_lock:
        state.tick_count += 1
        instrument_key = tick.get("instrument_key", tick.get("symbol", "unknown"))
        state.latest_ticks[instrument_key] = tick

        logger.debug("tick_handler received tick %d: keys=%s last_price=%r", state.tick_count, list(tick.keys()), tick.get("last_price"))

        _proxy_index_volume(tick)
        if tick.get("volume_source") == "future_proxy":
            logger.debug("Index volume proxied from future for tick %d", state.tick_count)

        # Run strategy
        try:
            signal = state.signal_generator.on_tick(tick)
            if signal is not None:
                signal_dict = {
                    "symbol": signal.symbol,
                    "side": signal.side,
                    "instrument_key": signal.instrument_key,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "target": signal.target,
                    "qty": signal.qty,
                    "confidence": signal.confidence,
                    "timestamp": signal.timestamp.isoformat() if signal.timestamp else "",
                    "metadata": signal.metadata,
                    "tag": str(uuid.uuid4()),
                }
                state.signals.append(signal_dict)
                if len(state.signals) > state.max_signals:
                    state.signals = state.signals[-state.max_signals:]

                logger.info(
                    "Signal: %s %s at %.2f (confidence=%.2f)",
                    signal.symbol, signal.side, signal.entry_price, signal.confidence,
                )
                await broadcast_signal(signal_dict)
        except Exception:
            logger.exception("Strategy error on tick %d", state.tick_count)

        # Broadcast tick to browser
        await broadcast_tick(tick)

        # Broadcast status every 10 ticks
        if state.tick_count % 10 == 0:
            await broadcast_status()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard UI."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


@app.get("/api/status")
async def get_status():
    """Get current system status."""
    return JSONResponse({
        "connected": state.connected,
        "tick_count": state.tick_count,
        "daily_pnl": state.daily_pnl,
        "daily_trades": state.daily_trades,
        "risk_status": state.risk_status,
        "positions": state.positions,
        "error_message": state.error_message,
        "uptime_seconds": time.time() - state.start_time if state.start_time else 0,
    })


@app.get("/api/signals")
async def get_signals():
    """Get recent signals."""
    return JSONResponse({"signals": state.signals[-50:]})


@app.get("/api/positions")
async def get_positions():
    """Get current positions."""
    return JSONResponse({"positions": state.positions})


@app.get("/api/ticks")
async def get_ticks():
    """Get latest ticks for all instruments."""
    return JSONResponse({"ticks": state.latest_ticks})


@app.get("/api/risk")
async def get_risk():
    """Get risk status."""
    return JSONResponse({
        "risk_status": state.risk_status,
        "daily_loss_pct": state.risk_status.get("daily_loss_pct", 0.0),
        "trades_today": state.risk_status.get("trades_today", 0),
        "max_daily_loss_pct": 0.04,
        "max_trades_per_day": 3,
        "max_risk_per_trade_pct": 0.02,
    })


@app.get("/api/history")
async def get_history():
    """Get historical OHLCV data for the chart (merged index + future)."""
    try:
        warmup = fetch_warmup_data(state.access_token)
        option_keys = resolve_option_keys_for_history(state.access_token)
        return JSONResponse({
            "ohlcv": warmup.get("ohlcv", []),
            "instrument_keys": warmup.get("instrument_keys", []) + option_keys,
        })
    except Exception as e:
        logger.exception("History fetch failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/token")
async def set_token(body: dict[str, Any]):
    """Set the Upstox access token for WebSocket connection."""
    token = body.get("access_token", "")
    if not token:
        return JSONResponse({"error": "access_token is required"}, status_code=400)
    state.access_token = token
    logger.info("Access token set (length=%d)", len(token))
    return JSONResponse({"status": "token_set", "length": len(token)})


@app.post("/api/connect")
async def connect_upstox():
    """Connect to Upstox WebSocket with the provided access token."""
    if not state.access_token:
        return JSONResponse({"error": "No access token provided. Use /api/token to set it."}, status_code=400)

    if state.connected:
        return JSONResponse({"error": "Already connected."}, status_code=400)

    try:
        instrument_keys = [
            "NSE_INDEX|Nifty 50",
            "NSE_INDEX|Nifty Bank",
        ]
        nifty_fut = _get_nifty_future_key()
        if nifty_fut:
            instrument_keys.append(nifty_fut)
        try:
            instrument_keys.extend(resolve_option_keys_for_history(state.access_token))
        except Exception as opt_exc:
            logger.error("Option key resolution failed: %s", opt_exc)

        # Create WebSocket client
        state.ws_client = WebSocketClient(
            token=state.access_token,
            tick_handler=tick_handler,
            buffer=state.buffer,
            instrument_keys=instrument_keys,
        )

        # Start connection in background
        asyncio.create_task(_run_websocket(instrument_keys))
        state.connected = True
        state.error_message = ""

        logger.info("WebSocket connection initiated")
        return JSONResponse({"status": "connecting", "instruments": instrument_keys})

    except Exception as e:
        state.error_message = str(e)
        logger.exception("Failed to connect to Upstox WebSocket")
        return JSONResponse({"error": str(e)}, status_code=500)


async def _run_websocket(instrument_keys: list[str]) -> None:
    """Run the WebSocket client in the background."""
    try:
        await state.ws_client.connect()
    except Exception as e:
        state.connected = False
        state.error_message = str(e)
        logger.exception("WebSocket connection failed")
        await broadcast_status()


@app.post("/api/disconnect")
async def disconnect_upstox():
    """Disconnect from Upstox WebSocket."""
    if state.ws_client:
        await state.ws_client.disconnect()
        state.connected = False
        state.ws_client = None
        logger.info("WebSocket disconnected")
        return JSONResponse({"status": "disconnected"})
    return JSONResponse({"error": "Not connected"}, status_code=400)


# ---------------------------------------------------------------------------
# New UI Integration Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/quotes")
async def get_quotes():
    """Returns the option chain in the format expected by the new UI."""
    nifty_tick = state.latest_ticks.get("NSE_INDEX|Nifty 50")
    if not nifty_tick:
        # If not connected, try to find any tick that looks like Nifty
        for key, tick in state.latest_ticks.items():
            if "Nifty 50" in key:
                nifty_tick = tick
                break

    spot_price = nifty_tick.get("last_price", 22450.0) if nifty_tick else 22450.0
    atm_strike = round(spot_price / 50) * 50
    strikes_list = [atm_strike + i * 50 for i in range(-3, 4)]

    strike_chain = []
    for s in strikes_list:
        ce_tick = None
        pe_tick = None

        # Scan latest_ticks for matching strike and type
        for key, tick in state.latest_ticks.items():
            symbol = tick.get("symbol", "")
            if str(s) in symbol:
                if symbol.endswith("CE"):
                    ce_tick = tick
                elif symbol.endswith("PE"):
                    pe_tick = tick

        strike_chain.append({
            "strike": s,
            "callOI": ce_tick.get("oi", 0) if ce_tick else 0,
            "callCOI": 0, # Could be calculated if we tracked initial OI
            "callVolume": ce_tick.get("volume", 0) if ce_tick else 0,
            "callPremium": ce_tick.get("last_price", 0) if ce_tick else 0,
            "putOI": pe_tick.get("oi", 0) if pe_tick else 0,
            "putCOI": 0,
            "putVolume": pe_tick.get("volume", 0) if pe_tick else 0,
            "putPremium": pe_tick.get("last_price", 0) if pe_tick else 0
        })

    return JSONResponse({
        "spotPrice": round(spot_price, 2),
        "instrument": "NIFTY",
        "strikeChain": strike_chain
    })


@app.post("/api/order")
async def receive_terminal_order(request: Request):
    """Receive inbound order triggers from the new UI."""
    payload = await request.json()
    logger.info(
        "Inbound Order: ID=%s %s %s %s Qty=%s Price=%s",
        payload.get("orderId"),
        payload.get("side"),
        payload.get("instrument"),
        payload.get("strike"),
        payload.get("quantity"),
        payload.get("entryPrice")
    )

    # Add to internal state for tracking
    order_dict = {
        "id": payload.get("orderId"),
        "side": payload.get("side"),
        "type": payload.get("type"),
        "strike": payload.get("strike"),
        "quantity": payload.get("quantity"),
        "entry_price": payload.get("entryPrice"),
        "timestamp": payload.get("timestamp"),
        "instrument": payload.get("instrument"),
        "status": "ACTIVE"
    }
    state.positions.append(order_dict)
    state.daily_trades += 1

    await broadcast_status()
    return JSONResponse({"status": "SUCCESS", "orderId": payload.get("orderId")})


@app.post("/api/order/exit")
async def receive_terminal_exit(request: Request):
    """Receive position exits from the new UI."""
    payload = await request.json()
    logger.info(
        "Scalp Exit: ID=%s Price=%s PnL=%s",
        payload.get("orderId"),
        payload.get("closingPrice"),
        payload.get("pnl")
    )

    # Update internal state
    order_id = payload.get("orderId")
    for pos in state.positions:
        if pos.get("id") == order_id:
            pos["status"] = "CLOSED"
            pos["exit_price"] = payload.get("closingPrice")
            pos["pnl"] = payload.get("pnl")
            state.daily_pnl += pos["pnl"]
            break

    await broadcast_status()
    return JSONResponse({"status": "SUCCESS", "closedOrderId": order_id})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for browser clients to receive live data."""
    await websocket.accept()
    state.browser_clients.add(websocket)
    logger.info("Browser client connected (total=%d)", len(state.browser_clients))

    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": {
                "connected": state.connected,
                "tick_count": state.tick_count,
                "daily_pnl": state.daily_pnl,
                "daily_trades": state.daily_trades,
                "risk_status": state.risk_status,
                "positions": state.positions,
                "error_message": state.error_message,
            },
            "ts": now_ist().isoformat(),
        }))

        # Keep connection alive, listen for client messages
        while True:
            data = await websocket.receive_text()
            # Handle client messages (e.g., subscribe to specific instruments)
            try:
                msg = json.loads(data)
                if msg.get("action") == "subscribe":
                    keys = msg.get("instruments", [])
                    if state.ws_client and keys:
                        await state.ws_client.subscribe(keys)
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        state.browser_clients.discard(websocket)
        logger.info("Browser client disconnected (total=%d)", len(state.browser_clients))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
