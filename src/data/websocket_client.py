"""Async WebSocket V3 client for Upstox market data using official SDK.

Uses ``upstox_client.MarketDataStreamerV3`` with access_token-in-Configuration
(authorization header), subscribes in ``on_open``, and normalizes the nested
``feeds[x].fullFeed.marketFF`` JSON into our internal tick dict.

Source: https://upstox.com/developer/api-documentation/streamer-function
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import upstox_client

from src.utils.exception_handler import IngestionFatalError
from src.utils.logger import get_logger

from .market_buffer import MarketBuffer

logger = get_logger(__name__)

WS_URL: str = "wss://ws-api.upstox.com/v3/feed/marketdata"
MAX_RECONNECT_ATTEMPTS: int = 5
BASE_BACKOFF_SEC: int = 2


class WebSocketClient:
    """Thin async wrapper around ``upstox_client.MarketDataStreamerV3``."""

    def __init__(
        self,
        token: str,
        tick_handler: Callable[[dict[str, Any]], Any],
        buffer: MarketBuffer,
    ) -> None:
        self._token = token
        self._tick_handler = tick_handler
        self._buffer = buffer
        self._streamer: upstox_client.MarketDataStreamerV3 | None = None
        self._subscribed_keys: list[str] = []
        self._running_event: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._reconnect_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the SDK streamer and block until :meth:`disconnect`."""
        self._loop = asyncio.get_running_loop()
        self._running_event = asyncio.Event()

        configuration = upstox_client.Configuration()
        configuration.access_token = self._token
        logger.info("Initializing Upstox API client.")
        logger.debug("Upstox API client configuration: token_present=%s", bool(configuration.access_token))
        api_client = upstox_client.ApiClient(configuration)

        self._streamer = upstox_client.MarketDataStreamerV3(
            api_client,
            self._subscribed_keys,
            "full",
        )
        self._streamer.auto_reconnect(True, BASE_BACKOFF_SEC, MAX_RECONNECT_ATTEMPTS)

        self._streamer.on("open", self._on_open)
        self._streamer.on("message", self._on_message)
        self._streamer.on("error", self._on_error)
        self._streamer.on("close", self._on_close)
        self._streamer.on("reconnecting", self._on_reconnecting)
        self._streamer.on("autoReconnectStopped", self._on_reconnect_stopped)

        logger.info("Connecting to Upstox V3 stream...")
        self._streamer.connect()
        await self._running_event.wait()

    async def disconnect(self) -> None:
        """Stop the streamer."""
        if self._streamer:
            try:
                self._streamer.auto_reconnect(False, BASE_BACKOFF_SEC, 0)
                self._streamer.disconnect()
            except Exception as exc:
                logger.error("Disconnect error: %s", exc)
            self._streamer = None
        if self._running_event and not self._running_event.is_set():
            self._running_event.set()

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    async def subscribe(self, instrument_keys: list[str]) -> None:
        """Add keys. Will push to SDK if streamer already exists."""
        self._subscribed_keys = list(set(self._subscribed_keys + instrument_keys))
        if self._streamer:
            self._streamer.subscribe(self._subscribed_keys, "full")
            logger.info("Subscribed: %s", self._subscribed_keys)

    # ------------------------------------------------------------------
    # SDK callbacks (called from SDK internal thread -> bridge to asyncio)
    # ------------------------------------------------------------------

    def _on_open(self, *args: Any) -> None:
        """SDK event open callback — accepts arbitrary structural SDK args."""
        logger.info("Upstox WebSocket connection established.")
        if self._subscribed_keys and self._streamer:
            self._streamer.subscribe(self._subscribed_keys, "full")

    def _on_message(self, message: Any) -> None:
        """SDK callback — runs on SDK receiver thread."""
        if not self._loop or self._loop.is_closed():
            return
        tick = self._parse_feed(message)
        if tick is None:
            return
        try:
            self._buffer.push(tick)
        except Exception as exc:
            logger.error("Buffer push failed: %s", exc)
        asyncio.run_coroutine_threadsafe(self._tick_handler(tick), self._loop)

    def _on_error(self, error: Any) -> None:
        logger.error("Upstox WS error: %s", error)

    def _on_close(self, ws: Any = None, close_status_code: Any = None, close_msg: Any = None) -> None:
        """SDK event close callback — properly tracks object instance mapping via self."""
        logger.warning(f"Upstox WebSocket connection closed. Code: {close_status_code}, Message: {close_msg}")

    def _on_reconnecting(self, *args: Any, **kwargs: Any) -> None:
        logger.warning("Upstox reconnecting...")

    def _on_reconnect_stopped(self, *args: Any, **kwargs: Any) -> None:
        logger.critical("Upstox reconnect budget exhausted.")
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._raise_fatal(), self._loop)

    async def _raise_fatal(self) -> None:
        if self._running_event and not self._running_event.is_set():
            self._running_event.set()
        raise IngestionFatalError("Reconnect failed after max attempts.")

    # ------------------------------------------------------------------
    # Feed parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_feed(raw: Any) -> dict[str, Any] | None:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                return None
        if not isinstance(raw, dict) or raw.get("type") != "live_feed":
            return None

        feeds = raw.get("feeds") or {}
        current_ts = raw.get("currentTs") or ""

        for instrument_key, feed_data in feeds.items():
            # Index feed: fullFeed.indexFF, Options feed: fullFeed.marketFF
            market_ff = (
                feed_data.get("fullFeed", {}).get("marketFF")
                or feed_data.get("fullFeed", {}).get("indexFF")
                or {}
            )
            ltpc = market_ff.get("ltpc") or {}

            ltp = ltpc.get("ltp")
            if ltp is None:
                ltp = market_ff.get("atp")
            if ltp is None:
                continue

            tick: dict[str, Any] = {
                "instrument_key": instrument_key,
                "symbol": instrument_key.split("|")[-1] if "|" in instrument_key else instrument_key,
                "last_price": float(ltp),
                "volume": market_ff.get("vtt"),
                "oi": market_ff.get("oi"),
                "ltq": ltpc.get("ltq"),
                "close_price": ltpc.get("cp"),
                "timestamp": current_ts or str(ltpc.get("ltt", "")),
                "iv": market_ff.get("iv"),
                "atp": market_ff.get("atp"),
                "tbq": market_ff.get("tbq"),
                "tsq": market_ff.get("tsq"),
            }

            for k in ("volume", "ltq", "tbq", "tsq", "oi"):
                val = tick[k]
                if isinstance(val, str):
                    try:
                        tick[k] = int(val)
                    except ValueError:
                        pass

            return tick

        return None
