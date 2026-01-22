"""
Flask server for options screener API
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from screener import screen_options
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route("/")
def index():
    """Serve the HTML frontend"""
    return send_from_directory(".", "index.html")


@app.route("/api/scan", methods=["POST"])
def scan_options():
    """
    Scan options based on filter criteria.

    Expected JSON body:
    {
        "tickers": ["AAPL", "TSLA"],
        "max_price": 0.05,
        "contract_type": "call",
        "expiration_ranges": ["lt1m", "1-3m"],
        "otm_min": -5,
        "otm_max": 10
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        tickers = data.get("tickers", [])
        if isinstance(tickers, str):
            tickers = [t.strip() for t in tickers.split(",") if t.strip()]

        max_price = float(data.get("max_price", 0.05))
        contract_type = data.get("contract_type", "call").lower()
        expiration_ranges = data.get("expiration_ranges", ["1-3m"])
        otm_min = float(data.get("otm_min", -5))
        otm_max = float(data.get("otm_max", 10))

        # Validate contract type
        if contract_type not in ["call", "put"]:
            return jsonify({"error": "contract_type must be 'call' or 'put'"}), 400

        # Run the screener
        results = screen_options(
            tickers=tickers,
            max_price=max_price,
            contract_type=contract_type,
            expiration_ranges=expiration_ranges,
            otm_min=otm_min,
            otm_max=otm_max
        )

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Starting Options Screener server...")
    print("Open http://localhost:5000 in your browser")
    app.run(host="0.0.0.0", port=5000, debug=True)
