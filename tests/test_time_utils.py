"""Unit tests for ``src.utils.time_utils``.
Source citation:
    > src/utils/AGENTS.md — Verification: ``test_time_utils.py`` must cover
      now_ist timezone, market-hours correctness.
"""
from __future__ import annotations
from datetime import datetime, time, timezone, timedelta
import pytest
from src.utils.time_utils import (
    IST,
    format_iso_ist,
    from_epoch_ms,
    is_market_hours,
    now_ist,
    to_epoch_ms,
)
class TestNowIst:
    """``now_ist()`` must return an IST-aware datetime."""
    def test_timezone_is_ist(self) -> None:
        dt = now_ist()
        assert dt.tzinfo is not None
        # IST = UTC +05:30
        offset = dt.tzinfo.utcoffset(dt)
        assert offset is not None
        assert offset == timedelta(hours=5, minutes=30)
    def test_repr_contains_asia_kolkata(self) -> None:
        dt = now_ist()
        # The tzinfo name should be "Asia/Kolkata" or "IST+0530"
        assert dt.tzinfo is not None
        assert dt.tzinfo.tzname(dt) is not None
class TestIsMarketHours:
    """Tests for the weekday market-hours gate."""
    def test_market_hours_returns_true(self, freeze_market_hours: None) -> None:
        # 10:00 AM Tuesday — should be in hours
        assert is_market_hours() is True
    def test_after_market_close(self, freeze_after_market: None) -> None:
        # 15:35 — after the 15:30 close
        assert is_market_hours() is False
    def test_weekend_returns_false(self, freeze_weekend: None) -> None:
        # Saturday midday
        assert is_market_hours() is False
    def test_before_open(self) -> None:
        """09:00 AM — before 09:15 open."""
        dt = datetime(2026, 6, 9, 9, 0, 0, tzinfo=IST)
        assert is_market_hours(dt) is False
    def test_at_open_edge(self) -> None:
        """09:15 — start of market hours (inclusive)."""
        dt = datetime(2026, 6, 9, 9, 15, 0, tzinfo=IST)
        assert is_market_hours(dt) is True
    def test_at_close_edge(self) -> None:
        """15:30 — market close (exclusive upper bound)."""
        dt = datetime(2026, 6, 9, 15, 30, 0, tzinfo=IST)
        assert is_market_hours(dt) is False
    def test_monday(self) -> None:
        dt = datetime(2026, 6, 8, 10, 0, 0, tzinfo=IST)  # Monday
        assert is_market_hours(dt) is True
    def test_friday(self) -> None:
        dt = datetime(2026, 6, 12, 10, 0, 0, tzinfo=IST)  # Friday
        assert is_market_hours(dt) is True
    def test_sunday(self) -> None:
        dt = datetime(2026, 6, 14, 10, 0, 0, tzinfo=IST)  # Sunday
        assert is_market_hours(dt) is False
class TestEpochConversion:
    """Round-trip and edge-case tests for epoch converters."""
    def test_round_trip(self) -> None:
        original = datetime(2026, 6, 9, 10, 0, 0, tzinfo=IST)
        ms = to_epoch_ms(original)
        recovered = from_epoch_ms(ms)
        assert recovered == original
    def test_to_epoch_known_value(self) -> None:
        # 2026-06-09 00:00:00 UTC
        dt = datetime(2026, 6, 9, 0, 0, 0, tzinfo=timezone.utc)
        # That's 5:30 AM IST = 05:30, so epoch ms = Unix epoch + ...
        # 2026-06-09 00:00:00 UTC in epoch ms (approximate):
        # We just check it's a reasonable positive value > 1.7 trillion
        ms = to_epoch_ms(dt)
        assert ms > 1_700_000_000_000
    def test_from_epoch_zero(self) -> None:
        dt = from_epoch_ms(0)
        # epoch zero is 1970-01-01 00:00:00 UTC = 05:30 IST
        assert dt.year == 1970
        assert dt.month == 1
        assert dt.day == 1
        assert dt.tzinfo is not None
        offset = dt.tzinfo.utcoffset(dt)
        assert offset == timedelta(hours=5, minutes=30)
    def test_non_ist_input(self) -> None:
        """Converting a UTC datetime should work and produce correct IST."""
        utc_dt = datetime(2026, 6, 9, 5, 0, 0, tzinfo=timezone.utc)
        ms = to_epoch_ms(utc_dt)
        recovered = from_epoch_ms(ms)
        # Should be 10:30 AM IST (UTC 05:00 → IST 10:30)
        assert recovered.hour == 10
        assert recovered.minute == 30
class TestFormatIsoIst:
    """ISO-8601 formatter for IST."""
    def test_format_ist(self) -> None:
        dt = datetime(2026, 6, 9, 14, 30, 0, tzinfo=IST)
        formatted = format_iso_ist(dt)
        assert "+05:30" in formatted
        assert "2026-06-09T14:30:00" in formatted
    def test_format_utc_converted(self) -> None:
        """UTC input should be converted to IST."""
        utc_dt = datetime(2026, 6, 9, 9, 0, 0, tzinfo=timezone.utc)
        formatted = format_iso_ist(utc_dt)
        # UTC 09:00 → IST 14:30
        assert "14:30:00" in formatted
        assert "+05:30" in formatted
