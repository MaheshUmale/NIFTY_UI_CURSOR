"""Order management, position tracker, EOD square-off.

The only module that can send orders to Upstox. Consumes RiskApprovedOrder
from the risk gate. Never accepts raw Signal objects.

Source citation:
    > src/execution/AGENTS.md — MIS product mandate, ApiException handling,
      idempotent tags, atomic position updates.
"""
from __future__ import annotations

from .order_manager import OrderManager
from .position_tracker import PositionTracker
from .square_off import SquareOff

__all__ = ["OrderManager", "PositionTracker", "SquareOff"]