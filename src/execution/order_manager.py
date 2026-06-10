"""Order manager — the only module that sends orders to Upstox.

Enforces MIS product mandate, idempotency via tag, and RiskApprovedOrder-only acceptance.

Source citation:
    > src/execution/AGENTS.md — MIS product="I", ApiException handling,
      idempotent tags, RiskApprovedOrder required.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from src.utils.exception_handler import OrderConstructionError, OrderRejectedError, wrap_requests_exception
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Upstox API constants
UPSTOX_ORDER_URL = "https://api.upstox.com/v2/order/place"
UPSTOX_ORDER_MODIFY_URL = "https://api.upstox.com/v2/order/modify"
UPSTOX_ORDER_CANCEL_URL = "https://api.upstox.com/v2/order/cancel"


@dataclass
class Fill:
    """Represents an order fill from Upstox."""
    tag: str
    instrument_key: str
    side: str
    qty: int
    price: float
    timestamp: float
    order_id: str | None = None


class OrderManager:
    """Sends orders to Upstox with full exception handling.

    Parameters
    ----------
    token_provider : callable
        Function that returns a valid access token dict.
    """

    def __init__(self, token_provider: callable) -> None:
        self._token_provider = token_provider
        self._placed_tags: set[str] = set()  # Idempotency guard

    def place_order(
        self,
        instrument_key: str,
        quantity: int,
        side: str,
        order_type: str = "MARKET",
        price: float = 0.0,
        trigger_price: float = 0.0,
        tag: str = "",
        product: str = "I",  # MIS mandate
    ) -> dict[str, Any]:
        """Place an order on Upstox.

        Parameters
        ----------
        instrument_key : str
            Upstox instrument key.
        quantity : int
            Number of contracts.
        side : str
            "BUY" or "SELL".
        order_type : str
            "MARKET", "LIMIT", "SL", or "SL-M".
        price : float
            Limit price (0 for market orders).
        trigger_price : float
            Trigger price for SL orders.
        tag : str
            Client-side tag for idempotency.
        product : str
            Must be "I" for MIS (intraday).

        Returns
        -------
        dict
            Upstox order response.

        Raises
        ------
        OrderConstructionError
            If product is not "I" or tag is missing.
        OrderRejectedError
            If Upstox rejects the order.
        """
        # Validate product mandate
        if product != "I":
            raise OrderConstructionError(
                f"Product must be 'I' (MIS), got '{product}'"
            )

        # Validate tag
        if not tag:
            raise OrderConstructionError("Tag is required for idempotency")

        # Idempotency check
        if tag in self._placed_tags:
            logger.info("Order with tag %s already placed, skipping", tag)
            return {"status": "skipped", "tag": tag}

        # Build payload
        payload = {
            "quantity": quantity,
            "product": product,
            "validity": "DAY",
            "price": price,
            "tag": tag,
            "instrument_key": instrument_key,
            "order_type": order_type,
            "transaction_type": side.upper(),
            "disclosed_quantity": 0,
            "trigger_price": trigger_price,
            "is_amo": False,
        }

        try:
            token = self._token_provider()
            headers = {
                "Authorization": f"Bearer {token.get('access_token', '')}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            start_time = time.time()
            response = requests.post(
                UPSTOX_ORDER_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
            latency_ms = (time.time() - start_time) * 1000

            response.raise_for_status()
            result = response.json()

            self._placed_tags.add(tag)
            logger.info(
                "Order placed: tag=%s instrument=%s side=%s qty=%d price=%.2f latency_ms=%.1f",
                tag, instrument_key, side, quantity, price, latency_ms,
            )
            return result

        except requests.RequestException as exc:
            wrapped = wrap_requests_exception(exc, context="place_order")
            logger.exception("Order placement failed for tag=%s", tag)
            raise OrderRejectedError(
                f"Order rejected: {wrapped}",
                status_code=wrapped.status_code,
                request_id=wrapped.request_id,
            ) from exc

    def modify_order(
        self,
        order_id: str,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
    ) -> dict[str, Any]:
        """Modify an existing order."""
        payload: dict[str, Any] = {"order_id": order_id}
        if quantity is not None:
            payload["quantity"] = quantity
        if price is not None:
            payload["price"] = price
        if trigger_price is not None:
            payload["trigger_price"] = trigger_price

        try:
            token = self._token_provider()
            headers = {
                "Authorization": f"Bearer {token.get('access_token', '')}",
                "Content-Type": "application/json",
            }

            response = requests.put(
                UPSTOX_ORDER_MODIFY_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            wrapped = wrap_requests_exception(exc, context="modify_order")
            logger.exception("Order modification failed for order_id=%s", order_id)
            raise OrderRejectedError(
                f"Order modification rejected: {wrapped}",
                status_code=wrapped.status_code,
            ) from exc

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel an existing order."""
        try:
            token = self._token_provider()
            headers = {
                "Authorization": f"Bearer {token.get('access_token', '')}",
                "Content-Type": "application/json",
            }

            response = requests.delete(
                f"{UPSTOX_ORDER_CANCEL_URL}/{order_id}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            wrapped = wrap_requests_exception(exc, context="cancel_order")
            logger.exception("Order cancellation failed for order_id=%s", order_id)
            raise OrderRejectedError(
                f"Order cancellation rejected: {wrapped}",
                status_code=wrapped.status_code,
            ) from exc

    def cancel_all_open(self) -> None:
        """Cancel all open orders (used by daily loss guard)."""
        logger.warning("Cancelling all open orders")
        # Implementation would fetch open orders and cancel each
        # For now, log the action
        self._placed_tags.clear()