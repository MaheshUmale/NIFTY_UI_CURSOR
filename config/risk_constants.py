"""IMMUTABLE risk constants — sole owner: Risk & Compliance Auditor.

DO NOT MODIFY WITHOUT RISK AUDITOR SIGN-OFF.

This module is the single source of truth for all hard risk limits enforced
by the live trading system. No sub-module may declare these values locally
and no environment variable, config file, or runtime flag may override them.

The canonical narrative contract for each constant lives in
``config/AGENTS.md`` under "IMMUTABLE Risk Rules (Risk Auditor — VETO POWER)".
A CI test (``tests/test_risk_constants_invariants.py``) asserts that the
values declared in this file match that contract byte-for-byte. Any drift
fails the build before it can reach production.

Source citation:
    > config/AGENTS.md — IMMUTABLE Risk Rules (Risk Auditor — VETO POWER)
"""
from __future__ import annotations

from datetime import time

# ---------------------------------------------------------------------------
# Time-of-day gates (all in IST)
# ---------------------------------------------------------------------------

#: 15:15 IST — after this time, no new entry orders are accepted.
BLOCK_NEW_ENTRIES_AFTER: time = time(15, 15)

#: 15:18 IST — cancel all open (pending) orders at this time.
CANCEL_OPEN_ORDERS_AT: time = time(15, 18)

#: 15:20 IST — hard square-off deadline; all open positions must be flat
#: by this time. Position reduction is forced via ``square_off.flatten_all()``.
FORCE_SQUARE_OFF_BY: time = time(15, 20)

#: Market open in IST. Used for sanity checks on instrument expiry / date.
MARKET_OPEN_IST: time = time(9, 15)

#: Market close in IST. After this time the WebSocket is expected to be idle.
MARKET_CLOSE_IST: time = time(15, 30)

# ---------------------------------------------------------------------------
# Capital / loss limits (fractions of deployable capital)
# ---------------------------------------------------------------------------

#: 4 % of capital — daily loss circuit breaker. When realised + unrealised
#: loss crosses this fraction of capital, all new entries are blocked and
#: open orders are cancelled. Positions are NOT auto-flattended at this level.
MAX_DAILY_LOSS_PCT: float = 0.04

#: 2 % of capital — maximum risk per single trade. The risk gate computes
#: ``risk_per_trade = qty * (entry_price - stop_loss)`` and rejects signals
#: whose risk exceeds this fraction of deployable capital.
MAX_RISK_PER_TRADE_PCT: float = 0.02

#: 5 % of capital — catastrophic loss floor. When crossed the system
#: performs an emergency flatten of every open position within 5 seconds
#: and disables further entries for the rest of the trading day.
EMERGENCY_FLATTEN_PCT: float = 0.05

#: 0.5 % — buffer applied to expected fill price to account for slippage
#: on market and stop-loss orders. Used by the execution layer when
#: computing realised P&L.
SLIPPAGE_BUFFER_PCT: float = 0.005

# ---------------------------------------------------------------------------
# Order routing rules
# ---------------------------------------------------------------------------

#: All orders must use the Intraday (MIS) product. A missing or different
#: value must raise ``OrderConstructionError`` BEFORE the Upstox API call.
ORDER_PRODUCT: str = "I"

#: Order variety. Upstox supports "single", "bo" (bracket), "co" (cover).
#: The execution layer defaults to bracket orders for risk-defined entries.
DEFAULT_ORDER_VARIETY: str = "bo"

# ---------------------------------------------------------------------------
# Trade count and liquidity gates
# ---------------------------------------------------------------------------

#: Maximum number of round-trip entries per trading day, across all
#: instruments and directions. Enforced by ``journal.trade_count_today()``.
MAX_TRADES_PER_DAY: int = 3

#: Minimum open interest (in contracts) for an instrument to be considered
#: tradeable. Below this, the signal is vetoed as ``VETO_LOW_LIQUIDITY``.
MIN_OPEN_INTEREST: int = 50_000

# ---------------------------------------------------------------------------
# Risk gate veto reason codes
# ---------------------------------------------------------------------------
# These string codes are emitted by the risk gate on rejection. They form
# the audit trail — never change a code's spelling without coordinating a
# data migration of the trade journal.

VETO_TIME: str = "VETO_TIME"
VETO_DAILY_LOSS: str = "VETO_DAILY_LOSS"
VETO_TRADE_LIMIT: str = "VETO_TRADE_LIMIT"
VETO_POSITION_SIZE: str = "VETO_POSITION_SIZE"
VETO_LOW_LIQUIDITY: str = "VETO_LOW_LIQUIDITY"
