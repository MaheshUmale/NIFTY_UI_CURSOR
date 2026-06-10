"""Square-off module — handles EOD forced liquidation.

Flattens all positions by 15:20 IST and cancels open orders by 15:18 IST.

Source citation:
    > src/execution/AGENTS.md — Time-of-day rules, force close positions.
"""
from __future__ import annotations

import asyncio
from typing import Any

from config.risk_constants import FORCE_SQUARE_OFF_BY, CANCEL_OPEN_ORDERS_AT
from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


class SquareOff:
    """Handles end-of-day forced square-off.

    Parameters
    ----------
    order_manager : Any
        OrderManager instance for cancelling orders.
    position_tracker : Any
        PositionTracker instance for reading positions.
    """

    def __init__(self, order_manager: Any, position_tracker: Any) -> None:
        self._order_manager = order_manager
        self._position_tracker = position_tracker
        self._orders_cancelled: bool = False
        self._positions_flattened: bool = False

    async def flatten_all(self) -> None:
        """Flatten all open positions immediately.

        Used by daily loss guard and EOD square-off.
        """
        if self._positions_flattened:
            logger.info("Positions already flattened")
            return

        logger.warning("Flattening all positions")
        positions = self._position_tracker.get_all_positions()

        for instrument_key, pos in positions.items():
            try:
                # Determine opposite side to flatten
                flatten_side = "SELL" if pos.side == "BUY" else "BUY"

                # Place market order to flatten
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._order_manager.place_order(
                        instrument_key=instrument_key,
                        quantity=pos.qty,
                        side=flatten_side,
                        order_type="MARKET",
                        tag=f"flatten-{instrument_key}",
                        product="I",
                    ),
                )

                # Update position tracker
                current_price = pos.current_price if pos.current_price > 0 else pos.avg_price
                self._position_tracker.close_position(instrument_key, current_price)

                logger.info("Flattened position: %s %s qty=%d", instrument_key, flatten_side, pos.qty)

            except Exception as e:
                logger.exception("Failed to flatten position %s", instrument_key)

        self._positions_flattened = True

    async def cancel_all_orders(self) -> None:
        """Cancel all open orders.

        Called at 15:18 IST.
        """
        if self._orders_cancelled:
            logger.info("Orders already cancelled")
            return

        logger.warning("Cancelling all open orders")
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._order_manager.cancel_all_open,
            )
            self._orders_cancelled = True
        except Exception as e:
            logger.exception("Failed to cancel all orders")

    def reset(self) -> None:
        """Reset daily state (called at start of new trading day)."""
        self._orders_cancelled = False
        self._positions_flattened = False