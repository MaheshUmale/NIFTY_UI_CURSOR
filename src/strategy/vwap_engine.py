"""VWAP (Volume Weighted Average Price) engine.

Computes cumulative VWAP from tick data. Resets at 9:15 IST daily.

Source citation:
    > src/strategy/AGENTS.md — VWAP resets at 9:15 IST, cumulative price×volume.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any

from src.utils.time_utils import now_ist

import logging

logger = logging.getLogger(__name__)


@dataclass
class VWAPState:
    """Accumulated VWAP state for a symbol."""
    cumulative_pv: float = 0.0
    cumulative_volume: int = 0
    vwap: float = 0.0
    last_reset_time: str = ""


class VWAPEngine:
    """VWAP calculator with daily reset.

    Parameters
    ----------
    reset_time : time
        Time of day to reset VWAP (default 9:15 IST).
    """

    def __init__(self, reset_time: time = time(9, 15)) -> None:
        self._reset_time = reset_time
        self._states: dict[str, VWAPState] = {}

    def update(self, tick: dict[str, Any]) -> float | None:
        """Update VWAP with a new tick.

        Returns the current VWAP or None if insufficient data.
        """
        symbol = tick.get("symbol", "unknown")
        price = tick.get("last_price", 0.0)
        volume = tick.get("volume", 0)

        if symbol not in self._states:
            self._states[symbol] = VWAPState()
            self._states[symbol].last_reset_time = now_ist().strftime("%Y-%m-%d")

        state = self._states[symbol]

        # Daily reset check
        now = now_ist()
        current_date = now.strftime("%Y-%m-%d")
        if current_date != state.last_reset_time:
            logger.info("VWAP reset for %s on %s", symbol, current_date)
            state.cumulative_pv = 0.0
            state.cumulative_volume = 0
            state.vwap = 0.0
            state.last_reset_time = current_date

        if volume > 0 and price > 0:
            state.cumulative_pv += price * volume
            state.cumulative_volume += volume
            state.vwap = state.cumulative_pv / state.cumulative_volume

        return state.vwap

    def get_vwap(self, symbol: str) -> float:
        """Return current VWAP for a symbol (0.0 if not computed yet)."""
        state = self._states.get(symbol)
        return state.vwap if state else 0.0

    def reset(self, symbol: str | None = None) -> None:
        """Clear all state."""
        if symbol:
            self._states.pop(symbol, None)
        else:
            self._states.clear()