import requests
import json
import pandas as pd
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Note: You'll need to sign up for a free API key at https://site.financialmodelingprep.com/developer/docs/
# Free tier allows 250 requests per day

def explore_fmp_analyst_estimates(ticker, api_key=None):
    """
    Explore Financial Modeling Prep API for analyst estimates including cash flow

    FMP provides several endpoints for forward-looking data:
    1. Analyst Estimates - includes revenue, EPS, etc.
    2. Analyst Recommendations
    3. Price Targets
    """

    if not api_key:
        print("\n" + "="*80)
        print("FINANCIAL MODELING PREP API - DEMO MODE")
        print("="*80)
        print("\n⚠️  No API key provided. Sign up for free at:")
        print("   https://site.financialmodelingprep.com/developer/docs/")
        print("\n   Free tier: 250 requests/day")
        print("   Pricing: $14-29/month for more requests")
        print("\n" + "="*80)
        return

    print("\n" + "="*80)
    print(f"EXPLORING FINANCIAL MODELING PREP API FOR {ticker}")
    print("="*80)

    # 1. Analyst Estimates endpoint
    print("\n1. Checking Analyst Estimates endpoint...")
    url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{ticker}"
    params = {"apikey": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data and isinstance(data, list) and len(data) > 0:
            print("   ✓ Analyst Estimates found!")
            print(f"   Available periods: {len(data)}")

            # Check what data is available
            print("\n   Sample data structure:")
            print(json.dumps(data[0], indent=2))

            # Convert to DataFrame
            df = pd.DataFrame(data)
            print("\n   Available columns:")
            print(f"   {list(df.columns)}")

            # Filter for future estimates
            print("\n   📊 Future Estimates:")
            print(df[['date', 'symbol', 'estimatedRevenueAvg', 'estimatedRevenueLow',
                      'estimatedRevenueHigh', 'estimatedEpsAvg', 'numberAnalysts']].head(10).to_string(index=False))

            return df
        else:
            print(f"   ❌ No data returned. Response: {data}")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")

    # 2. Check for Cash Flow Statement estimates
    print("\n\n2. Checking Cash Flow Statement Estimates...")
    url = f"https://financialmodelingprep.com/api/v3/analyst-estimates-cash-flow/{ticker}"
    params = {"apikey": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data and isinstance(data, list) and len(data) > 0:
            print("   ✓ Cash Flow Estimates found!")
            print(f"   Available periods: {len(data)}")

            # Show sample
            print("\n   Sample data structure:")
            print(json.dumps(data[0], indent=2))

            # Convert to DataFrame
            df = pd.DataFrame(data)
            print("\n   Available columns:")
            print(f"   {list(df.columns)}")

            # Display cash flow estimates
            if 'estimatedOperatingCashFlowAvg' in df.columns:
                print("\n   📊 Operating Cash Flow Estimates:")
                cf_cols = ['date', 'symbol', 'estimatedOperatingCashFlowAvg',
                          'estimatedOperatingCashFlowLow', 'estimatedOperatingCashFlowHigh',
                          'numberAnalysts']
                available_cols = [col for col in cf_cols if col in df.columns]
                print(df[available_cols].head(10).to_string(index=False))
            else:
                print("\n   Available estimate columns:")
                estimate_cols = [col for col in df.columns if 'estimated' in col.lower()]
                print(f"   {estimate_cols}")

            return df
        else:
            print(f"   ❌ No cash flow estimates found. Response: {data}")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")

    # 3. Check analyst recommendations
    print("\n\n3. Checking Analyst Recommendations...")
    url = f"https://financialmodelingprep.com/api/v3/analyst-stock-recommendations/{ticker}"
    params = {"apikey": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data and isinstance(data, list) and len(data) > 0:
            print("   ✓ Analyst Recommendations found!")
            print(f"   Recent recommendations: {len(data)}")

            df = pd.DataFrame(data)
            print("\n   Recent recommendations:")
            print(df.head(5).to_string(index=False))
        else:
            print(f"   ❌ No recommendations found.")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")

def main():
    ticker = "AMD"

    # You need to provide your own API key here
    # Sign up at: https://site.financialmodelingprep.com/developer/docs/
    api_key = None  # Replace with your actual API key: "YOUR_API_KEY_HERE"

    if api_key is None:
        print("\n" + "="*80)
        print("FMP API KEY REQUIRED")
        print("="*80)
        print("\nTo use Financial Modeling Prep API:")
        print("1. Sign up at: https://site.financialmodelingprep.com/developer/docs/")
        print("2. Get your free API key (250 requests/day)")
        print("3. Update this script with your API key")
        print("\n   api_key = 'YOUR_API_KEY_HERE'  # Line 128")
        print("\n" + "="*80)

        print("\n\n📋 What FMP API Typically Provides:")
        print("-" * 80)
        print("✓ Analyst Estimates for:")
        print("  - Revenue (quarterly & annual)")
        print("  - EPS (quarterly & annual)")
        print("  - EBITDA")
        print("  - Net Income")
        print("  - SG&A Expense")
        print("\n❓ Cash Flow Estimates:")
        print("  - MAY include operating cash flow estimates")
        print("  - This varies by API tier and data availability")
        print("\n💰 Pricing:")
        print("  - Free: 250 requests/day")
        print("  - Starter: $14/month (750 requests/day)")
        print("  - Professional: $29/month (1500 requests/day)")
        print("=" * 80)
        return

    explore_fmp_analyst_estimates(ticker, api_key)

if __name__ == "__main__":
    main()
