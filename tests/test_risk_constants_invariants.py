"""Test that the immutable risk constants in ``config/risk_constants.py``
match the narrative contract in ``config/AGENTS.md`` exactly.
This is the single most important CI gate — if this test fails, no PR
merges. It prevents silent drift between the documented risk rules and
the runtime values.
Source citation:
    > config/AGENTS.md — Verification: "a CI test must assert that
      config/risk_constants.py contains exactly the values above".
"""
from __future__ import annotations
from datetime import time
from config.risk_constants import (
    BLOCK_NEW_ENTRIES_AFTER,
    CANCEL_OPEN_ORDERS_AT,
    FORCE_SQUARE_OFF_BY,
    MAX_DAILY_LOSS_PCT,
    MAX_RISK_PER_TRADE_PCT,
    MAX_TRADES_PER_DAY,
    MIN_OPEN_INTEREST,
    ORDER_PRODUCT,
    SLIPPAGE_BUFFER_PCT,
    VETO_DAILY_LOSS,
    VETO_LOW_LIQUIDITY,
    VETO_POSITION_SIZE,
    VETO_TIME,
    VETO_TRADE_LIMIT,
    EMERGENCY_FLATTEN_PCT,
)
class TestRiskConstantsLocked:
    """Every value here is **IMMUTABLE** — see config/AGENTS.md.
    If a value changes, the Risk & Compliance Auditor must sign off and
    update this test AND ``config/AGENTS.md`` atomically.
    """
    def test_block_new_entries_after(self) -> None:
        assert BLOCK_NEW_ENTRIES_AFTER == time(15, 15)
    def test_cancel_open_orders_at(self) -> None:
        assert CANCEL_OPEN_ORDERS_AT == time(15, 18)
    def test_force_square_off_by(self) -> None:
        assert FORCE_SQUARE_OFF_BY == time(15, 20)
    def test_max_daily_loss_pct(self) -> None:
        assert MAX_DAILY_LOSS_PCT == 0.04
    def test_max_risk_per_trade_pct(self) -> None:
        assert MAX_RISK_PER_TRADE_PCT == 0.02
    def test_emergency_flatten_pct(self) -> None:
        assert EMERGENCY_FLATTEN_PCT == 0.05
    def test_slippage_buffer_pct(self) -> None:
        assert SLIPPAGE_BUFFER_PCT == 0.005
    def test_order_product(self) -> None:
        assert ORDER_PRODUCT == "I"
    def test_max_trades_per_day(self) -> None:
        assert MAX_TRADES_PER_DAY == 3
    def test_min_open_interest(self) -> None:
        assert MIN_OPEN_INTEREST == 50_000
    # --- Veto reason codes ---
    def test_veto_time(self) -> None:
        assert VETO_TIME == "VETO_TIME"
    def test_veto_daily_loss(self) -> None:
        assert VETO_DAILY_LOSS == "VETO_DAILY_LOSS"
    def test_veto_trade_limit(self) -> None:
        assert VETO_TRADE_LIMIT == "VETO_TRADE_LIMIT"
    def test_veto_position_size(self) -> None:
        assert VETO_POSITION_SIZE == "VETO_POSITION_SIZE"
    def test_veto_low_liquidity(self) -> None:
        assert VETO_LOW_LIQUIDITY == "VETO_LOW_LIQUIDITY"
    # --- Strategy config remains tunable (not tested for specific values) ---
