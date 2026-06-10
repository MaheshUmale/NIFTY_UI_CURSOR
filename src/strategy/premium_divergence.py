"""Premium VWAP divergence engine.

Calculates premium VWAP vs spot VWAP gap for call/put options.

Source citation:
    > UNIFIED_TRADING_STRATEGY.md - VWAP_gap = (Premium_VWAP - Spot_VWAP) / Spot_VWAP.
    > src/strategy/AGENTS.md - No order placement, no risk overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


@dataclass
class PremiumVWAPState:
    """State for premium VWAP tracking."""
    call_cumulative_pv: float = 0.0
    call_cumulative_volume: int = 0
    call_vwap: float = 0.0
    put_cumulative_pv: float = 0.0
    put_cumulative_volume: int = 0
    put_vwap: float = 0.0
    spot_cumulative_pv: float = 0.0
    spot_cumulative_volume: int = 0
    spot_vwap: float = 0.0
    last_reset_date: str = ""


class PremiumDivergenceEngine:
    """Track premium vs spot VWAP divergence.

    Used to detect hidden accumulation/distribution.
    """

    def __init__(self) -> None:
        self._state = PremiumVWAPState()
        self._state.last_reset_date = now_ist().strftime("%Y-%m-%d")

    def update(
        self,
        premium_price: float,
        spot_price: float,
        volume: int,
        is_call: bool = True,
    ) -> dict[str, float]:
        """Update VWAP values with new tick.

        Parameters
        ----------
        premium_price : float
            Option premium price.
        spot_price : float
            Underlying spot price.
        volume : int
            Trading volume.
        is_call : bool
            True for call option, False for put.

        Returns
        -------
        dict
            Current VWAP gap values.
        """
        current_date = now_ist().strftime("%Y-%m-%d")
        if current_date != self._state.last_reset_date:
            self._state = PremiumVWAPState()
            self._state.last_reset_date = current_date

        if spot_price > 0 and volume > 0:
            self._state.spot_cumulative_pv += spot_price * volume
            self._state.spot_cumulative_volume += volume
            self._state.spot_vwap = (
                self._state.spot_cumulative_pv / self._state.spot_cumulative_volume
                if self._state.spot_cumulative_volume > 0 else 0
            )

        if premium_price > 0 and volume > 0:
            if is_call:
                self._state.call_cumulative_pv += premium_price * volume
                self._state.call_cumulative_volume += volume
                self._state.call_vwap = (
                    self._state.call_cumulative_pv / self._state.call_cumulative_volume
                    if self._state.call_cumulative_volume > 0 else 0
                )
            else:
                self._state.put_cumulative_pv += premium_price * volume
                self._state.put_cumulative_volume += volume
                self._state.put_vwap = (
                    self._state.put_cumulative_pv / self._state.put_cumulative_volume
                    if self._state.put_cumulative_volume > 0 else 0
                )

        return self.get_gaps()

    def get_gaps(self) -> dict[str, float]:
        """Calculate VWAP gaps.

        Returns
        -------
        dict
            call_gap, put_gap, raw_call, raw_put, spot_vwap.
        """
        call_gap = 0.0
        put_gap = 0.0

        if self._state.spot_vwap > 0:
            call_gap = (self._state.call_vwap - self._state.spot_vwap) / self._state.spot_vwap
            put_gap = (self._state.put_vwap - self._state.spot_vwap) / self._state.spot_vwap

        return {
            "call_gap": call_gap,
            "put_gap": put_gap,
            "call_vwap": self._state.call_vwap,
            "put_vwap": self._state.put_vwap,
            "spot_vwap": self._state.spot_vwap,
        }

    def detect_hidden_accumulation(self, pcr_trend: str) -> str:
        """Detect hidden accumulation signals."""
        gaps = self.get_gaps()

        if gaps["call_gap"] > 0.02 and pcr_trend == "RISING":
            logger.info("Hidden bullish accumulation detected: call_gap=%.2f%%", gaps["call_gap"] * 100)
            return "HIDDEN_BULLISH"

        if gaps["put_gap"] > 0.02 and pcr_trend == "FALLING":
            logger.info("Hidden bearish accumulation detected: put_gap=%.2f%%", gaps["put_gap"] * 100)
            return "HIDDEN_BEARISH"

        return "NONE"

    def reset(self) -> None:
        """Reset state for new trading day."""
        self._state = PremiumVWAPState()
        self._state.last_reset_date = now_ist().strftime("%Y-%m-%d")
