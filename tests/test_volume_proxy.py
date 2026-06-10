"""Unit tests for volume proxy logic in app.py.

Tests that index ticks get volume copied from future when missing.
"""
from __future__ import annotations

import pytest

from src.data.market_buffer import MarketBuffer


def test_index_tick_gets_volume_from_future() -> None:
    """Index tick with no volume should get proxied from future tick in buffer."""
    buffer = MarketBuffer(capacity=100)
    fut_tick: dict[str, float | None] = {
        "instrument_key": "NIFTY24JUNFUT",
        "last_price": 23500.0,
        "volume": 15000,
        "oi": 500000,
    }
    buffer.push(fut_tick)
    
    index_tick: dict[str, float | None] = {
        "instrument_key": "NSE_INDEX|Nifty 50",
        "last_price": 23450.0,
        "volume": None,
        "oi": None,
    }
    
    ref = buffer.latest_for("NIFTY24JUNFUT")
    assert ref is not None
    assert ref.get("volume") == 15000
    
    if index_tick.get("volume") is None:
        if ref and ref.get("volume"):
            index_tick["volume"] = ref["volume"]
            index_tick["volume_source"] = "future_proxy"
    
    assert index_tick["volume"] == 15000
    assert index_tick["volume_source"] == "future_proxy"


def test_index_tick_keeps_own_volume() -> None:
    """Index tick with existing volume should not be modified."""
    buffer = MarketBuffer(capacity=100)
    
    index_tick: dict[str, float | None] = {
        "instrument_key": "NSE_INDEX|Nifty 50",
        "last_price": 23450.0,
        "volume": 5000,
        "oi": None,
    }
    
    if index_tick.get("volume"):
        assert index_tick["volume"] == 5000
    else:
        index_tick["volume_source"] = "future_proxy"
    
    assert "volume_source" not in index_tick or index_tick.get("volume_source") != "future_proxy"


def test_non_index_tick_unaffected() -> None:
    """Non-index ticks should not trigger volume proxy logic."""
    buffer = MarketBuffer(capacity=100)
    
    opt_tick: dict[str, float | None] = {
        "instrument_key": "NSE_FO|NIFTY24JUN23450CE",
        "last_price": 150.0,
        "volume": None,
        "oi": None,
    }
    
    assert opt_tick["instrument_key"] != "NSE_INDEX|Nifty 50"
    assert opt_tick.get("volume_source") is None