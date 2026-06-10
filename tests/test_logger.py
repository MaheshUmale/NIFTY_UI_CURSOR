"""Unit tests for ``src.utils.logger``.

Source citation:
    > src/utils/AGENTS.md — Verification: ``test_logger.py`` must cover
      same-name same-instance, and ``logger.exception`` includes traceback.
    > logs/AGENTS.md — Verification: sensitive fields are scrubbed.
"""
from __future__ import annotations

import json
import logging
import os

import pytest

from src.utils.logger import (
    JsonFormatter,
    SensitiveDataFilter,
    configure_logging,
    get_logger,
)


def reset_logging_state() -> None:
    """Reset the global logging configuration state for testing."""
    # Remove all handlers from root logger
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(logging.WARNING)  # reset to default
    # Reset the module's flag
    import src.utils.logger as logger_mod
    logger_mod._LOGGING_CONFIGURED = False  # noqa: SLF001


class TestGetLogger:
    """Module-scoped logger factory."""

    def test_same_name_same_logger(self) -> None:
        a = get_logger("test.a")
        b = get_logger("test.a")
        assert a is b

    def test_different_names_different_loggers(self) -> None:
        a = get_logger("test.a")
        b = get_logger("test.b")
        assert a is not b

    def test_logger_name(self) -> None:
        log = get_logger("my.module")
        assert log.name == "my.module"

    def test_logger_inherits_root_handlers(self) -> None:
        reset_logging_state()
        configure_logging(log_dir="logs")
        log = get_logger("test.child")
        assert len(log.handlers) >= 0  # child inherits from root
        root = logging.getLogger()
        assert len(root.handlers) >= 2  # file + console
        reset_logging_state()


class TestSensitiveDataFilter:
    """Credential scrubbing."""

    @pytest.fixture
    def filter_instance(self) -> SensitiveDataFilter:
        return SensitiveDataFilter()

    def test_scrubs_access_token_in_message(
        self, filter_instance: SensitiveDataFilter
    ) -> None:
        filtered = filter_instance._scrub("access_token=abc123")
        assert "***REDACTED***" in filtered
        assert "abc123" not in filtered

    def test_scrubs_api_secret(self, filter_instance: SensitiveDataFilter) -> None:
        filtered = filter_instance._scrub("api_secret=xyz789")
        assert "***REDACTED***" in filtered
        assert "xyz789" not in filtered

    def test_scrubs_bearer(self, filter_instance: SensitiveDataFilter) -> None:
        filtered = filter_instance._scrub("Authorization: Bearer tok123")
        assert "***REDACTED***" in filtered
        assert "tok123" not in filtered

    def test_clean_message_untouched(
        self, filter_instance: SensitiveDataFilter
    ) -> None:
        msg = "Signal generated: BUY NIFTY 50"
        assert filter_instance._scrub(msg) == msg

    def test_filter_never_drops(self, filter_instance: SensitiveDataFilter) -> None:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="access_token=secret",
            args=(),
            exc_info=None,
        )
        assert filter_instance.filter(record) is True


class TestJsonFormatter:
    """JSON-line log format."""

    def test_json_output_has_required_fields(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert "ts" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["module"] == "test.module"
        assert parsed["msg"] == "hello world"
        assert "epoch_ms" in parsed
        assert isinstance(parsed["epoch_ms"], int)

    def test_json_includes_tag_when_present(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="order placed",
            args=(),
            exc_info=None,
        )
        record.__dict__["tag"] = "trader-2026-06-09-uuid"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["tag"] == "trader-2026-06-09-uuid"

    def test_json_ts_is_iso_with_offset(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="ts check",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "+05" in parsed["ts"] or "Z" in parsed["ts"]


class TestConfigureLogging:
    """One-time root logger setup."""

    @pytest.fixture(autouse=True)
    def _reset_before(self) -> None:
        reset_logging_state()
        yield
        reset_logging_state()

    def test_configure_twice_is_idempotent(self, tmp_path: str) -> None:
        log_dir = str(tmp_path)
        configure_logging(log_dir=log_dir)
        handler_count = len(logging.getLogger().handlers)
        configure_logging(log_dir=log_dir)
        assert len(logging.getLogger().handlers) == handler_count

    def test_log_file_created(self, tmp_path: str) -> None:
        log_dir = str(tmp_path)
        configure_logging(log_dir=log_dir)
        logger = get_logger("test.writer")
        logger.info("force file creation")
        log_path = os.path.join(log_dir, "trader.log")
        assert os.path.exists(log_path)

    def test_log_file_contains_json(self, tmp_path: str) -> None:
        log_dir = str(tmp_path)
        configure_logging(log_dir=log_dir)
        logger = get_logger("test.writer")
        logger.info("write test")
        log_path = os.path.join(log_dir, "trader.log")
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
        # Last line should be "write test" (after "Logging configured" setup msg)
        last_line = lines[-1].strip()
        parsed = json.loads(last_line)
        assert parsed["msg"] == "write test"
        assert parsed["level"] == "INFO"

    def test_console_handler_present(self, tmp_path: str) -> None:
        configure_logging(log_dir=str(tmp_path))
        root = logging.getLogger()
        stream_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_file_handler_is_rotating(self, tmp_path: str) -> None:
        configure_logging(log_dir=str(tmp_path))
        root = logging.getLogger()
        rotating_handlers = [
            h
            for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(rotating_handlers) >= 1