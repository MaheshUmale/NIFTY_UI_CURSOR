"""Async WebSocket V3 client for Upstox market data.

Connects to ``wss://ws.upstox.com/feed/market-data-feed/v3``,
subscribes to instrument keys, and pushes ticks into a ``MarketBuffer``
via a registered callback.

Reconnection uses exponential backoff (1s → 2s → 4s → 8s → 16s → 30s max).
After 5 consecutive failures, raises ``IngestionFatalError``.

Source citation:
    > src/data/AGENTS.md — Async WebSocket, token subscription, reconnection
      with exponential backoff, backpressure via ring buffer.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import websockets

from src.utils.exception_handler import IngestionFatalError, wrap_requests_exception
from src.utils.logger import get_logger

from .market_buffer import MarketBuffer

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WS_URL: str = "wss://ws.upstox.com/feed/market-data-feed/v3"
MAX_RECONNECT_ATTEMPTS: int = 5
BASE_BACKOFF_SEC: float = 1.0
MAX_BACKOFF_SEC: float = 30.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class WebSocketClient:
    """Async WebSocket V3 client.

    Parameters
    ----------
    token : str
        Upstox access token (``Bearer`` value).
    tick_handler : Callable
        Async callback invoked on each tick: ``await handler(tick: dict)``.
    buffer : MarketBuffer
        Ring buffer where each tick is also pushed.
    """

    def __init__(
        self,
        token: str,
        tick_handler: Callable[[dict[str, Any]], Any],
        buffer: MarketBuffer,
    ) -> None:
        self._token = token
        self._tick_handler = tick_handler
        self._buffer = buffer
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._subscribed_keys: list[str] = []
        self._running: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to the WebSocket and start processing ticks.

        This method blocks until the connection is closed or fails
        unrecoverably. Launch as::

            asyncio.create_task(client.connect())
        """
        self._running = True
        attempt = 0
        backoff = BASE_BACKOFF_SEC

        while self._running and attempt <= MAX_RECONNECT_ATTEMPTS:
            try:
                logger.info("Connecting to WebSocket (attempt %d)", attempt + 1)
                self._ws = await websockets.connect(
                    WS_URL,
                    additional_headers={"Authorization": f"Bearer {self._token}"},
                    ping_interval=20,
                    ping_timeout=10,
                )
                attempt = 0  # reset on successful connect
                backoff = BASE_BACKOFF_SEC

                # Re-subscribe to previously subscribed keys
                if self._subscribed_keys:
                    await self._subscribe(self._subscribed_keys)

                # Message loop
                async for message in self._ws:
                    await self._on_message(message)
                    # Check if window shift was requested by consumer
                    if self._buffer.is_window_shift_requested:
                        logger.info("Window shift detected, will re-subscribe on next loop")

                # If we exit the loop cleanly, the connection was closed
                logger.info("WebSocket connection closed normally")
                break

            except (websockets.WebSocketException, asyncio.TimeoutError) as exc:
                attempt += 1
                logger.warning(
                    "WebSocket error (attempt %d/%d): %s",
                    attempt, MAX_RECONNECT_ATTEMPTS, exc,
                )
                if attempt > MAX_RECONNECT_ATTEMPTS:
                    logger.critical("Max reconnect attempts reached")
                    raise IngestionFatalError(
                        f"WebSocket reconnection failed after {MAX_RECONNECT_ATTEMPTS} attempts"
                    ) from exc

                logger.info("Reconnecting in %.1f s...", backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_SEC)

        self._running = False

    async def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        self._running = False
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
            logger.info("WebSocket disconnected")

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    async def subscribe(self, instrument_keys: list[str]) -> None:
        """Subscribe to market data for the given instrument keys.

        Can be called before or after ``connect()``. If called before,
        the keys are queued and sent on connect.
        """
        self._subscribed_keys = list(set(self._subscribed_keys + instrument_keys))
        if self._ws is not None:
            await self._subscribe(instrument_keys)

    async def _subscribe(self, instrument_keys: list[str]) -> None:
        """Send the subscription request over the WebSocket."""
        if self._ws is None:
            return

        payload = json.dumps({
            "action": "subscribe",
            "params": {
                "symbols": instrument_keys,
                "mode": "full",
            },
        })
        await self._ws.send(payload)
        logger.debug("Subscribed to %d keys", len(instrument_keys))

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def _on_message(self, raw: str) -> None:
        """Parse and dispatch an incoming tick message."""
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse WebSocket message: %s", raw[:200])
            return

        # Push to buffer and call the registered handler
        self._buffer.push(data)
        try:
            await self._tick_handler(data)
        except Exception:
            logger.exception("Tick handler raised an exception")