"""Signal generator - orchestrates ORB, VWAP, EMA, Confluence, and COI PCR.

Produces Signal objects for the risk gate. Never places orders.

Source citation:
    > src/strategy/AGENTS.md - No order placement, no risk overrides.
    > UNIFIED_TRADING_STRATEGY.md - Core COI PCR Signals, Confluence Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from config.strategy_config import LUNCH_WINDOW_END, LUNCH_WINDOW_START
from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

from .orb_strategy import ORBStrategy
from .vwap_engine import VWAPEngine
from .ema_filter import EMAFilter
from .confluence import ConfluenceEngine, ConfluenceVote
from .coi_pcr import COIPCRCalculator
from .gex_calculator import GEXCalculator
from .iv_skew import IVSkewCalculator
from .max_pain import MaxPainTracker
from .premium_divergence import PremiumDivergenceEngine
from .momentum_index import CompositeMomentumIndex, TrapDetector

logger = get_logger(__name__)


@dataclass
class Signal:
    """A trading signal produced by the strategy layer."""
    symbol: str
    side: str
    instrument_key: str
    entry_price: float
    stop_loss: float
    target: float
    qty: int
    confidence: float
    timestamp: datetime
    metadata: dict[str, Any]
    trading_bias: str = "NEUTRAL"

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = now_ist()


class SignalGenerator:
    """Orchestrates strategy components to produce signals.

    Parameters
    ----------
    orb : ORBStrategy
    vwap : VWAPEngine
    ema : EMAFilter
    confluence : ConfluenceEngine
    coi_pcr : COIPCRCalculator
    gex : GEXCalculator
    iv_skew : IVSkewCalculator
    max_pain : MaxPainTracker
    premium_div : PremiumDivergenceEngine
    momentum : CompositeMomentumIndex
    trap : TrapDetector
    """

    def __init__(
        self,
        orb: ORBStrategy | None = None,
        vwap: VWAPEngine | None = None,
        ema: EMAFilter | None = None,
        confluence: ConfluenceEngine | None = None,
        coi_pcr: COIPCRCalculator | None = None,
        gex: GEXCalculator | None = None,
        iv_skew: IVSkewCalculator | None = None,
        max_pain: MaxPainTracker | None = None,
        premium_div: PremiumDivergenceEngine | None = None,
        momentum: CompositeMomentumIndex | None = None,
        trap: TrapDetector | None = None,
    ) -> None:
        self._orb = orb or ORBStrategy()
        self._vwap = vwap or VWAPEngine()
        self._ema = ema or EMAFilter()
        self._confluence = confluence or ConfluenceEngine()
        self._coi_pcr = coi_pcr or COIPCRCalculator()
        self._gex = gex or GEXCalculator()
        self._iv_skew = iv_skew or IVSkewCalculator()
        self._max_pain = max_pain or MaxPainTracker()
        self._premium_div = premium_div or PremiumDivergenceEngine()
        self._momentum = momentum or CompositeMomentumIndex()
        self._trap = trap or TrapDetector()

    def on_tick(self, tick: dict[str, Any]) -> Signal | None:
        """Process a tick and potentially generate a signal.

        Returns a Signal if all conditions are met, else None.
        """
        symbol = tick.get("symbol", "unknown")
        price = tick.get("last_price", 0.0)
        volume = tick.get("volume", 0)
        instrument_key = tick.get("instrument_key", "")

        if price <= 0:
            return None

        self._check_lunch_exclusion()

        self._vwap.update(tick)
        vwap = self._vwap.get_vwap(symbol)
        self._ema.update(symbol, price)

        self._coi_pcr.update(tick)
        pcr = self._coi_pcr.get_pcr()
        pcr_trend = self._coi_pcr.get_pcr_trend()

        orb_direction = self._orb.check_breakout(tick)
        if orb_direction is None:
            return None

        votes = self._build_confluence_votes(tick, price, vwap, orb_direction, pcr, pcr_trend)

        conviction = self._confluence.get_conviction(votes)
        if conviction == "LOW_CONVICTION_WATCH":
            logger.info("Low conviction for %s: %s", symbol, conviction)
            return None

        if self._trap.check_trap(pcr, [], False, {}).get("is_trap", False):
            logger.info("Trap detected for %s, no signal generated", symbol)
            return None

        confidence = sum(1 for v in votes if v.passed) / len(votes) if votes else 0.5

        trading_bias = self._determine_trading_bias(orb_direction, pcr, pcr_trend)

        signal = Signal(
            symbol=symbol,
            side=orb_direction,
            instrument_key=instrument_key,
            entry_price=price,
            stop_loss=price * 0.98 if orb_direction == "LONG" else price * 1.02,
            target=price * 1.05 if orb_direction == "LONG" else price * 0.95,
            qty=1,
            confidence=confidence,
            timestamp=now_ist(),
            metadata={
                "vwap": vwap,
                "pcr": pcr,
                "pcr_trend": pcr_trend,
                "confluence_layers": [v.layer for v in votes if v.passed],
                "window_status": self._coi_pcr.get_window_status(),
            },
            trading_bias=trading_bias,
        )

        logger.info(
            "Signal generated: %s %s at %.2f (confidence=%.2f, bias=%s)",
            symbol, orb_direction, price, confidence, trading_bias,
        )
        return signal

    def _build_confluence_votes(
        self,
        tick: dict[str, Any],
        price: float,
        vwap: float,
        orb_direction: str,
        pcr: float,
        pcr_trend: str,
    ) -> list[ConfluenceVote]:
        """Build 3-layer confluence votes."""
        votes: list[ConfluenceVote] = []

        votes.append(ConfluenceVote(
            "spot_structure",
            orb_direction in ["LONG", "SHORT"],
            f"ORB {orb_direction}",
        ))

        is_premium_above_vwap = price > vwap if vwap > 0 else False
        votes.append(ConfluenceVote(
            "premium_swing",
            is_premium_above_vwap,
            "Price above VWAP",
        ))

        pcr_extreme = pcr > 1.2 or pcr < 0.8
        votes.append(ConfluenceVote(
            "oi_walls",
            pcr_extreme,
            f"COI PCR {'extreme' if pcr_extreme else 'normal'}: {pcr:.2f}",
        ))

        return votes

    def _determine_trading_bias(self, orb_direction: str, pcr: float, pcr_trend: str) -> str:
        """Determine trading bias from signals."""
        if pcr > 1.2 and pcr_trend == "RISING" and orb_direction == "SHORT":
            return "HIGH-CONVICTION BEARISH"
        elif pcr < 0.8 and pcr_trend == "FALLING" and orb_direction == "LONG":
            return "HIGH-CONVICTION BULLISH"
        return "NEUTRAL"

    def _check_lunch_exclusion(self) -> None:
        """Check if we should skip signals during lunch churn."""
        current_time = now_ist().time()
        if LUNCH_WINDOW_START <= current_time <= LUNCH_WINDOW_END:
            logger.debug("In lunch window (%s-%s), signals suppressed", LUNCH_WINDOW_START, LUNCH_WINDOW_END)

    def reset(self) -> None:
        """Reset all strategy state (called at end of day)."""
        self._orb.reset()
        self._vwap.reset()
        self._ema.reset()
        self._coi_pcr.reset()
        self._gex.reset()
        self._iv_skew.reset()
        self._max_pain.reset()
        self._premium_div.reset()
        self._momentum = CompositeMomentumIndex()
        self._trap.reset()
