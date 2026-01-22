"""
Polygon.io API client for options data
"""
import requests
from typing import Optional, List, Dict, Any

API_KEY = "mxHpmdO4wzkVJhzExKhIfbXbUDr0OmCW"
BASE_URL = "https://api.polygon.io"


def get_options_chain(ticker: str, contract_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch all options contracts for a given underlying ticker using the snapshot endpoint.

    Args:
        ticker: The underlying stock ticker (e.g., "AAPL")
        contract_type: Optional filter for "call" or "put"

    Returns:
        Dict with 'results' (list of option contracts) and 'underlying_price'
    """
    url = f"{BASE_URL}/v3/snapshot/options/{ticker}"
    params = {
        "apiKey": API_KEY,
        "limit": 250
    }

    if contract_type:
        params["contract_type"] = contract_type

    all_results = []
    underlying_price = None

    while url:
        response = requests.get(url, params=params)

        if response.status_code != 200:
            error_msg = response.json().get("error", response.text)
            return {"results": [], "underlying_price": None, "error": f"API error: {error_msg}"}

        data = response.json()

        # Extract underlying price from first result if available
        if data.get("results") and underlying_price is None:
            first_result = data["results"][0]
            if "underlying_asset" in first_result:
                underlying_price = first_result["underlying_asset"].get("price")

        all_results.extend(data.get("results", []))

        # Handle pagination
        next_url = data.get("next_url")
        if next_url:
            url = next_url
            params = {"apiKey": API_KEY}  # next_url includes other params
        else:
            url = None

    return {
        "results": all_results,
        "underlying_price": underlying_price
    }


def get_underlying_price(ticker: str) -> Optional[float]:
    """
    Get the current price of an underlying stock.

    Args:
        ticker: The stock ticker (e.g., "AAPL")

    Returns:
        Current stock price or None if unavailable
    """
    url = f"{BASE_URL}/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}"
    params = {"apiKey": API_KEY}

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    data = response.json()
    ticker_data = data.get("ticker", {})

    # Try to get the last trade price
    if "lastTrade" in ticker_data:
        return ticker_data["lastTrade"].get("p")

    # Fallback to day's close
    if "day" in ticker_data:
        return ticker_data["day"].get("c")

    return None


if __name__ == "__main__":
    # Quick test
    print("Testing Polygon.io client...")

    # Test stock price
    price = get_underlying_price("AAPL")
    print(f"AAPL current price: ${price}")

    # Test options chain (limited)
    print("\nFetching AAPL options chain...")
    chain = get_options_chain("AAPL", contract_type="call")
    print(f"Found {len(chain['results'])} call options")
    print(f"Underlying price from options: ${chain['underlying_price']}")

    if chain["results"]:
        sample = chain["results"][0]
        print(f"\nSample option:")
        print(f"  Ticker: {sample.get('details', {}).get('ticker')}")
        print(f"  Strike: ${sample.get('details', {}).get('strike_price')}")
        print(f"  Expiration: {sample.get('details', {}).get('expiration_date')}")
        if "last_trade" in sample:
            print(f"  Last Trade Price: ${sample['last_trade'].get('price')}")
