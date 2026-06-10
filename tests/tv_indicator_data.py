from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

@app.route('/stream', methods=['POST'])
def receive_stream():
    # 1. Check if data arrived via standard JSON fetch
    data = request.json
    
    # 2. If not, parse it from the unblockable HTML form payload
    if not data and 'payload' in request.form:
        try:
            data = json.loads(request.form['payload'])
        except Exception:
            pass

    if data:
        print(f"📡 Streamed Data Received: {data}")
        
        # Save the data directly into a local file
        with open("tradingview_stream.jsonl", "a") as f:
            f.write(json.dumps(data) + "\n")
            
        return jsonify({"status": "success"}), 200
        
    return jsonify({"status": "no data"}), 400

if __name__ == '__main__':
    print("Python Server running on http://localhost:5000...")
    app.run(port=5000)
