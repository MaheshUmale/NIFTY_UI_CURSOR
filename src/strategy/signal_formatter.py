"""Signal formatter - produces output in unified format.

Formats signals according to UNIFIED_TRADING_STRATEGY.md.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


class SignalFormatter:
    """Format signals in unified output format."""

    @staticmethod
    def format(
        signal: dict[str, Any],
        spot_price: float,
        atm_strike: float,
        pcr: float,
        pcr_trend: str,
        window_status: str,
        market_structure: str,
        premium_swings: str,
        arrival_coi_shift: str,
        institutional_context: str,
        trading_bias: str,
    ) -> str:
        """Format a signal in unified format.

        Returns
        -------
        str
            Formatted signal string.
        """
        ts = now_ist()
        day_regime = "Thursday Expiry" if ts.weekday() == 3 else "Standard"

        lines = [
            f"Timestamp: {ts.strftime('%H:%M')} | Day Regime: {day_regime} | Index tracked: {signal.get('symbol', 'NIFTY')}",
            f"Index Spot: {spot_price:.2f} | ATM Strike: {int(atm_strike)} | Window Status: {window_status}",
            f"Current COI PCR: {pcr:.2f} | Trend (last 30 mins): {pcr_trend}",
            f"Absolute OI Walls: [Strike] (Resistance) vs [Strike] (Support)",
            "Confluence Analysis:",
            f"  Market Structure: {market_structure}",
            f"  Premium Swings: {premium_swings}",
            f"  Arrival COI Shift: {arrival_coi_shift}",
            f"  Institutional Context: {institutional_context}",
            f"Trading Bias: {trading_bias}",
            f"Action: See signal details below",
        ]

        return "\n".join(lines)

    @staticmethod
    def format_summary(signal: dict[str, Any]) -> str:
        """Format a concise signal summary."""
        return (
            f"{signal.get('symbol', 'NIFTY')} {signal.get('side', 'N/A')} "
            f"@ {signal.get('entry_price', 0):.2f} "
            f"(confidence={signal.get('confidence', 0):.2f})"
        )
