"""Data loaders for backtesting — DuckDB weekly files and live session JSON.

Loads historical tick data from two sources:
1. DuckDB weekly expiry files (options_data + spot_data tables)
2. Live streaming session JSON files (tick-by-tick market data)

Source citation:
    > src/data/AGENTS.md — Raw tick normalization; OI/IV data caching
    > config/AGENTS.md — Index-specific constants (NIFTY 50, BANKNIFTY)
"""
from __future__ import annotations

import json
import os
import glob
from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Any, Iterator

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Tick:
    """Normalized tick for backtesting."""
    instrument_key: str
    symbol: str
    last_price: float
    volume: int
    oi: int
    timestamp: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    strike: int = 0
    option_type: str = ""  # "CE" or "PE"
    expiry: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpotTick:
    """NIFTY spot tick for backtesting."""
    symbol: str
    last_price: float
    volume: int
    timestamp: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0


# ---------------------------------------------------------------------------
# DuckDB Loader
# ---------------------------------------------------------------------------

class DuckDBLoader:
    """Load historical data from weekly DuckDB files.

    Each file contains:
    - options_data: OHLCV + OI per strike per bar
    - spot_data: NIFTY spot OHLCV per bar

    Parameters
    ----------
    data_dir : str
        Directory containing .duckdb files (e.g., D:\\OPTIONS_DATA)
    """

    def __init__(self, data_dir: str = "D:\\OPTIONS_DATA") -> None:
        self._data_dir = Path(data_dir)
        self._conn = None

    def list_files(self) -> list[str]:
        """List all weekly DuckDB files sorted by date."""
        files = sorted(glob.glob(str(self._data_dir / "*.duckdb")))
        # Exclude nifty_master.duckdb
        return [f for f in files if "nifty_master" not in f]

    def load_week(self, date_str: str) -> dict[str, Any]:
        """Load a single weekly expiry file.

        Parameters
        ----------
        date_str : str
            Date string like "20260505" (YYYYMMDD)

        Returns
        -------
        dict with keys: 'options_data', 'spot_data', 'metadata'
        """
        import duckdb

        db_path = self._data_dir / f"{date_str}.duckdb"
        if not db_path.exists():
            logger.warning("DuckDB file not found: %s", db_path)
            return {}

        conn = duckdb.connect(str(db_path), read_only=True)
        try:
            # Load options data
            options_df = conn.execute("SELECT * FROM options_data").fetchdf()
            spot_df = conn.execute("SELECT * FROM spot_data").fetchdf()

            metadata = {
                "date_str": date_str,
                "options_rows": len(options_df),
                "spot_rows": len(spot_df),
                "strikes": sorted(options_df["Strike"].unique().tolist()) if len(options_df) > 0 else [],
                "option_types": sorted(options_df["OptionType"].unique().tolist()) if len(options_df) > 0 else [],
                "date_range": (
                    options_df["Date"].min() if len(options_df) > 0 else None,
                    options_df["Date"].max() if len(options_df) > 0 else None,
                ),
            }

            return {
                "options_data": options_df,
                "spot_data": spot_df,
                "metadata": metadata,
            }
        finally:
            conn.close()

    def iter_ticks(self, date_str: str) -> Iterator[Tick]:
        """Iterate over all ticks in a weekly file as normalized Tick objects.

        Yields ticks in chronological order (sorted by Timestamp).
        """
        data = self.load_week(date_str)
        if not data:
            return

        options_df = data["options_data"]
        spot_df = data["spot_data"]

        # Convert options data to ticks
        if len(options_df) > 0:
            # Sort by timestamp
            options_df = options_df.sort_values("Timestamp")

            for _, row in options_df.iterrows():
                try:
                    ts = self._parse_timestamp(row.get("Timestamp", ""))
                    yield Tick(
                        instrument_key=f"NIFTY_{row.get('Strike', 0)}_{row.get('OptionType', '')}",
                        symbol="NIFTY",
                        last_price=float(row.get("Close", 0.0)),
                        volume=int(row.get("Volume", 0)),
                        oi=int(row.get("OI", 0)),
                        timestamp=ts,
                        open=float(row.get("Open", 0.0)),
                        high=float(row.get("High", 0.0)),
                        low=float(row.get("Low", 0.0)),
                        close=float(row.get("Close", 0.0)),
                        strike=int(row.get("Strike", 0)),
                        option_type=str(row.get("OptionType", "")),
                        expiry=str(row.get("Expiry", "")),
                        metadata={"ticker": str(row.get("Ticker", ""))},
                    )
                except Exception:
                    logger.debug("Failed to parse options tick: %s", row.to_dict())
                    continue

    def iter_spot_ticks(self, date_str: str) -> Iterator[SpotTick]:
        """Iterate over spot data ticks for a given date."""
        data = self.load_week(date_str)
        if not data:
            return

        spot_df = data["spot_data"]
        if len(spot_df) > 0:
            spot_df = spot_df.sort_values("Timestamp")
            for _, row in spot_df.iterrows():
                try:
                    ts = self._parse_timestamp(row.get("Timestamp", ""))
                    yield SpotTick(
                        symbol="NIFTY",
                        last_price=float(row.get("Close", 0.0)),
                        volume=int(row.get("Volume", 0)),
                        timestamp=ts,
                        open=float(row.get("Open", 0.0)),
                        high=float(row.get("High", 0.0)),
                        low=float(row.get("Low", 0.0)),
                        close=float(row.get("Close", 0.0)),
                    )
                except Exception:
                    logger.debug("Failed to parse spot tick: %s", row.to_dict())
                    continue

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse timestamp string to datetime."""
        if not ts_str:
            return datetime.now()
        try:
            # Try common formats
            for fmt in ["%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    return datetime.strptime(ts_str, fmt)
                except ValueError:
                    continue
            # Try ISO format
            return datetime.fromisoformat(ts_str)
        except Exception:
            return datetime.now()


# ---------------------------------------------------------------------------
# Session Loader (Live Streaming JSON)
# ---------------------------------------------------------------------------

class SessionLoader:
    """Load live streaming session JSON files.

    Each session folder contains thousands of JSON files with tick data.
    File naming: md_YYYYMMDD_HHMMSS_mmm_NNNNNN.json

    Parameters
    ----------
    data_dir : str
        Directory containing session folders (e.g., D:\\OPTIONS_DATA)
    """

    def __init__(self, data_dir: str = "D:\\OPTIONS_DATA") -> None:
        self._data_dir = Path(data_dir)

    def list_sessions(self) -> list[str]:
        """List all session folders sorted by date."""
        sessions = sorted(glob.glob(str(self._data_dir / "session_*")))
        return [os.path.basename(s) for s in sessions]

    def load_session(self, session_name: str) -> list[dict[str, Any]]:
        """Load all JSON files from a session folder.

        Returns a list of parsed JSON objects in chronological order.
        """
        session_dir = self._data_dir / session_name
        if not session_dir.exists():
            logger.warning("Session folder not found: %s", session_dir)
            return []

        files = sorted(glob.glob(str(session_dir / "*.json")))
        logger.info("Loading session %s: %d files", session_name, len(files))

        ticks = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    ticks.append(data)
            except Exception:
                logger.debug("Failed to load JSON file: %s", f)
                continue

        return ticks

    def iter_ticks(self, session_name: str) -> Iterator[Tick]:
        """Iterate over all ticks in a session as normalized Tick objects.

        Yields ticks in chronological order.
        """
        ticks = self.load_session(session_name)
        for tick_data in ticks:
            # Handle different message types
            msg_type = tick_data.get("type", "")

            if msg_type == "tick":
                # Extract tick data from the message
                tick_info = tick_data.get("data", tick_data)
                try:
                    ts_str = tick_data.get("currentTs", "")
                    ts = self._parse_epoch_ms(ts_str)

                    yield Tick(
                        instrument_key=tick_info.get("instrument_key", ""),
                        symbol=tick_info.get("symbol", "NIFTY"),
                        last_price=float(tick_info.get("last_price", 0.0)),
                        volume=int(tick_info.get("volume", 0)),
                        oi=int(tick_info.get("oi", 0)),
                        timestamp=ts,
                        open=float(tick_info.get("open", 0.0)),
                        high=float(tick_info.get("high", 0.0)),
                        low=float(tick_info.get("low", 0.0)),
                        close=float(tick_info.get("close", 0.0)),
                        strike=int(tick_info.get("strike", 0)),
                        option_type=str(tick_info.get("option_type", "")),
                        expiry=str(tick_info.get("expiry", "")),
                        metadata={"raw": tick_info},
                    )
                except Exception:
                    logger.debug("Failed to parse tick: %s", str(tick_data)[:200])
                    continue

    def _parse_epoch_ms(self, ts_str: str) -> datetime:
        """Parse epoch milliseconds string to datetime."""
        try:
            ts_ms = int(ts_str)
            return datetime.fromtimestamp(ts_ms / 1000.0)
        except (ValueError, TypeError):
            return datetime.now()