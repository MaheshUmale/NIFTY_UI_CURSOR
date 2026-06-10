"""Market history warm-up for strategy indicators.

Fetches 1-minute OHLCV from Upstox V3 History APIs:
- Intraday: current day candles for NIFTY index + NIFTY future
- Historical: previous day candles for context
- Merge: use INDEX price fields, FUTURE volume (indices have no volume)
- Options: ATM ± 3 strike chain snapshot for OI/PCR warm-up

Instruments:
- NIFTY 50 : ``NSE_INDEX|Nifty 50``
- NIFTY FUT: resolved dynamically from tests/ExtractInstrumentKeys.py logic
- Option keys: resolved from instrument master
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import upstox_client

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

INDEX_KEY: str = "NSE_INDEX|Nifty 50"
INDEX_FUT_PREFIX: str = "NIFTY"  # used to resolve current-month future
UNIT: str = "minutes"
INTERVAL: str = "1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _history_client(token: str) -> upstox_client.HistoryV3Api:
    configuration = upstox_client.Configuration()
    configuration.access_token = token
    return upstox_client.HistoryV3Api(upstox_client.ApiClient(configuration))


def _dt(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_warmup_data(token: str) -> dict[str, Any]:
    """Return merged OHLCV history + option data for strategy warm-up.

    Returns
    -------
    dict with keys:
        ohlcv: list[dict]  — merged 1-min candles (index price + future volume)
        option_chain: list[dict] | None — latest option snapshot
        instrument_keys: list[str] — resolved F&O keys for live subscription
    """
    client = _history_client(token)
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    # 1. Intraday index
    intra_index = _safe_intraday(client, INDEX_KEY)
    # 2. Intraday future
    fut_key = _resolve_nifty_future_key(token)
    intra_fut = _safe_intraday(client, fut_key) if fut_key else []

    # 3. Previous day history (both)
    hist_index = _safe_historical(client, INDEX_KEY, today, yesterday)
    hist_fut = _safe_historical(client, fut_key, today, yesterday) if fut_key else []

    # 4. Merge: index price + future volume
    ohlcv = _merge_index_future(
        _combine(intra_index, hist_index),
        _combine(intra_fut, hist_fut),
    )

    # 5. Option chain (latest from instrument master fetch not available here,
    #    so we return the FNO keys for the live subscription to pick up)
    option_keys = _resolve_option_keys(token) if fut_key else []

    return {
        "ohlcv": ohlcv,
        "option_chain": None,
        "instrument_keys": ([INDEX_KEY, fut_key] if fut_key else [INDEX_KEY]) + option_keys,
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _safe_intraday(
    client: upstox_client.HistoryV3Api,
    instrument_key: str | None,
) -> list[dict[str, Any]]:
    if not instrument_key:
        return []
    try:
        resp = client.get_intra_day_candle_data(instrument_key, UNIT, INTERVAL)
        candles = getattr(resp, "data", None) or resp.get("data", {}) if isinstance(resp, dict) else getattr(resp, "data", None)
        if candles is None:
            return []
        return list(candles) if isinstance(candles, list) else list(getattr(candles, "candles", []) or [])
    except Exception as exc:
        logger.warning("Intraday fetch failed for %s: %s", instrument_key, exc)
        return []


def _safe_historical(
    client: upstox_client.HistoryV3Api,
    instrument_key: str | None,
    to_date: datetime,
    from_date: datetime,
) -> list[dict[str, Any]]:
    if not instrument_key:
        return []
    try:
        resp = client.get_historical_candle_data1(
            instrument_key, UNIT, INTERVAL, _dt(to_date), _dt(from_date)
        )
        candles = getattr(resp, "data", None)
        if candles is None:
            return []
        return list(candles) if isinstance(candles, list) else list(getattr(candles, "candles", []) or [])
    except Exception as exc:
        logger.warning("Historical fetch failed for %s: %s", instrument_key, exc)
        return []


def _combine(
    a: list[dict[str, Any]], b: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Deduplicate by timestamp, preserving order oldest -> newest."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for row in a + b:
        ts = str(row.get("timestamp", ""))
        if ts in seen:
            continue
        seen.add(ts)
        merged.append(row)
    merged.sort(key=lambda r: r.get("timestamp", ""))
    return merged


def _merge_index_future(
    index_candles: list[dict[str, Any]],
    fut_candles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge index candles with future volume by timestamp.

    Index candle shape: [ts, open, high, low, close, ...]
    Future candle shape: [ts, open, high, low, close, volume, ...]
    """
    fut_by_ts: dict[str, dict[str, Any]] = {}
    for c in fut_candles:
        ts = str(c.get("timestamp", ""))
        if not ts:
            continue
        fut_by_ts[ts] = c

    merged: list[dict[str, Any]] = []
    for c in index_candles:
        ts = str(c.get("timestamp", ""))
        if not ts:
            continue
        fut = fut_by_ts.get(ts, {})
        merged.append(
            {
                "timestamp": ts,
                "open": _num(c.get("open")),
                "high": _num(c.get("high")),
                "low": _num(c.get("low")),
                "close": _num(c.get("close")),
                "volume": _num(fut.get("volume")) or 0,
                "oi": _num(fut.get("oi")),
            }
        )
    return merged


def _resolve_nifty_future_key(token: str) -> str | None:
    """Resolve current-month NIFTY future instrument key from instrument master."""
    try:
        import gzip
        import io

        import pandas as pd
        import requests

        url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as fh:
            df = pd.read_json(fh)

        fut_df = df[
            (df["name"] == INDEX_FUT_PREFIX) & (df["instrument_type"] == "FUT")
        ].sort_values(by="expiry")

        if fut_df.empty:
            logger.error("No NIFTY future found in instrument master")
            return None

        return str(fut_df.iloc[0]["instrument_key"])
    except Exception as exc:
        logger.error("Future key resolution failed: %s", exc)
        return None


def _resolve_option_keys(token: str) -> list[str]:
    """Resolve ATM ± 3 option keys for NIFTY (same as ExtractInstrumentKeys)."""
    try:
        import gzip
        import io

        import pandas as pd
        import requests

        url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as fh:
            df = pd.read_json(fh)

        opt_df = df[
            (df["name"] == INDEX_FUT_PREFIX) & (df["instrument_type"].isin(["CE", "PE"]))
        ].copy()
        if opt_df.empty:
            logger.error("Option chain empty for %s", INDEX_FUT_PREFIX)
            return []

        opt_df["expiry"] = pd.to_datetime(opt_df["expiry"], origin="unix", unit="ms")
        nearest = opt_df["expiry"].min()
        near_opt = opt_df[opt_df["expiry"] == nearest]

        strikes = sorted(near_opt["strike_price"].dropna().unique())
        if not strikes:
            logger.error("No strikes found in option chain")
            return []

        spot = _resolve_index_spot_for_atm(token, df)
        if spot is None:
            logger.error("Failed to resolve NIFTY spot for ATM calc")
            return []

        atm = min(strikes, key=lambda x: abs(x - spot))
        idx = strikes.index(atm)
        start = max(0, idx - 3)
        end = min(len(strikes), idx + 4)
        selected = strikes[start:end]

        keys: list[str] = []
        for strike in selected:
            ce = near_opt[(near_opt["strike_price"] == strike) & (near_opt["instrument_type"] == "CE")]
            pe = near_opt[(near_opt["strike_price"] == strike) & (near_opt["instrument_type"] == "PE")]
            if not ce.empty and not pe.empty:
                keys.append(str(ce.iloc[0]["instrument_key"]))
                keys.append(str(pe.iloc[0]["instrument_key"]))
        return keys
    except Exception as exc:
        logger.error("Option key resolution failed: %s", exc)
        return []


def _resolve_index_spot_for_atm(token: str, instrument_master: Any) -> float | None:
    try:
        import upstox_client

        configuration = upstox_client.Configuration()
        configuration.access_token = token
        quote_api = upstox_client.MarketQuoteV3Api(upstox_client.ApiClient(configuration))
        ltp_resp = quote_api.get_ltp(instrument_key=INDEX_KEY)
        spot = getattr(getattr(ltp_resp, "data", None), "get", lambda k, d=None: d)(INDEX_KEY)
        if hasattr(spot, "last_price"):
            spot = spot.last_price
        if spot is not None:
            return float(spot)
    except Exception as exc:
        logger.warning("LTP spot fetch failed: %s", exc)

    try:
        fut_key = _resolve_nifty_future_key(token)
        if fut_key and instrument_master is not None:
            fut_row = instrument_master[instrument_master["instrument_key"] == fut_key]
            if not fut_row.empty:
                return float(fut_row.iloc[0].get("last_price", fut_row.iloc[0].get("ltp", 0)) or 0) or None
    except Exception as exc:
        logger.warning("Fallback spot resolution failed: %s", exc)

    return None


def _num(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def resolve_option_keys_for_history(token: str) -> list[str]:
    return _resolve_option_keys(token)
