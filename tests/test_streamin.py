import upstox_client
import time
import sys as system

def on_message(message):
    print(message)


def main():
    configuration = upstox_client.Configuration()
    # Replace with your actual access token
    access_token = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI3NkFGMzUiLCJqdGkiOiI2YTI4ZTBkZjNiZDEwNzEyNTc3OGY2ZTciLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc4MTA2MzkwNCwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzgxMTI4ODAwfQ.5W8FdsUtArm-FA3MAyBqhu1zXx7ZKFH1xWZD5vttBnU'
    configuration.access_token = access_token

    streamer = upstox_client.MarketDataStreamerV3(
        upstox_client.ApiClient(configuration), ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"], "full")

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
