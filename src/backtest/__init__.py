"""Backtesting engine for the NIFTY trading system.

Replays historical tick data through the strategy pipeline and
simulates order execution with P&L tracking.

Source citation:
    > src/strategy/AGENTS.md — Backtesting mandatory for every signal generator
    > config/AGENTS.md — Immutable risk rules apply to backtesting too
"""
from .engine import BacktestEngine
from .data_loader import DuckDBLoader, SessionLoader

__all__ = ["BacktestEngine", "DuckDBLoader", "SessionLoader"]