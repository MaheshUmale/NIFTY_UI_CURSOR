"""Unit tests for ``src.utils.exception_handler``.
Source citation:
    > src/utils/AGENTS.md — Verification: ``test_exception_handler.py`` must
      cover raw HTTP error wrapping and preservation of original exception.
"""
from __future__ import annotations
import pytest
import requests
from src.utils.exception_handler import (
    IngestionFatalError,
    OrderConstructionError,
    OrderRejectedError,
    RiskVetoError,
    TokenExpiredError,
    UpstoxAPIError,
    wrap_requests_exception,
)
from config.risk_constants import VETO_TIME, VETO_DAILY_LOSS, VETO_TRADE_LIMIT
class TestExceptionHierarchy:
    """Verify the type hierarchy."""
    def test_token_expired_is_upstox_error(self) -> None:
        assert issubclass(TokenExpiredError, UpstoxAPIError)
    def test_order_rejected_is_upstox_error(self) -> None:
        assert issubclass(OrderRejectedError, UpstoxAPIError)
    def test_order_construction_not_upstox_error(self) -> None:
        """OrderConstructionError is a plain Exception — it fires BEFORE
        the API call, so it's not an Upstox error."""
        assert not issubclass(OrderConstructionError, UpstoxAPIError)
    def test_ingestion_fatal_not_upstox_error(self) -> None:
        assert not issubclass(IngestionFatalError, UpstoxAPIError)
    def test_risk_veto_not_upstox_error(self) -> None:
        assert not issubclass(RiskVetoError, UpstoxAPIError)
    def test_upstox_api_error_attributes(self) -> None:
        exc = UpstoxAPIError("test", status_code=400, request_id="req-1")
        assert exc.status_code == 400
        assert exc.request_id == "req-1"
        assert exc.original is None
    def test_upstox_api_error_with_original(self) -> None:
        original = ValueError("inner")
        exc = UpstoxAPIError("wrapped", original=original)
        assert exc.original is original
        assert "wrapped" in str(exc)
class TestOrderConstructionError:
    """OrderConstructionError tests."""
    def test_plain_exception(self) -> None:
        exc = OrderConstructionError("product must be 'I'")
        assert "product must be 'I'" in str(exc)
class TestRiskVetoError:
    """RiskVetoError tests."""
    def test_default_reason_code(self) -> None:
        exc = RiskVetoError("Too late")
        assert exc.reason_code == VETO_TIME
    def test_custom_reason_code(self) -> None:
        exc = RiskVetoError("Daily loss hit", reason_code=VETO_DAILY_LOSS)
        assert exc.reason_code == VETO_DAILY_LOSS
    def test_trade_limit_veto(self) -> None:
        exc = RiskVetoError("3 trades done", reason_code=VETO_TRADE_LIMIT)
        assert exc.reason_code == VETO_TRADE_LIMIT
    def test_message_preserved(self) -> None:
        exc = RiskVetoError("exact message")
        assert str(exc) == "exact message"
class TestWrapRequestsException:
    """HTTP-to-domain exception mapper."""
    def test_upstox_api_error_passthrough(self) -> None:
        original = UpstoxAPIError("already wrapped")
        result = wrap_requests_exception(original)
        assert result is original
    def test_http_error_wrapping(self) -> None:
        """Simulate a ``requests.HTTPError``."""
        try:
            resp = requests.Response()
            resp.status_code = 429
            resp._content = b'{"message": "rate limit"}'
            resp.headers["X-Request-Id"] = "req-999"
            raise requests.HTTPError(response=resp)
        except requests.HTTPError as exc:
            wrapped = wrap_requests_exception(exc, context="place_order")
            assert isinstance(wrapped, UpstoxAPIError)
            assert wrapped.status_code == 429
            assert wrapped.request_id == "req-999"
            assert isinstance(wrapped.original, requests.HTTPError)
    def test_connection_error_wrapping(self) -> None:
        try:
            raise requests.ConnectionError("connection refused")
        except requests.ConnectionError as exc:
            wrapped = wrap_requests_exception(exc)
            assert isinstance(wrapped, UpstoxAPIError)
            assert wrapped.original is exc
    def test_generic_exception_wrapping(self) -> None:
        try:
            raise RuntimeError("unexpected")
        except RuntimeError as exc:
            wrapped = wrap_requests_exception(exc)
            assert isinstance(wrapped, UpstoxAPIError)
            assert isinstance(wrapped.original, RuntimeError)
    def test_wrap_with_context(self) -> None:
        try:
            raise requests.ConnectionError()
        except requests.ConnectionError as exc:
            wrapped = wrap_requests_exception(exc, context="websocket_auth")
            assert "websocket_auth" in wrapped.args[0]
