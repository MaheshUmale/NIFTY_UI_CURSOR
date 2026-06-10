import upstox_client
import time
import sys as system

def on_message(message):
    print(message)

instrument_keys = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"]
instrument_keys = ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank",'NSE_FO|62329', 'NSE_FO|50568', 'NSE_FO|50570', 'NSE_FO|50572', 'NSE_FO|50574', 'NSE_FO|50576', 'NSE_FO|50585', 'NSE_FO|50591', 'NSE_FO|50569', 'NSE_FO|50571', 'NSE_FO|50573', 'NSE_FO|50575', 'NSE_FO|50577', 'NSE_FO|50586', 'NSE_FO|50592', 'NSE_FO|62326', 'NSE_FO|75604', 'NSE_FO|75606', 'NSE_FO|75608', 'NSE_FO|57721', 'NSE_FO|75610', 'NSE_FO|75612', 'NSE_FO|75614', 'NSE_FO|75605', 'NSE_FO|75607', 'NSE_FO|75609', 'NSE_FO|57722', 'NSE_FO|75611', 'NSE_FO|75613', 'NSE_FO|75615']

def main():
    configuration = upstox_client.Configuration()
    # Replace with your actual access token
    access_token = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NkFGMzUiLCJqdGkiOiI2YTI4ZTBkZjNiZDEwNzEyNTc3OGY2ZTciLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc4MTA2MzkwNCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzgxMTI4ODAwfQ.5W8FdsUtArm-FA3MAyBqhu1zXx7ZKFH1xWZD5vttBnU'
    access_token = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NkFGMzUiLCJqdGkiOiI2YTI4ZmQzNjAzZDM5YjRjZTQ2Yzk1N2IiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc4MTA3MTE1OCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzgxMTI4ODAwfQ.LwTW4Rg5raYFy8IChCI0bBS-HuQSEJbNyBTntAtF8OM'  # Use the provided access token
    configuration.access_token = access_token

    streamer = upstox_client.MarketDataStreamerV3(
        upstox_client.ApiClient(configuration), instrument_keys, "full")

    streamer.on("message", on_message)
    streamer.connect()
    
    return streamer  # Return the streamer object to control its lifecycle


if __name__ == "__main__":
    streamer = None
    try:
        streamer = main()
        time.sleep(10)  # Stream data for 10 seconds
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        if streamer:
            print("Disconnecting market data streamer safely...")
            try:
                streamer.disconnect()  # Gracefully shuts down background WebSocket threads
            except Exception as cleanup_error:
                print(f"Error during disconnect: {cleanup_error}")
        
        print("Exiting application.")
        system.exit(0)
