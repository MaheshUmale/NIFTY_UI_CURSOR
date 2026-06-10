# Backend to UI Interface Specification Document
**Version:** 1.0.0-PRO
**Author:** Day Trader Options Terminal Integration Team
**Focus:** High-Frequency CE/PE Scalping with Volatility and Gamma Exposure (GEX) Underlays

---

## 1. Overview & Network Architecture

The Day Trader Options Terminal is a high-performance web dashboard designed to run in a web browser container while connecting with an external, high-performance **Python Algorithmic Engine** running on a local or remote host.

### Network Flow Diagram
```
┌────────────────────────────────────────────────────────┐
│               WEB VIEWPORT CLIENT (REDUX)              │
│               Runs at: Local / Cloud Run               │
│                                                        │
│   ▲ [Active API Poller]       │ [Order Dispatch]       │
│   │ (HTTP GET JSON Feed)     ▼ (HTTP POST payload)     │
└───┼───────────────────────────┼────────────────────────┘
    │                           │
┌───┴───────────────────────────▼────────────────────────┐
│                PYTHON TRADING ENVIRONMENT  (Port 8000) │
│                Runs at: http://localhost:8000          │
└────────────────────────────────────────────────────────┘
```

The user interface supports three operational telemetry configurations:
1. **Simulation Mode**: Uses the internal low-latency multi-agent market generator.
2. **Replay Mode**: Restreams historical DuckDB high-resolution 1-minute delta ticks.
3. **External Python Feed Mode**: Connects directly to the Python application on port `8000` (or a customized URI) to ingest real-depth order books and feed raw trades to live broker wrappers.

---

## 2. Ingestion Interface: JSON Payload Schema

When the UI is in **External Mode**, it polls the Python API endpoint configured in the UI (default: `http://localhost:8000/api/quotes`) every 1,000 milliseconds to update candles, Option Chain matrices, PCR ratios, and Gamma profiles.

### GET Response Payload JSON Schema
```json
{
  "timestamp": "14:15:23",
  "spotPrice": 22452.80,
  "futuresPrice": 22510.45,
  "atmStrike": 22450,
  "coiPcr": 1.04,
  "windowStatus": "Aligned",
  "spotCandles": [
    { "time": "14:11", "open": 22450.2, "high": 22452.9, "low": 22449.1, "close": 22451.8 },
    { "time": "14:12", "open": 22451.8, "high": 22453.4, "low": 22451.2, "close": 22452.5 }
  ],
  "ceCandles": [
    { "time": "14:11", "open": 112.5, "high": 115.0, "low": 111.0, "close": 113.8 },
    { "time": "14:12", "open": 113.8, "high": 116.2, "low": 113.0, "close": 115.4 }
  ],
  "peCandles": [
    { "time": "14:11", "open": 98.4, "high": 100.1, "low": 95.8, "close": 96.5 },
    { "time": "14:12", "open": 96.5, "high": 98.0, "low": 94.2, "close": 95.1 }
  ],
  "strikes": [
    {
      "strike": 22355,
      "callOi": 1850020,
      "callOiChange": 450000,
      "callPremium": 162.40,
      "putOi": 540010,
      "putOiChange": -20000,
      "putPremium": 42.10,
      "gammaValue": -0.052
    },
    {
      "strike": 22400,
      "callOi": 2200500,
      "callOiChange": 720000,
      "callPremium": 128.95,
      "putOi": 1450200,
      "putOiChange": 310000,
      "putPremium": 61.20,
      "gammaValue": -0.125
    },
    {
      "strike": 22450,
      "callOi": 5400000,
      "callOiChange": 1400000,
      "callPremium": 92.10,
      "putOi": 5100000,
      "putOiChange": 1890000,
      "putPremium": 94.30,
      "gammaValue": 0.354
    },
    {
      "strike": 22500,
      "callOi": 6200200,
      "callOiChange": 2100000,
      "callPremium": 64.30,
      "putOi": 2800500,
      "putOiChange": 410000,
      "putPremium": 122.80,
      "gammaValue": -0.180
    }
  ]
}
```

---

## 3. Data Field Definitions & Ranges

### 3.1 Metadata & Index Telemetry
*   `timestamp` *(string)*: Real-time time label formatted as `HH:MM:SS` or `HH:MM` for high-precision event mapping.
*   `spotPrice` *(float)*: The current underlying cash price of the benchmark (e.g. NIFTY 50). Values lie typically in the `15000.00` to `26000.00` range.
*   `futuresPrice` *(float)*: Current derivative future contract valuation. Used to verify the basis premium (`Futures - Spot`).
*   `atmStrike` *(integer)*: Nearest ATM (At-The-Money) options strike incremented by `50` for Nifty (e.g. `22400`, `22450`, `22500`) or `100` for BankNifty.
*   `coiPcr` *(float)*: Cumulative Open Interest Put-Call Ratio calculated as `Σ(Put Open Interest) / Σ(Call Open Interest)`.
    *   `< 0.7`: Extreme Bearish sentiment (Overbought Calls).
    *   `1.0`: Neutrally balanced market.
    *   `> 1.3`: Highly Bullish sentiment (Overbought Puts / Put writing dominance).
*   `windowStatus` *(string)*: Alignment state between Spot trends and GEX profile. Expected values: `"Aligned"`, `"Misaligned"`, or `"Conflict"`.

### 3.2 Candlestick Time Series (`spotCandles`, `ceCandles`, `peCandles`)
Each array contains a sequence of minute-by-minute trading intervals with fields:
*   `time` *(string)*: Standard timestamp text (e.g. `"14:12"`).
*   `open` *(float)*: Tick open price.
*   `high` *(float)*: Maximum premium reached in interval.
*   `low` *(float)*: Minimum premium reached in interval.
*   `close` *(float)*: Terminal premium of interval.

### 3.3 Option Chain Strike Matrix (`strikes`)
Points centered around the ATM strike ($\pm 3$ levels) to populate the visual ladder:
*   `strike` *(integer)*: Absolute strike exercise price. Must be a multiple of `50` (Nifty) or `100` (BanknIFTY).
*   `callOi` / `putOi` *(integer)*: Total open derivative contracts active representing support and resistance barriers.
*   `callOiChange` / `putOiChange` *(integer)*: Intraday flow rate of capital writing options. Positive denotes contract additions; negative denotes short covering.
*   `callPremium` / `putPremium` *(float)*: Price multiplier per share of the option. Determines execution trade size.
*   `gammaValue` *(float)*: The local Options Net Gamma. Positive values reflect a stable "long customer gamma" cushion, while negative profiles spark violent, accelerated trend continuation.

---

## 4. Execution Interface: Order Dispatch API

When a trader triggers a scalp (either Ce/Pe, Instant Market Orders, or the automated algorithm), the UI fires a secure, non-blocking **JSON POST** to the Python app's matching order routing URL (default: `http://localhost:8000/api/order`).

### Request Headers
```http
Content-Type: application/json
Accept: application/json
```

### POST JSON Payload Structure
```json
{
  "orderId": "AUTO-RZXQ2",
  "instrument": "NIFTY",
  "side": "BUY",
  "optionType": "CE",
  "strike": 22450,
  "quantity": 150,
  "price": 92.10,
  "stopLoss": 82.90,
  "takeProfit": 110.50,
  "timestamp": "14:15:23",
  "isAutoAlgo": false
}
```

### Response Expected from Python Engine
```json
{
  "success": true,
  "brokerId": "ZEB-847250",
  "status": "FILLED",
  "executedPrice": 92.10,
  "message": "Market order dispatched to NSE gateway successfully."
}
```

---

## 5. Quick Verification with Python mock server

To speed up development and instantly verify integration locally, you can spin up this minimal, zero-dependency Python loop on Port 8000:

```python
import http.server
import json
import random

class IngestionHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Allow preflight CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # Simulating active dynamic Indian options quotes
        payload = {
            "timestamp": "14:15:00",
            "spotPrice": 22450.0 + random.uniform(-10, 10),
            "futuresPrice": 22502.0,
            "atmStrike": 22450,
            "coiPcr": 1.15,
            "windowStatus": "Aligned",
            "spotCandles": [{"time": "14:15", "open": 22450, "high": 22456, "low": 22448, "close": 22452}],
            "ceCandles": [{"time": "14:15", "open": 90, "high": 95, "low": 89, "close": 92}],
            "peCandles": [{"time": "14:15", "open": 95, "high": 98, "low": 91, "close": 94}],
            "strikes": [
                {"strike": 22400, "callOi": 3000000, "callOiChange": 500000, "callPremium": 128.0, "putOi": 4500000, "putOiChange": 900000, "putPremium": 61.0, "gammaValue": 0.12},
                {"strike": 22450, "callOi": 5400000, "callOiChange": 1400000, "callPremium": 92.0, "putOi": 5100000, "putOiChange": 1890000, "putPremium": 94.0, "gammaValue": 0.35},
                {"strike": 22500, "callOi": 6200000, "callOiChange": 2100000, "callPremium": 64.0, "putOi": 2800000, "putOiChange": 410000, "putPremium": 122.0, "gammaValue": -0.18}
            ]
        }
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        order_payload = json.loads(post_data.decode('utf-8'))

        print(f"[NSE Broker] Dispatched Order Event: {order_payload}")

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response = {
            "success": True,
            "brokerId": f"NSE-ID-{random.randint(100000, 999999)}",
            "status": "FILLED",
            "executedPrice": order_payload.get("price", 92.0),
            "message": "Dispatched cleanly by Mock Python Engine"
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', 8000), IngestionHandler)
    print("Zero-Dependency Python Algorithmic Server running on PORT 8000...")
    server.serve_forever()
```
