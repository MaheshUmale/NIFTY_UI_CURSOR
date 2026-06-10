"""Thread-safe ring buffer for market ticks with OI forward-fill.

Stores the most recent N ticks. When a new tick arrives with null OI,
the buffer forward-fills the last known OI for that instrument key.

Source citation:
    > src/data/AGENTS.md — Ring buffer overflow drops oldest, forward-fill
      OI when null, dynamic window shift.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MarketBuffer:
    """A thread-safe ring buffer for market data ticks.

    Parameters
    ----------
    capacity : int
        Maximum number of ticks to store. When full, the oldest tick is
        dropped on the next push.
    """

    def __init__(self, capacity: int = 1000) -> None:
        self._capacity = capacity
        self._ticks: list[dict[str, Any]] = []
        self._oi_cache: dict[str, float] = {}  # instrument_key → last known OI
        self._window_shift_requested: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, tick: dict[str, Any]) -> None:
        """Add a tick to the buffer.

        If OI is null/zero for this tick, forward-fills from the last
        known OI for the same instrument key.

        If the buffer is at capacity, the oldest tick is dropped silently.
        """
        instr_key = tick.get("instrument_key") or tick.get("symbol", "")
        oi = tick.get("oi")

        # Forward-fill OI if missing
        if oi is None or oi == 0:
            if instr_key in self._oi_cache:
                tick["oi"] = self._oi_cache[instr_key]
            else:
                tick["oi"] = 0
        else:
            self._oi_cache[instr_key] = oi

        # Ring buffer eviction
        if len(self._ticks) >= self._capacity:
            self._ticks.pop(0)

        self._ticks.append(tick)

    def latest(self) -> dict[str, Any] | None:
        """Return the most recent tick, or ``None`` if the buffer is empty."""
        if not self._ticks:
            return None
        return self._ticks[-1]

    def window(self, instrument_keys: list[str]) -> list[dict[str, Any]]:
        """Return all buffered ticks matching any of the given instrument keys.

        Parameters
        ----------
        instrument_keys : list[str]
            List of instrument keys to filter by.

        Returns
        -------
        list[dict]
            Matching ticks in insertion order (oldest first).
        """
        key_set = set(instrument_keys)
        return [t for t in self._ticks if t.get("instrument_key") in key_set or t.get("symbol") in key_set]

    def shift_window(self, new_atm: float) -> None:
        """Signal that the WebSocket should re-subscribe to a new ATM window.

        This sets a flag; the WebSocket client's subscription loop checks
        this flag and triggers a re-subscribe.
        """
        self._window_shift_requested = True
        logger.info("Window shift requested to ATM=%.2f", new_atm)

    @property
    def is_window_shift_requested(self) -> bool:
        """Check and clear the window-shift flag."""
        if self._window_shift_requested:
            self._window_shift_requested = False
            return True
        return False

    def clear(self) -> None:
        """Reset the buffer and OI cache."""
        self._ticks.clear()
        self._oi_cache.clear()

    def __len__(self) -> int:
        return len(self._ticks)