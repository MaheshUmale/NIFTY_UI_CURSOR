"""Composite Momentum Index and Trap Detection.

Weighted combination of PCR slope, VWAP gap, and delta flow.

Source citation:
    > UNIFIED_TRADING_STRATEGY.md - momentum_index = w1.PCR_slope + w2.VWAP_gap + w3.Delta_flow.
    > src/strategy/AGENTS.md - No order placement, no risk overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MomentumState:
    """State for momentum tracking."""
    momentum_index: float = 0.0
    trap_detected: bool = False
    trap_reasons: list[str] = field(default_factory=list)


class CompositeMomentumIndex:
    """Calculate weighted momentum index.

    momentum_index = w1 * PCR_slope_norm + w2 * VWAP_gap_norm + w3 * Delta_flow_norm
    """

    def __init__(self, w1: float = 0.4, w2: float = 0.3, w3: float = 0.3) -> None:
        self._weights = (w1, w2, w3)
        self._state = MomentumState()

    def calculate(
        self,
        pcr_slope: float,
        vwap_gap: float,
        delta_flow: float,
    ) -> float:
        """Calculate composite momentum index."""
        self._state.momentum_index = (
            self._weights[0] * pcr_slope +
            self._weights[1] * vwap_gap +
            self._weights[2] * delta_flow
        )
        return self._state.momentum_index

    def get_signal(self) -> str:
        """Return signal based on momentum index.

        Returns "GO_LONG", "NO_GO", or "HOLD".
        """
        if self._state.momentum_index > 0.5:
            return "GO_LONG"
        elif self._state.momentum_index < -0.5:
            return "NO_GO"
        return "HOLD"


class TrapDetector:
    """Detect trap conditions (no-trade signatures)."""

    def __init__(self) -> None:
        self._state = MomentumState()

    def check_trap(
        self,
        pcr: float,
        pcr_history: list[float],
        max_pain_static: bool,
        vol_oi_ratios: dict[str, float],
    ) -> dict[str, Any]:
        """Check for trap conditions.

        Parameters
        ----------
        pcr : float
            Current PCR value.
        pcr_history : list[float]
            Historical PCR values.
        max_pain_static : bool
            Whether Max Pain has stayed static.
        vol_oi_ratios : dict
            Volume/OI ratios by strike.

        Returns
        -------
        dict
            Trap detection result with 'is_trap', 'reasons', 'should_avoid'.
        """
        reasons: list[str] = []
        is_trap = False

        # PCR flat around 0.8-1.0
        if 0.8 <= pcr <= 1.0:
            reasons.append("PCR_FLAT_ZONE")

        # Max Pain static
        if max_pain_static:
            reasons.append("MAX_PAIN_STATIC")

        # Volume/OI spike on both sides without direction
        high_volume_on_calls = any(
            ratio > 2.0 for strike, ratio in vol_oi_ratios.items() if "CE" in strike
        )
        high_volume_on_puts = any(
            ratio > 2.0 for strike, ratio in vol_oi_ratios.items() if "PE" in strike
        )

        if high_volume_on_calls and high_volume_on_puts:
            reasons.append("BILATERAL_VOLUME_SPIKE")
            is_trap = True

        self._state.trap_detected = is_trap
        self._state.trap_reasons = reasons

        return {
            "is_trap": is_trap,
            "reasons": reasons,
            "should_avoid": is_trap,
        }

    def reset(self) -> None:
        """Reset state."""
        self._state = MomentumState()
