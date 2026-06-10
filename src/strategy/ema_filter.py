"""EMA (Exponential Moving Average) filter for option premiums.

Blocks counter-trend scalps when premium is below its 9 EMA.

Source citation:
    > src/strategy/AGENTS.md — EMA9 filter, premium < EMA blocks long.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EMAState:
    """EMA state for a symbol."""
    ema: float = 0.0
    count: int = 0
    alpha: float = 0.0


class EMAFilter:
    """9-period EMA filter for option premiums.

    Parameters
    ----------
    period : int
        EMA period (default 9).
    """

    def __init__(self, period: int = 9) -> None:
        self._period = period
        self._alpha = 2.0 / (period + 1)
        self._states: dict[str, EMAState] = {}

    def update(self, symbol: str, price: float) -> float:
        """Update EMA with a new price and return current EMA value."""
        if symbol not in self._states:
            self._states[symbol] = EMAState(alpha=self._alpha)

        state = self._states[symbol]
        state.count += 1

        if state.count == 1:
            state.ema = price
        else:
            state.ema = self._alpha * price + (1 - self._alpha) * state.ema

        return state.ema

    def is_above_ema(self, symbol: str, price: float) -> bool:
        """Return True if price is above the current EMA."""
        ema = self._states.get(symbol)
        if ema is None or ema.count < self._period:
            return True  # Not enough data, pass by default
        return price >= ema.ema

    def reset(self, symbol: str | None = None) -> None:
        """Clear state."""
        if symbol:
            self._states.pop(symbol, None)
        else:
            self._states.clear()