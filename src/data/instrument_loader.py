"""Instrument master CSV loader with daily cache.

Downloads the Upstox instrument CSV, parses it, caches by UTC day, and
provides symbol → instrument_key resolution for supported indices.

Source citation:
    > src/data/AGENTS.md — Cache invariants, symbol → instrument_key resolution.
    > ALL_DOCS/UPSTOX-api-docs.json — CSV format reference.
"""
from __future__ import annotations

import csv
import io
import pickle
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.utils.exception_handler import IngestionFatalError, wrap_requests_exception
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INSTRUMENT_CSV_URL: str = (
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz"
)
NSE_FO_PREFIX: str = "NSE_FO"
CACHE_TTL_HOURS: int = 24


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class InstrumentLoader:
    """Load and cache the Upstox instrument master.

    Parameters
    ----------
    cache_dir : str
        Directory for daily cache files. Default ``data/instrument_cache``.
    """

    def __init__(self, cache_dir: str = "data/instrument_cache") -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._instruments: dict[str, dict[str, Any]] = {}  # symbol → record
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_instruments(self) -> dict[str, dict[str, Any]]:
        """Load the instrument master, using a cache file if fresh.

        Returns
        -------
        dict[str, dict]
            Mapping of ``tradingsymbol`` → instrument record dict.
            Only ``NSE_FO`` segment instruments are retained.

        Raises
        ------
        IngestionFatalError
            If the CSV cannot be downloaded and no cache exists.
        """
        if self._loaded:
            return self._instruments

        cache_path = self._cache_path_for_today()
        if cache_path.exists() and self._is_cache_fresh(cache_path):
            logger.debug("Loading instrument cache from %s", cache_path)
            self._instruments = self._load_cache(cache_path)
            self._loaded = True
            return self._instruments

        # Download and parse the CSV
        try:
            logger.info("Downloading instrument CSV from %s", INSTRUMENT_CSV_URL)
            raw = self._download_csv()
            self._instruments = self._parse_csv(raw)
            self._save_cache(cache_path, self._instruments)
            self._loaded = True
            logger.info("Loaded %d NSE_FO instruments", len(self._instruments))
        except Exception as exc:
            # If we have a stale cache, fall back to it
            if self._instruments:
                logger.warning("Download failed, using stale cache: %s", exc)
                return self._instruments
            raise IngestionFatalError(
                f"Failed to load instrument master: {exc}"
            ) from exc

        return self._instruments

    def resolve(self, symbol: str, expiry: str | None = None) -> dict[str, Any] | None:
        """Resolve a trading symbol to an instrument record.

        Parameters
        ----------
        symbol : str
            Trading symbol (e.g. ``NIFTY24JUNFUT``).
        expiry : str, optional
            If provided, filters by expiry (format depends on instrument).

        Returns
        -------
        dict or None
            The matching instrument record, or ``None``.
        """
        if not self._loaded:
            self.load_instruments()

        rec = self._instruments.get(symbol)
        if rec is not None and expiry is not None:
            if rec.get("expiry") != expiry:
                return None
        return rec

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_path_for_today(self) -> Path:
        today_str = date.today().isoformat()
        return self._cache_dir / f"{today_str}.pkl"

    @staticmethod
    def _is_cache_fresh(cache_path: Path) -> bool:
        """Return ``True`` if the cache file is less than CACHE_TTL_HOURS old."""
        mtime = cache_path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        return age_hours < CACHE_TTL_HOURS

    def _download_csv(self) -> str:
        """Download the compressed CSV and return its decompressed text."""
        try:
            resp = requests.get(INSTRUMENT_CSV_URL, timeout=60)
            resp.raise_for_status()
            import gzip

            decompressed = gzip.decompress(resp.content)
            return decompressed.decode("utf-8")
        except requests.RequestException as exc:
            wrapped = wrap_requests_exception(exc, context="download_instrument_csv")
            logger.exception("Failed to download instrument CSV")
            raise wrapped from exc

    def _parse_csv(self, raw_csv: str) -> dict[str, dict[str, Any]]:
        """Parse the CSV text and return only NSE_FO instruments keyed by tradingsymbol."""
        reader = csv.DictReader(io.StringIO(raw_csv))
        instruments: dict[str, dict[str, Any]] = {}
        for row in reader:
            if row.get("exchange_segment", "").startswith(NSE_FO_PREFIX):
                symbol = row.get("tradingsymbol", "")
                if symbol:
                    instruments[symbol] = dict(row)
        return instruments

    def _save_cache(self, cache_path: Path, data: dict[str, Any]) -> None:
        """Serialize to pickle."""
        with open(cache_path, "wb") as f:
            pickle.dump(data, f)

    @staticmethod
    def _load_cache(cache_path: Path) -> dict[str, Any]:
        """Deserialize from pickle."""
        with open(cache_path, "rb") as f:
            return pickle.load(f)