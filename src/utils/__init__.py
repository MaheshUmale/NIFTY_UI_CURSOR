"""Cross-cutting utilities for the trading system.
Every module in the system imports from this package. No business logic,
no I/O beyond logging and clock access.
Exports
-------
get_logger          — module-scoped logger factory (logger.py)
configure_logging   — one-time root logger setup (logger.py)
now_ist             — IST-aware datetime (time_utils.py)
is_market_hours     — market-hours check (time_utils.py)
to_epoch_ms         — datetime → milliseconds UTC (time_utils.py)
from_epoch_ms       — milliseconds UTC → IST-aware datetime (time_utils.py)
format_iso_ist      — IST-aware ISO-8601 formatter (time_utils.py)
UpstoxAPIError      — base Upstox exception (exception_handler.py)
TokenExpiredError   — expired token exception (exception_handler.py)
OrderConstructionError — order payload validation exception (exception_handler.py)
OrderRejectedError  — Upstox rejection exception (exception_handler.py)
IngestionFatalError — unrecoverable data-ingestion exception (exception_handler.py)
RiskVetoError       — risk gate veto exception (exception_handler.py)
wrap_requests_exception — HTTP exception converter (exception_handler.py)
... and all constants from constants.py
Source citation:
    > src/utils/AGENTS.md — Package contract
"""
from __future__ import annotations
from src.utils.constants import (
    DEFAULT_TAG_PREFIX,
    DURATION_DAY,
    EXCHANGE_BSE,
    EXCHANGE_NSE,
    LOG_FORMAT_VERSION,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    ORDER_TYPE_SL,
    ORDER_TYPE_SL_M,
    SEGMENT_FO,
    TRANSACTION_TYPE_BUY,
    TRANSACTION_TYPE_SELL,
)
from src.utils.exception_handler import (
    IngestionFatalError,
    OrderConstructionError,
    OrderRejectedError,
    RiskVetoError,
    TokenExpiredError,
    UpstoxAPIError,
    wrap_requests_exception,
)
from src.utils.logger import configure_logging, get_logger
from src.utils.time_utils import (
    IST,
    format_iso_ist,
    from_epoch_ms,
    is_market_hours,
    now_ist,
    to_epoch_ms,
)
__all__ = [
    # logger
    "get_logger",
    "configure_logging",
    # time_utils
    "IST",
    "now_ist",
    "is_market_hours",
    "to_epoch_ms",
    "from_epoch_ms",
    "format_iso_ist",
    # exception_handler
    "UpstoxAPIError",
    "TokenExpiredError",
    "OrderConstructionError",
    "OrderRejectedError",
    "IngestionFatalError",
    "RiskVetoError",
    "wrap_requests_exception",
    # constants
    "DEFAULT_TAG_PREFIX",
    "EXCHANGE_NSE",
    "EXCHANGE_BSE",
    "SEGMENT_FO",
    "TRANSACTION_TYPE_BUY",
    "TRANSACTION_TYPE_SELL",
    "ORDER_TYPE_MARKET",
    "ORDER_TYPE_LIMIT",
    "ORDER_TYPE_SL",
    "ORDER_TYPE_SL_M",
    "DURATION_DAY",
    "LOG_FORMAT_VERSION",
]
