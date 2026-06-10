"""Typed exception hierarchy and HTTP-to-domain exception mapper.
All Upstox API exceptions are wrapped into ``UpstoxAPIError`` subclasses so
that callers never catch raw ``requests.HTTPError`` or ``urllib3`` exceptions.
The rule is unbreakable: every ``except`` block either logs with
``logger.exception(...)`` and recovers, or re-raises. Never silent.
Source citation:
    > src/utils/AGENTS.md — Exception wrapper contract.
    > config/risk_constants.py — VETO_* reason codes imported for RiskVetoError.
"""
from __future__ import annotations
from typing import Any
from config.risk_constants import (
    VETO_DAILY_LOSS,
    VETO_LOW_LIQUIDITY,
    VETO_POSITION_SIZE,
    VETO_TIME,
    VETO_TRADE_LIMIT,
)
# ---------------------------------------------------------------------------
# Base domain exception
# ---------------------------------------------------------------------------
class UpstoxAPIError(Exception):
    """Base exception for all Upstox API interaction failures.
    Attributes
    ----------
    status_code : int | None
        HTTP status code returned by Upstox (if available).
    request_id : str | None
        Upstox-side request identifier for debugging.
    original : BaseException | None
        The original exception that triggered this error (chained via
        ``__cause__``).
    """
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        original: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.original = original
# ---------------------------------------------------------------------------
# Auth exceptions
# ---------------------------------------------------------------------------
class TokenExpiredError(UpstoxAPIError):
    """Raised when the access token is past its expiry time."""
# ---------------------------------------------------------------------------
# Order execution exceptions
# ---------------------------------------------------------------------------
class OrderConstructionError(Exception):
    """Raised when an order payload fails validation BEFORE the API call.
    Example: missing ``product="I"`` or invalid instrument key.
    """
class OrderRejectedError(UpstoxAPIError):
    """Raised when Upstox returns a non-retryable rejection (4xx/5xx)."""
# ---------------------------------------------------------------------------
# Data ingestion exceptions
# ---------------------------------------------------------------------------
class IngestionFatalError(Exception):
    """Raised when the WebSocket reconnection budget is exhausted.
    This error causes a non-zero exit. Never silently caught.
    """
# ---------------------------------------------------------------------------
# Risk gate exceptions
# ---------------------------------------------------------------------------
class RiskVetoError(Exception):
    """Raised by the risk gate when a signal fails one of the five hard vetoes.
    Attributes
    ----------
    reason_code : str
        One of ``VETO_TIME``, ``VETO_DAILY_LOSS``, ``VETO_TRADE_LIMIT``,
        ``VETO_POSITION_SIZE``, or ``VETO_LOW_LIQUIDITY``.
    Usage
    -----
    .. code-block:: python
        raise RiskVetoError("After 3:15 PM", reason_code=VETO_TIME)
    """
    def __init__(self, message: str, *, reason_code: str = VETO_TIME) -> None:
        super().__init__(message)
        self.reason_code = reason_code
# ---------------------------------------------------------------------------
# Public helper: HTTP → domain exception mapper
# ---------------------------------------------------------------------------
def wrap_requests_exception(
    exc: BaseException,
    *,
    context: str = "",
) -> UpstoxAPIError:
    """Convert a ``requests`` / ``urllib3`` exception into an ``UpstoxAPIError``.
    The original exception is preserved as ``__cause__`` for traceability.
    The helper **returns** the wrapped error — the caller is responsible for
    raising (or not) as appropriate in their own ``except`` block.
    Parameters
    ----------
    exc : BaseException
        The exception caught from a ``requests`` or ``urllib3`` call.
    context : str
        Optional human-readable description of the operation that failed
        (e.g. ``"place_order"``). Prepended to the message text.
    Returns
    -------
    UpstoxAPIError
        An ``UpstoxAPIError`` (or subclass) wrapping the original exception.
        If ``exc`` is already an ``UpstoxAPIError``, it is returned unchanged.
    """
    import requests
    import urllib3
    if isinstance(exc, UpstoxAPIError):
        return exc
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        req_id = exc.response.headers.get("X-Request-Id") if exc.response is not None else None
        msg = f"Upstox HTTP error ({status})" if not context else f"{context}: HTTP {status}"
        return UpstoxAPIError(msg, status_code=status, request_id=req_id, original=exc)
    if isinstance(exc, requests.ConnectionError):
        msg = "Upstox connection refused" if not context else f"{context}: connection refused"
        return UpstoxAPIError(msg, original=exc)
    if isinstance(exc, urllib3.exceptions.MaxRetryError):
        msg = "Upstox max retries exceeded" if not context else f"{context}: max retries exceeded"
        return UpstoxAPIError(msg, original=exc)
    # Generic catch-all: wrap any other exception type
    return UpstoxAPIError(
        context if context else str(exc),
        original=exc,
    )
