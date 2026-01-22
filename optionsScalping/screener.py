"""
Options screener logic - filters options contracts based on user criteria
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from polygon_client import get_options_chain, get_underlying_price


# Expiration range mappings (in days from today)
EXPIRATION_RANGES = {
    "lt1m": (0, 30),       # Less than 1 month
    "1-3m": (31, 90),      # 1-3 months
    "3-5m": (91, 150),     # 3-5 months
    "5-8m": (151, 240),    # 5-8 months
    "8-12m": (241, 365),   # 8-12 months
}


def format_time_ago(ns_timestamp: Optional[int]) -> str:
    """
    Convert a nanosecond Unix timestamp to a human-readable "X ago" format.

    Args:
        ns_timestamp: Unix timestamp in nanoseconds

    Returns:
        Human-readable string like "5m ago", "2h ago", "3d ago"
    """
    if not ns_timestamp:
        return "N/A"

    try:
        seconds = ns_timestamp / 1_000_000_000
        trade_time = datetime.fromtimestamp(seconds)
        delta = datetime.now() - trade_time

        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return f"{delta.seconds}s ago"
    except (ValueError, OSError):
        return "N/A"


def calculate_otm_percent(strike: float, current_price: float, contract_type: str) -> float:
    """
    Calculate how far out of the money an option is as a percentage.

    For CALLS: OTM % = (strike - current_price) / current_price * 100
        Positive % means strike is ABOVE current price (out of the money)

    For PUTS: OTM % = (current_price - strike) / current_price * 100
        Positive % means strike is BELOW current price (out of the money)

    Args:
        strike: The option's strike price
        current_price: The underlying's current price
        contract_type: "call" or "put"

    Returns:
        OTM percentage (positive = out of the money)
    """
    if current_price == 0:
        return 0

    if contract_type == "call":
        return ((strike - current_price) / current_price) * 100
    else:  # put
        return ((current_price - strike) / current_price) * 100


def is_in_expiration_range(expiration_date: str, selected_ranges: List[str]) -> bool:
    """
    Check if an expiration date falls within any of the selected ranges.

    Args:
        expiration_date: Date string in YYYY-MM-DD format
        selected_ranges: List of range keys (e.g., ["lt1m", "1-3m"])

    Returns:
        True if expiration is within any selected range
    """
    try:
        exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
        today = datetime.now()
        days_to_expiration = (exp_date - today).days

        for range_key in selected_ranges:
            if range_key in EXPIRATION_RANGES:
                min_days, max_days = EXPIRATION_RANGES[range_key]
                if min_days <= days_to_expiration <= max_days:
                    return True

        return False
    except (ValueError, TypeError):
        return False


def screen_options(
    tickers: List[str],
    max_price: float,
    contract_type: str,
    expiration_ranges: List[str],
    otm_min: float,
    otm_max: float
) -> Dict[str, Any]:
    """
    Screen options across multiple tickers based on filter criteria.

    Args:
        tickers: List of underlying stock tickers
        max_price: Maximum last trade price (e.g., 0.05 for under 5 cents)
        contract_type: "call" or "put"
        expiration_ranges: List of expiration range keys
        otm_min: Minimum OTM percentage
        otm_max: Maximum OTM percentage

    Returns:
        Dict with 'results' list and 'errors' list
    """
    all_results = []
    errors = []

    for ticker in tickers:
        ticker = ticker.strip().upper()
        if not ticker:
            continue

        print(f"Scanning {ticker}...")

        # Fetch options chain
        chain_data = get_options_chain(ticker, contract_type=contract_type)

        if "error" in chain_data:
            errors.append({"ticker": ticker, "error": chain_data["error"]})
            continue

        underlying_price = chain_data.get("underlying_price")

        # If we didn't get underlying price from options, try stock endpoint
        if underlying_price is None:
            underlying_price = get_underlying_price(ticker)

        if underlying_price is None:
            errors.append({"ticker": ticker, "error": "Could not get underlying price"})
            continue

        # Filter options
        for option in chain_data.get("results", []):
            details = option.get("details", {})
            last_trade = option.get("last_trade", {})
            last_quote = option.get("last_quote", {})

            # Get option details
            strike = details.get("strike_price")
            expiration = details.get("expiration_date")
            option_ticker = details.get("ticker")
            option_type = details.get("contract_type")
            last_price = last_trade.get("price")

            # Get bid/ask from last_quote
            bid = last_quote.get("bid")
            ask = last_quote.get("ask")

            # Get timestamp - prefer trade timestamp, fallback to quote timestamp
            trade_timestamp = last_trade.get("sip_timestamp")
            quote_timestamp = last_quote.get("sip_timestamp")
            data_timestamp = trade_timestamp or quote_timestamp

            # Skip if missing critical data
            if strike is None or expiration is None or last_price is None:
                continue

            # Filter by price
            if last_price > max_price:
                continue

            # Filter by expiration range
            if not is_in_expiration_range(expiration, expiration_ranges):
                continue

            # Calculate and filter by OTM percentage
            otm_pct = calculate_otm_percent(strike, underlying_price, contract_type)
            if not (otm_min <= otm_pct <= otm_max):
                continue

            # Add to results
            all_results.append({
                "underlying_ticker": ticker,
                "option_ticker": option_ticker,
                "contract_type": option_type,
                "strike": strike,
                "expiration": expiration,
                "last_price": last_price,
                "bid": bid,
                "ask": ask,
                "data_age": format_time_ago(data_timestamp),
                "otm_percent": round(otm_pct, 2),
                "underlying_price": underlying_price,
                "days_to_expiration": (datetime.strptime(expiration, "%Y-%m-%d") - datetime.now()).days
            })

    # Sort by last_price ascending
    all_results.sort(key=lambda x: x["last_price"])

    return {
        "results": all_results,
        "errors": errors,
        "total_found": len(all_results)
    }


if __name__ == "__main__":
    # Test the screener
    print("Testing options screener...")

    results = screen_options(
        tickers=["AAPL"],
        max_price=0.10,
        contract_type="call",
        expiration_ranges=["1-3m", "3-5m"],
        otm_min=0,
        otm_max=15
    )

    print(f"\nFound {results['total_found']} matching options")

    for r in results["results"][:5]:
        print(f"\n{r['option_ticker']}")
        print(f"  Strike: ${r['strike']} | Expiration: {r['expiration']}")
        print(f"  Last Price: ${r['last_price']} | OTM: {r['otm_percent']}%")

    if results["errors"]:
        print(f"\nErrors: {results['errors']}")
