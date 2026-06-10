# Purpose

Signal generation: Opening Range Breakout (ORB), VWAP engine, 9 EMA premium filter, confluence logic, COI PCR, GEX, IV Skew, Max Pain, Premium Divergence. Produces **suggestions** (never orders) that pass through the risk gate.

# Ownership

| File | Owner |
|------|-------|
| `__init__.py` | Strategy & Core Logic Engineer |
| `orb_strategy.py` | Strategy & Core Logic Engineer |
| `vwap_engine.py` | Strategy & Core Logic Engineer |
| `ema_filter.py` | Strategy & Core Logic Engineer |
| `signal_generator.py` | Strategy & Core Logic Engineer |
| `confluence.py` | Strategy & Core Logic Engineer |
| `coi_pcr.py` | Strategy & Core Logic Engineer |
| `gex_calculator.py` | Strategy & Core Logic Engineer |
| `iv_skew.py` | Strategy & Core Logic Engineer |
| `max_pain.py` | Strategy & Core Logic Engineer |
| `premium_divergence.py` | Strategy & Core Logic Engineer |
| `momentum_index.py` | Strategy & Core Logic Engineer |

# Local Contracts

- **No order placement:** This module emits `Signal` objects only. It **must not** import from `src/execution/`. Violation = architectural drift.
- **No risk overrides:** This module reads `config/strategy_config.py` for tunable thresholds. It **must not** read `config/risk_constants.py`. Risk constants are the risk gate's domain.
- **Backtesting mandatory:** Every signal generator must ship with a `backtest()` function that replays historical ticks and reports hit-rate, Sharpe, max drawdown. A signal without a backtest is not shippable.
- **Deterministic:** Given the same tick stream, the strategy must produce the same signal set. No `random`, no time-of-day noise.
- **Source of truth:** `UNIFIED_TRADING_STRATEGY.md`.

# Work Guidance

- **ORB defaults:** Track 9:15–9:30 IST range (15 min). Require close **above** range high (long) or **below** range low (short) with a volume = `VOLUME_CONFIRMATION_MULT` × 20-period average.
- **VWAP reset:** VWAP resets at 9:15 IST per `VWAP_RESET_TIME`. Use cumulative price × volume, not a rolling window, to keep institutional positioning intact.
- **EMA9 filter:** A long scalp on a Call premium is invalid if the premium is **below** its 1-minute 9 EMA. Symmetric for Puts.
- **Time-of-day exclusion:** Do not generate signals between 11:45–13:15 IST (lunch churn) unless the signal is a grade-A breakout with full confluence.
- **Confluence gate:** Every signal must pass at least 2 of 3 layers: spot structure + premium swing + OI wall. Otherwise mark as `LOW_CONVICTION_WATCH` and never publish.
- **COI PCR:** Calculate for 7-strike window (ATM ±3). PCR > 1.2 bullish, < 0.8 bearish (use expiry-adjusted thresholds on Thursdays).
- **GEX:** Net positive = dealers long gamma (dampening). Net negative = dealers short gamma (amplifying).
- **Max Pain:** Track intraday shifts. Large shifts during final hour indicate meaningful push.
- **Premium Divergence:** Call VWAP gap = (Call_VWAP - Spot_VWAP) / Spot_VWAP. Detect hidden accumulation when spot range-bound but premium VWAP diverges.
- **Trap Detection:** Veto if PCR flat (0.8-1.0), Max Pain static, and bilateral volume/OI spikes without bias.
- **Daily reset:** Strategy state must reset to neutral at 9:15 IST every day. Persist nothing across sessions.

# Verification

- `test_orb_strategy.py` must cover:
  - Range high/low correctness with synthetic ticks.
  - Breakout direction (up vs down) is deterministic.
  - Volume confirmation rejects low-volume fakeouts.
- `test_signal_generator.py` must cover:
  - Combined ORB + VWAP cross ? signal.
  - EMA9 veto correctly blocks counter-trend scalps.
  - Lunch window suppresses signals.
- `test_confluence.py` must cover:
  - 2-of-3 layer minimum enforced.
  - LOW_CONVICTION_WATCH never promotes to actionable.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files required. Sub-modules are documented in the Ownership table above.
