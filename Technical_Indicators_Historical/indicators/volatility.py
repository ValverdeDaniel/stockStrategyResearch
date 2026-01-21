"""
Volatility indicators: Bollinger Bands
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base_indicator import BaseIndicator


class BollingerBands(BaseIndicator):
    """Bollinger Bands indicator"""

    def __init__(
        self,
        period: int = 20,
        std_dev_upper: float = 2.0,
        std_dev_lower: float = 2.0,
        price: str = 'close',
        ma_type: str = 'simple',
        displace: int = 0,
        colors: Dict[str, str] = None
    ):
        """
        Initialize Bollinger Bands indicator

        Args:
            period: Number of periods for moving average
            std_dev_upper: Number of standard deviations for upper band
            std_dev_lower: Number of standard deviations for lower band
            price: Price type to use
            ma_type: Moving average type (simple, exponential, weighted, wilders)
            displace: Number of periods to displace the bands
            colors: Colors for upper, middle, and lower bands
        """
        super().__init__("BollingerBands")

        if colors is None:
            colors = {
                'upper': '#E74C3C',
                'middle': '#95A5A6',
                'lower': '#27AE60',
                'fill': 'rgba(149, 165, 166, 0.1)'
            }

        self.params = {
            'period': period,
            'std_dev_upper': std_dev_upper,
            'std_dev_lower': std_dev_lower,
            'price': price,
            'ma_type': ma_type,
            'displace': displace,
            'colors': colors
        }

    def _calculate_ma(self, data: pd.Series, period: int, ma_type: str) -> pd.Series:
        """
        Calculate moving average based on type

        Args:
            data: Price series
            period: MA period
            ma_type: Type of MA

        Returns:
            Moving average series
        """
        if ma_type == 'simple':
            return data.rolling(window=period).mean()
        elif ma_type == 'exponential':
            return data.ewm(span=period, adjust=False).mean()
        elif ma_type == 'weighted':
            weights = np.arange(1, period + 1)
            return data.rolling(period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )
        elif ma_type == 'wilders':
            return data.ewm(alpha=1/period, adjust=False).mean()
        else:
            # Default to simple
            return data.rolling(window=period).mean()

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Bollinger Bands values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with Bollinger Bands values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for Bollinger Bands calculation")

        # Get price column
        price_data = self.get_price_column(df, self.params['price'])

        # Calculate middle band (moving average)
        middle_band = self._calculate_ma(price_data, self.params['period'], self.params['ma_type'])

        # Calculate standard deviation
        std_dev = price_data.rolling(window=self.params['period']).std()

        # Calculate upper and lower bands
        upper_band = middle_band + (std_dev * self.params['std_dev_upper'])
        lower_band = middle_band - (std_dev * self.params['std_dev_lower'])

        # Apply displacement if specified
        if self.params['displace'] != 0:
            upper_band = upper_band.shift(self.params['displace'])
            middle_band = middle_band.shift(self.params['displace'])
            lower_band = lower_band.shift(self.params['displace'])

        # Calculate band width and %B for additional analysis
        band_width = upper_band - lower_band
        percent_b = (price_data - lower_band) / (upper_band - lower_band)

        # Store in DataFrame
        result = pd.DataFrame(index=df.index)
        result['BB_Upper'] = upper_band
        result['BB_Middle'] = middle_band
        result['BB_Lower'] = lower_band
        result['BB_Width'] = band_width
        result['BB_PercentB'] = percent_b

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for Bollinger Bands"""
        return {
            'name': 'BollingerBands',
            'type': 'bands',
            'panel': 'price',  # Plot on main price panel
            'y_axis': 'price',
            'traces': [
                {
                    'name': 'Upper Band',
                    'type': 'line',
                    'color': self.params['colors']['upper'],
                    'width': 1,
                    'dash': 'dot'
                },
                {
                    'name': 'Middle Band',
                    'type': 'line',
                    'color': self.params['colors']['middle'],
                    'width': 1
                },
                {
                    'name': 'Lower Band',
                    'type': 'line',
                    'color': self.params['colors']['lower'],
                    'width': 1,
                    'dash': 'dot'
                }
            ],
            'fill': {
                'between': ['BB_Upper', 'BB_Lower'],
                'color': self.params['colors']['fill']
            }
        }

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for Bollinger Bands parameters"""
        return {
            'period': {
                'type': 'slider',
                'label': 'Length',
                'min': 5,
                'max': 100,
                'value': self.params['period'],
                'step': 1
            },
            'std_dev_upper': {
                'type': 'number',
                'label': '# Deviations Above',
                'value': self.params['std_dev_upper'],
                'min': 0.5,
                'max': 4.0,
                'step': 0.5
            },
            'std_dev_lower': {
                'type': 'number',
                'label': '# Deviations Below',
                'value': self.params['std_dev_lower'],
                'min': 0.5,
                'max': 4.0,
                'step': 0.5
            },
            'price': {
                'type': 'dropdown',
                'label': 'Price',
                'options': [
                    {'label': 'Close', 'value': 'close'},
                    {'label': 'Open', 'value': 'open'},
                    {'label': 'OHLC Average', 'value': 'ohlc4'},
                    {'label': 'High', 'value': 'high'},
                    {'label': 'Low', 'value': 'low'},
                    {'label': 'Median (HL/2)', 'value': 'hl2'}
                ],
                'value': self.params['price']
            },
            'ma_type': {
                'type': 'dropdown',
                'label': 'Average',
                'options': [
                    {'label': 'Simple', 'value': 'simple'},
                    {'label': 'Exponential', 'value': 'exponential'},
                    {'label': 'Weighted', 'value': 'weighted'},
                    {'label': 'Wilders', 'value': 'wilders'}
                ],
                'value': self.params['ma_type']
            },
            'displace': {
                'type': 'number',
                'label': 'Displace',
                'value': self.params['displace'],
                'min': -50,
                'max': 50
            },
            'upper_color': {
                'type': 'color',
                'label': 'Upper Band Color',
                'value': self.params['colors']['upper']
            },
            'middle_color': {
                'type': 'color',
                'label': 'Middle Band Color',
                'value': self.params['colors']['middle']
            },
            'lower_color': {
                'type': 'color',
                'label': 'Lower Band Color',
                'value': self.params['colors']['lower']
            }
        }

    def get_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on Bollinger Bands

        Args:
            df: DataFrame with price data

        Returns:
            DataFrame with buy/sell signals
        """
        if self.data is None:
            self.calculate(df)

        signals = pd.DataFrame(index=df.index)
        price = self.get_price_column(df, self.params['price'])

        # Buy signal when price touches lower band
        # Sell signal when price touches upper band
        signals['signal'] = 0
        signals.loc[price <= self.data['BB_Lower'], 'signal'] = 1  # Buy
        signals.loc[price >= self.data['BB_Upper'], 'signal'] = -1  # Sell

        # Alternative strategy: Mean reversion
        # Buy when %B < 0 (below lower band)
        # Sell when %B > 1 (above upper band)
        signals['mean_reversion'] = 0
        signals.loc[self.data['BB_PercentB'] < 0, 'mean_reversion'] = 1
        signals.loc[self.data['BB_PercentB'] > 1, 'mean_reversion'] = -1

        return signals

    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for Bollinger Bands"""
        return {
            'period': 20,
            'std_dev_upper': 2.0,
            'std_dev_lower': 2.0,
            'price': 'close',
            'ma_type': 'simple',
            'displace': 0,
            'colors': {
                'upper': '#E74C3C',
                'middle': '#95A5A6',
                'lower': '#27AE60',
                'fill': 'rgba(149, 165, 166, 0.1)'
            }
        }