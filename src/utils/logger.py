"""Centralised logging setup for the trading system.

All sub-modules obtain their logger via ``get_logger(__name__)``, which
returns a child of the root logger configured once by ``configure_logging()``.

The root logger writes JSON lines to a rotating file handler and human-readable
text to console. A ``SensitiveDataFilter`` scrubs credentials from every
record regardless of destination.

Source citation:
    > src/utils/AGENTS.md — Logger convention, no-``print`` rule.
    > logs/AGENTS.md — JSON-line format, rotation, IST timestamps,
      sensitive-field scrubbing.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Module state (set once by configure_logging)
# ---------------------------------------------------------------------------

_LOGGING_CONFIGURED: bool = False

# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


class SensitiveDataFilter(logging.Filter):
    """Scrub credentials and PII from log records.

    Replaces the **value** of any recognised sensitive key with the string
    ``"***REDACTED***"`` in:

    - The ``msg`` field (via regex replacement of ``key=value`` patterns).
    - The ``args`` tuple (if a positional argument matches a known key).
    - The ``extra`` dict (if a known key is present in the record's
      ``__dict__``).

    Sensitive key patterns (case-insensitive substring match):
    - ``access_token``
    - ``api_secret``
    - ``authorization``
    - ``bearer``
    """

    SENSITIVE_KEYS: set[str] = {"access_token", "api_secret", "authorization", "bearer"}

    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub the formatted message
        record.msg = self._scrub(record.msg)

        # Scrub positional args that might be strings
        if record.args:
            scrubbed_args = tuple(
                arg if not isinstance(arg, str) else self._scrub(arg)
                for arg in record.args
            )
            record.args = scrubbed_args

        # Scrub fields added via ``extra=``, stored directly on the record
        for key in list(record.__dict__.keys()):
            if self._is_sensitive(key):
                record.__dict__[key] = "***REDACTED***"

        # Also scrub the common field names that appear in record.__dict__
        # even if they don't match the exact key list (e.g. "auth" fields
        # set by upstream code).
        for attr in ("access_token", "api_secret", "authorization", "bearer"):
            if hasattr(record, attr):
                setattr(record, attr, "***REDACTED***")

        return True  # Never drop records

    def _is_sensitive(self, key: str) -> bool:
        """Return ``True`` if the key (case-insensitive) contains any
        sensitive pattern."""
        lower = key.lower()
        return any(sk in lower for sk in self.SENSITIVE_KEYS)

    def _scrub(self, text: str) -> str:
        """Replace sensitive ``key=value`` or ``key: value`` patterns.

        Uses a greedy regex that captures the key and everything after it
        until a semicolon, comma, or end-of-line, then substitutes the
        entire span with ``key=***REDACTED***`` or ``key:***REDACTED***``.
        """
        for key in self.SENSITIVE_KEYS:
            # key=value — greedy capture until ; , or EOL
            text = re.sub(
                rf"(?i){re.escape(key)}=[^;,\n]+",
                f"{key}=***REDACTED***",
                text,
            )
            # key: value — colon-separated variant (e.g. "Authorization: Bearer tok123")
            text = re.sub(
                rf"(?i){re.escape(key)}:\s*[^;,\n]+",
                f"{key}:***REDACTED***",
                text,
            )
        return text


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------


class JsonFormatter(logging.Formatter):
    """Format log records as JSON lines for machine parsing.

    Produces one JSON object per line with fields:
    ``ts``, ``level``, ``module``, ``msg``, ``tag`` (optional), ``epoch_ms``.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Compute epoch ms from the record's created timestamp (floating-point
        # seconds since epoch, UTC).
        epoch_ms = int(record.created * 1000)

        # ISO-8601 with +05:30 offset using IST timezone.
        # Local import avoids any risk of circular dependency at module load.
        import datetime as _dt

        IST_ZONE = _dt.timezone(_dt.timedelta(hours=5, minutes=30), name="Asia/Kolkata")
        utc_dt = _dt.datetime.fromtimestamp(record.created, tz=_dt.timezone.utc)
        ist_dt = utc_dt.astimezone(IST_ZONE)
        ts = ist_dt.isoformat()

        payload: dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
            "epoch_ms": epoch_ms,
        }

        # Include optional ``tag`` if the caller passed it in ``extra``.
        tag = getattr(record, "tag", None)
        if tag is not None:
            payload["tag"] = str(tag)

        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    """Initialise the root logger with file + console handlers.

    Idempotent: calling this function more than once has no effect after the
    first call.

    Parameters
    ----------
    level : str
        Log level string (``"DEBUG"``, ``"INFO"``, ``"WARNING"``,
        ``"ERROR"``, ``"CRITICAL"``).
    log_dir : str
        Relative or absolute path to the logs directory. Created automatically
        if it does not exist.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    # Ensure the log directory exists
    os.makedirs(log_dir, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    # JSON-formatted rotating file handler
    file_path = os.path.join(log_dir, "trader.log")
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=20,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(JsonFormatter())
    file_handler.addFilter(SensitiveDataFilter())
    root.addHandler(file_handler)

    # Human-readable console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    console_handler.addFilter(SensitiveDataFilter())
    root.addHandler(console_handler)

    _LOGGING_CONFIGURED = True

    root.info("Logging configured", extra={"level": level, "log_dir": log_dir})


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger.

    All sub-modules should call::

        logger = get_logger(__name__)

    The returned logger is a child of the root logger and inherits handlers
    configured by :func:`configure_logging`.

    Parameters
    ----------
    name : str
        Typically ``__name__`` from the calling module.

    Returns
    -------
    logging.Logger
        A logger instance with the given name.
    """
    return logging.getLogger(name)