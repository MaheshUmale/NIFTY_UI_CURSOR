# Unified Trading Strategy Document
## Consolidated Framework for Intraday Index Options Trading

**Version**: 1.0  
**Date**: June 7, 2026  
**Target Market**: Indian Index Derivatives (NIFTY/BANKNIFTY)  
**System Type**: Web-based Trading System with Backtesting & Live Signal Generation

---

## TABLE OF CONTENTS
1. [Executive Summary](#executive-summary)
2. [Core Philosophy](#core-philosophy)
3. [Mathematical Foundations](#mathematical-foundations)
4. [System Architecture](#system-architecture)
5. [Feature Engineering Module](#feature-engineering-module)
6. [Signal Generation Engine](#signal-generation-engine)
7. [Risk Management & Filters](#risk-management--filters)
8. [Time-of-Day Structural Filters](#time-of-day-structural-filters)
9. [Premium Divergence Engine](#premium-divergence-engine)
10. [Confluence Engine](#confluence-engine)
11. [Execution Protocols](#execution-protocols)
12. [Backtesting Framework](#backtesting-framework)
13. [Technology Stack](#technology-stack)
14. [Implementation Roadmap](#implementation-roadmap)
15. [Data Flow & APIs](#data-flow--apis)

---

## EXECUTIVE SUMMARY

This document synthesizes multiple institutional-grade trading strategies into a unified framework for developing an automated trading assistant specializing in Indian Index Derivatives. The system integrates:

- **COI PCR Trading Agent** (Advanced & Intraday versions) - Focus on Change in Open Interest Put-Call Ratio from institutional perspective
- **Quantitative Options Coding Agent** - ML-friendly feature engineering (IV skew, GEX, Max Pain, VWAP)
- **Premium Divergence Architecture** - Premium vs. spot price action analysis
- **Institutional-Grade Intraday Index Options Edge** - Integrated ecosystem approach

The unified system treats volatility, order flow, positioning, and premium action as interconnected elements rather than isolated indicators, seeking composite signatures where multiple institutional behaviors align to generate high-conviction intraday signals.

---

## CORE PHILOSOPHY

### Institutional Perspective
All strategies analyze the market from the **option sellers' perspective** (institutional capital) rather than retail traders. This flips conventional interpretations:
- **Short Buildup**: Aggressive writing (Increasing OI + Decreasing Premium) = Bearish for Calls, Bullish for Puts
- **Long Buildup**: Aggressive buying (Increasing OI + Increasing Premium) = Momentum setups
- **Short Covering**: Forced buyback (Decreasing OI + Increasing Premium Spike) = Explosive moves
- **Long Unwinding**: Profit booking (Decreasing OI + Decreasing Premium) = Trend exhaustion

### Core Principles
1. **Institutional Flow Detection**: Track smart money via OI changes, premium flows, and volume patterns
2. **Confluence Validation**: Require multiple independent signals to align before generating trades
3. **Dynamic Adaptation**: Adjust parameters based on market regime, time-of-day, and volatility conditions
4. **Risk-First Approach**: Multiple veto filters prevent false signals and protect capital
5. **Expiry Awareness**: Special protocols for Thursday expiry anomalies and gamma flip risks

---

## MATHEMATICAL FOUNDATIONS

### 1. Change in Open Interest (COI) Put-Call Ratio (PCR)
**Definition**: 
```
COI PCR = (Sum of Put COI over N strikes) / (Sum of Call COI over N strikes)
```
Where N = 7 strikes (ATM ±3 strikes) for NIFTY (50-point strike intervals)

**Calculation Frequency**: Every 15 minutes during market hours (9:15 AM - 3:00 PM)

**Strike Selection Protocol**:
- ATM: Spot price rounded to nearest strike
- OTM Calls: Exactly 3 strikes above ATM
- OTM Puts: Exactly 3 strikes below ATM
- Total Scope: Exactly 7 strikes analyzed

### 2. Dynamic 7-Strike Window Shifting
**Trigger Condition**: Spot price crosses midpoint between current ATM and next strike up/down

**Data Inheritance**: Retain historical cumulative COI from 9:15 AM onward for new strike set

**Overlapping Data Lock**:
- Moving UP: Drop lowest 1-3 put strikes, include new ATM, add 1-3 higher OTM call strikes
- Moving DOWN: Drop highest 1-3 call strikes, include new ATM, add 1-3 lower OTM put strikes

**Recalibration**: Pause signal generation for exactly 15 minutes after shift ([WINDOW SHIFTING - STABILIZING])

### 3. Gamma Exposure (GEX)
**Definition**:
```
Net GEX = Σ(Call_gamma × Call_OI) - Σ(Put_gamma × Put_OI)
```
Where gamma is calculated using Black-Scholes model

**Interpretation**:
- **Positive GEX**: Dealers long gamma → sell into rallies, buy on dips (dampening)
- **Negative GEX**: Dealers short gamma → buy on rallies, sell on dips (amplifying)
- **Zero-Gamma Level**: Price where net GEX ≈ 0 (regime change level)

### 4. Implied Volatility (IV) Skew
**Definition**:
```
IV Skew = IV_call_ATM - IV_put_ATM
```
Or alternatively: slope of IV vs. strike curve

**Tracking**: 
- IV Trend: d(IV_skew)/dt (expanding vs. collapsing)
- IV Regimes: Normal, elevated, crushed

### 5. Premium VWAP vs. Spot VWAP
**Premium VWAP**:
```
VWAP_premium = Σ(Option_premium × Volume) / Σ(Volume)
```
(for ATM/NTM call and put series)

**Spot VWAP**:
```
VWAP_spot = Σ(Spot_price × Volume) / Σ(Volume)
```

**Divergence Signal**:
```
VWAP_gap = (VWAP_premium - VWAP_spot) / VWAP_spot
```

### 6. Theta Acceleration
**Definition**:
```
Theta = -∂V/∂t (time decay)
Theta_Accel = d(Theta)/dt
```
Tracks acceleration of time decay (particularly important near expiry)

### 7. Max Pain
**Definition**:
```
MaxPain = argmin_K [ Σ max(0, S-K) × OI_call(K) + Σ max(0, K-S) × OI_put(K) ]
```
Where S = underlying price, K = strike price

**Tracking**: Intraday Max Pain level shifts indicate institutional positioning bias

---

## SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                              │
│                                                                     │
│  UPSTOX WebSocket ────► Tick Normalization ────► Redis Cache       │
│      (LTP, OI, Volume,     │        (1-min OHLCV + OI + Greeks)    │
│       IV, Greeks)          │                                       │
│                           │                                       │
│  Historical Data ───────► Batch Processor ─────► DuckDB Analytics  │
│   (DuckDB Storage)         │        (Feature-rich dataset)         │
│                           │                                       │
└───────────────────────────┬───────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                        FEATURE ENGINE                             │
│                                                                     │
│  • COI PCR Calculation (7-strike window)                           │
│  • IV Skew & Trend Analysis                                        │
│  • Gamma Exposure (GEX) & Zero-Gamma Detection                    │
│  • Call/Put Wall Identification                                   │
│  • Premium VWAP Calculation (Call & Put series)                  │
│  • Spot VWAP Calculation                                         │
│  • VWAP Divergence Analysis                                      │
│  • Theta Acceleration Computation                                │
│  • Max Pain Tracking                                             │
│  • Volume/OI Ratio Analysis                                      │
│                                                                     │
└───────────────────────────┬───────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                      SIGNAL GENERATION ENGINE                     │
│                                                                     │
│  • Core COI PCR Trend Analysis                                     │
│  • Confluence Engine (3-Layer Validation)                         │
│  • Premium Divergence Signals                                     │
│  • Gamma Hedging Triggers                                         │
│  • Volatility-OI Nexus Signals                                    │
│  • Composite Momentum Index (Weighted Features)                   │
│  • Trap Detection (No-Trade Signatures)                           │
│                                                                     │
└───────────────────────────┬───────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                        RISK MANAGEMENT                            │
│                                                                     │
│  • Price-OI Divergence Filter (Trap Check)                        │
│  • 12:30 PM European Window Filter                                │
│  • Volume Confirmation Filter                                     │
│  • Time-of-Day Structural Filters                                 │
│  • Expiry Day Anomaly Mitigation                                  │
│  • Gamma Lock Protection (Post 1:30 PM Thursdays)                 │
│                                                                     │
└───────────────────────────┬───────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│                     EXECUTION & INTERFACE                         │
│                                                                     │
│  • Web Interface: Multi-chart Layout                              │
│    - Spot Index Chart                                             │
│    - ATM Call Premium Chart                                       │
│    - ATM Put Premium Chart                                        │
│    - Synchronized time axis                                       │
│    - VWAP overlays                                                │
│    - Signal highlighting                                          │
│                                                                     │
│  • Signal Output Format                                           │
│    Timestamp: [HH:MM] \| Day Regime: [Standard/Thursday Expiry]   │
│    Index Spot: [Value] \| ATM Strike: [Strike] \| Window Status:  │
│    [Aligned/Shifted/Stabilizing]                                  │
│    Current COI PCR: [Value] \| Trend (last 30 mins): [Rising/Falling/Flat] │
│    Absolute OI Walls: [Call Wall Strike] (Resistance) vs [Put Wall Strike] (Support) │
│    Confluence Analysis:                                           │
│      Market Structure: [Higher Highs/Lower Lows/Ranging]         │
│      Premium Swings: [CE Breakout/PE Breakout/Compression]       │
│      Arrival COI Shift: [Call Writing Spike at Resistance/Put     │
│      Writing at Support/None]                                     │
│      Institutional Context: [Put Unwinding/Call Unwinding/Short   │
│      Build-up/Long Liquidation]                                   │
│    Trading Bias: [HIGH-CONVICTION BULLISH/HIGH-CONVICTION BEARISH│
│    /NEUTRAL/GAMMA LOCK/HARD EXIT]                                 │
│    Action: [Specific Instruction]                                 │
│                                                                     │
│  • Order Execution (Optional, with confirmation)                  │
│    - UPSTOX REST API Integration                                  │
│    - Manual confirmation required for live orders                 │
│    - Paper trading/simulation mode available                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## FEATURE ENGINEERING MODULE

### 1. COI PCR Calculator
**Inputs**: Put OI, Call OI for 7-strike window (ATM ±3)
**Outputs**: 
- Current COI PCR value
- PCR slope (rate of change)
- PCR trend (Rising/Falling/Flat over 30 minutes)
- Window status (Aligned/Shifted/Stabilizing)

**Implementation**:
```python
def calculate_coi_pcr(put_oi_array, call_oi_array):
    """
    Calculate COI PCR for 7-strike window
    put_oi_array, call_oi_array: arrays of 7 strikes [OTM3, OTM2, OTM1, ATM, OTM1, OTM2, OTM3]
    """
    total_put_oi = sum(put_oi_array)
    total_call_oi = sum(call_oi_array)
    if total_call_oi == 0:
        return float('inf')  # Avoid division by zero
    return total_put_oi / total_call_oi
```

### 2. Gamma Exposure (GEX) Calculator
**Inputs**: Option chain data with strike, gamma, OI for calls and puts
**Outputs**:
- Net GEX value
- Zero-Gamma level (strike where net GEX crosses zero)
- Call/Put Wall strikes (max call gamma, max put gamma)

**Implementation**:
```python
def calculate_gex(option_chain):
    """
    Calculate net Gamma Exposure
    option_chain: list of dicts with strike, call_gamma, call_oi, put_gamma, put_oi
    """
    call_gex = sum(opt['call_gamma'] * opt['call_oi'] for opt in option_chain)
    put_gex = sum(opt['put_gamma'] * opt['put_oi'] for opt in option_chain)
    net_gex = call_gex - put_gex
    
    # Find zero-gamma level (approximate)
    sorted_chain = sorted(option_chain, key=lambda x: x['strike'])
    # Implementation would interpolate where net GEX crosses zero
    
    return {
        'net_gex': net_gex,
        'call_gex': call_gex,
        'put_gex': put_gex,
        'zero_gamma_level': approximate_zero_gamma(sorted_chain)
    }
```

### 3. IV Skew & Trend Calculator
**Inputs**: ATM call IV, ATM put IV from option chain
**Outputs**:
- IV Skew value
- IV Skew trend (expanding/collapsing/flat)
- IV Percentile (current vs. historical range)

### 4. Premium VWAP Engine
**Inputs**: Tick-level premium and volume data for ATM/NTM options
**Outputs**:
- Call Premium VWAP
- Put Premium VWAP
- VWAP Gap (Call Premium VWAP - Spot VWAP) / Spot VWAP
- VWAP Gap (Put Premium VWAP - Spot VWAP) / Spot VWAP
- Premium breakout detection (vs. VWAP bands)

### 5. Max Pain Tracker
**Inputs**: Option chain with strikes and OI for calls and puts
**Outputs**:
- Current Max Pain strike
- Max Pain shift (change from previous period)
- Max Pain stability flag

---

## SIGNAL GENERATION ENGINE

### 1. Core COI PCR Signals
**Trend-Based Signals**:
- **Rising PCR** (last 30 min): Increasing COI PCR suggests put buying/call writing pressure
- **Falling PCR**: Decreasing COI PCR suggests call buying/put writing pressure
- **Flat PCR**: Stable COI PCR suggests equilibrium

**Threshold-Based Signals** (to be backtest-optimized):
- **Bullish Trigger**: COI PCR > 1.2 (standard day), > 1.4 (Thursday expiry)
- **Bearish Trigger**: COI PCR < 0.8 (standard day), < 0.6 (Thursday expiry)
- **Neutral Zone**: 0.8 ≤ COI PCR ≤ 1.2 (standard), 0.6 ≤ COI PCR ≤ 1.4 (Thursday)

### 2. Confluence Engine (3-Layer Validation)
To upgrade signal from standard to [HIGH CONVICTION - MAX ALLOCATION], you must validate the signal against this three-layer confluence engine before execution:

**Layer A: Spot Market Structure Analysis**
- **Long Validation**: The spot index must be forming a structural Higher High / Higher Low pattern on the 5-minute chart or breaking out of a clear swing high resistance zone
- **Short Validation**: The spot index must be forming a structural Lower High / Lower Low pattern on the 5-minute chart or breaking below a clear swing low support zone

**Layer B: Option Premium Swing & Volatility Check (CE / PE)**
- Check the underlying option charts (the specific ATM Call or Put option you intend to trade)
- **Long Validation**: The ATM Call premium must show a structural breakout above its immediate morning swing high, accompanied by a sharp volume spike in the contract itself
- **Short Validation**: The ATM Put premium must show a structural breakout above its immediate morning swing high, confirming absolute downside momentum

**Layer C: High Absolute OI Walls & Arrival COI Shifts**
- Look for major absolute Open Interest concentrations (the absolute “OI Walls”) across the entire option chain
- **Resistance Wall Hit (Short Entry)**: As the Spot Index rises and touches a major absolute Call OI Wall, look at the 1-minute COI at that exact swing high. If Call COI spikes massively at that moment while Put COI drops, the wall is holding. Execute a Short entry.
- **Support Wall Hit (Long Entry)**: As the Spot Index drops and touches a major absolute Put OI Wall, look at the 1-minute COI at that exact swing low. If Put COI spikes massively at that moment while Call COI drops, the support is holding. Execute a Long entry.

### 3. Premium Divergence Signals
- **Hidden Accumulation**: Spot range-bound + NTM call premium VWAP up + PCR↑ + call OI↓ (short covering)
- **Distribution Warning**: Spot range-bound + NTM put premium VWAP up + PCR↓ + put OI↓
- **Short-Covering Trigger**: Rising PCR with falling ATM call OI
- **Gamma Squeeze Detection**: Premium expansion coinciding with spot resistance breaks
- **9 EMA Execution Filter**: Never execute a long option scalp if that option’s premium is trading below its own 1-minute 9 EMA

### 4. Gamma Hedging Triggers
- **Zero-Gamma Breakout**: Price crossing an OI wall in a negative-gamma zone → Buy signal (since dealers must buy underlying)
- **Call Wall Breakout**: Price breaking above major Call OI wall with negative GEX → Bullish signal
- **Put Wall Breakdown**: Price breaking below major Put OI wall with negative GEX → Bearish signal

### 5. Volatility-OI Nexus Signals
- **IV-Crush Trap Avoidance**: PCR high + IV down = NO-GO (bull-trap)
- **Breakout Confirmation**: PCR moderate + IV up + growing call OI = GO (breakout)
- **Put Wall + IV Up**: PCR 1.1-1.4 + IV up + heavy put OI = GO (short-covering rally)

### 6. Composite Momentum Index
```
momentum_index = w1 * PCR_slope_norm + w2 * VWAP_gap_norm + w3 * Delta_flow_norm
```
Where:
- PCR_slope_norm = normalized PCR slope (instantaneous PCR change)
- VWAP_gap_norm = normalized VWAP gap (OptionPremiumVWAP_NTM - SpotVWAP) / SpotVWAP
- Delta_flow_norm = normalized delta flow (NetGammaFlow or NetDeltaTrades) / TotalOptionOI
- Weights w1-w3 optimized via backtesting

**Signal Generation**:
- if momentum_index > upper_threshold: signal = "GO (buy calls)"
- elif momentum_index < lower_threshold: signal = "NO-GO (stay out)"
- else: signal = "HOLD"

**Trap Index** (NO-GO conditions):
- PCR ≈ flat (around 0.8-1.0)
- Max-Pain level static (unchanged)
- Volume/OI ratio spikes simultaneously on both nearby call and put strikes (>2× OI with no directional bias)

---

## RISK MANAGEMENT & FILTERS

### 1. Price-OI Divergence Filter (Trap Check)
- **Veto Long Signal**: If Price is moving UP but COI PCR is moving DOWN → Retail trap (institutions selling calls)
- **Veto Short Signal**: If Price is moving DOWN but COI PCR is moving UP → Short trap (institutions selling puts)
- **Logic**: Prevents trading against institutional flow as indicated by COI PCR direction

### 2. 12:30 PM European Window Filter
- **Time**: Between 12:30 PM and 01:00 PM IST
- **Action**: Monitor if COI PCR trajectory sharply reverses due to global fund flows
- **Confirmation**: If trend direction flips, wait for two consecutive 15-minute intervals to confirm before acting
- **Purpose**: Avoids false signals from European market open volatility

### 3. Volume Confirmation Filter
- **Requirement**: A shifting COI PCR must be accompanied by a corresponding increase in multi-strike absolute volume
- **Validation**: Check volume on the 7-strike window (ATM ±3)
- **Signal Quality**: 
  - High conviction: COI PCR shift + volume increase
  - Low conviction: COI PCR shift without volume increase → Mark as [LOW CONVICTION - WATCH]

### 4. Expiry Day Anomaly Mitigation Protocol (Thursday)
**Applies to**: Thursday expiry days only

**Boundary Threshold Scaling**:
- Standard Bullish Trigger (1.2) scales up to 1.4
- Standard Bearish Trigger (0.8) scales down to 0.6
- **Rationale**: Values between 0.6 and 1.4 on Thursdays are frequently noise from traders closing legs of multi-leg spreads

**The 01:30 PM Gamma Lock**:
- **Rule**: Post-01:30 PM, premium values become negligible
- **Action**: If COI PCR spikes > 2.5 or drops < 0.2 after 01:30 PM, ignore directional implications
- **Status**: [EXPIRY GAMMA FLIP - EXECUTION SUSPENDED]
- **Rationale**: Indicates ongoing short squeeze or massive unwinding of dead options

**Multi-Month Validation**:
- **Action**: Cross-verify Next-Month Expiry total OI PCR
- **Condition**: If Current-Day COI PCR indicates strong breakout but Next-Month structural PCR remains perfectly flat/opposite
- **Result**: Do not carry overnight positions (pure intraday expiry manipulation)

### 5. Gamma Lock Protection
- **Condition**: Post 1:30 PM on Thursdays
- **Action**: Disable directional trading based on COI PCR extremes
- **Alternative**: Allow only range-bound strategies or position squaring

---

## TIME-OF-DAY STRUCTURAL FILTERS

Signals are interpreted differently based on market session:

### 1. Morning Open (0-60′ from 9:15 AM)
- **Characteristics**: Highest volume, widest price swings, genuine directional moves
- **PCR Interpretation**: Large swings are meaningful; early PCR rise may indicate strong buy interest
- **Max Pain**: Shifts often reflect overnight rebalancing
- **OI Changes**: Rapid OI changes suggest immediate institutional positioning
- **Signal Weight**: Full weight (1.0x)

### 2. Midday Dull Phase (60-360′ from 9:15 AM)
- **Characteristics**: Volume thins out, price chops in a range
- **PCR Interpretation**: Small PCR drift often means noise; sustained trends rare
- **Max Pain**: Relatively static mid-day; shifts here are unusual and noteworthy
- **OI Changes**: Gradual OI build-up may indicate dealer position building for later
- **Signal Weight**: Reduced weight (0.3x-0.5x); require larger divergences or final hour confirmation

### 3. Afternoon Run / Power Hour (last 60′)
- **Characteristics**: Volume picks up as European markets open; institutional positioning for close
- **PCR Interpretation**: Final-hour PCR shifts often forecast next-day direction
- **Max Pain**: Strong Max-Pain shift on strong flows during final hour indicates meaningful push
- **OI Changes**: Big OI additions may indicate block trades or gamma scrambles
- **Signal Weight**: Enhanced weight (1.2x-1.5x); institutional flows more reliable

---

## PREMIUM DIVERGENCE ENGINE

Specialized module for analyzing premium vs. spot price action:

### 1. Premium VWAP Calculation
- **Call Premium VWAP**: VWAP of ATM/NTM call option premiums
- **Put Premium VWAP**: VWAP of ATM/NTM put option premiums
- **Spot VWAP**: VWAP of underlying index
- **Update Frequency**: Real-time (tick-level or 1-second)

### 2. Divergence Analysis
**Call Premium Divergence**:
```
Call_VWAP_gap = (Call_Premium_VWAP - Spot_VWAP) / Spot_VWAP
```

**Put Premium Divergence**:
```
Put_VWAP_gap = (Put_Premium_VWAP - Spot_VWAP) / Spot_VWAP
```

### 3. Premium Breakout Detection
- **Method**: Identify when premium breaks above/below morning swing high/low
- **Confirmation**: Require accompanying volume spike in the option contract
- **Filters**: 
  - 9 EMA Execution Filter (premium must be above its 1-minute 9 EMA)
  - Time-of-Day Exclusion Zone (11:45 AM - 1:15 PM)

### 4. Hidden Accumulation Signals
- **Bullish Accumulation**: Spot range-bound + Call_VWAP_gap > 0 + PCR↑ + call OI↓
- **Bearish Accumulation**: Spot range-bound + Put_VWAP_gap > 0 + PCR↓ + put OI↓
- **Interpretation**: Smart money building position while spot hasn't moved yet

### 5. Short-Covering Triggers
- **Call Short Covering**: Rising PCR + falling ATM call OI + spot strength
- **Put Short Covering**: Rising PCR + falling ATM put OI + spot weakness
- **Signal**: Often precedes explosive moves (gamma squeeze)

---

## CONFLUENCE ENGINE

Three-layer validation system for high-conviction signals:

### Layer A: Spot Market Structure
**Tools**: 
- Swing high/low identification (5-minute chart)
- Higher High/Higher Low pattern detection
- Breakout validation from consolidation zones

**Validation**:
- Long: HH/HL pattern OR breakout above swing high resistance
- Short: LH/LL pattern OR breakdown below swing low support

### Layer B: Option Premium Swing & Volatility
**Tools**:
- Premium chart analysis (call and put separately)
- Swing high/low detection on premium charts
- Volume spike validation

**Validation**:
- Long (Call): Structural breakout above morning swing high + volume spike
- Short (Put): Structural breakout above morning swing high + volume spike

### Layer C: High Absolute OI Walls & Arrival COI Shifts
**Tools**:
- OI wall identification (largest call/put OI concentrations)
- 1-minute COI analysis at exact swing points
- COI spike detection at walls

**Validation**:
- Long Entry: Spot touches Put OI Wall + Put COI spikes + Call COI drops
- Short Entry: Spot touches Call OI Wall + Call COI spikes + Put COI drops
- **Stabilization**: After wall hit, wait for COI to stabilize at new levels

---

## EXECUTION PROTOCOLS

### 1. Signal Output Format
When requested for an intraday update, output the assessment exactly in this layout:
```
Timestamp: [HH:MM] | Day Regime: [Standard / Thursday Expiry] | Index tracked: [NIFTY / BANKNIFTY]
Index Spot: [Value] | ATM Strike: [Strike] | Window Status: [Aligned / Shifted / Stabilizing]
Current COI PCR: [Value] | Trend (last 30 mins): [Rising/Falling/Flat]
Absolute OI Walls: [Major Call Wall Strike] (Resistance) vs [Major Put Wall Strike] (Support)
Confluence Analysis:
Market Structure: [Higher Highs / Lower Lows / Ranging]
Premium Swings: [CE Breakout / PE Breakout / Compression]
Arrival COI Shift: [Call Writing Spike at Resistance / Put Writing at Support / None]
Institutional Context: [Put Unwinding / Call Unwinding / Short Build-up / Long Liquidation]
Trading Bias: [HIGH-CONVICTION BULLISH / HIGH-CONVICTION BEARISH / NEUTRAL / GAMMA LOCK / HARD EXIT]
Action: [Specific Instruction based on Sections 3, 4, 5 & 6]
```

### 2. Action Definitions
**HIGH-CONVICTION BULLISH**: 
- Enter long position (buy calls/sell puts)
- Consider maximum allocation based on signal strength
- Set stop-loss below recent swing low or support level

**HIGH-CONVICTION BEARISH**: 
- Enter short position (sell calls/buy puts)
- Consider maximum allocation based on signal strength
- Set stop-loss above recent swing high or resistance level

**NEUTRAL**: 
- No new positions
- Consider reducing existing positions
- Await clearer signal

**GAMMA LOCK**: 
- Avoid directional trades
- Consider gamma scalping strategies
- Monitor for imminent volatility expansion

**HARD EXIT**: 
- Exit all positions immediately
- Typically triggered by negative COI (unwinding) detection
- Emergency risk management action

### 3. Position Sizing & Risk Parameters
- **Base Risk Per Trade**: 0.5-1.0% of capital
- **Maximum Position Size**: 3-5% of capital per direction
- **Daily Loss Limit**: 3-5% of capital (trading halt if breached)
- **Stop-Loss**: 
  - Technical: Below/above recent swing point
  - ATR-based: 1.5x ATR from entry
  - Time-based: Exit if not profitable within 2-3 candles
- **Profit Targets**: 
  - Primary: 1:1 risk-reward ratio
  - Secondary: Trail position with EMA/VWAP
  - Tertiary: Exit at opposite signal or time-of-day filter

### 4. Order Execution Guidelines
- **Order Type**: Prefer limit orders near VWAP to minimize slippage
- **Slicing**: For large orders, use iceberg algorithm (smaller limit orders)
- **Timing**: Avoid first/last 5 minutes of session unless high-conviction signal
- **Confirmation**: Manual confirmation required for live trading (paper trading optional)
- **Broker**: UPSTOX REST API with OAuth2 authentication

---

## BACKTESTING FRAMEWORK

### 1. Historical Data Requirements
- **Data Type**: 1-minute OHLCV + OI + IV + Greeks for NIFTY options
- **Duration**: Minimum 1 year for robust statistics
- **Fields**: Timestamp, open, high, low, close, volume, OI, IV, delta, gamma, theta, vega
- **Source**: UPSTOX Historical API or NSE BhavCopies

### 2. Backtesting Methodology
**Walk-Forward Analysis**:
- **Training Period**: 3 months
- **Testing Period**: 1 month
- **Rotation**: Roll forward by 1 month
- **Purpose**: Prevent overfitting, adapt to changing market regimes

**Transaction Cost Modeling**:
- **Slippage**: 1-2 ticks per leg (market order)
- **Spread**: Bid-ask spread at time of entry
- **Brokerage**: UPSTOX standard charges
- **Taxes**: STT, GST, stamp duty as applicable

### 3. Performance Metrics
- **Return Metrics**: 
  - Total Return
  - Annualized Return (CAGR)
  - Monthly Return Consistency
- **Risk Metrics**: 
  - Maximum Drawdown
  - Sharpe Ratio (risk-free rate = 6%)
  - Sortino Ratio
  - Calmar Ratio
- **Win/Loss Metrics**: 
  - Win Rate (% profitable trades)
  - Profit Factor (gross profit/gross loss)
  - Average Win/Average Loss
  - Consecutive Wins/Losses
- **Signal Quality Metrics**: 
  - Signal Accuracy (% correct predictions)
  - Signal Latency (time from condition to signal)
  - False Signal Rate

### 4. Validation Tests
- **Regime Testing**: Performance across volatility regimes (low/med/high IV)
- **Time-of-Day Testing**: Performance by session (open/midday/close)
- **Expiry Day Testing**: Performance on Thursday vs. other days
- **Drawdown Analysis**: Depth and duration of losing periods
- **Stress Testing**: Performance during market crashes/events

### 5. Implementation
- **Framework**: Python with Backtrader, Zipline, or custom engine
- **Output**: Equity curve, trade log, performance report
- **Optimization**: Parameter tuning via grid search or Bayesian optimization
- **Overfitting Prevention**: Out-of-sample testing, walk-forward validation

---

## TECHNOLOGY STACK

### 1. Backend (Python 3.9+)
- **Web Framework**: FastAPI (high performance, async support)
- **Data Processing**: Pandas, NumPy for calculations
- **Math/Stats**: SciPy, statsmodels for statistical tests
- **Financial Libs**: QuantLib/Black-Scholes for Greeks calculation
- **Database**: 
  - DuckDB (analytical queries, historical data)
  - Redis (real-time caching, pub/sub)
- **Real-Time**: 
  - WebSocket client (UPSTOX market data feed)
  - Async HTTP client (UPSTOX REST API)
- **Utilities**: 
  - Pydantic (data validation)
  - Python-dotenv (environment management)
  - APScheduler (time-based tasks)

### 2. Frontend (Web Interface)
- **Framework**: React.js 18+ with hooks
- **State Management**: Redux Toolkit or React Query
- **Charting**: 
  - Lightweight Charts (TradingView) for performance
  - Alternative: Chart.js or Recharts for customization
- **UI Library**: 
  - Material-UI (MUI) or Ant Design for professional components
  - Alternative: Tailwind CSS + Headless UI
- **Real-Time Updates**: 
  - WebSocket connection for live data
  - Server-Sent Events (SSE) as fallback
- **Features**: 
  - Multi-chart layout with synchronized time axis
  - Drawing tools (trendlines, Fibonacci)
  - Custom indicators (VWAP, EMA, Bollinger Bands)
  - Signal highlighting and alert system

### 3. DevOps & Infrastructure
- **Containerization**: Docker for consistent environments
- **Orchestration**: Docker Compose (local), Kubernetes (production)
- **CI/CD**: 
  - GitHub Actions for automated testing/deployment
  - Pre-commit hooks for code quality
- **Monitoring**: 
  - Prometheus + Grafana for metrics
  - ELK Stack for log aggregation
  - Health checks and alerting
- **Security**: 
  - OAuth2 implementation for UPSTOX API
  - Environment variable management (AWS Secrets Manager/HashiCorp Vault)
  - Input validation and sanitization
  - Rate limiting and DDoS protection

### 4. Testing & Quality Assurance
- **Unit Testing**: pytest with coverage >80%
- **Integration Testing**: Testcontainers for database/services
- **End-to-End Testing**: Cypress or Playwright for UI flows
- **Performance Testing**: Locust or k6 for load testing
- **Code Quality**: 
  - Black/ruff for formatting
  - MyPy for type checking
  - Bandit for security scanning
  - SonarQube for technical debt tracking

---

## IMPLEMENTATION ROADMAP

### Phase 0: Foundation (Week 0)
- [x] Analyze trading strategies for integration points
- [ ] Set up development environment (Python, Node.js, Docker)
- [ ] Initialize Git repository with proper structure
- [ ] Create project documentation and README

### Phase 1: Data Layer & Core Engine (Weeks 1-2)
- [ ] Implement UPSTOX WebSocket client for live data ingestion
- [ ] Create DuckDB schema for OHLCV + OI + Greeks storage
- [ ] Build tick normalization and 1-minute aggregation service
- [ ] Implement core COI PCR calculation engine (7-strike window)
- [ ] Develop dynamic window shifting logic
- [ ] Create basic signal generation (PCR trend-based)
- [ ] Build simple web interface showing current PCR and signals

### Phase 2: Feature Engineering (Weeks 3-4)
- [ ] Implement Gamma Exposure (GEX) calculator
- [ ] Develop IV skew & trend analysis module
- [ ] Build Premium VWAP engine (call/put series)
- [ ] Create Max Pain tracker
- [ ] Add volume/OI ratio analysis
- [ ] Implement Theta acceleration calculation
- [ ] Enhance web interface with multi-chart layout
- [ ] Add drawing tools and technical indicators

### Phase 3: Signal Engine & Risk Management (Weeks 5-6)
- [ ] Implement Confluence Engine (3-layer validation)
- [ ] Build Premium Divergence signals module
- [ ] Create Gamma Hedging triggers
- [ ] Develop Volatility-OI Nexus signals
- [ ] Implement Composite Momentum Index with weights
- [ ] Build Trap Detection (No-Trade signatures)
- [ ] Add Risk Management filters:
  * Price-OI Divergence Filter
  * 12:30 PM European Window Filter
  * Volume Confirmation Filter
  * Time-of-Day Structural Filters
  * Expiry Day Anomaly Mitigation
- [ ] Create signal output formatter per specification
- [ ] Enhance web interface with signal highlighting

### Phase 4: Execution Interface & Backtesting (Weeks 7-8)
- [ ] Implement UPSTOX REST API client for order execution
- [ ] Create order management system (paper/live modes)
- [ ] Add position sizing and risk calculation engine
- [ ] Build manual confirmation system for live orders
- [ ] Develop backtesting engine with historical data
- [ ] Implement walk-forward analysis framework
- [ ] Create performance metrics calculator (Sharpe, drawdown, etc.)
- [ ] Add transaction cost modeling (slippage, spread, fees)

### Phase 5: Testing, Optimization & Deployment (Weeks 9-10)
- [ ] Conduct unit testing for all modules (>80% coverage)
- [ ] Perform integration testing of data pipeline
- [ ] Run backtesting on historical data (minimum 6 months)
- [ ] Optimize signal weights and thresholds via grid search
- [ ] Test time-of-day filters and expiry day protocols
- [ ] Validate signal output format compliance
- [ ] Deploy to staging environment (Docker Compose)
- [ ] Conduct user acceptance testing (UAT)
- [ ] Prepare production deployment documentation

### Phase 6: Production Release & Monitoring (Week 11+)
- [ ] Deploy to production environment
- [ ] Set up monitoring and alerting systems
- [ ] Implement logging and audit trails
- [ ] Create operational runbooks and procedures
- [ ] Establish feedback loop for continuous improvement
- [ ] Plan monthly model retraining and parameter updates

---

## DATA FLOW & APIS

### 1. UPSTOX API Integration
**Authentication**:
- OAuth2 flow: Authorization Code Grant
- Token refresh mechanism (automatic)
- Secure storage of client credentials

**WebSocket Feed (Market Data Feed V3)**:
- **Endpoints**: 
  - `wss://ws-feeds.upstox.com/market-data-feed`
  - Authorization: Bearer token in header
- **Subscription Modes**:
  - `ltpc`: Last Traded Price/close (for spot/futures)
  - `option_greeks`: IV, delta, gamma, theta, vega (for options)
  - `full`: Complete market data (LTP, OI, volume, bid/ask, etc.)
- **Instrument Keys Format**: 
  - NIFTY Spot: `NSE_INDEX|Nifty 50`
  - NIFTY Futures: `NSE_FO|<instrument_key>`
  - NIFTY Options: `NSE_FO|<instrument_key>` (call/put)
- **Data Fields**: 
  - `ltp`: Last traded price
  - `volume`: Traded volume
  - `oi`: Open interest
  - `bid_price`, `bid_qty`: Best bid
  - `ask_price`, `ask_qty`: Best ask
  - `timestamp`: Exchange timestamp (milliseconds)

**REST Endpoints Used**:
- `/v2/option/chain`: Option chain data (strikes, OI, IV, Greeks)
- `/v3/market-quote/ohlc`: Historical candle data (for backtesting)
- `/v3/historical-candle/{instrumentKey}/{unit}/{interval}/{to_date}`: Historical data
- `/v2/user/get-funds-and-margin`: Account funds and margins
- `/v2/order/place`: Place orders (with confirmation)
- `/v2/order/cancel`: Cancel orders

### 2. Internal APIs (FastAPI)
**WebSocket Endpoints** (for frontend):
- `/ws/market-data`: Real-time market data broadcast
- `/ws/signals`: Real-time signal updates
- `/ws/positions`: Position and P&L updates

**REST Endpoints**:
- `/api/v1/market-data`: Current market data snapshot
- `/api/v1/signals`: Current trading signal and analysis
- `/api/v1/historical`: Historical data retrieval
- `/api/v1/backtest`: Run backtesting job
- `/api/v1/parameters`: Get/set strategy parameters
- `/api/v1/health`: System health check

### 3. Database Schema (DuckDB)
**Tables**:
- `market_ticks`: Raw tick data (timestamp, symbol, ltp, volume, oi, bid, ask)
- `market_1m`: 1-minute aggregated data (OHLCV + OI + Greeks)
- `features`: Calculated features (PCR, GEX, IV_skew, VWAP_gap, etc.)
- `signals`: Generated signals with timestamp and metadata
- `trades`: Executed trades (paper and live)
- `performance`: Daily/periodic performance metrics

**Indexes**:
- Primary: timestamp, symbol
- Composite: (timestamp, symbol) for time-series queries
- Partial: Recent data (last 30 days) for faster access

### 4. Data Flow Summary
```
[UPSTOX WebSocket] 
     ↓ (JSON/protobuf messages)
[Normalization Service] 
     ↓ (Standardized format)
[Redis Cache] ←→ [Feature Engine] 
     ↓ (Calculated features)
[Signal Engine] ←→ [Risk Management] 
     ↓ (Filtered signals)
[Execution Interface] 
     ↓ (WebSocket/REST)
[Frontend Web Interface]
     ↓
[User Actions] → [Order Confirmation] → [UPSTOX REST API]
```

### 5. Backup & Recovery
- **Historical Data**: Daily snapshots of DuckDB to cloud storage
- **Configuration**: Version-controlled in Git (encrypted secrets)
- **Logs**: Rotated and archived (JSON format for analysis)
- **Failover**: Hot standby with database replication
- **DR Test**: Quarterly disaster recovery exercises

---

## APPENDICES

### A. GLOSSARY OF TERMS
- **COI**: Change in Open Interest (difference from previous period)
- **PCR**: Put-Call Ratio (Put OI / Call OI)
- **GEX**: Gamma Exposure (net dealer gamma position)
- **IV**: Implied Volatility
- **VWAP**: Volume-Weighted Average Price
- **OI**: Open Interest (total outstanding contracts)
- **ATM**: At-The-Money (strike closest to spot price)
- **OTM**: Out-of-The-Money
- **ITM**: In-The-Money
- **Swing High/Low**: Local peak/trough in price action
- **Confluence**: Multiple independent signals aligning
- **Gamma Flip**: Zero-net-gamma level (regime change)
- **Max Pain**: Strike where option buyers lose minimum value

### B. PARAMETER DEFAULTS (TO BE BACKTEST-OPTIMIZED)
**COI PCR Thresholds**:
- Bullish Entry: > 1.2 (std), > 1.4 (Thu)
- Bearish Entry: < 0.8 (std), < 0.6 (Thu)
- Neutral Zone: 0.8-1.2 (std), 0.6-1.4 (Thu)

**Signal Weights** (Composite Momentum Index):
- w1 (PCR_slope): 0.4
- w2 (VWAP_gap): 0.3
- w3 (Delta_flow): 0.3

**Time-of-Day Weights**:
- Open (0-60′): 1.0x
- Midday (60-360′): 0.4x
- Close (last 60′): 1.3x

**Risk Parameters**:
- Risk per trade: 0.75% of capital
- Daily loss limit: 4.0% of capital
- Max position size: 4.0% per direction
- Stop-loss: 1.5x ATR or technical level

**Thresholds for Filters**:
- Volume confirmation: 20% increase in 7-strike volume
- European window: 12:30-13:00 IST
- Gamma lock: Post 13:30 IST on Thursdays
- Expiry thresholds: PCR > 2.5 or < 0.2 after 13:30 IST

### C. SIGNAL VALIDATION CRITERIA
A signal is considered valid when:
1. Generated during market hours (9:15 AM - 3:00 PM IST)
2. Not filtered out by any risk management rule
3. Has sufficient confluence validation (2+ layers)
4. Aligns with time-of-day structural bias
5. Confirmed by volume (if applicable)
6. Not in exclusion zones (lunch, expiry gamma lock)
7. Has reasonable risk-reward potential (>1:1)

### D. EXAMPLE SIGNAL OUTPUT
```
Timestamp: 14:35 | Day Regime: Standard | Index tracked: NIFTY
Index Spot: 22450.50 | ATM Strike: 22450 | Window Status: Aligned
Current COI PCR: 0.92 | Trend (last 30 mins): Falling
Absolute OI Walls: 22600 (Resistance) vs 22200 (Support)
Confluence Analysis:
Market Structure: Lower Highs / Lower Lows
Premium Swings: PE Breakout
Arrival COI Shift: Put Writing Spike at Support
Institutional Context: Short Build-up
Trading Bias: HIGH-CONVICTION BEARISH
Action: Enter short position (sell NIFTY 22450 PE) with target at 22200 and stop-loss at 22600
```

---

## CONCLUSION

This Unified Trading Strategy Document provides a comprehensive blueprint for building an institutional-grade trading system for Indian Index Derivatives. By integrating the strengths of multiple sophisticated approaches—COI PCR analysis, premium divergence detection, gamma exposure modeling, and quantitative feature engineering—the system aims to:

1. **Detect Institutional Flow**: Smart money positioning via OI changes and premium actions
2. **Require Confluence**: Multiple independent signals must align for high-conviction trades
3. **Adapt Dynamically**: Parameters adjust by market regime, time-of-day, and volatility
4. **Manage Risk Rigorously**: Multiple veto filters protect against false signals and losses
5. **Respect Market Structure**: Special handling for expiry days, lunch periods, and volatility regimes

The system is designed for:
- **Accuracy**: High-conviction signals through layered validation
- **Flexibility**: Adaptable to changing market conditions
- **Transparency**: Clear signal rationale and execution logic
- **Safety**: Risk-first approach with multiple protection layers
- **Practicality**: Implementable with available UPSTOX API and modern web technologies

Successful implementation requires disciplined adherence to the risk management protocols, continuous backtesting and validation, and respect for the time-tested principles of institutional order flow analysis.

**Next Steps**: Begin implementation with Phase 0 (foundation setup) and proceed systematically through the roadmap, validating each component before moving to the next phase.