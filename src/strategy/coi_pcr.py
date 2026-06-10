"""COI PCR (Change in Open Interest Put-Call Ratio) calculator.

Calculates PCR for the 7-strike window (ATM +3) and tracks trend.

Source citation:
    > UNIFIED_TRADING_STRATEGY.md — COI PCR, 7-strike window, dynamic shifting.
    > src/strategy/AGENTS.md — No order placement, no risk overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from config.strategy_config import PCR_BEARISH_TRIGGER, PCR_BULLISH_TRIGGER
from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


@dataclass
class COIPCRState:
    """State for COI PCR tracking."""
    put_oi_history: dict[int, list[float]] = field(default_factory=dict)
    call_oi_history: dict[int, list[float]] = field(default_factory=dict)
    pcr_history: list[float] = field(default_factory=list)
    last_atm_strike: float = 0.0
    window_status: str = "ALIGN"
    stabilizing_until: float = 0.0


class COIPCRCalculator:
    """Calculate COI PCR for 7-strike window (ATM +3).

    Parameters
    ----------
    window_size : int
        Number of strikes on each side of ATM (default 3, total 7 strikes).
    """

    def __init__(self, window_size: int = 3) -> None:
        self._window_size = window_size
        self._state = COIPCRState()
        self._strike_step = 50  # NIFTY default

    def update(self, tick: dict[str, Any]) -> float | None:
        """Process a tick and update COI PCR."""
        symbol = tick.get("symbol", "")
        price = tick.get("last_price", 0.0)
        oi = tick.get("oi", 0)
        instrument_key = tick.get("instrument_key", "")

        if oi is None:
            oi = 0

        strike = self._extract_strike(instrument_key, price)
        if strike is None:
            return None

        atm = round(price / self._strike_step) * self._strike_step
        if abs(strike - atm) > self._window_size * self._strike_step:
            return None

        strike_idx = int((strike - atm) / self._strike_step)
        if strike_idx not in self._state.put_oi_history:
            self._state.put_oi_history[strike_idx] = []
            self._state.call_oi_history[strike_idx] = []

        is_call = "CE" in instrument_key or "CALL" in str(tick.get("option_type", "")).upper()

        if is_call:
            self._state.call_oi_history[strike_idx].append(float(oi))
        else:
            self._state.put_oi_history[strike_idx].append(float(oi))

        return self.get_pcr(atm)

    def get_pcr(self, atm: float | None = None) -> float:
        """Calculate current COI PCR."""
        put_oi_total = sum(ois[-1] if ois else 0 for ois in self._state.put_oi_history.values())
        call_oi_total = sum(ois[-1] if ois else 0 for ois in self._state.call_oi_history.values())

        if call_oi_total == 0:
            return float("inf")

        pcr = put_oi_total / call_oi_total
        self._state.pcr_history.append(pcr)

        if len(self._state.pcr_history) > 120:
            self._state.pcr_history = self._state.pcr_history[-120:]

        return pcr

    def get_pcr_trend(self, window_minutes: int = 30) -> str:
        """Get PCR trend over specified minutes."""
        if len(self._state.pcr_history) < 4:
            return "FLAT"

        recent = self._state.pcr_history[-window_minutes * 2:] if len(self._state.pcr_history) >= window_minutes * 2 else self._state.pcr_history
        if len(recent) < 2:
            return "FLAT"

        first = sum(recent[:len(recent)//4]) / (len(recent)//4) if len(recent) >= 4 else recent[0]
        last = sum(recent[-len(recent)//4:]) / (len(recent)//4) if len(recent) >= 4 else recent[-1]

        diff = last - first

        if diff > 0.05:
            return "RISING"
        elif diff < -0.05:
            return "FALLING"
        return "FLAT"

    def shift_window(self, new_atm: float) -> None:
        """Handle window shift when spot crosses ATM midpoint."""
        if self._state.last_atm_strike != 0 and new_atm != self._state.last_atm_strike:
            self._state.window_status = "STABILIZING"
            self._state.stabilizing_until = now_ist().timestamp() + 900
            logger.info("Window shift: ATM %.0f -> %.0f, entering STABILIZING phase",
                        self._state.last_atm_strike, new_atm)

        self._state.last_atm_strike = new_atm

    def get_window_status(self) -> str:
        """Get current window status."""
        if self._state.stabilizing_until and now_ist().timestamp() < self._state.stabilizing_until:
            return "STABILIZING"
        return "ALIGN"

    def is_bullish_signal(self) -> bool:
        """Check if current PCR indicates bullish bias."""
        pcr = self.get_pcr()
        return pcr > PCR_BULLISH_TRIGGER

    def is_bearish_signal(self) -> bool:
        """Check if current PCR indicates bearish bias."""
        pcr = self.get_pcr()
        return pcr < PCR_BEARISH_TRIGGER

    def _extract_strike(self, instrument_key: str, price: float) -> int | None:
        """Extract strike price from instrument key or price."""
        try:
            if "NIFTY" in instrument_key:
                for suffix in ["CE", "PE"]:
                    if suffix in instrument_key:
                        strike_str = instrument_key.split(suffix)[-1]
                        return int(strike_str) if strike_str.isdigit() else None
        except (ValueError, IndexError):
            pass
        return int(round(price / self._strike_step) * self._strike_step)

    def reset(self) -> None:
        """Reset state for new trading day."""
        self._state = COIPCRState()

