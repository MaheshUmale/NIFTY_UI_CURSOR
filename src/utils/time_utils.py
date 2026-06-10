"""IST timezone helpers and market-hours checks.
Every function in this module is a **pure function** (deterministic given
inputs) or has only side effects limited to clock access. No I/O, no
Upstox calls, no DB writes.
NEVER use naive ``datetime.now()``. Always use ``now_ist()``.
Source citation:
    > src/utils/AGENTS.md — Pure helpers, time zone contract.
    > config/risk_constants.py — MARKET_OPEN_IST and MARKET_CLOSE_IST
      imported as the single source of truth for gate times.
"""
from __future__ import annotations
import datetime
from typing import Final
from config.risk_constants import MARKET_CLOSE_IST, MARKET_OPEN_IST
# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------
#: India Standard Time (UTC +05:30) as a fixed-offset timezone.
IST: Final[datetime.timezone] = datetime.timezone(
    datetime.timedelta(hours=5, minutes=30),
    name="Asia/Kolkata",
)
# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def now_ist() -> datetime.datetime:
    """Return the current time as an IST-aware :class:`datetime.datetime`.
    Returns
    -------
    datetime.datetime
        Timezone-aware datetime with ``tzinfo=IST``.
    """
    return datetime.datetime.now(tz=IST)
def is_market_hours(ts: datetime.datetime | None = None) -> bool:
    """Return ``True`` if ``ts`` falls within NSE market hours.
    Market hours are defined as Monday–Friday, 09:15–15:30 IST.
    Holidays are **not** detected by this function (the scheduler layer
    is responsible for holiday awareness).
    Parameters
    ----------
    ts : datetime.datetime | None
        The timestamp to check. If ``None``, ``now_ist()`` is used.
    Returns
    -------
    bool
        ``True`` if the timestamp is within market hours on a weekday.
    """
    dt = ts if ts is not None else now_ist()
    # Weekend check (Monday=0, Sunday=6)
    if dt.weekday() >= 5:
        return False
    # Time-of-day check against the canonical gate constants
    t = dt.time()
    return MARKET_OPEN_IST <= t < MARKET_CLOSE_IST
def to_epoch_ms(dt: datetime.datetime) -> int:
    """Convert an IST-aware or UTC-aware datetime to UTC epoch milliseconds.
    Parameters
    ----------
    dt : datetime.datetime
        Timezone-aware datetime. If it carries a tzinfo other than UTC,
        it is converted to UTC internally before computing the epoch.
    Returns
    -------
    int
        Milliseconds since 1970-01-01 00:00:00 UTC.
    """
    # Ensure UTC for the calculation
    utc_dt = dt.astimezone(datetime.timezone.utc)
    epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    delta = utc_dt - epoch
    return int(delta.total_seconds() * 1000)
def from_epoch_ms(ms: int) -> datetime.datetime:
    """Convert UTC epoch milliseconds to an IST-aware datetime.
    Parameters
    ----------
    ms : int
        Milliseconds since 1970-01-01 00:00:00 UTC.
    Returns
    -------
    datetime.datetime
        IST-aware datetime.
    """
    utc_dt = datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc)
    return utc_dt.astimezone(IST)
def format_iso_ist(dt: datetime.datetime) -> str:
    """Format an IST-aware datetime as ISO-8601 with explicit ``+05:30`` offset.
    Parameters
    ----------
    dt : datetime.datetime
        Timezone-aware datetime. If not IST, it is converted.
    Returns
    -------
    str
        ISO-8601 string, e.g. ``"2026-06-09T14:32:00.123000+05:30"``.
    """
    # Ensure the datetime carries the IST offset for the formatted output
    ist_dt = dt.astimezone(IST)
    return ist_dt.isoformat()
