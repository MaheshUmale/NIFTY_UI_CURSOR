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
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.data.market_buffer import MarketBuffer
from src.data.websocket_client import WebSocketClient
from src.strategy.signal_generator import Signal, SignalGenerator
from src.utils.logger import get_logger, configure_logging
from src.utils.time_utils import now_ist, is_market_hours

# ---------------------------------------------------------------------------
# Configure logging
# ---------------------------------------------------------------------------
configure_logging()
logger = get_logger(__name__)

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


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    load_dotenv(Path(__file__).parent / "config" / ".env")
    logger.info("Trading system starting up...")
    state.start_time = time.time()

    token = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
    if token:
        state.access_token = token
        logger.info("Access token loaded from .env (length=%d)", len(token))
        try:
            state.ws_client = WebSocketClient(
                token=state.access_token,
                tick_handler=tick_handler,
                buffer=state.buffer,
            )
            instrument_keys = [
                "NSE_INDEX|Nifty 50",
                "NSE_INDEX|Nifty Bank",
            ]
            asyncio.create_task(_run_websocket(instrument_keys))
            state.connected = True
            state.error_message = ""
            logger.info("WebSocket auto-connect initiated for %s", instrument_keys)
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
        # Create WebSocket client
        state.ws_client = WebSocketClient(
            token=state.access_token,
            tick_handler=tick_handler,
            buffer=state.buffer,
        )

        # Subscribe to NIFTY instruments
        instrument_keys = [
            "NSE_INDEX|NIFTY 50",
            "NSE_INDEX|NIFTY BANK",
        ]

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
        await state.ws_client.subscribe(instrument_keys)
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


@app.post("/api/simulate_tick")
async def simulate_tick(body: dict[str, Any]):
    """Simulate a tick for testing purposes (no real Upstox connection needed)."""
    tick = {
        "instrument_key": body.get("instrument_key", "NSE_INDEX|NIFTY 50"),
        "symbol": body.get("symbol", "NIFTY"),
        "last_price": body.get("last_price", 24500.0),
        "volume": body.get("volume", 1000),
        "oi": body.get("oi", 50000),
        "timestamp": now_ist().isoformat(),
    }
    await tick_handler(tick)
    return JSONResponse({"status": "tick_simulated", "tick": tick})


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
# E2E Test endpoint — simulates the full pipeline
# ---------------------------------------------------------------------------

@app.post("/api/e2e_test")
async def run_e2e_test():
    """Run an end-to-end test of the full pipeline with simulated ticks."""
    results = {
        "test_name": "E2E Live Streaming Pipeline Test",
        "steps": [],
        "passed": True,
    }

    # Step 1: Test market buffer
    try:
        buffer = MarketBuffer(capacity=100)
        test_tick = {
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "symbol": "NIFTY",
            "last_price": 24500.0,
            "volume": 1000,
            "oi": 50000,
        }
        buffer.push(test_tick)
        latest = buffer.latest()
        assert latest is not None, "Buffer should have a tick"
        assert latest["last_price"] == 24500.0, "Price should match"
        results["steps"].append({"step": "market_buffer", "status": "PASS", "detail": "Buffer stores and retrieves ticks"})
    except Exception as e:
        results["steps"].append({"step": "market_buffer", "status": "FAIL", "detail": str(e)})
        results["passed"] = False

    # Step 2: Test signal generator
    try:
        generator = SignalGenerator()
        # Feed multiple ticks to build ORB range
        for i in range(20):
            tick = {
                "instrument_key": "NSE_INDEX|NIFTY 50",
                "symbol": "NIFTY",
                "last_price": 24500.0 + i * 10,
                "volume": 1000 + i * 100,
                "oi": 50000,
            }
            generator.on_tick(tick)
        results["steps"].append({"step": "signal_generator", "status": "PASS", "detail": "Signal generator processes ticks without error"})
    except Exception as e:
        results["steps"].append({"step": "signal_generator", "status": "FAIL", "detail": str(e)})
        results["passed"] = False

    # Step 3: Test tick handler
    try:
        state.tick_count = 0
        await tick_handler(test_tick)
        assert state.tick_count == 1, "Tick count should be 1"
        assert "NSE_INDEX|NIFTY 50" in state.latest_ticks, "Latest tick should be stored"
        results["steps"].append({"step": "tick_handler", "status": "PASS", "detail": "Tick handler processes ticks and updates state"})
    except Exception as e:
        results["steps"].append({"step": "tick_handler", "status": "FAIL", "detail": str(e)})
        results["passed"] = False

    # Step 4: Test REST API endpoints
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Test /api/status
        resp = client.get("/api/status")
        assert resp.status_code == 200, f"Status endpoint returned {resp.status_code}"
        data = resp.json()
        assert "connected" in data, "Status should have 'connected' field"

        # Test /api/signals
        resp = client.get("/api/signals")
        assert resp.status_code == 200, f"Signals endpoint returned {resp.status_code}"

        # Test /api/risk
        resp = client.get("/api/risk")
        assert resp.status_code == 200, f"Risk endpoint returned {resp.status_code}"

        # Test /api/ticks
        resp = client.get("/api/ticks")
        assert resp.status_code == 200, f"Ticks endpoint returned {resp.status_code}"

        # Test /api/positions
        resp = client.get("/api/positions")
        assert resp.status_code == 200, f"Positions endpoint returned {resp.status_code}"

        # Test /api/simulate_tick
        resp = client.post("/api/simulate_tick", json={
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "symbol": "NIFTY",
            "last_price": 24500.0,
            "volume": 1000,
            "oi": 50000,
        })
        assert resp.status_code == 200, f"Simulate tick returned {resp.status_code}"

        results["steps"].append({"step": "rest_api", "status": "PASS", "detail": "All REST API endpoints respond correctly"})
    except Exception as e:
        results["steps"].append({"step": "rest_api", "status": "FAIL", "detail": str(e)})
        results["passed"] = False

    # Step 5: Test dashboard UI
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200, f"Dashboard returned {resp.status_code}"
        assert "NIFTY" in resp.text or "Trading" in resp.text, "Dashboard should contain trading-related content"
        results["steps"].append({"step": "dashboard_ui", "status": "PASS", "detail": "Dashboard UI serves HTML correctly"})
    except Exception as e:
        results["steps"].append({"step": "dashboard_ui", "status": "FAIL", "detail": str(e)})
        results["passed"] = False

    # Step 6: Test WebSocket endpoint
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "status", f"Expected status message, got {msg['type']}"
        results["steps"].append({"step": "websocket", "status": "PASS", "detail": "WebSocket endpoint accepts connections and sends status"})
    except Exception as e:
        results["steps"].append({"step": "websocket", "status": "FAIL", "detail": str(e)})
        results["passed"] = False

    return JSONResponse(results)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")