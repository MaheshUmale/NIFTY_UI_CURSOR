"""Shared string / int / enum constants used across the trading system.
No classes with behaviour. No imports from other ``src`` modules.
Add new constants here; do not modify old ones (Risk Auditor owns deltas).
Source citation:
    > src/utils/AGENTS.md — Versioned constants, no business logic.
"""
from __future__ import annotations
# ---------------------------------------------------------------------------
# Trade tagging
# ---------------------------------------------------------------------------
#: Prefix for all client-generated trade tags. Tag format:
#: ``{DEFAULT_TAG_PREFIX}-{ISO8601-date}-{uuid4}``
DEFAULT_TAG_PREFIX: str = "trader"
# ---------------------------------------------------------------------------
# Exchange / segment identifiers
# ---------------------------------------------------------------------------
EXCHANGE_NSE: str = "NSE"
EXCHANGE_BSE: str = "BSE"
SEGMENT_FO: str = "NSE_FO"  # NSE Futures & Options segment
# ---------------------------------------------------------------------------
# Transaction sides
# ---------------------------------------------------------------------------
TRANSACTION_TYPE_BUY: str = "BUY"
TRANSACTION_TYPE_SELL: str = "SELL"
# ---------------------------------------------------------------------------
# Order types (Upstox API v2/v3)
# ---------------------------------------------------------------------------
ORDER_TYPE_MARKET: str = "MARKET"
ORDER_TYPE_LIMIT: str = "LIMIT"
ORDER_TYPE_SL: str = "SL"      # Stop Loss (trigger-based)
ORDER_TYPE_SL_M: str = "SL-M"  # Stop Loss Market
# ---------------------------------------------------------------------------
# Order duration
# ---------------------------------------------------------------------------
DURATION_DAY: str = "DAY"
# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
#: Incremented whenever the JSON log-line schema changes. Used by downstream
#: log-parsing pipelines to detect incompatible records.
LOG_FORMAT_VERSION: str = "1.0"
