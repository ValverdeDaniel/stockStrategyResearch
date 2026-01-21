"""
Base class for all technical indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod


class BaseIndicator(ABC):
    """Abstract base class for all technical indicators"""

    def __init__(self, name: str, params: Dict[str, Any] = None):
        """
        Initialize base indicator

        Args:
            name: Name of the indicator
            params: Parameters for the indicator
        """
        self.name = name
        self.params = params or {}
        self.data = None
        self.calculated_values = {}

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the indicator values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with calculated indicator values
        """
        pass

    @abstractmethod
    def get_plot_config(self) -> Dict[str, Any]:
        """
        Get configuration for plotting the indicator

        Returns:
            Dictionary with plot configuration
        """
        pass

    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate input data

        Args:
            df: DataFrame to validate

        Returns:
            True if data is valid, False otherwise
        """
        if df is None or df.empty:
            return False

        required_columns = self.get_required_columns()
        if not all(col in df.columns for col in required_columns):
            print(f"Missing required columns: {required_columns}")
            return False

        return True

    def get_required_columns(self) -> List[str]:
        """
        Get list of required columns for this indicator

        Returns:
            List of column names
        """
        return ['open', 'high', 'low', 'close', 'volume']

    def get_price_column(self, df: pd.DataFrame, price_type: str = 'close') -> pd.Series:
        """
        Get the appropriate price column based on price type

        Args:
            df: DataFrame with OHLCV data
            price_type: Type of price to use

        Returns:
            Series with price data
        """
        price_map = {
            'close': df['close'],
            'open': df['open'],
            'high': df['high'],
            'low': df['low'],
            'hl2': (df['high'] + df['low']) / 2,
            'hlc3': (df['high'] + df['low'] + df['close']) / 3,
            'ohlc4': (df['open'] + df['high'] + df['low'] + df['close']) / 4,
            'median': (df['high'] + df['low']) / 2
        }

        return price_map.get(price_type, df['close'])

    def get_parameter_controls(self) -> Dict[str, Any]:
        """
        Get UI control configuration for parameters

        Returns:
            Dictionary with parameter control definitions
        """
        return {}

    def update_params(self, new_params: Dict[str, Any]) -> None:
        """
        Update indicator parameters

        Args:
            new_params: New parameter values
        """
        self.params.update(new_params)
        # Clear calculated values when parameters change
        self.calculated_values = {}

    def get_default_params(self) -> Dict[str, Any]:
        """
        Get default parameters for the indicator

        Returns:
            Dictionary with default parameter values
        """
        return {}

    def get_indicator_value(self, index: Any) -> Optional[float]:
        """
        Get indicator value at a specific index

        Args:
            index: Index to get value for

        Returns:
            Indicator value or None
        """
        if self.data is not None and index in self.data.index:
            return self.data.loc[index, self.name]
        return None

    def get_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on indicator

        Args:
            df: DataFrame with indicator values

        Returns:
            DataFrame with buy/sell signals
        """
        # Default implementation - can be overridden by specific indicators
        signals = pd.DataFrame(index=df.index)
        signals['signal'] = 0
        return signals

    def get_description(self) -> str:
        """
        Get description of the indicator

        Returns:
            String description
        """
        return f"{self.name} indicator with parameters: {self.params}"

    def __str__(self) -> str:
        """String representation of the indicator"""
        return f"{self.name}({self.params})"

    def __repr__(self) -> str:
        """Detailed representation of the indicator"""
        return f"{self.__class__.__name__}(name='{self.name}', params={self.params})"