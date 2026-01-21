"""
Check what forecast data is available for different tickers
"""
import requests
import json

EODHD_API_KEY = "67ffece4b2ae08.94077168"

def check_forecasts(ticker):
    print(f"\n=== {ticker} FORECAST DATA ===")

    url = f"https://eodhd.com/api/fundamentals/{ticker}.US"
    params = {
        "api_token": EODHD_API_KEY,
        "fmt": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Check Earnings.Trend structure
    if "Earnings" in data and "Trend" in data["Earnings"]:
        trend = data["Earnings"]["Trend"]
        print(f"Available trend periods: {list(trend.keys())}")

        # Check each period
        for period in ["+1y", "+2y", "0y", "2025-12-31", "2026-12-31", "2025-Q4", "2026-Q4"]:
            if period in trend:
                print(f"\n{period} data:")
                if "earningsEstimateAvg" in trend[period]:
                    print(f"  EPS Estimate: {trend[period]['earningsEstimateAvg']}")
                if "revenueEstimateAvg" in trend[period]:
                    print(f"  Revenue Estimate: {trend[period]['revenueEstimateAvg']}")
                if "earningsEstimateNumberOfAnalysts" in trend[period]:
                    print(f"  Number of Analysts: {trend[period]['earningsEstimateNumberOfAnalysts']}")
    else:
        print("No Earnings.Trend data found")

    # Check for any future years in Earnings.Annual
    if "Earnings" in data and "Annual" in data["Earnings"]:
        annual = data["Earnings"]["Annual"]
        future_years = [k for k in annual.keys() if k.startswith("2025") or k.startswith("2026")]
        if future_years:
            print(f"\nFuture years in Earnings.Annual: {future_years}")

# Check multiple tickers
for ticker in ["MSFT", "AAPL", "AMD", "NVDA"]:
    check_forecasts(ticker)