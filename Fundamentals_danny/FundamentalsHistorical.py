import requests
import json
import pandas as pd
from datetime import datetime

# API Keys
POLYGON_API_KEY = "mxHpmdO4wzkVJhzExKhIfbXbUDr0OmCW"
EODHD_API_KEY = "67ffece4b2ae08.94077168"

def get_eodhd_fundamentals(ticker):
    """Fetch fundamental data from EODHD API and return as DataFrame"""
    url = f"https://eodhd.com/api/fundamentals/{ticker}.US"
    params = {
        "api_token": EODHD_API_KEY,
        "fmt": "json"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        print("\n=== EODHD API Response ===")

        # Check for cash flow data
        if "Financials" in data and "Cash_Flow" in data["Financials"]:
            cash_flow = data["Financials"]["Cash_Flow"]

            # Get yearly data
            yearly_data = cash_flow.get("yearly", {})

            # Get shares outstanding
            shares = None
            if "SharesStats" in data and "SharesOutstanding" in data["SharesStats"]:
                shares = data["SharesStats"]["SharesOutstanding"]

            # Build list of dictionaries for DataFrame
            rows = []
            for year in sorted(yearly_data.keys(), reverse=True):
                year_data = yearly_data[year]
                operating_cf = year_data.get("operatingCashFlow", None)

                row = {
                    "Year": year,
                    "Operating Cash Flow": operating_cf,
                    "Shares Outstanding": shares,
                }

                if shares and isinstance(operating_cf, (int, float)):
                    row["Cash Flow Per Share"] = operating_cf / shares
                else:
                    row["Cash Flow Per Share"] = None

                rows.append(row)

            # Create DataFrame
            df = pd.DataFrame(rows)

            print(f"\nAnnual Cash Flow Data for {ticker}:")
            print("-" * 80)
            print(df.to_string(index=False))
            print()

            return df
        else:
            print("Cash flow data not found in response")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from EODHD: {e}")
        return pd.DataFrame()

def get_polygon_financials(ticker):
    """Fetch financial data from Polygon API and return as DataFrame"""
    url = f"https://api.polygon.io/vX/reference/financials"
    params = {
        "ticker": ticker,
        "timeframe": "annual",
        "limit": 10,
        "apiKey": POLYGON_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        print("\n=== Polygon API Response ===")

        if "results" in data and len(data["results"]) > 0:
            # Build list of dictionaries for DataFrame
            rows = []

            for result in data["results"]:
                fiscal_period = result.get("fiscal_period", "N/A")
                fiscal_year = result.get("fiscal_year", "N/A")
                start_date = result.get("start_date", "N/A")
                end_date = result.get("end_date", "N/A")

                # Access cash flow statement
                cash_flow = result.get("financials", {}).get("cash_flow_statement", {})
                balance_sheet = result.get("financials", {}).get("balance_sheet", {})

                operating_cf = cash_flow.get("net_cash_flow_from_operating_activities", {}).get("value")
                shares = balance_sheet.get("equity_attributable_to_parent", {}).get("value")

                # Try to get basic shares outstanding
                if not shares:
                    shares = balance_sheet.get("common_stock_shares_outstanding", {}).get("value")

                row = {
                    "Fiscal Year": fiscal_year,
                    "Period": fiscal_period,
                    "Start Date": start_date,
                    "End Date": end_date,
                    "Operating Cash Flow": operating_cf,
                    "Shares Outstanding": shares,
                }

                if shares and operating_cf:
                    row["Cash Flow Per Share"] = operating_cf / shares
                else:
                    row["Cash Flow Per Share"] = None

                rows.append(row)

            # Create DataFrame
            df = pd.DataFrame(rows)

            print(f"\nAnnual Cash Flow Per Share for {ticker}:")
            print("-" * 80)
            print(df.to_string(index=False))
            print()

            return df
        else:
            print("No financial data found in Polygon response")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Polygon: {e}")
        return pd.DataFrame()

def main():
    ticker = "AMD"

    print(f"Fetching annual cash flow per share data for {ticker}...")
    print("=" * 80)

    # Try EODHD first
    eodhd_df = get_eodhd_fundamentals(ticker)

    # Try Polygon
    polygon_df = get_polygon_financials(ticker)

    print("\n" + "=" * 80)
    print("Data fetch complete!")

    # Return DataFrames for further use if needed
    return {
        "eodhd": eodhd_df,
        "polygon": polygon_df
    }

if __name__ == "__main__":
    results = main()
