"""Risk gate — the Five Hard Vetoes.

The only module that can transform a ``Signal`` into a ``RiskApprovedOrder``.

**VETO POWER is absolute.** If ``can_trade(signal)`` returns ``False``,
execution **must not** proceed. No override flag, no admin override,
no ``force=True`` parameter.

Dependency rules
----------------
- Imports from ``config.risk_constants`` (single source of truth).
- Imports from ``src.utils.time_utils`` (time helpers).
- Imports from ``src.utils.exception_handler`` (RiskVetoError).
- **Does NOT** import from ``src.execution``, ``src.strategy``, ``src.data``,
  or ``src.auth``.
- ``TradeJournal`` is injected via constructor, not imported directly.

Source citation:
    > src/risk/AGENTS.md — Five Hard Vetoes, RiskApprovedOrder fields.
    > config/AGENTS.md — IMMUTABLE risk rules.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from config.risk_constants import (
    BLOCK_NEW_ENTRIES_AFTER,
    MAX_DAILY_LOSS_PCT,
    MAX_RISK_PER_TRADE_PCT,
    MAX_TRADES_PER_DAY,
    MIN_OPEN_INTEREST,
    VETO_DAILY_LOSS,
    VETO_LOW_LIQUIDITY,
    VETO_POSITION_SIZE,
    VETO_TIME,
    VETO_TRADE_LIMIT,
)
from src.utils.exception_handler import RiskVetoError
from src.utils.time_utils import now_ist


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    """A trading signal produced by the strategy layer.

    This is a **suggestion** only — the risk gate decides whether it may
    become an order.

    Attributes
    ----------
    instrument_key : str
        Upstox instrument key (e.g. ``NSE_FO|12345``).
    symbol : str
        Index symbol (e.g. ``NIFTY``).
    side : str
        ``"BUY"`` or ``"SELL"``.
    suggested_qty : int
        Number of contracts suggested by the strategy.
    entry_price : float
        Suggested entry price (premium for options).
    stop_loss : float
        Suggested stop-loss price.
    target : float
        Suggested target price.
    signal_ts : datetime
        When the signal was generated (IST-aware).
    confidence : float
        Strategy confidence score (0.0–1.0).
    metadata : dict[str, Any]
        Arbitrary strategy-specific context (confluence layers, etc.).
    """

    instrument_key: str
    symbol: str
    side: str
    suggested_qty: int
    entry_price: float
    stop_loss: float
    target: float
    signal_ts: datetime = field(default_factory=now_ist)
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskApprovedOrder:
    """An order that has passed all five risk vetoes and may be placed.

    Attributes
    ----------
    instrument_key : str
    qty : int
        Final quantity (may be capped by the risk gate).
    entry_price : float
    stop_loss : float
    target : float
    tag : str
        Client-generated uuid4 tag for idempotency.
        Format: ``trader-{date}-{uuid4}``.
    signal_snapshot : Signal
        Frozen copy of the original signal that produced this order.
    approved_at : datetime
        IST-aware timestamp of approval.
    """

    instrument_key: str
    qty: int
    entry_price: float
    stop_loss: float
    target: float
    tag: str
    signal_snapshot: Signal
    approved_at: datetime = field(default_factory=now_ist)


# ---------------------------------------------------------------------------
# Position tracker interface (injected, not imported)
# ---------------------------------------------------------------------------


class PositionTrackerProtocol:
    """Duck-typed interface for the position tracker.

    The risk gate calls ``daily_loss_pct`` — the execution layer provides
    the concrete implementation.
    """

    @property
    def daily_loss_pct(self) -> float:
        """Realised + unrealised loss as a fraction of capital (0.0–1.0)."""
        ...


class InstrumentDataProtocol:
    """Duck-typed interface for instrument market data.

    The risk gate calls ``open_interest`` for the OI liquidity veto.
    """

    @property
    def open_interest(self) -> int | None:
        """Current open interest in contracts, or ``None`` if unknown."""
        ...


class TradeJournalProtocol:
    """Duck-typed interface for the trade journal.

    The risk gate calls ``trade_count_today()`` for the trade-limit veto.
    """

    def trade_count_today(self) -> int:
        """Number of round-trip trades already recorded today."""
        ...


# ---------------------------------------------------------------------------
# Risk manager
# ---------------------------------------------------------------------------


class RiskManager:
    """The VETO POWER gate.

    Parameters
    ----------
    capital : float
        Deployable trading capital in INR.
    position_tracker : PositionTrackerProtocol
    trade_journal : TradeJournalProtocol
    """

    def __init__(
        self,
        capital: float,
        position_tracker: PositionTrackerProtocol,
        trade_journal: TradeJournalProtocol,
    ) -> None:
        self._capital = capital
        self._position_tracker = position_tracker
        self._trade_journal = trade_journal

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_trade(self, signal: Signal) -> RiskApprovedOrder:
        """Run the Five Hard Vetoes on ``signal``.

        Parameters
        ----------
        signal : Signal
            The signal produced by the strategy layer.

        Returns
        -------
        RiskApprovedOrder
            If all five vetoes pass. Carries a uuid4 ``tag`` and a frozen
            ``signal_snapshot``.

        Raises
        ------
        RiskVetoError
            With the specific ``reason_code`` of the first veto that failed.
            This is not a recoverable error — the signal must be discarded.
        """
        signal_log = {
            "instrument_key": signal.instrument_key,
            "symbol": signal.symbol,
            "side": signal.side,
            "qty": signal.suggested_qty,
        }

        # 1. Time check
        self._veto_time(signal, signal_log)

        # 2. Daily loss check
        self._veto_daily_loss(signal, signal_log)

        # 3. Trade count check
        self._veto_trade_count(signal, signal_log)

        # 4. Position size check
        self._veto_position_size(signal, signal_log)

        # 5. OI liquidity check (delegated — OI comes from the signal metadata
        #    or the instrument data protocol, not from Upstox directly here)
        self._veto_liquidity(signal, signal_log)

        # All vetoes passed — build the approved order
        tag = self._generate_tag()
        return RiskApprovedOrder(
            instrument_key=signal.instrument_key,
            qty=signal.suggested_qty,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            target=signal.target,
            tag=tag,
            signal_snapshot=signal,
        )

    # ------------------------------------------------------------------
    # Individual vetoes (each may raise RiskVetoError)
    # ------------------------------------------------------------------

    def _veto_time(self, signal: Signal, ctx: dict[str, Any]) -> None:
        """Veto if the current time is at or past BLOCK_NEW_ENTRIES_AFTER."""
        if now_ist().time() >= BLOCK_NEW_ENTRIES_AFTER:
            raise RiskVetoError(
                f"Time veto: {now_ist().strftime('%H:%M')} >= {BLOCK_NEW_ENTRIES_AFTER}",
                reason_code=VETO_TIME,
            )

    def _veto_daily_loss(self, signal: Signal, ctx: dict[str, Any]) -> None:
        """Veto if daily loss exceeds MAX_DAILY_LOSS_PCT."""
        pct = self._position_tracker.daily_loss_pct
        if pct is not None and pct >= MAX_DAILY_LOSS_PCT:
            raise RiskVetoError(
                f"Daily loss veto: {pct:.2%} >= {MAX_DAILY_LOSS_PCT:.0%}",
                reason_code=VETO_DAILY_LOSS,
            )

    def _veto_trade_count(self, signal: Signal, ctx: dict[str, Any]) -> None:
        """Veto if today's trade count is at or above MAX_TRADES_PER_DAY."""
        count = self._trade_journal.trade_count_today()
        if count >= MAX_TRADES_PER_DAY:
            raise RiskVetoError(
                f"Trade limit veto: {count} >= {MAX_TRADES_PER_DAY}",
                reason_code=VETO_TRADE_LIMIT,
            )

    def _veto_position_size(self, signal: Signal, ctx: dict[str, Any]) -> None:
        """Veto if position risk exceeds MAX_RISK_PER_TRADE_PCT of capital.

        Risk = qty * abs(entry_price - stop_loss).
        """
        risk = signal.suggested_qty * abs(signal.entry_price - signal.stop_loss)
        max_risk = self._capital * MAX_RISK_PER_TRADE_PCT
        if risk > max_risk:
            raise RiskVetoError(
                f"Position size veto: risk {risk:.2f} > {max_risk:.2f} "
                f"({MAX_RISK_PER_TRADE_PCT:.0%} of {self._capital:.0f})",
                reason_code=VETO_POSITION_SIZE,
            )

    def _veto_liquidity(self, signal: Signal, ctx: dict[str, Any]) -> None:
        """Veto if open interest is below the minimum threshold.

        Reads OI from signal metadata (populated by the data layer).
        If OI is not available (``None``), the veto **passes** — we do not
        block trades on missing data.
        """
        oi = signal.metadata.get("open_interest")
        if oi is not None and oi < MIN_OPEN_INTEREST:
            raise RiskVetoError(
                f"Liquidity veto: OI {oi} < {MIN_OPEN_INTEREST}",
                reason_code=VETO_LOW_LIQUIDITY,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_tag() -> str:
        """Generate a unique, deterministic trade tag."""
        import datetime as _dt

        date_str = _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%d")
        uid = uuid.uuid4().hex[:8]
        return f"trader-{date_str}-{uid}"