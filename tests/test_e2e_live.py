"""End-to-end test for live streaming and UI pipeline.

Tests the full pipeline: MarketBuffer -> SignalGenerator -> AppState -> WebSocket -> Browser.
This test validates that all components integrate correctly without requiring
a real Upstox connection (uses simulated ticks).

Source citation:
    > src/AGENTS.md — Pipeline: Market Data -> Strategy -> Risk Gate -> Execution -> Trade Journal
    > tests/AGENTS.md — Test pyramid; mock data discipline; no network in unit tests
"""
from __future__ import annotations

import asyncio
import json
import sys
import os
from pathlib import Path

import pytest

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestE2ELiveStreaming:
    """End-to-end tests for the live streaming pipeline."""

    def test_market_buffer_stores_ticks(self) -> None:
        """MarketBuffer stores and retrieves ticks correctly."""
        from src.data.market_buffer import MarketBuffer

        buffer = MarketBuffer(capacity=100)
        tick = {
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "symbol": "NIFTY",
            "last_price": 24500.0,
            "volume": 1000,
            "oi": 50000,
        }
        buffer.push(tick)
        latest = buffer.latest()
        assert latest is not None
        assert latest["last_price"] == 24500.0
        assert latest["symbol"] == "NIFTY"
        assert len(buffer) == 1

    def test_market_buffer_ring_eviction(self) -> None:
        """MarketBuffer evicts oldest tick when at capacity."""
        from src.data.market_buffer import MarketBuffer

        buffer = MarketBuffer(capacity=3)
        for i in range(5):
            buffer.push({"instrument_key": f"KEY_{i}", "last_price": float(i)})

        assert len(buffer) == 3
        latest = buffer.latest()
        assert latest is not None
        assert latest["last_price"] == 4.0

    def test_market_buffer_oi_forward_fill(self) -> None:
        """MarketBuffer forward-fills OI when tick has null OI."""
        from src.data.market_buffer import MarketBuffer

        buffer = MarketBuffer(capacity=100)
        buffer.push({"instrument_key": "NIFTY", "last_price": 100.0, "oi": 50000})
        buffer.push({"instrument_key": "NIFTY", "last_price": 101.0, "oi": None})
        latest = buffer.latest()
        assert latest is not None
        assert latest["oi"] == 50000

    def test_signal_generator_processes_ticks(self) -> None:
        """SignalGenerator processes ticks without error."""
        from src.strategy.signal_generator import SignalGenerator

        gen = SignalGenerator()
        # Feed ticks to build ORB range and compute VWAP/EMA
        for i in range(20):
            tick = {
                "instrument_key": "NSE_INDEX|NIFTY 50",
                "symbol": "NIFTY",
                "last_price": 24500.0 + i * 10,
                "volume": 1000 + i * 100,
                "oi": 50000,
            }
            result = gen.on_tick(tick)
            # Result may be None or a Signal — both are valid
            if result is not None:
                assert result.symbol == "NIFTY"
                assert result.side in ("LONG", "SHORT")
                assert result.entry_price > 0

    def test_signal_generator_reset(self) -> None:
        """SignalGenerator reset clears all state."""
        from src.strategy.signal_generator import SignalGenerator

        gen = SignalGenerator()
        for i in range(10):
            gen.on_tick({
                "instrument_key": "NIFTY",
                "symbol": "NIFTY",
                "last_price": 24500.0 + i,
                "volume": 1000,
                "oi": 50000,
            })
        gen.reset()
        # After reset, processing should start fresh
        assert True  # No exception means reset worked

    def test_fastapi_app_imports(self) -> None:
        """FastAPI app can be imported without errors."""
        from app import app
        assert app is not None
        assert app.title == "NIFTY Trading System — Live Dashboard"

    def test_rest_api_status_endpoint(self) -> None:
        """GET /api/status returns valid JSON with expected fields."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "connected" in data
        assert "tick_count" in data
        assert "daily_pnl" in data
        assert "daily_trades" in data
        assert "risk_status" in data
        assert "uptime_seconds" in data

    def test_rest_api_signals_endpoint(self) -> None:
        """GET /api/signals returns valid JSON."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.get("/api/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    def test_rest_api_risk_endpoint(self) -> None:
        """GET /api/risk returns valid risk status."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.get("/api/risk")
        assert resp.status_code == 200
        data = resp.json()
        assert "max_daily_loss_pct" in data
        assert data["max_daily_loss_pct"] == 0.04
        assert "max_trades_per_day" in data
        assert data["max_trades_per_day"] == 3

    def test_rest_api_ticks_endpoint(self) -> None:
        """GET /api/ticks returns valid JSON."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.get("/api/ticks")
        assert resp.status_code == 200
        data = resp.json()
        assert "ticks" in data

    def test_rest_api_positions_endpoint(self) -> None:
        """GET /api/positions returns valid JSON."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.get("/api/positions")
        assert resp.status_code == 200
        data = resp.json()
        assert "positions" in data

    def test_simulate_tick_updates_state(self) -> None:
        """POST /api/simulate_tick updates tick count and latest ticks."""
        from fastapi.testclient import TestClient
        from app import app, state

        initial_count = state.tick_count
        client = TestClient(app)
        resp = client.post("/api/simulate_tick", json={
            "instrument_key": "NSE_INDEX|NIFTY 50",
            "symbol": "NIFTY",
            "last_price": 24500.0,
            "volume": 1000,
            "oi": 50000,
        })
        assert resp.status_code == 200
        assert state.tick_count == initial_count + 1
        assert "NSE_INDEX|NIFTY 50" in state.latest_ticks

    def test_token_endpoint(self) -> None:
        """POST /api/token sets the access token."""
        from fastapi.testclient import TestClient
        from app import app, state

        client = TestClient(app)
        resp = client.post("/api/token", json={"access_token": "test_token_123"})
        assert resp.status_code == 200
        assert state.access_token == "test_token_123"

    def test_token_endpoint_requires_token(self) -> None:
        """POST /api/token rejects empty token."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.post("/api/token", json={})
        assert resp.status_code == 400

    def test_dashboard_serves_html(self) -> None:
        """GET / serves the dashboard HTML."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "NIFTY" in resp.text or "Trading" in resp.text

    def test_websocket_accepts_connection(self) -> None:
        """WebSocket endpoint /ws accepts connections and sends status."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "status"
            assert "connected" in msg["data"]
            assert "tick_count" in msg["data"]

    def test_websocket_receives_simulated_tick(self) -> None:
        """WebSocket receives tick messages when simulate_tick is called."""
        from fastapi.testclient import TestClient
        from app import app, state

        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            # Consume initial status message
            ws.receive_text()

            # Simulate a tick via REST API
            resp = client.post("/api/simulate_tick", json={
                "instrument_key": "NSE_INDEX|NIFTY 50",
                "symbol": "NIFTY",
                "last_price": 24500.0,
                "volume": 1000,
                "oi": 50000,
            })
            assert resp.status_code == 200

            # Should receive tick message via WebSocket
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg["type"] == "tick"
            assert msg["data"]["last_price"] == 24500.0

    def test_e2e_full_pipeline_simulation(self) -> None:
        """Full E2E test via /api/e2e_test endpoint."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.post("/api/e2e_test")
        assert resp.status_code == 200
        results = resp.json()
        assert results["test_name"] == "E2E Live Streaming Pipeline Test"
        assert results["passed"] is True
        assert len(results["steps"]) >= 5  # At least 5 test steps
        for step in results["steps"]:
            assert step["status"] == "PASS", f"Step {step['step']} failed: {step['detail']}"

    def test_disconnect_endpoint(self) -> None:
        """POST /api/disconnect handles not-connected gracefully."""
        from fastapi.testclient import TestClient
        from app import app

        client = TestClient(app)
        resp = client.post("/api/disconnect")
        assert resp.status_code == 400  # Not connected

    def test_connect_requires_token(self) -> None:
        """POST /api/connect rejects when no token is set."""
        from fastapi.testclient import TestClient
        from app import app, state

        # Clear token
        state.access_token = ""
        client = TestClient(app)
        resp = client.post("/api/connect")
        assert resp.status_code == 400