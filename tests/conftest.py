"""Shared pytest fixtures for the NIFTY trading system.

All tests that would otherwise trigger ``UpstoxAuth.get_valid_token()`` must
``monkeypatch`` it with ``fake_access_token``.

Source citation:
    > tests/AGENTS.md — Mock the auth module first, time-freezing with
      freezegun, no network in unit tests.
"""
from __future__ import annotations

import uuid

import pytest
from freezegun import freeze_time


# ---------------------------------------------------------------------------
# Auth fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_access_token() -> str:
    """Return a deterministic fake Upstox access token."""
    return "fake_access_token_abc123def456"


@pytest.fixture
def fake_tag() -> str:
    """Return a deterministic trade tag."""
    return f"trader-2026-06-09-{uuid.uuid5(uuid.NAMESPACE_DNS, 'test')}"


# ---------------------------------------------------------------------------
# Time-related fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def freeze_market_hours() -> None:
    """Freeze time at 10:00 AM IST on a weekday (Tuesday) during market hours."""
    freezer = freeze_time("2026-06-09 10:00:00+05:30")
    freezer.start()
    yield
    freezer.stop()


@pytest.fixture
def freeze_after_market() -> None:
    """Freeze time at 15:35 IST — after market close."""
    freezer = freeze_time("2026-06-09 15:35:00+05:30")
    freezer.start()
    yield
    freezer.stop()


@pytest.fixture
def freeze_weekend() -> None:
    """Freeze time at 12:00 IST on a Saturday — weekend, no trading."""
    freezer = freeze_time("2026-06-13 12:00:00+05:30")
    freezer.start()
    yield
    freezer.stop()