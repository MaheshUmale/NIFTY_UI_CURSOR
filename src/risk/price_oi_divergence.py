"""Price-OI Divergence Filter.

Veto signals when price moves opposite to institutional flow (COI PCR).

Source citation:
    > UNIFIED_TRADING_STRATEGY.md - Price-OI Divergence Filter (Trap Check).
    > src/risk/AGENTS.md - Five Hard Vetoes, RiskApprovedOrder fields.
"""
from __future__ import annotations

from datetime import time
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


class PriceOIDivergenceFilter:
    """Filter that vetoes when price moves opposite to COI PCR trend."""

    def __init__(self) -> None:
        self._european_window_start = time(12, 30)
        self._european_window_end = time(13, 0)

    def should_veto_long(
        self,
        price_moving_up: bool,
        pcr_trend: str,
    ) -> bool:
        """Veto long if price up but PCR falling.

        This indicates institutions selling calls (retail trap).
        """
        if price_moving_up and pcr_trend == "FALLING":
            logger.warning(
                "VETO LONG: Price moving up but PCR falling - retail trap"
            )
            return True
        return False

    def should_veto_short(
        self,
        price_moving_down: bool,
        pcr_trend: str,
    ) -> bool:
        """Veto short if price down but PCR rising.

        This indicates institutions selling puts (short trap).
        """
        if price_moving_down and pcr_trend == "RISING":
            logger.warning(
                "VETO SHORT: Price moving down but PCR rising - short trap"
            )
            return True
        return False

    def is_european_window(self) -> bool:
        """Check if current time is in European window (12:30-13:00)."""
        current_time = now_ist().time()
        return self._european_window_start <= current_time <= self._european_window_end

    def get_european_window_status(self) -> dict[str, bool]:
        """Return European window status with recommendation."""
        in_window = self.is_european_window()
        return {
            "in_european_window": in_window,
            "recommendation": "WAIT_FOR_CONFIRMATION" if in_window else "NORMAL",
        }
