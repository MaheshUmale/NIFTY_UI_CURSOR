"""Verify full end-to-end with real Upstox token via lifecycle."""
from __future__ import annotations

import asyncio
import time

from src.data.market_buffer import MarketBuffer
from src.data.websocket_client import WebSocketClient, WS_URL
from src.strategy.signal_generator import SignalGenerator
from src.utils.logger import configure_logging, get_logger
from src.utils.time_utils import now_ist

configure_logging()
logger = get_logger(__name__)

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NkFGMzUiLCJqdGkiOiI2YTI4ZmQzNjAzZDM5YjRjZTQ2Yzk1N2IiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc4MTA3MTE1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzgxMTI4ODAwfQ.LwTW4Rg5raYFy8IChCI0bBS-HuQSEJbNyBTntAtF8OM"
INSTRUMENT_KEYS = [
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
]

tick_count = 0
signal_count = 0
buffer = MarketBuffer(capacity=2000)
strategy = SignalGenerator()

received_ticks = []

def on_tick(tick):
    global tick_count, signal_count
    tick_count += 1
    buffer.push(tick)
    received_ticks.append(tick)

    sig = strategy.on_tick(tick)
    if sig is not None:
        signal_count += 1
        logger.info("SIGNAL #%d: %s %s @ %.2f", signal_count, sig.symbol, sig.side, sig.entry_price)


async def main():
    client = WebSocketClient(token=ACCESS_TOKEN, tick_handler=on_tick, buffer=buffer)
    try:
        await client.connect()
    except Exception as e:
        logger.error("connect raised: %s", e)

    logger.info("=== RESULT ===")
    logger.info("WS_URL constant: %s", WS_URL)
    logger.info("Ticks received: %d", tick_count)
    logger.info("Signals generated: %d", signal_count)
    logger.info("Buffer size: %d", len(buffer))
    if received_ticks:
        last = received_ticks[-1]
        logger.info("Last tick: %s price=%.2f oi=%s", last.get("instrument_key"), last.get("last_price"), last.get("oi"))
    logger.info("DONE")


if __name__ == "__main__":
    asyncio.run(main())
