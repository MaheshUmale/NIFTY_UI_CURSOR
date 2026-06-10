"""Position tracker — manages open positions and calculates P&L.

Enforces atomic position updates via apply_fill() and tracks daily loss.

Source citation:
    > src/execution/AGENTS.md — Atomic updates, daily loss tracking.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


@dataclass
class Position:
    """Represents an open position."""
    instrument_key: str
    symbol: str
    side: str  # "BUY" or "SELL"
    qty: int
    avg_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


class PositionTracker:
    """Tracks open positions and calculates daily P&L.

    Parameters
    ----------
    capital : float
        Deployable capital in INR.
    """

    def __init__(self, capital: float = 200_000.0) -> None:
        self._capital = capital
        self._positions: dict[str, Position] = {}
        self._daily_realized_pnl: float = 0.0
        self._daily_unrealized_pnl: float = 0.0
        self._filled_tags: set[str] = set()  # Prevent double-counting

    @property
    def daily_loss_pct(self) -> float:
        """Daily loss as a fraction of capital (0.0–1.0)."""
        total_pnl = self._daily_realized_pnl + self._daily_unrealized_pnl
        if total_pnl >= 0:
            return 0.0
        return abs(total_pnl) / self._capital

    def apply_fill(self, tag: str, fill: dict[str, Any]) -> None:
        """Apply a fill to update positions.

        Must be called exactly once per fill (idempotency via tag).

        Parameters
        ----------
        tag : str
            Unique fill identifier (uuid4).
        fill : dict
            Must contain: instrument_key, symbol, side, qty, price.

        Raises
        ------
        ValueError
            If tag has already been applied.
        """
        if tag in self._filled_tags:
            raise ValueError(f"Fill with tag {tag} already applied")

        instrument_key = fill.get("instrument_key", "")
        symbol = fill.get("symbol", "")
        side = fill.get("side", "").upper()
        qty = fill.get("qty", 0)
        price = fill.get("price", 0.0)

        if instrument_key not in self._positions:
            self._positions[instrument_key] = Position(
                instrument_key=instrument_key,
                symbol=symbol,
                side=side,
                qty=qty,
                avg_price=price,
            )
        else:
            pos = self._positions[instrument_key]
            # Update average price
            total_qty = pos.qty + qty
            if total_qty > 0:
                pos.avg_price = (pos.avg_price * pos.qty + price * qty) / total_qty
            pos.qty = total_qty

        self._filled_tags.add(tag)
        logger.info(
            "Fill applied: tag=%s instrument=%s side=%s qty=%d price=%.2f",
            tag, instrument_key, side, qty, price,
        )

    def update_prices(self, prices: dict[str, float]) -> None:
        """Update current prices for all positions and recalculate unrealized P&L."""
        self._daily_unrealized_pnl = 0.0
        for instrument_key, pos in self._positions.items():
            if instrument_key in prices:
                pos.current_price = prices[instrument_key]
                if pos.side == "BUY":
                    pos.unrealized_pnl = (pos.current_price - pos.avg_price) * pos.qty
                else:
                    pos.unrealized_pnl = (pos.avg_price - pos.current_price) * pos.qty
                self._daily_unrealized_pnl += pos.unrealized_pnl

    def close_position(self, instrument_key: str, price: float) -> float:
        """Close a position and return realized P&L."""
        if instrument_key not in self._positions:
            return 0.0

        pos = self._positions.pop(instrument_key)
        if pos.side == "BUY":
            realized = (price - pos.avg_price) * pos.qty
        else:
            realized = (pos.avg_price - price) * pos.qty

        self._daily_realized_pnl += realized
        logger.info(
            "Position closed: %s realized_pnl=%.2f",
            instrument_key, realized,
        )
        return realized

    def get_position(self, instrument_key: str) -> Position | None:
        """Return current position for an instrument."""
        return self._positions.get(instrument_key)

    def get_all_positions(self) -> dict[str, Position]:
        """Return all open positions."""
        return self._positions.copy()

    def reset(self) -> None:
        """Reset all state (called at end of day)."""
        self._positions.clear()
        self._daily_realized_pnl = 0.0
        self._daily_unrealized_pnl = 0.0
        self._filled_tags.clear()