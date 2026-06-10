"""Confluence engine - multi-layer signal validation.

Requires at least 2 of 3 layers to agree before a signal is published.

Source citation:
    > src/strategy/AGENTS.md - 2-of-3 layer minimum, LOW_CONVICTION_WATCH.
    > UNIFIED_TRADING_STRATEGY.md - Layer A: Spot Structure, Layer B: Premium Swing, Layer C: OI Walls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.strategy_config import CONFLUENCE_MIN_LAYERS, CONFLUENCE_TOTAL_LAYERS
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConfluenceVote:
    """A single confluence layer vote."""
    layer: str
    passed: bool
    reason: str = ""


class ConfluenceEngine:
    """Multi-layer confluence gate.

    Layer A: Spot Market Structure Analysis
        - LONG: Higher Highs / Higher Lows pattern OR breakout above swing high
        - SHORT: Lower Highs / Lower Lows pattern OR breakdown below swing low

    Layer B: Option Premium Swing & Volatility Check
        - LONG (Call): Structural breakout above morning swing high + volume spike
        - SHORT (Put): Structural breakout above morning swing high + volume spike

    Layer C: High Absolute OI Walls & Arrival COI Shifts
        - LONG Entry: Spot touches Put OI Wall + Put COI spikes + Call COI drops
        - SHORT Entry: Spot touches Call OI Wall + Call COI spikes + Put COI drops

    Parameters
    ----------
    min_layers : int
        Minimum number of layers that must agree (default 2).
    total_layers : int
        Total number of confluence layers (default 3).
    """

    def __init__(self, min_layers: int = CONFLUENCE_MIN_LAYERS, total_layers: int = CONFLUENCE_TOTAL_LAYERS) -> None:
        self._min_layers = min_layers
        self._total_layers = total_layers

    def evaluate(self, votes: list[ConfluenceVote]) -> bool:
        """Evaluate confluence votes.

        Returns True if at least min_layers votes passed.
        """
        passed = sum(1 for v in votes if v.passed)
        return passed >= self._min_layers

    def get_conviction(self, votes: list[ConfluenceVote]) -> str:
        """Return conviction level based on votes.

        Returns "ACTIONABLE" if min_layers passed, else "LOW_CONVICTION_WATCH".
        """
        if self.evaluate(votes):
            return "ACTIONABLE"
        return "LOW_CONVICTION_WATCH"

    def get_trading_bias(self, votes: list[ConfluenceVote]) -> str:
        """Determine trading bias from confluence votes.

        Returns one of:
        - HIGH-CONVICTION BULLISH
        - HIGH-CONVICTION BEARISH
        - NEUTRAL
        - GAMMA LOCK
        """
        spot_votes = [v for v in votes if v.layer == "spot_structure"]
        premium_votes = [v for v in votes if v.layer == "premium_swing"]
        oi_votes = [v for v in votes if v.layer == "oi_walls"]

        if oi_votes and oi_votes[0].passed:
            for sv in spot_votes:
                if sv.passed and "LOW" in sv.reason.upper():
                    return "GAMMA LOCK"

        bullish_spot = any(v.passed for v in spot_votes if "HIGH" in v.reason.upper() or "BREAK" in v.reason.upper())
        bullish_premium = any(v.passed for v in premium_votes)

        if bullish_spot and bullish_premium:
            return "HIGH-CONVICTION BULLISH"

        bearish_spot = any(v.passed for v in spot_votes if "LOW" in v.reason.upper() or "BREAK" in v.reason.upper())
        bearish_premium = any(v.passed for v in premium_votes)

        if bearish_spot and bearish_premium:
            return "HIGH-CONVICTION BEARISH"

        return "NEUTRAL"

    def reset(self) -> None:
        """Reset state."""
        pass
