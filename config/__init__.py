"""Configuration package.

The single source of truth for risk limits and strategy parameters.
See :mod:`config.risk_constants` and :mod:`config.strategy_config` for the
authoritative narrative; see ``config/AGENTS.md`` for ownership and
mutability rules.
"""
from __future__ import annotations

from . import index_params, risk_constants, strategy_config

__all__ = ["risk_constants", "strategy_config", "index_params"]
