"""IV Skew & Trend calculator.

Computes implied volatility skew and tracks its trend.

Source citation:
    > UNIFIED_TRADING_STRATEGY.md - IV Skew = IV_Call_ATM - IV_Put_ATM.
    > src/strategy/AGENTS.md - No order placement, no risk overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


@dataclass
class IVSkewState:
    """State for IV skew tracking."""
    iv_call_atm: float = 0.0
    iv_put_atm: float = 0.0
    skew: float = 0.0
    skew_history: list[float] = field(default_factory=list)
    trend: str = "FLAT"


class IVSkewCalculator:
    """Calculate IV Skew and its trend.

    IV Skew = IV_Call_ATM - IV_Put_ATM (positive skew = call > put IV)
    """

    def __init__(self) -> None:
        self._state = IVSkewState()

    def update(
        self,
        iv_call_atm: float,
        iv_put_atm: float,
        timestamp: str | None = None,
    ) -> float:
        """Update IV skew with new data."""
        self._state.iv_call_atm = iv_call_atm
        self._state.iv_put_atm = iv_put_atm
        self._state.skew = iv_call_atm - iv_put_atm
        self._state.skew_history.append(self._state.skew)

        if len(self._state.skew_history) > 120:
            self._state.skew_history = self._state.skew_history[-120:]

        self._state.trend = self._compute_trend()
        return self._state.skew

    def _compute_trend(self) -> str:
        """Compute skew trend: EXPANDING, COLLAPSING, or FLAT."""
        if len(self._state.skew_history) < 4:
            return "FLAT"

        recent = self._state.skew_history
        first = sum(recent[:len(recent)//4]) / (len(recent)//4) if len(recent) >= 4 else recent[0]
        last = sum(recent[-len(recent)//4:]) / (len(recent)//4) if len(recent) >= 4 else recent[-1]

        diff = last - first

        if diff > 0.02:
            return "EXPANDING"
        elif diff < -0.02:
            return "COLLAPSING"
        return "FLAT"

    def get_skew(self) -> float:
        """Return current IV skew."""
        return self._state.skew

    def get_trend(self) -> str:
        """Return skew trend."""
        return self._state.trend

    def is_expanded(self) -> bool:
        """Return True if skew is expanding (IV call > IV put, fear)."""
        return self._state.skew > 0.05

    def is_crushed(self) -> bool:
        """Return True if skew is crushed (IV put > IV call, complacency)."""
        return self._state.skew < -0.05

    def reset(self) -> None:
        """Reset state for new trading day."""
        self._state = IVSkewState()
