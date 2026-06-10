"""Max Pain tracker.

Computes the strike where option buyers lose minimum value.

Source citation:
    > UNIFIED_TRADING_STRATEGY.md - Max Pain = argmin_K [sum max(0,S-K).xOI_Call + sum max(0,K-S).xOI_Put].
    > src/strategy/AGENTS.md - No order placement, no risk overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MaxPainState:
    """State for Max Pain tracking."""
    max_pain_strike: float = 0.0
    previous_max_pain: float = 0.0
    shift_amount: float = 0.0


class MaxPainTracker:
    """Track Max Pain level for option chain.

    The strike where the sum of call and put intrinsic values is minimized.
    Used as a reference point for institutional positioning bias.
    """

    def __init__(self) -> None:
        self._state = MaxPainState()

    def update(self, option_chain: list[dict[str, Any]], spot_price: float) -> float:
        """Calculate Max Pain from option chain.

        Parameters
        ----------
        option_chain : list[dict]
            List of option dicts with keys: strike, call_oi, put_oi.
        spot_price : float
            Current spot price.

        Returns
        -------
        float
            Max Pain strike.
        """
        self._state.previous_max_pain = self._state.max_pain_strike

        if not option_chain:
            return self._state.max_pain_strike

        strikes = sorted(set(opt.get("strike", 0) for opt in option_chain))
        min_pain = float("inf")
        max_pain_strike = strikes[0] if strikes else 0

        for test_strike in strikes:
            pain = 0.0
            for opt in option_chain:
                strike = opt.get("strike", 0)
                call_oi = opt.get("call_oi", 0)
                put_oi = opt.get("put_oi", 0)

                if spot_price > strike:
                    pain += (spot_price - strike) * call_oi

                if spot_price < strike:
                    pain += (strike - spot_price) * put_oi

            if pain < min_pain:
                min_pain = pain
                max_pain_strike = test_strike

        self._state.max_pain_strike = max_pain_strike
        self._state.shift_amount = max_pain_strike - self._state.previous_max_pain

        return max_pain_strike

    def get_max_pain(self) -> float:
        """Return current Max Pain strike."""
        return self._state.max_pain_strike

    def has_shifted(self) -> bool:
        """Return True if Max Pain shifted significantly."""
        return abs(self._state.shift_amount) >= 50

    def reset(self) -> None:
        """Reset state for new trading day."""
        self._state = MaxPainState()
