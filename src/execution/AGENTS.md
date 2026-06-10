# Purpose

Order management: place, modify, cancel with full `ApiException` handling; position tracker; end-of-day forced square-off. The only module allowed to send orders to Upstox.

# Ownership

| File | Owner |
|------|-------|
| `__init__.py` | Upstox API Architect |
| `order_manager.py` | Upstox API Architect |
| `position_tracker.py` | Risk & Compliance Auditor |
| `square_off.py` | Risk & Compliance Auditor |

# Local Contracts

- **MIS product mandate:** Every order payload must set `product="I"`. A missing or different value must raise `OrderConstructionError` BEFORE the API call. No exception, no override.
- **ApiException = log + graceful, never crash:** Every Upstox exception must be caught, logged with `logger.exception(...)`, and mapped to a typed internal exception. The async loop must continue.
- **No signal acceptance without risk-gate approval:** The `order_manager.place_order()` API must accept a `RiskApprovedOrder` object, not a raw `Signal`. The risk gate is the only producer of `RiskApprovedOrder`. This enforces the dependency rule.
- **Idempotency:** Every order must carry a client-side `tag` (uuid4) so retries don't duplicate. Tag format: `trader-{ISO8601-date}-{uuid4}`.
- **Atomic position updates:** `position_tracker.apply_fill(fill)` must be called **exactly once** per Upstox order update callback. No double-counting.

# Work Guidance

- **Bracket / cover orders:** Use Upstox `BO` (Bracket Order) or `CO` (Cover Order) for every entry, with `stop_loss` and `target` set in the same call. This guarantees the stop is server-side, not client-side.
- **Time-of-day rules (Risk Auditor mandate):**
  - 15:15 IST → block new entries (`BLOCK_NEW_ENTRIES_AFTER`).
  - 15:18 IST → cancel all open orders (`CANCEL_OPEN_ORDERS_AT`).
  - 15:20 IST → force close all positions (`FORCE_SQUARE_OFF_BY`).
- **Daily loss trip:** If `position_tracker.daily_loss_pct >= MAX_DAILY_LOSS_PCT (0.04)`, immediately cancel all open orders and square off all positions. No human override.
- **Modifying SL/Target:** Use `modify_order` rather than cancel-and-replace, to preserve the parent order_id.
- **Logging:** Every fill must be logged with `tag`, `instrument_key`, `qty`, `price`, `latency_ms`, and the `Signal` snapshot that produced it.

# Verification

- `test_order_manager.py` must cover:
  - `ApiException` → `OrderRejectedError`, loop continues.
  - Missing `product="I"` → `OrderConstructionError`, no API call.
  - `RiskApprovedOrder` required (TypeError on raw Signal).
  - Idempotency: same tag → single order.
- `test_position_tracker.py` must cover:
  - Net quantity correctly computed for partial fills.
  - Realized vs unrealized P&L separation.
  - Daily loss trip fires exactly once when threshold crossed.
- `test_square_off.py` must cover:
  - All open positions reduced to 0 by 15:20 IST.
  - Open orders cancelled at 15:18 IST.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-modules are documented in the Ownership table above.
