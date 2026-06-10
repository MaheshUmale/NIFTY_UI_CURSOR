"""Tunable strategy parameters — owner: Strategy & Core Logic Engineer.

These values are intentionally distinct from :mod:`config.risk_constants`.
They control the *signal generation* layer (ORB, VWAP, EMA9, confluence)
and may be tuned weekly via backtest, but they never weaken the
immutable risk limits defined in :mod:`config.risk_constants`.

The canonical narrative contract lives in ``config/AGENTS.md`` under
"Tunable Strategy Parameters".

Source citation:
    > config/AGENTS.md — Tunable Strategy Parameters
"""
from __future__ import annotations

from datetime import time

# ---------------------------------------------------------------------------
# Opening Range Breakout (ORB)
# ---------------------------------------------------------------------------

#: Minutes used to compute the opening range. The default 15-minute window
#: runs from 9:15 to 9:30 IST. Breakout is confirmed only after this range
#: is fully formed.
ORB_RANGE_MINUTES: int = 15

#: Volume confirmation multiplier. The breakout candle's volume must be
#: at least ``VOLUME_CONFIRMATION_MULT`` times the 20-period average volume,
#: otherwise the breakout is treated as a fakeout.
VOLUME_CONFIRMATION_MULT: float = 1.5

#: Look-back period for the volume average used in the volume confirmation
#: filter.
VOLUME_AVG_PERIOD: int = 20

# ---------------------------------------------------------------------------
# VWAP engine
# ---------------------------------------------------------------------------

#: VWAP resets at 9:15 IST every day. The engine uses cumulative
#: price × volume, not a rolling window, to preserve institutional
#: positioning.
VWAP_RESET_TIME: time = time(9, 15)

# ---------------------------------------------------------------------------
# EMA premium filter
# ---------------------------------------------------------------------------

#: Period of the exponential moving average applied to option premium
#: prices. Scalps on Calls are blocked when premium < EMA(premium).
EMA_PERIOD: int = 9

#: Bar size (seconds) for the EMA computation. 60 s = 1-minute bars.
EMA_BAR_SECONDS: int = 60

# ---------------------------------------------------------------------------
# Confluence / signal quality
# ---------------------------------------------------------------------------

#: Put-Call Ratio (PCR) threshold above which the market is treated as
#: bullish. Used by the confluence layer as a contextual bias.
PCR_BULLISH_TRIGGER: float = 1.2

#: PCR threshold below which the market is treated as bearish.
PCR_BEARISH_TRIGGER: float = 0.8

#: Minimum number of confluence layers (spot structure, premium swing,
#: OI wall) that must agree before a signal is published as actionable.
CONFLUENCE_MIN_LAYERS: int = 2

#: Total number of confluence layers the engine can vote on.
CONFLUENCE_TOTAL_LAYERS: int = 3

# ---------------------------------------------------------------------------
# Time-of-day exclusions
# ---------------------------------------------------------------------------

#: Start of the lunch churn window. Signals in this band are suppressed
#: unless they are grade-A breakouts with full confluence.
LUNCH_WINDOW_START: time = time(11, 45)

#: End of the lunch churn window.
LUNCH_WINDOW_END: time = time(13, 15)

# ---------------------------------------------------------------------------
# Data window
# ---------------------------------------------------------------------------

#: Number of strikes kept on each side of the at-the-money strike when
#: the WebSocket subscribes to option chains. Total window = 2*N+1.
ATM_STRIKE_WINDOW: int = 3

# ---------------------------------------------------------------------------
# Expiry Day Parameters
# ---------------------------------------------------------------------------

#: PCR threshold for bullish entry on expiry days (Thursday).
PCR_EXPIRY_BULLISH_TRIGGER: float = 1.4

#: PCR threshold for bearish entry on expiry days (Thursday).
PCR_EXPIRY_BEARISH_TRIGGER: float = 0.6

#: Time when gamma lock period begins on expiry days.
GAMMA_LOCK_START: time = time(13, 30)

# ---------------------------------------------------------------------------
# Momentum Index Weights
# ---------------------------------------------------------------------------

#: Weight for PCR slope in momentum index.
MOMENTUM_WEIGHT_PCR: float = 0.4

#: Weight for VWAP gap in momentum index.
MOMENTUM_WEIGHT_VWAP: float = 0.3

#: Weight for delta flow in momentum index.
MOMENTUM_WEIGHT_DELTA: float = 0.3

# ---------------------------------------------------------------------------
# Signal thresholds
# ---------------------------------------------------------------------------

#: Upper threshold for momentum index to generate long signal.
MOMENTUM_UPPER_THRESHOLD: float = 0.5

#: Lower threshold for momentum index to generate exit signal.
MOMENTUM_LOWER_THRESHOLD: float = -0.5

# ---------------------------------------------------------------------------
# Time-of-day weights
# ---------------------------------------------------------------------------

#: Signal weight multiplier for opening session (first 60 minutes).
TIME_WEIGHT_OPEN: float = 1.0

#: Signal weight multiplier for midday session (60-360 minutes from open).
TIME_WEIGHT_MIDDAY: float = 0.4

#: Signal weight multiplier for closing session (last 60 minutes).
TIME_WEIGHT_CLOSE: float = 1.3
