"""Gamma Exposure (GEX) calculator.

Computes net dealer gamma position for option chain.

Source citation:
    > UNIFIED_TRADING_STRATEGY.md - Net GEX = Call_GEX - Put_GEX.
    > src/strategy/AGENTS.md - No order placement, no risk overrides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GEXState:
    """State for GEX tracking."""
    total_call_gex: float = 0.0
    total_put_gex: float = 0.0
    net_gex: float = 0.0
    zero_gamma_level: float = 0.0
    call_wall_strike: float = 0.0
    put_wall_strike: float = 0.0


class GEXCalculator:
    """Calculate Gamma Exposure for option chain.

    Parameters
    ----------
    strike_step : int
        Strike interval (50 for NIFTY, 100 for BANKNIFTY).
    """

    def __init__(self, strike_step: int = 50) -> None:
        self._strike_step = strike_step
        self._state = GEXState()
        self._chain_cache: list[dict[str, Any]] = []

    def update_chain(self, option_chain: list[dict[str, Any]]) -> GEXState:
        """Process option chain and calculate GEX."""
        self._chain_cache = option_chain

        call_gex_total = 0.0
        put_gex_total = 0.0
        max_call_gex = 0.0
        max_put_gex = 0.0
        call_wall = 0.0
        put_wall = 0.0

        for opt in option_chain:
            call_gex = opt.get("call_gamma", 0.0) * opt.get("call_oi", 0)
            put_gex = opt.get("put_gamma", 0.0) * opt.get("put_oi", 0)

            call_gex_total += call_gex
            put_gex_total += put_gex

            if call_gex > max_call_gex:
                max_call_gex = call_gex
                call_wall = opt.get("strike", 0)

            if put_gex > max_put_gex:
                max_put_gex = put_gex
                put_wall = opt.get("strike", 0)

        self._state.total_call_gex = call_gex_total
        self._state.total_put_gex = put_gex_total
        self._state.net_gex = call_gex_total - put_gex_total
        self._state.call_wall_strike = call_wall
        self._state.put_wall_strike = put_wall

        self._state.zero_gamma_level = self._find_zero_gamma(option_chain)

        return self._state

    def _find_zero_gamma(self, chain: list[dict[str, Any]]) -> float:
        """Find strike where net GEX crosses zero."""
        if not chain:
            return 0.0

        sorted_chain = sorted(chain, key=lambda x: x.get("strike", 0))

        for i in range(len(sorted_chain) - 1):
            curr_strike = sorted_chain[i].get("strike", 0)
            next_strike = sorted_chain[i + 1].get("strike", 0)

            curr_net = (
                sorted_chain[i].get("call_gamma", 0.0) * sorted_chain[i].get("call_oi", 0) -
                sorted_chain[i].get("put_gamma", 0.0) * sorted_chain[i].get("put_oi", 0)
            )
            next_net = (
                sorted_chain[i + 1].get("call_gamma", 0.0) * sorted_chain[i + 1].get("call_oi", 0) -
                sorted_chain[i + 1].get("put_gamma", 0.0) * sorted_chain[i + 1].get("put_oi", 0)
            )

            if curr_net * next_net < 0:
                if next_net != curr_net:
                    ratio = -curr_net / (next_net - curr_net)
                    return curr_strike + ratio * (next_strike - curr_strike)

        return 0.0

    def is_positive_gamma(self) -> bool:
        """Return True if net GEX is positive (dealers long gamma)."""
        return self._state.net_gex > 0

    def is_negative_gamma(self) -> bool:
        """Return True if net GEX is negative (dealers short gamma)."""
        return self._state.net_gex < 0

    def reset(self) -> None:
        """Reset state for new trading day."""
        self._state = GEXState()
        self._chain_cache = []
