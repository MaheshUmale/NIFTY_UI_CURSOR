# Backend-to-UI Option Ingestion & API Integration Guide
**Developer Reference Specification • Live Quant Options Pipeline**

---

## 1. Integration Paradigm Overview

This React Option Terminal behaves as a visual quantitative cockpit. While it includes an algorithmic local market simulator (emulator mode) for testing, it is built to consume production-grade, real-time index matrices directly from an external quantitative trading script—typically a **Python server (such as FastAPI or Flask)** running on **Port 8000** or any user-defined network location.

When the application's ingestion source is toggled, it swaps from standard local simulations to an active network polling worker that polls your python webserver's endpoint at a configurable loop interval (e.g., 1s, 2s, 5s).

---

## 2. Dynamic Connection Endpoint Configuration

* **Default Configured Ingestion Endpoint:** `http://localhost:8000/api/quotes`
* **Custom URL Mapping:** The endpoint URL is dynamically editable directly via the **Python API Integration Tab** UI control in the React Terminal.
* **Network Handshake Protocol:** The external Python application must support standard HTTP **GET** operations on that route and must correctly permit Cross-Origin Resource Sharing (CORS) to prevent browser sandbox blockage.

---

## 3. JSON Payload Contract

The React application expects a single response payload matching the exact JSON dictionary format specified below. It requires a 7-strike option ladder centered on the current Spot Index level.

### Structured JSON Response Template
```json
{
  "spotPrice": 22485.50,
  "instrument": "NIFTY",
  "strikeChain": [
    {
      "strike": 22300,
      "callOI": 12000,
      "callCOI": 1200,
      "callVolume": 15000,
      "callPremium": 210.50,
      "putOI": 45000,
      "putCOI": -500,
      "putVolume": 5000,
      "putPremium": 12.50
    },
    {
      "strike": 22350,
      "callOI": 18000,
      "callCOI": 2300,
      "callVolume": 21000,
      "callPremium": 165.20,
      "putOI": 39000,
      "putCOI": 4200,
      "putVolume": 8500,
      "putPremium": 18.10
    },
    {
      "strike": 22400,
      "callOI": 28000,
      "callCOI": 4500,
      "callVolume": 35000,
      "callPremium": 125.80,
      "putOI": 31000,
      "putCOI": 6800,
      "putVolume": 14000,
      "putPremium": 28.50
    },
    {
      "strike": 22450,
      "callOI": 45000,
      "callCOI": 11000,
      "callVolume": 65000,
      "callPremium": 92.40,
      "putOI": 24000,
      "putCOI": 9500,
      "putVolume": 25000,
      "putPremium": 45.00
    },
    {
      "strike": 22500,
      "callOI": 68000,
      "callCOI": 18500,
      "callVolume": 98000,
      "callPremium": 64.10,
      "putOI": 15000,
      "putCOI": 4200,
      "putVolume": 31050,
      "putPremium": 66.80
    },
    {
      "strike": 22550,
      "callOI": 52000,
      "callCOI": 14000,
      "callVolume": 71000,
      "callPremium": 42.50,
      "putOI": 8000,
      "putCOI": 1200,
      "putVolume": 12000,
      "putPremium": 95.20
    },
    {
      "strike": 22600,
      "callOI": 41000,
      "callCOI": 8900,
      "callVolume": 45000,
      "callPremium": 27.00,
      "putOI": 4000,
      "putCOI": 100,
      "putVolume": 4500,
      "putPremium": 129.50
    }
  ]
}
```

---

## 4. In Depth Field-Level Diagnostics

Each parameter and list object key serves a direct mathematical or visual purpose in the option terminal view charts. Below is the detailed database-style field reference guide:

### Root Level Attributes

| Root Key Name | Data Type | Constraint Requirements | Purpose & UI Utilization |
| :--- | :--- | :--- | :--- |
| **`spotPrice`** | `Float` / `Double` | Must be strictly positive `> 0`. | Sets the vertical live spot cursor in the Option Chain visual panel, shifts order-execution strike metrics, and anchors the Black-Scholes mathematical drift curves. |
| **`instrument`** | `String` | Allowed static values: `"NIFTY"` \| `"BANKNIFTY"`. | Used to shift the client visual headers and calibrate tick spacing filters (50 for NIFTY, 100 for BANKNIFTY). |
| **`strikeChain`** | `List[Dict]` | Must present exactly **7 strikes** representing the ATM level, 3 strikes below, and 3 strikes above. | Generates the core vertical order data grid. Allows interactive, physical button tracking to send one-click buy orders. |

### Strike Chain Child Object Keys (`strikeChain[*]`)

Each strike node represents standard exchange listing contracts including call writing and put writing metrics. Ensure all fields are numbers.

| Field Key Name | Data Type | Unit Representation | Analytical / Visual Role |
| :--- | :--- | :--- | :--- |
| **`strike`** | `Integer` / `Float` | Absolute value (e.g., `22400`) | Serves as the primary unique key for the option chain row grid. Determines the strike sequence ordering from lowest to highest. |
| **`callOI`** | `Integer` | Lot size or contract count (e.g., `68000`) | Call Open Interest length. Determines the horizontal physical length of the Call OI side of the bar chart and drives the Net GEX accumulation profile. |
| **`putOI`** | `Integer` | Lot size or contract count (e.g., `45000`) | Put Open Interest length. Drives the horizontal Put OI bar size and tracks major market floors. |
| **`callCOI`** | `Integer` | Contracts Net Change (can be negative) | Change in Call Open Interest. Negative values denote call writers covering/unwinding their positions (bullish momentum indicator). |
| **`putCOI`** | `Integer` | Contracts Net Change (can be negative) | Change in Put Open Interest. Negative values denote put writers covering/unwinding their positions (bearish momentum indicator). |
| **`callVolume`** | `Integer` | Total daily contract count (e.g., `25000`) | Intraday call trading volume. Feeds our PCR volume indicators. |
| **`putVolume`** | `Integer` | Total daily contract count (e.g., `18500`) | Intraday put trading volume. Used to dynamically recalculate aggregate institutional trade action. |
| **`callPremium`** | `Float` | Index Base Points (e.g., `125.80`) | The Last Traded Price (LTP) of the Call Option. Used when executing one-click buy trades to estimate position entries and stop-losses. |
| **`putPremium`** | `Float` | Index Base Points (e.g., `28.50`) | The Last Traded Price (LTP) of the Put Option. Used when executing one-click buy trades to calculate position entries. |

---

## 5. Automated Calculations Driven by Ingested Fields

When you feed clean data via the backend specification API to this terminal, the client-side system automatically hooks your variables into advanced derivative models:

1. **Option PCR (Put-Call Ratio):**
   $$\text{PCR} = \frac{\sum \text{putOI}}{\sum \text{callOI}}$$
2. **Net Gamma Exposure (GEX Profile):**
   The UI evaluates the analytical option gamma for each strike, projecting index price units per 1% move of the spot index:
   $$\text{Net GEX} = (\text{Call Gamma} \times \text{CallOI} \times 100) - (\text{Put Gamma} \times \text{PutOI} \times 100)$$
3. **Volatility Trigger Flip Level:**
   The UI automatically runs a continuous numerical lookup scan to detect the exact price coordinate where $\text{Net GEX}$ flips from negative (dominated by put options) to positive (dominated by call options), rendering the pink **VOL TRIGGER FLIP ZONE** indicator on screen.

---

## 6. CORS Configuration Requirement & Python Boilerplate

Because your browser runs the React workspace within a secure sandboxed environment, your python script **must** bypass Cross-Origin Resource Sharing (CORS) limits. Make sure to allow headers `*` or include standard client credentials.

Here is the compliant FastAPI python implementation:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random

app = FastAPI(title="Quant Options Pipeline Server")

# CRITICAL CORS: Allow cross-origin AJAX fetches from AI Studio UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows browser iframe connections to query successfully
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/quotes")
def get_custom_option_quotes():
    # Simulate realistic live feed with random walk
    live_spot = 22485.50 + random.uniform(-10.0, 10.0)
    atm_strike = round(live_spot / 50) * 50

    # Pre-configure 7 strikes centering surrounding the ATM strike
    strikes = [atm_strike - 150, atm_strike - 100, atm_strike - 50, atm_strike, atm_strike + 50, atm_strike + 100, atm_strike + 150]

    options_chain = []
    for s in strikes:
        distance = live_spot - s
        options_chain.append({
            "strike": s,
            "callOI": int(52000 + random.randint(-5000, 15000) if s >= atm_strike else 18000),
            "callCOI": int(random.randint(2000, 10000)),
            "callVolume": int(35000 + random.randint(0, 90000)),
            "callPremium": round(max(5.0, 110.0 + (distance * 0.7) + random.uniform(-2.0, 2.0)), 2),
            "putOI": int(68000 + random.randint(-3000, 22000) if s <= atm_strike else 9500),
            "putCOI": int(random.randint(3000, 12000)),
            "putVolume": int(28000 + random.randint(0, 80000)),
            "putPremium": round(max(5.0, 95.0 - (distance * 0.6) + random.uniform(-2.0, 2.0)), 2)
        })

    return {
        "spotPrice": round(live_spot, 2),
        "instrument": "NIFTY",
        "strikeChain": options_chain
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 7. Dynamic Order Actions & Outgoing Trade Callbacks (Buy/Sell APIs)

When you interact with the option terminal using **One-Click Scalper Buttons**, **Keyboard Hotkeys**, or **Option Chain Hover Core (B)/(S) buttons**, the terminal executes the order client-side to track simulated P&L.

Crucially, **it also posts immediate outgoing transaction messages** to your Python backend to close the quantitative workflow loop. This enables your script to place real trades at your broker (e.g., Zerodha, AngelOne, Fyers) or manage portfolio hedge balances in real-time.

---

### A. Order Execution Hook (`POST /api/order`)

Whenever an option contract is bought (Long) or written/shorted (Short), the terminal triggers an asynchronous HTTP `POST` to:
`http://localhost:8000/api/order`

#### Payload Schema Example
```json
{
  "orderId": "A7Y6X2",
  "side": "BUY",
  "type": "CE",
  "strike": 22450,
  "quantity": 100,
  "entryPrice": 92.4,
  "timestamp": "13:42:04",
  "instrument": "NIFTY"
}
```

* **`side`**: `"BUY"` (indicates long debit entry) or `"SELL"` (indicates option writing / short credit entry).
* **`type`**: `"CE"` (Call Option) or `"PE"` (Put Option).
* **`strike`**: Selected numerical option strike price.
* **`quantity`**: The contracts lot size multiplier selected in sidebar.
* **`entryPrice`**: The matching option premium at execution moment.

---

### B. Scalp Exit Hook (`POST /api/order/exit`)

When a position is closed manually in the sidebar, or automatically whenever a trailing Stop-Loss (SL) or Take-Profit (TP) target is breached, the UI pushes an exit signal to:
`http://localhost:8000/api/order/exit`

#### Payload Schema Example
```json
{
  "orderId": "A7Y6X2",
  "closingPrice": 115.5,
  "pnl": 2310.0,
  "timestamp": "13:44:19"
}
```

* **`orderId`**: Tracks the original matching `orderId` value received on trade entry.
* **`closingPrice`**: Option premium at closure moment.
* **`pnl`**: Rupee (INR) P&L realized matching long/short sides.

---

### C. Unified Python API Endpoint Framework

Below is the complete, production-ready python template incorporating CORS headers that supports **both** live price-feed streaming and inbound order logs tracking:

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random

app = FastAPI(title="Quant Options Pipeline Server")

# CRITICAL CORS: Allow cross-origin AJAX fetches from AI Studio UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows browser iframe connections to query successfully
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Ingestion Pipeline endpoint (GET)
@app.get("/api/quotes")
def get_custom_option_quotes():
    live_spot = 22485.50 + random.uniform(-10.0, 10.0)
    atm_strike = round(live_spot / 50) * 50
    strikes = [atm_strike - 150, atm_strike - 100, atm_strike - 50, atm_strike, atm_strike + 50, atm_strike + 100, atm_strike + 150]

    options_chain = []
    for s in strikes:
        distance = live_spot - s
        options_chain.append({
            "strike": s,
            "callOI": int(52000 + random.randint(-5000, 15000) if s >= atm_strike else 18000),
            "callCOI": int(random.randint(2000, 10000)),
            "callVolume": int(35000 + random.randint(0, 90000)),
            "callPremium": round(max(5.0, 110.0 + (distance * 0.7) + random.uniform(-2.0, 2.0)), 2),
            "putOI": int(68000 + random.randint(-3000, 22000) if s <= atm_strike else 9500),
            "putCOI": int(random.randint(3000, 12000)),
            "putVolume": int(28000 + random.randint(0, 80000)),
            "putPremium": round(max(5.0, 95.0 - (distance * 0.6) + random.uniform(-2.0, 2.0)), 2)
        })

    return {
        "spotPrice": round(live_spot, 2),
        "instrument": "NIFTY",
        "strikeChain": options_chain
    }

# 2. Receive inbound order triggers (POST)
@app.post("/api/order")
async def receive_terminal_order(request: Request):
    payload = await request.json()
    print(f"\n[QUANT ALGO] Inbound Order Triggered:")
    print(f"ID: {payload.get('orderId')} | {payload.get('side')} {payload.get('instrument')} {payload.get('strike')} {payload.get('type')}")
    print(f"Qty: {payload.get('quantity')} | Premium Entry Price: ₹{payload.get('entryPrice')}")

    # Place actual orders at Zerodha/AngelOne here!
    return {"status": "SUCCESS", "orderId": payload.get("orderId")}

# 3. Receive position exits (POST)
@app.post("/api/order/exit")
async def receive_terminal_exit(request: Request):
    payload = await request.json()
    print(f"\n[QUANT ALGO] Scalp Position exited:")
    print(f"Original ID: {payload.get('orderId')} | Closing Premium: ₹{payload.get('closingPrice')} | Realized P&L: ₹{payload.get('pnl')}")

    # Cover short or Sell long option at standard broker here!
    return {"status": "SUCCESS", "closedOrderId": payload.get("orderId")}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```
