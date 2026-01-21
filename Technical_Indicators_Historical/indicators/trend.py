"""
Trend indicators: Simple Moving Average (SMA) and Exponential Moving Average (EMA)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base_indicator import BaseIndicator


class SMA(BaseIndicator):
    """Simple Moving Average indicator"""

    def __init__(self, period: int = 50, price: str = 'close', displace: int = 0, color: str = '#FF6B6B'):
        """
        Initialize SMA indicator

        Args:
            period: Number of periods for moving average
            price: Price type to use (close, open, high, low, hl2, hlc3, ohlc4)
            displace: Number of periods to displace the indicator
            color: Color for the plot line
        """
        super().__init__(f"SMA_{period}")
        self.params = {
            'period': period,
            'price': price,
            'displace': displace,
            'color': color
        }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate SMA values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with SMA values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for SMA calculation")

        # Get price column
        price_data = self.get_price_column(df, self.params['price'])

        # Calculate SMA
        sma = price_data.rolling(window=self.params['period']).mean()

        # Apply displacement if specified
        if self.params['displace'] != 0:
            sma = sma.shift(self.params['displace'])

        # Store in DataFrame
        result = pd.DataFrame(index=df.index)
        result[self.name] = sma

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for SMA"""
        return {
            'name': self.name,
            'type': 'line',
            'color': self.params['color'],
            'width': 1,
            'panel': 'price',  # Plot on main price panel
            'y_axis': 'price'
        }

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for SMA parameters"""
        return {
            'period': {
                'type': 'slider',
                'label': 'Period',
                'min': 5,
                'max': 500,
                'value': self.params['period'],
                'step': 1
            },
            'price': {
                'type': 'dropdown',
                'label': 'Price',
                'options': [
                    {'label': 'Close', 'value': 'close'},
                    {'label': 'Open', 'value': 'open'},
                    {'label': 'High', 'value': 'high'},
                    {'label': 'Low', 'value': 'low'},
                    {'label': 'HL/2', 'value': 'hl2'},
                    {'label': 'HLC/3', 'value': 'hlc3'},
                    {'label': 'OHLC/4', 'value': 'ohlc4'}
                ],
                'value': self.params['price']
            },
            'displace': {
                'type': 'number',
                'label': 'Displace',
                'value': self.params['displace'],
                'min': -50,
                'max': 50
            },
            'color': {
                'type': 'color',
                'label': 'Color',
                'value': self.params['color']
            }
        }

    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for SMA"""
        return {
            'period': 50,
            'price': 'close',
            'displace': 0,
            'color': '#FF6B6B'
        }


class EMA(BaseIndicator):
    """Exponential Moving Average indicator"""

    def __init__(self, period: int = 20, price: str = 'close', displace: int = 0, color: str = '#4ECDC4'):
        """
        Initialize EMA indicator

        Args:
            period: Number of periods for moving average
            price: Price type to use
            displace: Number of periods to displace the indicator
            color: Color for the plot line
        """
        super().__init__(f"EMA_{period}")
        self.params = {
            'period': period,
            'price': price,
            'displace': displace,
            'color': color
        }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EMA values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with EMA values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for EMA calculation")

        # Get price column
        price_data = self.get_price_column(df, self.params['price'])

        # Calculate EMA
        ema = price_data.ewm(span=self.params['period'], adjust=False).mean()

        # Apply displacement if specified
        if self.params['displace'] != 0:
            ema = ema.shift(self.params['displace'])

        # Store in DataFrame
        result = pd.DataFrame(index=df.index)
        result[self.name] = ema

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for EMA"""
        return {
            'name': self.name,
            'type': 'line',
            'color': self.params['color'],
            'width': 1,
            'panel': 'price',  # Plot on main price panel
            'y_axis': 'price'
        }

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for EMA parameters"""
        return {
            'period': {
                'type': 'slider',
                'label': 'Period',
                'min': 5,
                'max': 200,
                'value': self.params['period'],
                'step': 1
            },
            'price': {
                'type': 'dropdown',
                'label': 'Price',
                'options': [
                    {'label': 'Close', 'value': 'close'},
                    {'label': 'Open', 'value': 'open'},
                    {'label': 'High', 'value': 'high'},
                    {'label': 'Low', 'value': 'low'},
                    {'label': 'HL/2', 'value': 'hl2'},
                    {'label': 'HLC/3', 'value': 'hlc3'},
                    {'label': 'OHLC/4', 'value': 'ohlc4'}
                ],
                'value': self.params['price']
            },
            'displace': {
                'type': 'number',
                'label': 'Displace',
                'value': self.params['displace'],
                'min': -50,
                'max': 50
            },
            'color': {
                'type': 'color',
                'label': 'Color',
                'value': self.params['color']
            }
        }

    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for EMA"""
        return {
            'period': 20,
            'price': 'close',
            'displace': 0,
            'color': '#4ECDC4'
        }


class MultiSMA(BaseIndicator):
    """Multiple SMA lines with different periods"""

    def __init__(self, periods: list = None, price: str = 'close', colors: list = None):
        """
        Initialize Multi-SMA indicator

        Args:
            periods: List of periods for SMAs (default: [50, 200, 720])
            price: Price type to use
            colors: List of colors for each SMA
        """
        super().__init__("MultiSMA")

        if periods is None:
            periods = [50, 200, 720]

        if colors is None:
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']

        # Extend colors if needed
        while len(colors) < len(periods):
            colors.append('#95A5A6')

        self.params = {
            'periods': periods,
            'price': price,
            'colors': colors
        }
        self.sma_indicators = []

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate multiple SMA values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with all SMA values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for Multi-SMA calculation")

        result = pd.DataFrame(index=df.index)

        # Calculate each SMA
        for i, period in enumerate(self.params['periods']):
            color = self.params['colors'][i] if i < len(self.params['colors']) else '#95A5A6'
            sma = SMA(period=period, price=self.params['price'], color=color)
            sma_data = sma.calculate(df)
            result[f'SMA_{period}'] = sma_data[sma.name]
            self.sma_indicators.append(sma)

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for Multi-SMA"""
        configs = []
        for sma in self.sma_indicators:
            config = sma.get_plot_config()
            configs.append(config)
        return configs

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for Multi-SMA parameters"""
        return {
            'sma_50_enabled': {
                'type': 'checkbox',
                'label': 'SMA 50',
                'value': 50 in self.params['periods']
            },
            'sma_50_color': {
                'type': 'color',
                'label': 'SMA 50 Color',
                'value': self.params['colors'][0] if 50 in self.params['periods'] else '#FF6B6B'
            },
            'sma_200_enabled': {
                'type': 'checkbox',
                'label': 'SMA 200',
                'value': 200 in self.params['periods']
            },
            'sma_200_color': {
                'type': 'color',
                'label': 'SMA 200 Color',
                'value': self.params['colors'][1] if 200 in self.params['periods'] else '#4ECDC4'
            },
            'sma_720_enabled': {
                'type': 'checkbox',
                'label': 'SMA 720',
                'value': 720 in self.params['periods']
            },
            'sma_720_color': {
                'type': 'color',
                'label': 'SMA 720 Color',
                'value': self.params['colors'][2] if 720 in self.params['periods'] else '#45B7D1'
            },
            'price': {
                'type': 'dropdown',
                'label': 'Price Source',
                'options': [
                    {'label': 'Close', 'value': 'close'},
                    {'label': 'Open', 'value': 'open'},
                    {'label': 'High', 'value': 'high'},
                    {'label': 'Low', 'value': 'low'},
                    {'label': 'HL/2', 'value': 'hl2'},
                    {'label': 'HLC/3', 'value': 'hlc3'},
                    {'label': 'OHLC/4', 'value': 'ohlc4'}
                ],
                'value': self.params['price']
            }
        }