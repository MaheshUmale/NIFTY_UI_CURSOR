# Purpose

Unit and integration tests for every module. Defines the test pyramid (unit → integration → system) and the mock data generators that other test files must use.

# Ownership

| File | Owner |
|------|-------|
| `conftest.py` | All agents (shared fixtures) |
| `test_risk_constants_invariants.py` | Risk & Compliance Auditor |
| `test_risk_manager.py` | Risk & Compliance Auditor |
| `test_trade_journal.py` | Risk & Compliance Auditor |
| `test_time_utils.py` | All agents (shared concern) |
| `test_exception_handler.py` | All agents (shared concern) |
| `test_logger.py` | All agents (shared concern) |
| `test_e2e_live.py` | All agents (shared concern) — E2E live streaming & UI pipeline tests |
| `fixtures/` | All agents (shared mock data) |

# Local Contracts

- **Test pyramid enforced:**
  - **Unit tests** (no I/O, no Upstox) — must complete in < 100 ms each.
  - **Integration tests** (real SQLite, real Redis if available) — must complete in < 5 s each.
  - **System tests** (recorded Upstox fixtures) — must complete in < 30 s each.
- **Mock data discipline:** All Upstox-shaped test data must come from `tests/fixtures/upstox_ticks.json` (auto-generated from anonymized real ticks in `ALL_DOCS/upstox_strategy_db.raw_tick_data.json`). Never hard-code tick objects in test files.
- **Time-freezing:** Use `freezegun` (or `time_machine`) for any test that touches the time-of-day risk gates.
- **No network in unit tests:** Unit tests must never hit the real Upstox API. Patch `requests` / `websockets` at the test boundary.
- **Coverage gate:** `pytest --cov=src --cov-fail-under=80` must pass in CI. New code without tests = blocked PR.

# Work Guidance

- **Mock the auth module first:** Every test that would otherwise trigger `UpstoxAuth.get_valid_token()` must `monkeypatch` it to return a deterministic fake token. The fixture `fake_access_token` is provided in `conftest.py`.
- **No `print` in tests:** Use `caplog` to assert on log messages, not stdout. Tests must be silent on success.
- **Property-based testing:** Use `hypothesis` for invariants like "VWAP never negative" or "COI PCR is always finite when denominator ≠ 0".
- **Trade journal invariants:** Every test that writes to the journal must verify the row count, the unique `tag`, and the WAL mode.
- **Logger state reset:** Use the `reset_logging_state()` helper from `test_logger.py` or the `_reset_before` fixture when testing logging configuration.

# Verification

- `pytest -x --strict` must pass in < 60 s on a developer laptop.
- Coverage report must show ≥ 80% on `src/`.
- Mutation testing (mutmut) target: ≥ 70% killed mutants on `src/risk/` and `src/execution/`.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-files are documented in the Ownership table above. Add child AGENTS.md files only if `tests/fixtures/` grows into a sub-topic with its own standards.