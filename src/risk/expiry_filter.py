"""Expiry Day Anomaly Mitigation.

Handles Thursday expiry special rules and gamma lock.

Source citation:
    > UNIFIED_TRADING_STRATEGY.md - Expiry Day Anomaly Mitigation Protocol.
    > src/risk/AGENTS.md - Five Hard Vetoes, RiskApprovedOrder fields.
"""
from __future__ import annotations

from datetime import time, datetime
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import now_ist, IST

logger = get_logger(__name__)


class ExpiryDayFilter:
    """Handle expiry day special rules."""

    def __init__(self) -> None:
        self._gamma_lock_start = time(13, 30)

    def is_thursday_expiry(self) -> bool:
        """Check if today is a Thursday expiry day."""
        today = now_ist().date()
        return today.weekday() == 3

    def is_gamma_lock_period(self) -> bool:
        """Check if we are in gamma lock period (post 13:30 on Thursdays)."""
        if not self.is_thursday_expiry():
            return False
        current_time = now_ist().time()
        return current_time >= self._gamma_lock_start

    def is_extreme_pcr(self, pcr: float) -> bool:
        """Check if PCR is extreme (indicates gamma flip/unwinding)."""
        if self.is_gamma_lock_period():
            return pcr > 2.5 or pcr < 0.2
        return False

    def get_pcr_threshold(
        self,
        base_bullish: float = 1.2,
        base_bearish: float = 0.8,
    ) -> dict[str, float]:
        """Get PCR thresholds adjusted for expiry day.

        On Thursdays, thresholds are widened to avoid noise.
        """
        if self.is_thursday_expiry():
            return {
                "bullish": 1.4,
                "bearish": 0.6,
            }
        return {
            "bullish": base_bullish,
            "bearish": base_bearish,
        }

    def check_expiry_signal_validity(
        self,
        pcr: float,
        pcr_trend: str,
    ) -> dict[str, Any]:
        """Check if signal is valid for expiry day.

        Returns
        -------
        dict
            'valid': bool, 'status': str, 'reason': str or None.
        """
        if self.is_gamma_lock_period():
            if self.is_extreme_pcr(pcr):
                return {
                    "valid": False,
                    "status": "EXPIRY_GAMMA_FLIP",
                    "reason": "Extreme PCR after 13:30 on expiry day - ignore directional implications",
                }

        thresholds = self.get_pcr_threshold()
        if thresholds["bullish"] > pcr > thresholds["bearish"]:
            return {
                "valid": False,
                "status": "THURSDAY_NOISE_ZONE",
                "reason": "PCR in noise zone for expiry day",
            }

        return {
            "valid": True,
            "status": "NORMAL",
            "reason": None,
        }

    def is_multi_month_validation_needed(
        self,
        current_pcr: float,
        next_month_pcr: float | None = None,
    ) -> bool:
        """Check if multi-month validation is needed.

        If current COI indicates breakout but next-month PCR is flat/opposite,
        the move may be expiry manipulation.
        """
        if not self.is_thursday_expiry() or next_month_pcr is None:
            return False

        return (
            (current_pcr > 1.4 and next_month_pcr < 0.8) or
            (current_pcr < 0.6 and next_month_pcr > 1.2)
        )
