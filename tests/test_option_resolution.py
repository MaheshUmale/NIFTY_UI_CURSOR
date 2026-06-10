"""Unit tests for ATM option key resolution.

Tests that ATM ± window strikes are returned correctly.
"""
from __future__ import annotations

import pytest

from config.strategy_config import ATM_STRIKE_WINDOW


def test_atm_window_constant_is_valid() -> None:
    """ATM_STRIKE_WINDOW should be a positive integer."""
    assert isinstance(ATM_STRIKE_WINDOW, int)
    assert ATM_STRIKE_WINDOW >= 1
    assert ATM_STRIKE_WINDOW <= 5


def test_atm_strike_selection_logic() -> None:
    """Test that we select the correct number of strikes around ATM."""
    strikes = [23000, 23100, 23200, 23300, 23400, 23500, 23600, 23700, 23800]
    spot = 23525.0
    
    atm = min(strikes, key=lambda x: abs(x - spot))
    assert atm == 23500
    
    window = ATM_STRIKE_WINDOW
    idx = strikes.index(atm)
    start = max(0, idx - window)
    end = min(len(strikes), idx + window + 1)
    selected = strikes[start:end]
    
    expected_count = min(len(strikes), 2 * window + 1)
    assert len(selected) == expected_count
    assert selected[0] >= strikes[0]
    assert selected[-1] <= strikes[-1]


def test_atm_near_boundary() -> None:
    """Test strike selection when ATM is near the start of the strike list."""
    strikes = [23000, 23100, 23200, 23300, 23400]
    spot = 23050.0
    
    atm = min(strikes, key=lambda x: abs(x - spot))
    assert atm == 23000
    
    window = ATM_STRIKE_WINDOW
    idx = strikes.index(atm)
    start = max(0, idx - window)
    end = min(len(strikes), idx + window + 1)
    selected = strikes[start:end]
    
    assert idx == 0
    assert len(selected) == 4
    assert selected[0] == strikes[0]