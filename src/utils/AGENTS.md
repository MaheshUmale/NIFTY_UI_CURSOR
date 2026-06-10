# Purpose

Cross-cutting utilities used by all other modules: centralized logger, time/IST helpers, exception wrappers, and shared constants. Pure functions, no side effects beyond logging and time.

# Ownership

| File | Owner |
|------|-------|
| `__init__.py` | All agents (shared concern) |
| `logger.py` | All agents (shared concern) |
| `time_utils.py` | All agents (shared concern) |
| `exception_handler.py` | All agents (shared concern) |
| `constants.py` | All agents (shared concern) |

# Local Contracts

- **Pure helpers:** Every function in this module is a **pure function** (deterministic given inputs) OR has only side effects limited to `logging` / clock access. No I/O, no Upstox calls, no DB writes.
- **Re-export hub:** `src/utils/__init__.py` re-exports the public API so callers can `from src.utils import get_logger, now_ist, ...`.
- **No business logic:** This module **must not** import from `src/strategy/`, `src/execution/`, `src/risk/`, or `src/data/`. It is a leaf dependency.
- **Versioned constants:** Anything in `constants.py` is a string / int / enum, not a class with behavior. Add a new constant, do not modify old ones — Risk Auditor owns the deltas.

# Work Guidance

- **Logger convention:** `get_logger(name: str) -> logging.Logger` configures a single file + console handler per process. Do NOT configure handlers inside sub-modules.
- **Time zone:** `now_ist() -> datetime` returns an IST-aware datetime. Never use naive `datetime.now()`. Never use UTC for business logic.
- **Exception wrapper:** All Upstox exceptions must be wrapped in `UpstoxAPIError` (with `.status_code`, `.request_id`, `.original`). Do not re-raise raw `requests` or `urllib3` exceptions.
- **No `print`:** Any debug printing in this module is a violation — use `logger.debug`.

# Verification

- `test_logger.py` must cover:
  - Same name returns same logger instance.
  - `logger.exception` includes traceback.
- `test_time_utils.py` must cover:
  - `now_ist()` is timezone-aware Asia/Kolkata.
  - `is_market_hours(ts)` correctly identifies 9:15–15:30 window.
- `test_exception_handler.py` must cover:
  - Raw `requests.HTTPError` is wrapped to `UpstoxAPIError`.
  - Original exception is preserved on `.__cause__`.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-modules are documented in the Ownership table above.
