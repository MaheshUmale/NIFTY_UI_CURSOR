import gzip
import io
import json
import threading
import time
from datetime import datetime
import pandas as pd
import requests
import websocket
import upstox_client
from upstox_client.rest import ApiException

# Active Access Token
access_token = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NkFGMzUiLCJqdGkiOiI2YTI4ZmQzNjAzZDM5YjRjZTQ2Yzk1N2IiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTtMTA3MTE1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzgxMTI4ODAwfQ.LwTW4Rg5raYFy8IChCI0bBS-HuQSEJbNyBTntAtF8OM'
OUTPUT_FILE = "upstox_market_feed.jsonl"

def get_upstox_instruments(symbols=["NIFTY", "BANKNIFTY"], spot_prices={"NIFTY": 0, "BANKNIFTY": 0}):
    # 1. Download and Load Instrument Master (NSE_FO for Futures and Options)
    url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
    response = requests.get(url)
    with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
        df = pd.read_json(f)

    full_mapping = {}

    for symbol in symbols:
        spot = spot_prices.get(symbol)
        
        # --- 1. Current Month Future ---
        fut_df = df[(df['name'] == symbol) & (df['instrument_type'] == 'FUT')].sort_values(by='expiry')
        if fut_df.empty:
            continue
        current_fut_key = fut_df.iloc[0]['instrument_key']

        # --- 2. Nearest Expiry Options ---
        opt_df = df[(df['name'] == symbol) & (df['instrument_type'].isin(['CE', 'PE']))].copy()
        opt_df['expiry'] = pd.to_datetime(opt_df['expiry'], origin='unix', unit='ms')
        nearest_expiry = opt_df['expiry'].min()
        near_opt_df = opt_df[opt_df['expiry'] == nearest_expiry]

        # --- 3. Identify the 7 Strikes (3 OTM, 1 ATM, 3 ITM) ---
        unique_strikes = sorted(near_opt_df['strike_price'].unique())
        atm_strike = min(unique_strikes, key=lambda x: abs(x - spot))
        atm_index = unique_strikes.index(atm_strike)
        
        start_idx = max(0, atm_index - 3)
        end_idx = min(len(unique_strikes), atm_index + 4)
        selected_strikes = unique_strikes[start_idx : end_idx]

        # --- 4. Build Result ---
        option_keys = []
        for strike in selected_strikes:
            ce_rows = near_opt_df[(near_opt_df['strike_price'] == strike) & (near_opt_df['instrument_type'] == 'CE')]
            pe_rows = near_opt_df[(near_opt_df['strike_price'] == strike) & (near_opt_df['instrument_type'] == 'PE')]
            
            if ce_rows.empty or pe_rows.empty:
                continue
                
            option_keys.append({
                "strike": strike,
                "ce": ce_rows['instrument_key'].values[0],
                "ce_trading_symbol" : ce_rows['trading_symbol'].values[0],
                "pe": pe_rows['instrument_key'].values[0],
                "pe_trading_symbol" : pe_rows['trading_symbol'].values[0]
            })

        full_mapping[symbol] = {
            "future": current_fut_key,
            "expiry": nearest_expiry.strftime('%Y-%m-%d'),
            "options": option_keys,
            "all_keys": [current_fut_key] + [opt['ce'] for opt in option_keys] + [opt['pe'] for opt in option_keys]
        }

    return full_mapping

def getNiftyAndBNFnOKeys():
    ALL_FNO = []
    configuration = upstox_client.Configuration()
    configuration.access_token = access_token
    apiInstance = upstox_client.MarketQuoteV3Api(upstox_client.ApiClient(configuration))
    
    try:
        # Pass exact keys split by commas
        response = apiInstance.get_ltp(instrument_key="NSE_INDEX|Nifty 50,NSE_INDEX|Nifty Bank")
        
        # Access with the exact requested string keys safely from data dictionary
        nifty_50_data = response.data.get('NSE_INDEX|Nifty 50')
        nifty_bank_data = response.data.get('NSE_INDEX|Nifty Bank')

        if not nifty_50_data or not nifty_bank_data:
            print("Failed to get LTP data for indices.")
            return []

        nifty_50_last_price = nifty_50_data.last_price    
        nifty_bank_last_price = nifty_bank_data.last_price  

        print(f"Nifty 50 last price: {nifty_50_last_price}")
        print(f"Nifty Bank last price: {nifty_bank_last_price}")
        
        current_spots = {
            "NIFTY": nifty_50_last_price,
            "BANKNIFTY": nifty_bank_last_price
        }

        data = get_upstox_instruments(["NIFTY", "BANKNIFTY"], current_spots)
        
        if "NIFTY" in data:
            ALL_FNO += data['NIFTY']['all_keys']
        if "BANKNIFTY" in data:
            ALL_FNO += data['BANKNIFTY']['all_keys']
            
        return ALL_FNO
    except ApiException as e:
        print("Exception when calling MarketQuoteV3Api->get_ltp: %s\n" % e)
        return []

# Fetch structural instrument keys
INSTRUMENT_KEYS = getNiftyAndBNFnOKeys()
print(f"Subscribing to {len(INSTRUMENT_KEYS)} instrument keys.")

# --- DYNAMIC AUTHORIZED URL FETCH ---
configuration = upstox_client.Configuration()
configuration.access_token = access_token
websocket_api = upstox_client.WebsocketApi(upstox_client.ApiClient(configuration))
auth_response = websocket_api.get_market_data_feed_authorize(api_version='2.0')
WS_URL = auth_response.data.authorized_redirect_uri  # Dynamic working wss url

def on_message(ws, message):
    try:
        # Note: Upstox WebSocket returns binary Protobuf data. 
        # If you are not seeing clear JSON, you will need to pass it through a Protobuf decoder.
        print("Received stream snapshot packet...")
        with open(OUTPUT_FILE, "a") as f:
            f.write(json.dumps({"raw_data": str(message), "local_timestamp": datetime.utcnow().isoformat()}) + "\n")
    except Exception as e:
        print(f"Error handling message: {e}")

def on_open(ws):
    print("WebSocket link established successfully.")
    
    # 10-second thread shutdown sequence
    def countdown():
        time.sleep(10)
        print("10 seconds reached. Closing WebSocket...")
        ws.close()

    threading.Thread(target=countdown, daemon=True).start()
    
    # Subscribe packet template
    subscription_message = {
        "guid": "market-data-stream",
        "method": "sub",
        "data": {
            "mode": "full", 
            "instrumentKeys": INSTRUMENT_KEYS
        }
    }
    ws.send(json.dumps(subscription_message))

def on_error(ws, error):
    print(f"WebSocket Error encountered: {error}")

# Initialize and lock onto feed
ws = websocket.WebSocketApp(WS_URL, on_open=on_open, on_message=on_message, on_error=on_error)
ws.run_forever()
