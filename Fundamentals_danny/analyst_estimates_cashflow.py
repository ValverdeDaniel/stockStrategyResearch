import requests
import json
import pandas as pd
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# API Keys
EODHD_API_KEY = "67ffece4b2ae08.94077168"

def get_eodhd_analyst_estimates(ticker):
    """
    Fetch analyst estimates from EODHD API

    Note: EODHD provides EPS and Revenue estimates but NOT direct cash flow estimates.
    However, we can show the available forward-looking data.
    """
    url = f"https://eodhd.com/api/fundamentals/{ticker}.US"
    params = {"api_token": EODHD_API_KEY, "fmt": "json"}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        print("\n" + "="*80)
        print(f"ANALYST ESTIMATES FOR {ticker}")
        print("="*80)

        # Get Earnings Trend (forward estimates)
        if "Earnings" in data and "Trend" in data["Earnings"]:
            earnings_trend = data["Earnings"]["Trend"]

            # Filter for 2025 and 2026 estimates
            rows = []
            for date_key, estimate_data in earnings_trend.items():
                year = date_key.split('-')[0]
                if year in ['2025', '2026']:
                    period = estimate_data.get("period", "N/A")

                    row = {
                        "Date": date_key,
                        "Period": period,
                        "EPS Estimate (Avg)": estimate_data.get("earningsEstimateAvg"),
                        "EPS Estimate (Low)": estimate_data.get("earningsEstimateLow"),
                        "EPS Estimate (High)": estimate_data.get("earningsEstimateHigh"),
                        "Revenue Estimate (Avg)": estimate_data.get("revenueEstimateAvg"),
                        "Revenue Estimate (Low)": estimate_data.get("revenueEstimateLow"),
                        "Revenue Estimate (High)": estimate_data.get("revenueEstimateHigh"),
                        "Number of Analysts": estimate_data.get("earningsEstimateNumberOfAnalysts"),
                        "EPS Growth": estimate_data.get("earningsEstimateGrowth"),
                        "Revenue Growth": estimate_data.get("revenueEstimateGrowth"),
                    }
                    rows.append(row)

            if rows:
                # Sort by date
                rows_sorted = sorted(rows, key=lambda x: x["Date"])
                df = pd.DataFrame(rows_sorted)

                print("\n📊 Forward Analyst Estimates (2025-2026):")
                print("-" * 80)
                print(df.to_string(index=False))
                print("\n")

                # Display annual summary
                annual_data = [r for r in rows_sorted if r["Period"] in ["+1y", "0y"]]
                if annual_data:
                    print("\n📈 Annual Summary (2025-2026):")
                    print("-" * 80)
                    annual_df = pd.DataFrame(annual_data)
                    # Select key columns for cleaner display
                    summary_cols = ["Date", "Period", "EPS Estimate (Avg)", "Revenue Estimate (Avg)",
                                    "Number of Analysts", "EPS Growth", "Revenue Growth"]
                    print(annual_df[summary_cols].to_string(index=False))
                    print("\n")

                return df
            else:
                print("\n❌ No 2025 or 2026 estimates found")
                return pd.DataFrame()
        else:
            print("\n❌ No analyst estimates data available")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error fetching data from EODHD: {e}")
        return pd.DataFrame()

def estimate_cash_flow_from_eps(df, shares_outstanding=None):
    """
    Estimate operating cash flow from EPS estimates

    Note: This is a rough approximation. Actual cash flow per share
    can differ significantly from EPS due to:
    - Non-cash expenses (depreciation, stock-based compensation)
    - Working capital changes
    - Other adjustments

    Typically, operating cash flow > net income (EPS * shares)
    A common rule of thumb: Cash Flow ≈ 1.2-1.5x Net Income for mature tech companies
    """
    if df.empty:
        return df

    print("\n" + "="*80)
    print("ESTIMATED CASH FLOW (Based on EPS)")
    print("="*80)
    print("\n⚠️  WARNING: These are ROUGH ESTIMATES based on EPS projections.")
    print("Actual cash flow can vary significantly from net income.")
    print("For accurate cash flow forecasts, consider using specialized financial models.")
    print("-" * 80)

    # Create a copy for cash flow estimates
    cf_df = df.copy()

    # Filter for annual estimates only
    cf_df = cf_df[cf_df["Period"].isin(["+1y", "0y"])]

    if not cf_df.empty:
        # Use conversion factors (conservative to aggressive)
        conversion_factors = {
            "Conservative (1.0x)": 1.0,
            "Moderate (1.2x)": 1.2,
            "Optimistic (1.5x)": 1.5
        }

        for factor_name, factor_value in conversion_factors.items():
            # Calculate estimated operating cash flow
            cf_df[f"Est. Operating CF - {factor_name}"] = (
                cf_df["EPS Estimate (Avg)"].astype(float) * factor_value *
                (shares_outstanding if shares_outstanding else 1)
            )

        # Select relevant columns
        display_cols = ["Date", "Period", "EPS Estimate (Avg)"] + [
            col for col in cf_df.columns if "Est. Operating CF" in col
        ]

        print("\n" + cf_df[display_cols].to_string(index=False))

        if not shares_outstanding:
            print("\n💡 Note: Values shown are per-share. Multiply by shares outstanding for total cash flow.")

        print("\n")
        return cf_df

    return cf_df

def main():
    ticker = "AMD"
    shares_outstanding = 1.6e9  # AMD approximate shares outstanding (update as needed)

    print(f"\n🔍 Fetching analyst estimates for {ticker}...")

    # Get analyst estimates
    estimates_df = get_eodhd_analyst_estimates(ticker)

    # Estimate cash flow based on EPS
    if not estimates_df.empty:
        cf_estimates_df = estimate_cash_flow_from_eps(estimates_df, shares_outstanding)

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\n✅ EODHD provides:")
    print("   - EPS estimates for 2025 and 2026")
    print("   - Revenue estimates for 2025 and 2026")
    print("   - Analyst ratings and price targets")
    print("\n❌ EODHD does NOT provide:")
    print("   - Direct operating cash flow estimates")
    print("   - Free cash flow forecasts")
    print("\n❌ Polygon does NOT provide:")
    print("   - Analyst estimates for any metrics")
    print("   - Forward-looking financial data")
    print("\n💡 Recommendation:")
    print("   - For cash flow estimates, use the EPS-based approximations above")
    print("   - Consider using financial modeling or analyst reports for accurate CF forecasts")
    print("   - Alternative APIs: Financial Modeling Prep, Alpha Vantage, FactSet")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
