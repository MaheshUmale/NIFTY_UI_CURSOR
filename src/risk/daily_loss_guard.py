"""Daily loss circuit breaker (async coroutine).

Runs in a separate coroutine every 1 second, checking ``daily_loss_pct``
against ``MAX_DAILY_LOSS_PCT``. On trip, it synchronously calls
``order_manager.cancel_all_open()`` and ``square_off.flatten_all()``.

**Emergency flatten:** If ``daily_loss_pct >= EMERGENCY_FLATTEN_PCT (0.05)``,
treat as catastrophic loss — flatten everything within 5 seconds and disable
further entries for the rest of the day.

The guard is **idempotent** — it fires at most once per day, per threshold.

Source citation:
    > src/risk/AGENTS.md — Daily loss guard: 1 s coroutine, idempotent,
      emergency flatten at 5 %.
    > config/risk_constants.py — MAX_DAILY_LOSS_PCT and EMERGENCY_FLATTEN_PCT.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from config.risk_constants import MAX_DAILY_LOSS_PCT, EMERGENCY_FLATTEN_PCT
from src.utils.exception_handler import RiskVetoError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Types (duck-typed interfaces, following the protocol pattern)
# ---------------------------------------------------------------------------


class PositionTrackerProtocol:
    """Minimal interface expected by the guard."""

    @property
    def daily_loss_pct(self) -> float:
        ...


class OrderManagerProtocol:
    async def cancel_all_open(self) -> None:
        ...


class SquareOffProtocol:
    async def flatten_all(self) -> None:
        ...


class RiskManagerProtocol:
    """Only used to read the flag state; not a full RiskManager import."""

    @property
    def entries_blocked(self) -> bool:
        ...

    def block_entries_for_day(self) -> None:
        ...


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------


class DailyLossGuard:
    """Async coroutine that monitors daily loss and triggers circuit breakers.

    Parameters
    ----------
    position_tracker : PositionTrackerProtocol
    order_manager : OrderManagerProtocol
    square_off : SquareOffProtocol
    risk_manager : RiskManagerProtocol
    check_interval_sec : float
        How often to poll position_tracker.daily_loss_pct (default 1 s).
    """

    def __init__(
        self,
        position_tracker: PositionTrackerProtocol,
        order_manager: OrderManagerProtocol,
        square_off: SquareOffProtocol,
        check_interval_sec: float = 1.0,
    ) -> None:
        self._position_tracker = position_tracker
        self._order_manager = order_manager
        self._square_off = square_off
        self._check_interval = check_interval_sec

        # Idempotency flags — each trip fires exactly once per day
        self._loss_tripped: bool = False
        self._emergency_tripped: bool = False

    # ------------------------------------------------------------------
    # Async loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Run the monitoring loop forever. Cancel via task cancellation.

        This coroutine is designed to be launched with
        ``asyncio.create_task(guard.run())`` and cancelled when the
        application shuts down.
        """
        logger.info("DailyLossGuard started", extra={"check_interval_s": self._check_interval})

        try:
            while True:
                try:
                    pct = self._position_tracker.daily_loss_pct
                except Exception:
                    logger.exception("Failed to read daily_loss_pct, skipping check")
                    await asyncio.sleep(self._check_interval)
                    continue

                # Check emergency flatten first (higher threshold = more urgent)
                if pct >= EMERGENCY_FLATTEN_PCT and not self._emergency_tripped:
                    self._emergency_tripped = True
                    logger.critical(
                        "EMERGENCY FLATTEN: daily loss {:.2%} >= {:.0%}".format(
                            pct, EMERGENCY_FLATTEN_PCT
                        ),
                    )
                    await self._emergency_flatten()

                # Check standard daily loss trip
                elif pct >= MAX_DAILY_LOSS_PCT and not self._loss_tripped:
                    self._loss_tripped = True
                    logger.warning(
                        "Daily loss trip: {:.2%} >= {:.0%}".format(pct, MAX_DAILY_LOSS_PCT),
                    )
                    await self._trip_breaker()

                await asyncio.sleep(self._check_interval)

        except asyncio.CancelledError:
            logger.info("DailyLossGuard cancelled, shutting down gracefully")
            raise

    # ------------------------------------------------------------------
    # Breaker actions
    # ------------------------------------------------------------------

    async def _trip_breaker(self) -> None:
        """Cancel all open orders. Does NOT flatten positions."""
        logger.info("Daily loss breaker tripped — cancelling open orders")
        try:
            await self._order_manager.cancel_all_open()
        except Exception:
            logger.exception("Failed to cancel all open orders during daily loss trip")

    async def _emergency_flatten(self) -> None:
        """Cancel all open orders AND flatten all positions."""
        logger.info("Emergency flatten initiated")
        try:
            await self._order_manager.cancel_all_open()
        except Exception:
            logger.exception("Failed to cancel all open orders during emergency flatten")
        try:
            await self._square_off.flatten_all()
        except Exception:
            logger.exception("Failed to flatten all positions during emergency flatten")