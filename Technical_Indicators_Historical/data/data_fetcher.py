"""
Data fetcher module for retrieving stock data from EODHD and YFinance
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
import pytz
from typing import Optional, Dict, Any


class DataFetcher:
    """Fetches stock data from EODHD API or YFinance as fallback"""

    EODHD_API_KEY = "67ffece4b2ae08.94077168"
    EODHD_BASE_URL = "https://eodhd.com/api"

    def __init__(self, use_cache: bool = True):
        """
        Initialize data fetcher

        Args:
            use_cache: Whether to use caching for API calls
        """
        self.use_cache = use_cache
        self.cache = {}

    def fetch_historical_data(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        source: str = "yfinance"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a ticker

        Args:
            ticker: Stock symbol (e.g., 'AAPL')
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            source: Data source ('yfinance' or 'eodhd')

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        cache_key = f"{ticker}_{period}_{interval}_{source}"

        if self.use_cache and cache_key in self.cache:
            return self.cache[cache_key].copy()

        if source == "yfinance":
            df = self._fetch_from_yfinance(ticker, period, interval)
        elif source == "eodhd":
            df = self._fetch_from_eodhd(ticker, period)
        else:
            raise ValueError(f"Unknown source: {source}")

        if df is not None and self.use_cache:
            self.cache[cache_key] = df.copy()

        return df

    def _fetch_from_yfinance(
        self,
        ticker: str,
        period: str,
        interval: str
    ) -> pd.DataFrame:
        """
        Fetch data from YFinance

        Args:
            ticker: Stock symbol
            period: Time period
            interval: Data interval

        Returns:
            DataFrame with OHLCV data
        """
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            # Standardize column names
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Remove unnecessary columns
            df = df[['open', 'high', 'low', 'close', 'volume']]

            # Ensure timezone-aware index
            if df.index.tz is None:
                df.index = df.index.tz_localize('America/New_York')

            return df

        except Exception as e:
            print(f"Error fetching from YFinance: {e}")
            return None

    def _fetch_from_eodhd(self, ticker: str, period: str) -> pd.DataFrame:
        """
        Fetch data from EODHD API

        Args:
            ticker: Stock symbol
            period: Time period

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Convert period to date range
            end_date = datetime.now()

            period_map = {
                "1d": 1,
                "5d": 5,
                "1mo": 30,
                "3mo": 90,
                "6mo": 180,
                "1y": 365,
                "2y": 730,
                "5y": 1825
            }

            days = period_map.get(period, 365)
            start_date = end_date - timedelta(days=days)

            # Format dates for API
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")

            # Construct API URL
            url = f"{self.EODHD_BASE_URL}/eod/{ticker}.US"
            params = {
                "api_token": self.EODHD_API_KEY,
                "from": from_date,
                "to": to_date,
                "fmt": "json"
            }

            # Make API request
            response = requests.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if not data:
                print(f"No data returned from EODHD for {ticker}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Set date as index
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # Ensure timezone-aware index
            if df.index.tz is None:
                df.index = df.index.tz_localize('America/New_York')

            # Standardize column names
            df.columns = df.columns.str.lower()

            # Select relevant columns
            df = df[['open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            print(f"Error fetching from EODHD: {e}")
            print(f"Falling back to YFinance...")
            return self._fetch_from_yfinance(ticker, period, "1d")

    def fetch_realtime_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch real-time quote for a ticker

        Args:
            ticker: Stock symbol

        Returns:
            Dictionary with current price, change, volume, etc.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                'symbol': ticker,
                'price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'previousClose': info.get('previousClose', 0),
                'open': info.get('open', info.get('regularMarketOpen', 0)),
                'dayHigh': info.get('dayHigh', info.get('regularMarketDayHigh', 0)),
                'dayLow': info.get('dayLow', info.get('regularMarketDayLow', 0)),
                'volume': info.get('volume', info.get('regularMarketVolume', 0)),
                'marketCap': info.get('marketCap', 0),
                'pe': info.get('trailingPE', 0),
                'name': info.get('longName', ticker)
            }
        except Exception as e:
            print(f"Error fetching quote: {e}")
            return {'symbol': ticker, 'error': str(e)}

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate OHLCV data

        Args:
            df: DataFrame to validate

        Returns:
            True if data is valid, False otherwise
        """
        if df is None or df.empty:
            return False

        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            return False

        # Check for NaN values
        if df[required_columns].isnull().any().any():
            print("Warning: NaN values found in data")
            return False

        # Check OHLC relationships
        invalid_candles = (
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        )

        if invalid_candles.any():
            print(f"Warning: {invalid_candles.sum()} invalid candles found")
            return False

        return True

    def clear_cache(self):
        """Clear the data cache"""
        self.cache = {}
        print("Data cache cleared")