"""Unit tests for the risk gate — the Five Hard Vetoes.

Source citation:
    > src/risk/AGENTS.md — Verification: all 5 vetoes, RiskApprovedOrder
      fields, each veto logs the specific reason code.
"""
from __future__ import annotations

from datetime import time
from unittest.mock import MagicMock, PropertyMock

import pytest
from freezegun import freeze_time

from src.risk.risk_manager import (
    RiskApprovedOrder,
    RiskManager,
    Signal,
    PositionTrackerProtocol,
    TradeJournalProtocol,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def capital() -> float:
    return 200_000.0


@pytest.fixture
def position_tracker() -> PositionTrackerProtocol:
    tracker = MagicMock(spec=PositionTrackerProtocol)
    type(tracker).daily_loss_pct = PropertyMock(return_value=0.01)  # below 4% threshold
    return tracker


@pytest.fixture
def trade_journal() -> TradeJournalProtocol:
    journal = MagicMock(spec=TradeJournalProtocol)
    journal.trade_count_today.return_value = 0  # below 3-trade limit
    return journal


@pytest.fixture
def risk_manager(capital: float, position_tracker: PositionTrackerProtocol, trade_journal: TradeJournalProtocol) -> RiskManager:
    return RiskManager(capital=capital, position_tracker=position_tracker, trade_journal=trade_journal)


@pytest.fixture
def valid_signal() -> Signal:
    return Signal(
        instrument_key="NSE_FO|12345",
        symbol="NIFTY",
        side="BUY",
        suggested_qty=25,
        entry_price=150.0,
        stop_loss=140.0,
        target=170.0,
        confidence=0.8,
        metadata={"open_interest": 150_000},
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    """When all five vetoes pass, can_trade returns a RiskApprovedOrder."""

    def test_returns_risk_approved_order(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert isinstance(result, RiskApprovedOrder)

    def test_order_has_required_fields(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert result.instrument_key == "NSE_FO|12345"
            assert result.qty == 25
            assert result.entry_price == 150.0
            assert result.stop_loss == 140.0
            assert result.target == 170.0
            assert len(result.tag) > 10  # uuid4 hex
            assert result.tag.startswith("trader-")
            assert isinstance(result.signal_snapshot, Signal)

    def test_signal_snapshot_is_frozen(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert result.signal_snapshot == valid_signal
            import dataclasses
            assert dataclasses.fields(result.signal_snapshot) == dataclasses.fields(valid_signal)


# ---------------------------------------------------------------------------
# Veto 1: Time check
# ---------------------------------------------------------------------------


class TestTimeVeto:
    """BLOCK_NEW_ENTRIES_AFTER (15:15 IST) blocks new entries."""

    def test_passes_before_cutoff(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        """10:00 AM should pass."""
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert isinstance(result, RiskApprovedOrder)

    def test_fails_after_cutoff(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        """15:16 should veto."""
        with freeze_time("2026-06-09 15:16:00+05:30"):
            with pytest.raises(Exception) as exc_info:
                risk_manager.can_trade(valid_signal)
            from src.utils.exception_handler import RiskVetoError
            assert isinstance(exc_info.value, RiskVetoError)
            assert exc_info.value.reason_code == "VETO_TIME"

    def test_fails_exactly_at_cutoff(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        """15:15 exactly should veto."""
        with freeze_time("2026-06-09 15:15:00+05:30"):
            with pytest.raises(Exception):
                risk_manager.can_trade(valid_signal)

    def test_reason_code_is_veto_time(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        with freeze_time("2026-06-09 15:16:00+05:30"):
            try:
                risk_manager.can_trade(valid_signal)
            except Exception as e:
                from src.utils.exception_handler import RiskVetoError
                assert isinstance(e, RiskVetoError)
                assert e.reason_code == "VETO_TIME"


# ---------------------------------------------------------------------------
# Veto 2: Daily loss check
# ---------------------------------------------------------------------------


class TestDailyLossVeto:
    """MAX_DAILY_LOSS_PCT (4%) blocks new entries when breached."""

    def test_passes_below_threshold(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert isinstance(result, RiskApprovedOrder)

    def test_fails_at_threshold(self, risk_manager: RiskManager, valid_signal: Signal, position_tracker: PositionTrackerProtocol) -> None:
        type(position_tracker).daily_loss_pct = PropertyMock(return_value=0.04)
        with freeze_time("2026-06-09 10:00:00+05:30"):
            with pytest.raises(Exception):
                risk_manager.can_trade(valid_signal)

    def test_fails_above_threshold(self, risk_manager: RiskManager, valid_signal: Signal, position_tracker: PositionTrackerProtocol) -> None:
        type(position_tracker).daily_loss_pct = PropertyMock(return_value=0.05)
        with freeze_time("2026-06-09 10:00:00+05:30"):
            try:
                risk_manager.can_trade(valid_signal)
            except Exception as e:
                from src.utils.exception_handler import RiskVetoError
                assert isinstance(e, RiskVetoError)
                assert e.reason_code == "VETO_DAILY_LOSS"


# ---------------------------------------------------------------------------
# Veto 3: Trade count check
# ---------------------------------------------------------------------------


class TestTradeCountVeto:
    """MAX_TRADES_PER_DAY (3) blocks when reached."""

    def test_passes_below_limit(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert isinstance(result, RiskApprovedOrder)

    def test_fails_at_limit(self, risk_manager: RiskManager, valid_signal: Signal, trade_journal: TradeJournalProtocol) -> None:
        trade_journal.trade_count_today.return_value = 3
        with freeze_time("2026-06-09 10:00:00+05:30"):
            try:
                risk_manager.can_trade(valid_signal)
            except Exception as e:
                from src.utils.exception_handler import RiskVetoError
                assert isinstance(e, RiskVetoError)
                assert e.reason_code == "VETO_TRADE_LIMIT"

    def test_passes_below_limit_exact(self, risk_manager: RiskManager, valid_signal: Signal, trade_journal: TradeJournalProtocol) -> None:
        trade_journal.trade_count_today.return_value = 2
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert isinstance(result, RiskApprovedOrder)


# ---------------------------------------------------------------------------
# Veto 4: Position size check
# ---------------------------------------------------------------------------


class TestPositionSizeVeto:
    """MAX_RISK_PER_TRADE_PCT (2%) of capital."""

    def test_passes_small_risk(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        # risk = 25 * |150 - 140| = 250, max_risk = 200_000 * 0.02 = 4_000
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)
            assert isinstance(result, RiskApprovedOrder)

    def test_fails_large_risk(self, risk_manager: RiskManager) -> None:
        # risk = 100 * |5000 - 4000| = 100_000 > 4_000
        big_signal = Signal(
            instrument_key="NSE_FO|99999",
            symbol="NIFTY",
            side="BUY",
            suggested_qty=5000,
            entry_price=100.0,  # 5000 * |100 - 99| = 5000 > 4000
            stop_loss=99.0,
            target=105.0,
        )
        with freeze_time("2026-06-09 10:00:00+05:30"):
            try:
                risk_manager.can_trade(big_signal)
            except Exception as e:
                from src.utils.exception_handler import RiskVetoError
                assert isinstance(e, RiskVetoError)
                assert e.reason_code == "VETO_POSITION_SIZE"

    def test_edge_case_exact(self, risk_manager: RiskManager) -> None:
        # risk = 4000 exactly should pass (risk must be > max_risk to veto)
        signal = Signal(
            instrument_key="NSE_FO|1",
            symbol="NIFTY",
            side="BUY",
            suggested_qty=2000,
            entry_price=2.0,
            stop_loss=0.0,  # 2000 * 2.0 = 4000, not > 4000
            target=3.0,
        )
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(signal)
            assert isinstance(result, RiskApprovedOrder)


# ---------------------------------------------------------------------------
# Veto 5: OI liquidity check
# ---------------------------------------------------------------------------


class TestLiquidityVeto:
    """MIN_OPEN_INTEREST (50_000) blocks low-liquidity instruments."""

    def test_passes_high_oi(self, risk_manager: RiskManager, valid_signal: Signal) -> None:
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(valid_signal)  # OI=150_000
            assert isinstance(result, RiskApprovedOrder)

    def test_fails_low_oi(self, risk_manager: RiskManager) -> None:
        signal = Signal(
            instrument_key="NSE_FO|1",
            symbol="NIFTY",
            side="BUY",
            suggested_qty=25,
            entry_price=100.0,
            stop_loss=95.0,
            target=110.0,
            metadata={"open_interest": 10_000},
        )
        with freeze_time("2026-06-09 10:00:00+05:30"):
            try:
                risk_manager.can_trade(signal)
            except Exception as e:
                from src.utils.exception_handler import RiskVetoError
                assert isinstance(e, RiskVetoError)
                assert e.reason_code == "VETO_LOW_LIQUIDITY"

    def test_passes_missing_oi(self, risk_manager: RiskManager) -> None:
        """No OI metadata should NOT veto (pass by default)."""
        signal = Signal(
            instrument_key="NSE_FO|1",
            symbol="NIFTY",
            side="BUY",
            suggested_qty=25,
            entry_price=100.0,
            stop_loss=95.0,
            target=110.0,
        )
        with freeze_time("2026-06-09 10:00:00+05:30"):
            result = risk_manager.can_trade(signal)
            assert isinstance(result, RiskApprovedOrder)
