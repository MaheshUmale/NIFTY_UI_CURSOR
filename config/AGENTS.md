# Purpose

Configuration contracts for the trading system. Holds **immutable risk rules** (Risk Auditor owns), tunable strategy parameters, index-specific constants, and secret management.

# Ownership

| File | Owner | Mutability |
|------|-------|-------------|
| `risk_constants.py` | **Risk & Compliance Auditor** (sole owner) | **IMMUTABLE** — no child may weaken |
| `strategy_config.py` | Strategy & Core Logic Engineer | Tunable, must be reviewed weekly |
| `index_params.py` | Upstox API Architect | Hard-coded by broker contract |
| `.env` | Risk & Compliance Auditor (secrets gate) | Never committed; `.env.example` only |
| `.access_token.json` | Auth module (auto-generated) | Daily rotation; gitignored |

# Local Contracts

## IMMUTABLE Risk Rules (Risk Auditor — VETO POWER)

```python
# config/risk_constants.py — DO NOT MODIFY WITHOUT RISK AUDITOR SIGN-OFF
from datetime import time

BLOCK_NEW_ENTRIES_AFTER: time = time(15, 15)   # 3:15 PM IST
FORCE_SQUARE_OFF_BY:     time = time(15, 20)   # 3:20 PM IST
CANCEL_OPEN_ORDERS_AT:   time = time(15, 18)   # 3:18 PM IST
MAX_DAILY_LOSS_PCT:      float = 0.04
MAX_RISK_PER_TRADE_PCT: float = 0.02
MAX_TRADES_PER_DAY:     int   = 3
ORDER_PRODUCT:           str   = "I"          # MIS — Intraday
MIN_OPEN_INTEREST:       int   = 50_000
SLIPPAGE_BUFFER_PCT:     float = 0.005
EMERGENCY_FLATTEN_PCT:   float = 0.05        # > 5% daily loss → flatten all
```

**Any code that violates these constants must be refactored. No exceptions, no overrides, no environment-based bypass.**

## Tunable Strategy Parameters

```python
# config/strategy_config.py — review weekly
ORB_RANGE_MINUTES:     int   = 15        # 9:15 to 9:30
VWAP_RESET_TIME:        time  = time(9, 15)
EMA_PERIOD:             int   = 9
VOLUME_CONFIRMATION_MULT: float = 1.5      # require volume ≥ 1.5x 20-period avg
PCR_BULLISH_TRIGGER:    float = 1.2
PCR_BEARISH_TRIGGER:    float = 0.8
```

## Index-Specific Constants

| Index | Strike Step | Lot Size | Tick Size |
|-------|-------------|----------|-----------|
| NIFTY 50 | 50 | 25 | 0.05 |
| BANKNIFTY | 100 | 15 | 0.05 |
| FINNIFTY | 50 | 25 | 0.05 |
| MIDCPNIFTY | 25 | 50 | 0.05 |

# Work Guidance

- **Never** hard-code risk values inside `src/` — always import from `config/risk_constants.py`.
- **Never** commit `.env` or `.access_token.json`. Use `.gitignore` for both.
- When a strategy parameter is changed, the **Strategy Engineer** must run a backtest and update `Work Guidance` here with the new expected impact.
- When the Risk Auditor changes an immutable rule, this file and `src/risk/AGENTS.md` must be updated atomically.

# Verification

- **Automated check:** a CI test must assert that `config/risk_constants.py` contains exactly the values above (no drift, no PR can silently weaken them).
- **Manual review:** any PR touching this folder requires sign-off from the **Risk & Compliance Auditor**.
- **Secret hygiene:** pre-commit hook must reject any commit containing patterns matching `UPSTOX_API_SECRET=` or `"access_token":\s*"[A-Za-z0-9]{30,}"`.

# Child DOX Index

This folder is **flat** — no child AGENTS.md files are required. Sub-files (`.py`, `.env`, `.json`) are individually documented in the table under **Ownership** above.
