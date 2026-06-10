"""Signal generation: ORB, VWAP, EMA9, Confluence, COI PCR, GEX, IV Skew, Max Pain, Premium Divergence.

Produces Signal objects that pass through the risk gate.
**Never places orders directly.**

Source citation:
    > src/strategy/AGENTS.md - No order placement, no risk overrides.
"""
from __future__ import annotations

from .orb_strategy import ORBStrategy
from .signal_generator import SignalGenerator
from .vwap_engine import VWAPEngine
from .ema_filter import EMAFilter
from .confluence import ConfluenceEngine
from .coi_pcr import COIPCRCalculator
from .gex_calculator import GEXCalculator
from .iv_skew import IVSkewCalculator
from .max_pain import MaxPainTracker
from .premium_divergence import PremiumDivergenceEngine
from .momentum_index import CompositeMomentumIndex, TrapDetector
from .signal_formatter import SignalFormatter

__all__ = [
    "ORBStrategy",
    "SignalGenerator",
    "VWAPEngine",
    "EMAFilter",
    "ConfluenceEngine",
    "COIPCRCalculator",
    "GEXCalculator",
    "IVSkewCalculator",
    "MaxPainTracker",
    "PremiumDivergenceEngine",
    "CompositeMomentumIndex",
    "TrapDetector",
    "SignalFormatter",
]
