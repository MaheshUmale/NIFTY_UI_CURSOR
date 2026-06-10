"""Instrument key resolution for dynamic subscription.

Resolves current-month NIFTY/BANKNIFTY future + ATM±3 option keys from the
upstox instrument master. Uses the exchange stock/key conventions from
``tests/ExtractInstrumentKeys.py`` so the websocket client gets exactly the
live-tradeable contract keys.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MASTER_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
)


def resolve_current_month_future(symbol: str = "NIFTY") -> str | None:
    """Return instrument_key for current-month future of *symbol*.

    Uses the same filtering convention as tests/ExtractInstrumentKeys.py:
      - name == symbol
      - instrument_type == 'FUT'
      - sort by expiry, take first (nearest)
    """
    try:
        import gzip
        import io

        import pandas as pd
        import requests

        resp = requests.get(MASTER_URL, timeout=10)
        resp.raise_for_status()
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as fh:
            df = pd.read_json(fh)

        fut_df = df[
            (df["name"] == symbol) & (df["instrument_type"] == "FUT")
        ].sort_values(by="expiry")

        if fut_df.empty:
            logger.error("No future contract found for %s", symbol)
            return None

        return str(fut_df.iloc[0]["instrument_key"])
    except Exception as exc:
        logger.error("Instrument resolution failed for %s: %s", symbol, exc)
        return None


def resolve_nifty_50_future() -> str | None:
    """Convenience wrapper: return current NIFTY future instrument key."""
    return resolve_current_month_future("NIFTY")


def resolve_bank_nifty_future() -> str | None:
    """Convenience wrapper: return current BANKNIFTY future instrument key."""
    return resolve_current_month_future("BANKNIFTY")
