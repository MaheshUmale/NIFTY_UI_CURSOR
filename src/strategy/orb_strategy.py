"""Opening Range Breakout (ORB) strategy.

Computes the opening range (first 15 minutes of market open) and detects
breakouts with volume confirmation.

Source citation:
    > src/strategy/AGENTS.md — ORB 9:15-9:30, volume confirmation ≥ 1.5x.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time, datetime
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import IST, now_ist

logger = get_logger(__name__)


@dataclass
class ORBState:
    """Tracks the opening range for the current session."""
    range_high: float = 0.0
    range_low: float = float("inf")
    range_closed: bool = False
    tick_count: int = 0


class ORBStrategy:
    """Opening Range Breakout detector.

    Parameters
    ----------
    range_minutes : int
        Duration of the opening range in minutes (default 15).
    volume_mult : float
        Minimum breakout volume as a multiple of the 20-period average.
    """

    def __init__(
        self,
        range_minutes: int = 15,
        volume_mult: float = 1.5,
    ) -> None:
        self._range_minutes = range_minutes
        self._volume_mult = volume_mult
        self._states: dict[str, ORBState] = {}
        self._market_open = time(9, 15)
        self._range_end = time(9, 15 + range_minutes)

    def update(self, tick: dict[str, Any]) -> ORBState | None:
        """Process a tick and return the current ORB state.

        Returns None if we're outside the ORB window.
        """
        symbol = tick.get("symbol", "unknown")
        now = now_ist()
        t = now.time()

        # Initialize state for new symbol
        if symbol not in self._states:
            self._states[symbol] = ORBState()

        state = self._states[symbol]

        # Phase 1: Build the range (9:15 to range_end)
        if self._market_open <= t < self._range_end:
            high = tick.get("high", tick.get("last_price", 0))
            low = tick.get("low", tick.get("last_price", float("inf")))
            if high > state.range_high:
                state.range_high = high
            if low < state.range_low:
                state.range_low = low
            state.tick_count += 1
            return state

        # Phase 2: Check for breakout (after range_end)
        if t >= self._range_end and not state.range_closed:
            state.range_closed = True
            logger.info(
                "ORB range closed for %s: high=%.2f low=%.2f ticks=%d",
                symbol, state.range_high, state.range_low, state.tick_count,
            )
            return state

        return None

    def check_breakout(
        self, tick: dict[str, Any], avg_volume: float | None = None
    ) -> str | None:
        """Check if the current tick breaks out of the ORB range.

        Returns "LONG", "SHORT", or None.
        """
        symbol = tick.get("symbol", "unknown")
        state = self._states.get(symbol)
        if state is None or not state.range_closed:
            return None

        price = tick.get("last_price", 0.0)
        volume = tick.get("volume", 0)

        # Volume confirmation
        if avg_volume is not None and avg_volume > 0:
            if volume < avg_volume * self._volume_mult:
                return None

        if price > state.range_high:
            return "LONG"
        elif price < state.range_low:
            return "SHORT"

        return None

    def reset(self, symbol: str | None = None) -> None:
        """Reset ORB state (called at market open or end of day)."""
        if symbol:
            self._states.pop(symbol, None)
        else:
            self._states.clear()