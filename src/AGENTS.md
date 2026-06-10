# Purpose

Python source code root for the trading system. Defines module-level contracts, logging configuration, and shared exceptions that every sub-module must use.

# Ownership

| File | Owner |
|------|-------|
| `__init__.py` (per module) | Each module owner |
| `utils/logger.py` | All agents (shared concern) |
| `utils/exception_handler.py` | All agents (shared concern) |
| `utils/constants.py` | All agents (shared concern) |
| `utils/time_utils.py` | All agents (shared concern) |

# Local Contracts

- **Language runtime:** Python 3.11+ (strict). No 2.x, no 3.7/3.8 compat hacks.
- **Type hints:** **MANDATORY** on every public function. No `Any` except at strict boundaries.
- **Logging:** Every module that performs I/O, computation, or external calls must instantiate a module-level `logger = logging.getLogger(__name__)`.
- **No silent exception swallowing:** All `except` blocks must log the exception with `logger.exception(...)` or re-raise. This is non-negotiable.
- **No `print`:** Stdout is for humans in development only. Production code uses `logger.info`.
- **Import order:** stdlib → third-party → first-party (sorted by name within each group).
- **Async:** All I/O-bound loops must be `asyncio` based; CPU-bound math can be sync.

# Work Guidance

- Sub-modules listed in the Child DOX Index below are **loosely coupled** — they communicate via:
  1. In-memory data classes (see `src/data/market_buffer.py`)
  2. Explicit async event handlers (callbacks registered in the WebSocket client)
  3. **Never** via shared mutable global state.
- Strategy code (`src/strategy/`) **must not** import from `src/execution/` or `src/risk/`. The dependency graph flows strictly:
  `data → strategy → risk gate → execution → journal`.
- Risk code (`src/risk/`) holds the **veto power**. No sub-module may override its decisions; they can only be configured via `config/risk_constants.py`.

# Verification

- **Import lint:** `python -c "import src"` must succeed and import all sub-modules in dependency order.
- **Static type check:** `mypy --strict src/` must pass.
- **Cyclomatic complexity:** No function may exceed a McCabe score of 12 (enforce via `radon cc -n C src/`).
- **No print statements:** `grep -r "print(" src/` must return zero results.

# Child DOX Index

| Sub-folder | Owns | Link to child AGENTS.md |
|------------|------|------------------------|
| `src/auth/` | Upstox OAuth2, daily token persistence, rate-limit token bucket | `src/auth/AGENTS.md` |
| `src/data/` | Market data ingestion: instrument CSV, async WebSocket V3, ring buffer | `src/data/AGENTS.md` |
| `src/strategy/` | ORB, VWAP, 9 EMA, confluence, signal generation | `src/strategy/AGENTS.md` |
| `src/execution/` | Order management, position tracker, EOD square-off | `src/execution/AGENTS.md` |
| `src/risk/` | Risk gates (VETO), daily loss guard, SQLite journal | `src/risk/AGENTS.md` |
| `src/utils/` | Logger, time helpers, exception wrappers, shared constants | `src/utils/AGENTS.md` |

DOX Status (as of 2026-06-09):
- `src/AGENTS.md`: ✅ created
- `src/auth/AGENTS.md`: ✅ created
- `src/data/AGENTS.md`: ✅ created
- `src/strategy/AGENTS.md`: ✅ created
- `src/execution/AGENTS.md`: ✅ created
- `src/risk/AGENTS.md`: ✅ created
- `src/utils/AGENTS.md`: ✅ created
