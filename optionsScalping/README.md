# Options Screener

A tool to scan options contracts across multiple tickers and filter by price, expiration, and how far out-of-the-money they are.

## Features

- Scan multiple tickers at once
- Filter by last trade price (e.g., options under $0.05)
- Filter by expiration timeframe (multi-select)
- Filter by OTM percentage range
- Select calls or puts
- Results sorted by price (cheapest first)

## Requirements

- Python 3.8+
- Polygon.io API key (already configured)

## Installation

```bash
cd optionsScalping
pip install -r requirements.txt
```

This installs:
- `requests` - HTTP client for API calls
- `flask` - Web server
- `flask-cors` - Cross-origin support
- `pytest` - For running tests (optional)

## Running the Screener

### Start the Server

```bash
cd optionsScalping
python server.py
```

You should see:
```
Starting Options Screener server...
Open http://localhost:5000 in your browser
 * Running on http://127.0.0.1:5000
```

### Open the Web Interface

Open your browser and go to: **http://localhost:5000**

### Using the Screener

1. **Enter Tickers** - Comma-separated list (e.g., `AAPL, TSLA, NVDA, AMD`)

2. **Set Max Price** - Maximum last trade price in dollars
   - `0.05` = options under 5 cents
   - `0.10` = options under 10 cents

3. **Select Contract Type** - Call or Put

4. **Select Expiration Ranges** - Check one or more:
   - `< 1 month` (0-30 days)
   - `1-3 months` (31-90 days)
   - `3-5 months` (91-150 days)
   - `5-8 months` (151-240 days)
   - `8-12 months` (241-365 days)

5. **Set OTM Range** - How far out-of-the-money (percentage)
   - For **calls**: positive % means strike is ABOVE current price
   - For **puts**: positive % means strike is BELOW current price
   - Example: `0%` to `10%` finds options 0-10% out of the money

6. **Click "Scan Options"** - Results appear in a table below

### Results Table Columns

| Column | Description |
|--------|-------------|
| Ticker | Underlying stock ticker |
| Option | Full option ticker symbol |
| Type | call or put |
| Strike | Strike price |
| Expiration | Expiration date |
| Days | Days until expiration |
| Bid | Current bid price |
| Ask | Current ask price |
| Last Price | Last trade price |
| OTM % | How far out of the money (positive = OTM) |
| Stock Price | Current underlying stock price |
| Data Age | How long ago the data was updated |

### Stop the Server

Press `Ctrl+C` in the terminal where the server is running.

## Running Tests

### Install pytest (if not already installed)

```bash
pip install pytest
```

### Run All Tests

```bash
cd optionsScalping
python -m pytest test_screener.py -v
```

### Expected Output

```
============================= test session starts =============================
collected 26 items

test_screener.py::TestCalculateOtmPercent::test_call_otm_positive PASSED
test_screener.py::TestCalculateOtmPercent::test_call_itm_negative PASSED
test_screener.py::TestCalculateOtmPercent::test_call_atm PASSED
...
============================= 26 passed in 0.07s ==============================
```

### Run Specific Test Class

```bash
# Only OTM calculation tests
python -m pytest test_screener.py::TestCalculateOtmPercent -v

# Only expiration range tests
python -m pytest test_screener.py::TestIsInExpirationRange -v

# Only screening integration tests
python -m pytest test_screener.py::TestScreenOptions -v
```

### Run a Single Test

```bash
python -m pytest test_screener.py::TestCalculateOtmPercent::test_call_otm_positive -v
```

## File Structure

```
optionsScalping/
├── polygon_client.py    # Polygon.io API client
├── screener.py          # Core filtering logic
├── server.py            # Flask web server
├── index.html           # Web interface
├── test_screener.py     # Unit tests
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## API Usage (Optional)

You can also call the API directly without the web interface:

```bash
curl -X POST http://localhost:5000/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "TSLA"],
    "max_price": 0.05,
    "contract_type": "call",
    "expiration_ranges": ["1-3m", "3-5m"],
    "otm_min": 0,
    "otm_max": 10
  }'
```

## OTM Calculation Explained

**For Calls:**
```
OTM % = (strike - current_price) / current_price * 100
```
- Strike $110, Price $100 → +10% OTM (out of the money)
- Strike $90, Price $100 → -10% ITM (in the money)

**For Puts:**
```
OTM % = (current_price - strike) / current_price * 100
```
- Strike $90, Price $100 → +10% OTM (out of the money)
- Strike $110, Price $100 → -10% ITM (in the money)

## Troubleshooting

### "No results found"
- Try increasing the max price threshold
- Expand the OTM range (e.g., -10% to 20%)
- Select more expiration ranges
- Check if the ticker is valid

### API Errors
- Verify your Polygon.io API key in `polygon_client.py`
- Check if you've hit rate limits (wait a few seconds)
- Some tickers may not have options data

### Server won't start
- Check if port 5000 is already in use
- Try: `python server.py` from the `optionsScalping` directory
- Ensure all dependencies are installed
