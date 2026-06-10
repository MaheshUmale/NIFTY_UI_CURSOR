# Unified Framework: Volume-Driven Market Structure

This document defines the core formulas and logical interpretations for the trading indicator suite. This is designed for use by a coding/trading agent to parse market data and identify trade opportunities based on participation (raiding party) and structural resistance (the "Wall").

---

## 1. Volume Intensity & Conviction
### Formulas
* **Volume Percent (Relative Volume):**
  $$V_{pct} = \frac{Volume}{SMA(Volume, 20)}$$
* **Bubble Size (Volume Spike):**
  $$BubbleSize = \max\left( \text{round}\left(\frac{V}{avg(SMA(V, P), SMA(V, 10))}\right), \dots \right)$$
  *(where $P$ is the input period)*

### Interpretation
* **$V_{pct} \geq 3.0$:** Aggressive participation. High conviction.
* **$0.8 < V_{pct} < 1.2$:** Low conviction ("Thin Air"). Trade with caution.
* **Bubble Size:** Quantifies the magnitude of the volume spike relative to long-term (100) and short-term (10) averages.

---

## 2. Dynamic Structural Levels
### Formulas
* **Net Force ($netF$):**
  $$U_F = V \times sc \times (close > VWAP ? 1.5 : 1.0) \times bodyPC$$
  $$D_F = V \times sc \times (close < VWAP ? 1.5 : 1.0) \times bodyPC$$
  $$netF = SMA(U_F, L) - SMA(D_F, L)$$
* **Dynamic Pivot Point:**
  $$Pivot = SMA(BasePrice, L) + (NormalizedForce \times Close \times VolatilityScore)$$

### Interpretation
* **Positive $netF$:** Bullish dominance.
* **Negative $netF$:** Bearish dominance.
* **Pivot Direction:** Rising pivot lines indicate expanding structural support/resistance. Falling pivot lines indicate structural decay.

---

## 3. Volatility & Trend Logic (AVT)
### Formulas
* **Baseline (EVWMA):**
  $$Baseline = \frac{\sum (Price \times Volume)}{\sum Volume}$$
* **Volatility (Spread):**
  $$Spread = RMA(TrueRange, Len)$$
* **Bands:**
  $$Band = Baseline \pm (Spread \times Multiplier)$$

### Interpretation
* **Trend Lock:** Trend flips only on a close outside the opposite band. This filters out "wobble" (noise).
* **Flip Signal:** The bar where price crosses the band is the execution trigger.
* **"The Wall":** High-volume historical levels (Bubble Lines) acting as barriers near current price.

---

## 4. Operational Strategy
* **Absorption:** Price approaches a `Bubble Line` or `Dynamic Pivot` and stalls (volume decreases).
* **Aggression:** Volume spike ($V_{pct} \geq 2.0$) coinciding with an `Active Ray` creation.
* **Void Analysis:** High price movement with $V_{pct} < 0.8$ represents a low-conviction environment. **Avoid.**

---

## Data Integration Requirements
* **Input Data:** Upstox `instrument_key` (for real-time streaming).
* **Rolling Window:** Use a buffer to store the last $N$ periods for SMA/RMA calculations.
* **MTF Sync:** Ensure `request.security` fetches data from HTF (Higher Timeframe) to validate S/R DOTs.
