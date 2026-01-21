"""
FRED Data Module
"""
from .fred_fetcher import FREDDataFetcher, get_economic_indicator

__all__ = ['FREDDataFetcher', 'get_economic_indicator']