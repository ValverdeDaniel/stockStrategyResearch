"""
FRED Data Fetcher Module
Handles all data fetching operations from FRED API with caching support
"""

import os
import sys
import pandas as pd
import numpy as np
from fredapi import Fred
from typing import Optional, Dict, List, Union
from datetime import datetime, timedelta
import logging
import json
from cachetools import TTLCache
import pickle
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    FRED_API_KEY, FRED_SERIES_IDS, DEFAULT_START_DATE,
    DEFAULT_END_DATE, ENABLE_CACHE, CACHE_EXPIRY_HOURS, DATA_CACHE_DIR
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Windows UTF-8 encoding fix
if sys.platform == 'win32':
    import locale
    if locale.getpreferredencoding().upper() != 'UTF-8':
        os.environ['PYTHONIOENCODING'] = 'utf-8'

class FREDDataFetcher:
    """
    Fetches economic data from FRED API with caching support

    This class follows the pattern established in the existing codebase,
    particularly from Technical_Indicators_Historical/data/data_fetcher.py
    """

    def __init__(self, api_key: str = None, use_cache: bool = True):
        """
        Initialize FRED Data Fetcher

        Args:
            api_key: FRED API key (uses config default if not provided)
            use_cache: Whether to use caching for API calls
        """
        self.api_key = api_key or FRED_API_KEY

        if self.api_key == "YOUR_FRED_API_KEY_HERE":
            logger.warning("Please set your FRED API key in config.py")
            logger.info("Get your free API key from: https://fred.stlouisfed.org/docs/api/api_key.html")

        try:
            self.fred = Fred(api_key=self.api_key)
            logger.info("FRED API connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FRED API: {e}")
            raise

        self.use_cache = use_cache and ENABLE_CACHE
        self.cache = TTLCache(maxsize=100, ttl=CACHE_EXPIRY_HOURS * 3600) if self.use_cache else {}

        # Create cache directory if it doesn't exist
        if self.use_cache:
            self.cache_dir = Path(DATA_CACHE_DIR)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_series(self, series_id: str, start_date: str = None,
                    end_date: str = None, frequency: str = None) -> pd.DataFrame:
        """
        Fetch data for a specific FRED series

        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE')
            start_date: Start date for data (YYYY-MM-DD format)
            end_date: End date for data (YYYY-MM-DD format)
            frequency: Data frequency ('d', 'w', 'm', 'q', 'a')

        Returns:
            DataFrame with date index and series values
        """
        # Use defaults if not provided
        start_date = start_date or DEFAULT_START_DATE
        end_date = end_date or DEFAULT_END_DATE

        # Create cache key
        cache_key = f"{series_id}_{start_date}_{end_date}_{frequency}"

        # Check cache first
        if self.use_cache and cache_key in self.cache:
            logger.info(f"Loading {series_id} from cache")
            return self.cache[cache_key]

        # Check file cache
        cache_file = self.cache_dir / f"{cache_key}.pkl" if self.use_cache else None
        if cache_file and cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    logger.info(f"Loading {series_id} from file cache")
                    self.cache[cache_key] = data
                    return data
            except Exception as e:
                logger.warning(f"Failed to load from file cache: {e}")

        try:
            logger.info(f"Fetching {series_id} from FRED API...")

            # Fetch data from FRED
            if frequency:
                data = self.fred.get_series(
                    series_id,
                    observation_start=start_date,
                    observation_end=end_date,
                    frequency=frequency
                )
            else:
                data = self.fred.get_series(
                    series_id,
                    observation_start=start_date,
                    observation_end=end_date
                )

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=[series_id])
            df.index.name = 'date'

            # Clean data
            df = df.dropna()

            # Cache the result
            if self.use_cache:
                self.cache[cache_key] = df
                # Save to file
                if cache_file:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(df, f)

            logger.info(f"Successfully fetched {len(df)} data points for {series_id}")
            return df

        except Exception as e:
            logger.error(f"Error fetching {series_id}: {e}")
            raise

    def fetch_multiple_series(self, series_ids: List[str], start_date: str = None,
                            end_date: str = None) -> pd.DataFrame:
        """
        Fetch multiple FRED series and combine into single DataFrame

        Args:
            series_ids: List of FRED series IDs
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with all series as columns
        """
        dfs = []

        for series_id in series_ids:
            try:
                df = self.fetch_series(series_id, start_date, end_date)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to fetch {series_id}: {e}")

        if not dfs:
            raise ValueError("No series could be fetched successfully")

        # Combine all DataFrames
        result = pd.concat(dfs, axis=1, join='outer')
        result = result.sort_index()

        return result

    def get_series_info(self, series_id: str) -> Dict:
        """
        Get metadata information about a FRED series

        Args:
            series_id: FRED series ID

        Returns:
            Dictionary with series metadata
        """
        try:
            info = self.fred.get_series_info(series_id)
            return {
                'title': info.get('title', ''),
                'units': info.get('units', ''),
                'frequency': info.get('frequency', ''),
                'seasonal_adjustment': info.get('seasonal_adjustment', ''),
                'last_updated': info.get('last_updated', ''),
                'observation_start': info.get('observation_start', ''),
                'observation_end': info.get('observation_end', ''),
            }
        except Exception as e:
            logger.error(f"Error getting series info for {series_id}: {e}")
            return {}

    def calculate_growth_rate(self, df: pd.DataFrame, column: str,
                             periods: int = 1, method: str = 'pct') -> pd.Series:
        """
        Calculate growth rate for a series

        Args:
            df: DataFrame containing the series
            column: Column name to calculate growth for
            periods: Number of periods for growth calculation
            method: 'pct' for percentage change, 'log' for log difference

        Returns:
            Series with growth rates
        """
        if method == 'pct':
            return df[column].pct_change(periods) * 100
        elif method == 'log':
            return (np.log(df[column]) - np.log(df[column].shift(periods))) * 100
        else:
            raise ValueError(f"Unknown method: {method}")

    def calculate_yoy_growth(self, df: pd.DataFrame, column: str) -> pd.Series:
        """
        Calculate year-over-year growth rate

        Args:
            df: DataFrame with date index
            column: Column to calculate YoY growth for

        Returns:
            Series with YoY growth rates
        """
        # Determine frequency
        if pd.infer_freq(df.index) in ['Q', 'QS']:
            periods = 4  # Quarterly data
        elif pd.infer_freq(df.index) in ['M', 'MS']:
            periods = 12  # Monthly data
        else:
            periods = 1  # Annual or other

        return self.calculate_growth_rate(df, column, periods)

    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()

        # Clear file cache
        if self.use_cache and self.cache_dir.exists():
            for cache_file in self.cache_dir.glob('*.pkl'):
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")

        logger.info("Cache cleared successfully")


# Convenience function for quick data fetching
def get_economic_indicator(indicator_name: str, start_date: str = None,
                          end_date: str = None) -> pd.DataFrame:
    """
    Quick function to fetch common economic indicators

    Args:
        indicator_name: Name from FRED_SERIES_IDS in config
        start_date: Start date for data
        end_date: End date for data

    Returns:
        DataFrame with the requested data
    """
    if indicator_name not in FRED_SERIES_IDS:
        raise ValueError(f"Unknown indicator: {indicator_name}. "
                        f"Available: {list(FRED_SERIES_IDS.keys())}")

    fetcher = FREDDataFetcher()
    series_id = FRED_SERIES_IDS[indicator_name]
    return fetcher.fetch_series(series_id, start_date, end_date)


if __name__ == "__main__":
    # Test the fetcher
    print("Testing FRED Data Fetcher...")

    fetcher = FREDDataFetcher()

    # Test fetching GDP data
    try:
        gdp_data = fetcher.fetch_series('GDP', start_date='2020-01-01')
        print(f"\nGDP Data (last 5 observations):")
        print(gdp_data.tail())

        # Get series info
        info = fetcher.get_series_info('GDP')
        print(f"\nGDP Series Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"Error in test: {e}")