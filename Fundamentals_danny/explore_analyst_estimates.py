import requests
import json
import pandas as pd
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# API Keys
POLYGON_API_KEY = "mxHpmdO4wzkVJhzExKhIfbXbUDr0OmCW"
EODHD_API_KEY = "67ffece4b2ae08.94077168"

def explore_eodhd_estimates(ticker):
    """Explore EODHD API for analyst estimates and forecasts"""
    print("\n" + "="*80)
    print("EXPLORING EODHD API FOR ANALYST ESTIMATES")
    print("="*80)

    # 1. Check fundamentals endpoint for analyst estimates
    print("\n1. Checking Fundamentals endpoint (Analyst Ratings section)...")
    url = f"https://eodhd.com/api/fundamentals/{ticker}.US"
    params = {"api_token": EODHD_API_KEY, "fmt": "json"}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Check for Analyst Ratings
        if "AnalystRatings" in data:
            print("\n   ✓ AnalystRatings section found!")
            print(json.dumps(data["AnalystRatings"], indent=2)[:1000])  # First 1000 chars

        # Check for Earnings data
        if "Earnings" in data:
            print("\n   ✓ Earnings section found!")
            earnings = data["Earnings"]
            if "History" in earnings:
                print("\n   Earnings History (sample):")
                print(json.dumps(list(earnings["History"].items())[:2], indent=2))
            if "Trend" in earnings:
                print("\n   Earnings Trend (forward estimates):")
                print(json.dumps(earnings["Trend"], indent=2))
            if "Annual" in earnings:
                print("\n   Annual Earnings (sample):")
                print(json.dumps(list(earnings["Annual"].items())[:2], indent=2))

        # Check for Financials -> Cash_Flow -> Quarterly for projections
        if "Financials" in data and "Cash_Flow" in data["Financials"]:
            print("\n   ✓ Cash Flow section found!")
            cf = data["Financials"]["Cash_Flow"]
            print(f"   - Available periods: {list(cf.keys())}")

        # Check for any other relevant sections
        print(f"\n   Main sections available: {list(data.keys())[:20]}")

    except Exception as e:
        print(f"   ✗ Error: {e}")

    # 2. Try analyst estimates endpoint (if exists)
    print("\n\n2. Trying dedicated analyst estimates endpoint...")
    url = f"https://eodhd.com/api/analyst-estimates/{ticker}.US"
    params = {"api_token": EODHD_API_KEY, "fmt": "json"}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print("   ✓ Analyst estimates endpoint accessible!")
        print(json.dumps(data[:2] if isinstance(data, list) else data, indent=2)[:2000])
    except Exception as e:
        print(f"   ✗ Error: {e}")

def explore_polygon_estimates(ticker):
    """Explore Polygon API for analyst estimates and forecasts"""
    print("\n" + "="*80)
    print("EXPLORING POLYGON API FOR ANALYST ESTIMATES")
    print("="*80)

    # 1. Try ticker details endpoint
    print("\n1. Checking Ticker Details endpoint...")
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}"
    params = {"apiKey": POLYGON_API_KEY}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print("   ✓ Ticker details retrieved!")
        if "results" in data:
            print(f"   Available fields: {list(data['results'].keys())}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # 2. Try analyst ratings/estimates endpoint
    print("\n2. Checking for Analyst Ratings endpoint...")
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}/analyst-ratings"
    params = {"apiKey": POLYGON_API_KEY}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print("   ✓ Analyst ratings endpoint accessible!")
        print(json.dumps(data, indent=2)[:2000])
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # 3. Try consensus estimates endpoint
    print("\n3. Checking for Consensus/Estimates endpoint...")
    url = f"https://api.polygon.io/v1/indicators/estimates/{ticker}"
    params = {"apiKey": POLYGON_API_KEY}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print("   ✓ Estimates endpoint accessible!")
        print(json.dumps(data, indent=2)[:2000])
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # 4. Try market snapshot with fundamentals
    print("\n4. Checking Market Snapshot endpoint...")
    url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
    params = {"apiKey": POLYGON_API_KEY}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print("   ✓ Market snapshot retrieved!")
        if "ticker" in data:
            print(f"   Available fields: {list(data['ticker'].keys())}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # 5. Try financial forecasts endpoint
    print("\n5. Checking for Financial Forecasts endpoint...")
    url = f"https://api.polygon.io/vX/reference/financials"
    params = {
        "ticker": ticker,
        "timeframe": "annual",
        "period_of_report_date.gte": "2025-01-01",
        "apiKey": POLYGON_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        print("   ✓ Financial forecasts query successful!")
        print(f"   Results count: {len(data.get('results', []))}")
        if data.get('results'):
            print(json.dumps(data['results'][0], indent=2)[:1000])
    except Exception as e:
        print(f"   ✗ Error: {e}")

def main():
    ticker = "AMD"

    print(f"\nExploring APIs for analyst cash flow estimates for {ticker}")
    print("Looking for 2025 and 2026 forecasts...")

    # Explore EODHD
    explore_eodhd_estimates(ticker)

    # Explore Polygon
    explore_polygon_estimates(ticker)

    print("\n" + "="*80)
    print("EXPLORATION COMPLETE")
    print("="*80)
    print("\nSummary:")
    print("- Check above for any endpoints that returned estimate data")
    print("- Look for sections containing 'estimate', 'forecast', 'consensus', or future dates")
    print("="*80)

if __name__ == "__main__":
    main()
