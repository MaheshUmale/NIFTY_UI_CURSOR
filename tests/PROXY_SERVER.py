import io
import gzip
import json
import redis
import uvicorn
import threading
import pandas as pd
import requests
import upstox_client
from fastapi import FastAPI, HTTPException, Query, Request
from datetime import datetime

# --- CONFIGURATION ---
ACCESS_TOKEN = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NkFGMzUiLCJqdGkiOiI2YTI4ZmQzNjAzZDM5YjRjZTQ2Yzk1N2IiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTtMTA3MTE1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzgxMTI4ODAwfQ.LwTW4Rg5raYFy8IChCI0bBS-HuQSEJbNyBTntAtF8OM'
UPSTOX_BASE_URL = "https://upstox.com"

# Redis Config
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
CHANNEL_INDEX = "upstox_data_index"
CHANNEL_FO = "upstox_data_fo"

# System Control Config
RATE_LIMIT_PER_MINUTE = 60  # Allow 60 requests per minute per IP address
KEY_TO_SYMBOL_MAP = {}
METRICS = {"total_requests": 0, "cache_hits": 0, "cache_misses": 0, "rate_limited": 0}

app = FastAPI(title="Production-Grade Upstox Proxy Gateway & Broadcaster")


# --- 1. LOCAL RATE LIMITER MIDDLEWARE ---
@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    """Enforces strict client-side request limits to keep Upstox APIs stable."""
    if request.url.path == "/dashboard/status":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown_ip"
    current_minute = datetime.utcnow().strftime("%M")
    rate_key = f"ratelimit:{client_ip}:{current_minute}"

    try:
        current_count = redis_client.incr(rate_key)
        if current_count == 1:
            redis_client.expire(rate_key, 60)

        if current_count > RATE_LIMIT_PER_MINUTE:
            METRICS["rate_limited"] += 1
            raise HTTPException(status_code=429, detail="Local rate limit exceeded. Max 60 req/min.")
    except redis.RedisError:
        pass  

    METRICS["total_requests"] += 1
    response = await call_next(request)
    return response


# --- 2. INSTRUMENT INITIALIZATION & SELECTION ---
def load_instrument_mapping():
    global KEY_TO_SYMBOL_MAP
    print("Downloading instrument master file...")
    try:
        url = "https://upstox.com"
        response = requests.get(url, timeout=15)
        with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
            df = pd.read_json(f)
        KEY_TO_SYMBOL_MAP = dict(zip(df['instrument_key'], df['trading_symbol']))
        KEY_TO_SYMBOL_MAP["NSE_INDEX|Nifty 50"] = "NIFTY_50_INDEX"
        KEY_TO_SYMBOL_MAP["NSE_INDEX|Nifty Bank"] = "BANKNIFTY_INDEX"
    except Exception as e:
        print(f"Failed loading master files, utilizing empty map structure: {e}")


def get_subscription_keys():
    configuration = upstox_client.Configuration()
    configuration.access_token = ACCESS_TOKEN
    api_instance = upstox_client.MarketQuoteV3Api(upstox_client.ApiClient(configuration))
    default_keys = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"]
    try:
        response = api_instance.get_ltp(instrument_key="NSE_INDEX|Nifty 50,NSE_INDEX|Nifty Bank")
        nifty_spot = response.data.get('NSE_INDEX|Nifty 50').last_price
        banknifty_spot = response.data.get('NSE_INDEX|Nifty Bank').last_price
        
        url = "https://upstox.com"
        res = requests.get(url, timeout=15)
        with gzip.GzipFile(fileobj=io.BytesIO(res.content)) as f:
            df = pd.read_json(f)

        all_keys = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"]
        for symbol, spot in [("NIFTY", nifty_spot), ("BANKNIFTY", banknifty_spot)]:
            fut_df = df[(df['name'] == symbol) & (df['instrument_type'] == 'FUT')].sort_values(by='expiry')
            if not fut_df.empty:
                all_keys.append(fut_df.iloc[0]['instrument_key'])
                
            opt_df = df[(df['name'] == symbol) & (df['instrument_type'].isin(['CE', 'PE']))].copy()
            opt_df['expiry'] = pd.to_datetime(opt_df['expiry'], origin='unix', unit='ms')
            near_opt_df = opt_df[opt_df['expiry'] == opt_df['expiry'].min()]
            
            unique_strikes = sorted(near_opt_df['strike_price'].unique())
            atm_strike = min(unique_strikes, key=lambda x: abs(x - spot))
            atm_idx = unique_strikes.index(atm_strike)
            
            selected_strikes = unique_strikes[max(0, atm_idx - 3) : min(len(unique_strikes), atm_idx + 4)]
            for strike in selected_strikes:
                all_keys.extend(near_opt_df[near_opt_df['strike_price'] == strike]['instrument_key'].tolist())
        return list(set(all_keys))
    except Exception:
        return default_keys


# --- 3. STREAMING & LOCAL REDIS BROADCASTING ---
def on_message(message):
    try:
        data = json.loads(message) if isinstance(message, str) else message
        feeds = data.get("feeds", {}) if isinstance(data, dict) else {}
        for key, feed_value in feeds.items():
            trading_symbol = KEY_TO_SYMBOL_MAP.get(key, "UNKNOWN_INSTRUMENT")
            payload = {
                "instrument_key": key,
                "trading_symbol": trading_symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "feed_data": feed_value
            }
            payload_str = json.dumps(payload)
            if key.startswith("NSE_INDEX"):
                redis_client.publish(CHANNEL_INDEX, payload_str)
            elif key.startswith("NSE_FO"):
                redis_client.publish(CHANNEL_FO, payload_str)
    except Exception:
        pass


def run_websocket_broadcast():
    instrument_keys = get_subscription_keys()
    configuration = upstox_client.Configuration()
    configuration.access_token = ACCESS_TOKEN
    streamer = upstox_client.MarketDataStreamerV3(
        upstox_client.ApiClient(configuration), instrument_keys, "full"
    )
    streamer.on("message", on_message)
    streamer.connect()


# --- 4. EXPLICIT CACHED ROUTES ---
@app.get("/api/v2/market-quote/intra-day-candle/{instrument_key}/{interval}")
def proxy_intraday_candles(instrument_key: str, interval: str):
    cache_key = f"cache:intraday:{instrument_key}:{interval}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            METRICS["cache_hits"] += 1
            return json.loads(cached)
    except redis.RedisError:
        pass

    METRICS["cache_misses"] += 1
    url = f"{UPSTOX_BASE_URL}/market-quote/intra-day-candle/{instrument_key}/{interval}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
        
    res_data = response.json()
    ttl = 60
    if "3minute" in interval: ttl = 180
    elif "5minute" in interval: ttl = 300
    try:
        redis_client.setex(cache_key, ttl, json.dumps(res_data))
    except redis.RedisError:
        pass
    return res_data


@app.get("/api/v2/option/chain")
def proxy_option_chain(instrument_key: str, expiry_date: str):
    cache_key = f"cache:optionchain:{instrument_key}:{expiry_date}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            METRICS["cache_hits"] += 1
            return json.loads(cached)
    except redis.RedisError:
        pass

    METRICS["cache_misses"] += 1
    url = f"{UPSTOX_BASE_URL}/option/chain"
    params = {"instrument_key": instrument_key, "expiry_date": expiry_date}
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
    response = requests.get(url, params=params, headers=headers, timeout=10)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
        
    res_data = response.json()
    try:
        redis_client.setex(cache_key, 5, json.dumps(res_data))
    except redis.RedisError:
        pass
    return res_data


# --- 5. SYSTEM HEALTH MONITORING DASHBOARD ---
@app.get("/dashboard/status")
def get_proxy_health_and_metrics():
    redis_alive = False
    try:
        redis_alive = redis_client.ping()
    except Exception:
        pass

    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "redis_connected": redis_alive,
        "instrument_map_size": len(KEY_TO_SYMBOL_MAP),
        "performance_metrics": METRICS
    }


# --- 6. OPTIMIZED MULTI-METHOD CATCH-ALL PROXY ROUTE (GET, POST, PUT, DELETE) ---
@app.api_route("/api/v2/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def automated_universal_proxy(rest_of_path: str, request: Request):
    url = f"{UPSTOX_BASE_URL}/{rest_of_path}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Accept": "application/json"}
    
    body_bytes = await request.body()
    body_data = body_bytes if body_bytes else None

    if "content-type" in request.headers:
        headers["Content-Type"] = request.headers["content-type"]

    try:
        response = requests.request(
            method=request.method,
            url=url,
            params=dict(request.query_params),
            data=body_data,
            headers=headers,
            timeout=12
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=504, detail=f"Upstox service connectivity timeout: {e}")

    # Corrected success check status validation array
    if response.status_code not in [200, 204]:
        raise HTTPException(status_code=response.status_code, detail=response.text)
        
    if response.status_code == 204 or not response.text:
        return None

    return response.json()


# --- 7. INITIALIZATION SEQUENCE ---
if __name__ == "__main__":
    # 1. Map master items into memory
    load_instrument_mapping()
    
    # 2. Run WebSocket logic inside async-safe isolated daemon thread
    broadcast_thread = threading.Thread(target=run_websocket_broadcast, daemon=True)
    broadcast_thread.start()
    print("Background Upstox WebSocket Router is active.")
    # 3. Fire up Local Web server frameworkprint("Launching API Proxy Gateway Layer on port 9000...")
    uvicorn.run(app, host="localhost", port=9000)