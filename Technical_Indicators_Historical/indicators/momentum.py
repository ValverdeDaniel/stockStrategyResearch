"""
Momentum indicators: RSI, MACD, and Accelerator/Decelerator (AC)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base_indicator import BaseIndicator


class RSI(BaseIndicator):
    """Relative Strength Index indicator"""

    def __init__(
        self,
        period: int = 14,
        overbought: float = 70,
        oversold: float = 30,
        price: str = 'close',
        colors: Dict[str, str] = None
    ):
        """
        Initialize RSI indicator

        Args:
            period: Number of periods for RSI calculation
            overbought: Overbought level
            oversold: Oversold level
            price: Price type to use
            colors: Colors for RSI line, overbought, oversold, and fill
        """
        super().__init__("RSI")

        if colors is None:
            colors = {
                'rsi': '#8E44AD',
                'overbought': '#E74C3C',
                'oversold': '#27AE60',
                'fill_overbought': 'rgba(231, 76, 60, 0.2)',
                'fill_oversold': 'rgba(39, 174, 96, 0.2)'
            }

        self.params = {
            'period': period,
            'overbought': overbought,
            'oversold': oversold,
            'price': price,
            'colors': colors
        }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with RSI values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for RSI calculation")

        # Get price column
        price_data = self.get_price_column(df, self.params['price'])

        # Calculate price changes
        delta = price_data.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gain and loss
        avg_gain = gain.rolling(window=self.params['period']).mean()
        avg_loss = loss.rolling(window=self.params['period']).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Store in DataFrame
        result = pd.DataFrame(index=df.index)
        result['RSI'] = rsi
        result['Overbought'] = self.params['overbought']
        result['Oversold'] = self.params['oversold']

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for RSI"""
        return {
            'name': 'RSI',
            'type': 'multi_line',
            'panel': 'rsi',  # Separate panel for RSI
            'y_axis': 'percentage',
            'y_range': [0, 100],
            'lines': [
                {
                    'name': 'RSI',
                    'color': self.params['colors']['rsi'],
                    'width': 2
                },
                {
                    'name': 'Overbought',
                    'color': self.params['colors']['overbought'],
                    'width': 1,
                    'dash': 'dash'
                },
                {
                    'name': 'Oversold',
                    'color': self.params['colors']['oversold'],
                    'width': 1,
                    'dash': 'dash'
                }
            ],
            'fills': [
                {
                    'y0': self.params['overbought'],
                    'y1': 100,
                    'color': self.params['colors']['fill_overbought']
                },
                {
                    'y0': 0,
                    'y1': self.params['oversold'],
                    'color': self.params['colors']['fill_oversold']
                }
            ]
        }

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for RSI parameters"""
        return {
            'period': {
                'type': 'slider',
                'label': 'RSI Length',
                'min': 5,
                'max': 50,
                'value': self.params['period'],
                'step': 1
            },
            'overbought': {
                'type': 'slider',
                'label': 'Overbought Level',
                'min': 60,
                'max': 90,
                'value': self.params['overbought'],
                'step': 5
            },
            'oversold': {
                'type': 'slider',
                'label': 'Oversold Level',
                'min': 10,
                'max': 40,
                'value': self.params['oversold'],
                'step': 5
            },
            'price': {
                'type': 'dropdown',
                'label': 'Price Source',
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
            'rsi_color': {
                'type': 'color',
                'label': 'RSI Line Color',
                'value': self.params['colors']['rsi']
            },
            'overbought_color': {
                'type': 'color',
                'label': 'Overbought Color',
                'value': self.params['colors']['overbought']
            },
            'oversold_color': {
                'type': 'color',
                'label': 'Oversold Color',
                'value': self.params['colors']['oversold']
            }
        }


class MACD(BaseIndicator):
    """Moving Average Convergence Divergence indicator"""

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        ma_type: str = 'exponential',
        colors: Dict[str, str] = None
    ):
        """
        Initialize MACD indicator

        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line EMA period
            ma_type: Moving average type (exponential, simple, weighted, wilders)
            colors: Colors for MACD line, signal line, and histogram
        """
        super().__init__("MACD")

        if colors is None:
            colors = {
                'macd': '#3498DB',
                'signal': '#E67E22',
                'histogram_positive': '#27AE60',
                'histogram_negative': '#E74C3C'
            }

        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'ma_type': ma_type,
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
            # Wilder's smoothing (used in RSI)
            return data.ewm(alpha=1/period, adjust=False).mean()
        else:
            # Default to exponential
            return data.ewm(span=period, adjust=False).mean()

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with MACD values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for MACD calculation")

        # Use close price for MACD
        close = df['close']

        # Calculate MACD components
        fast_ma = self._calculate_ma(close, self.params['fast_period'], self.params['ma_type'])
        slow_ma = self._calculate_ma(close, self.params['slow_period'], self.params['ma_type'])

        macd_line = fast_ma - slow_ma
        signal_line = self._calculate_ma(macd_line, self.params['signal_period'], self.params['ma_type'])
        histogram = macd_line - signal_line

        # Store in DataFrame
        result = pd.DataFrame(index=df.index)
        result['MACD'] = macd_line
        result['Signal'] = signal_line
        result['Histogram'] = histogram

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for MACD"""
        return {
            'name': 'MACD',
            'type': 'multi_trace',
            'panel': 'macd',  # Separate panel for MACD
            'y_axis': 'value',
            'traces': [
                {
                    'name': 'MACD',
                    'type': 'line',
                    'color': self.params['colors']['macd'],
                    'width': 2
                },
                {
                    'name': 'Signal',
                    'type': 'line',
                    'color': self.params['colors']['signal'],
                    'width': 1
                },
                {
                    'name': 'Histogram',
                    'type': 'bar',
                    'color_positive': self.params['colors']['histogram_positive'],
                    'color_negative': self.params['colors']['histogram_negative']
                }
            ]
        }

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for MACD parameters"""
        return {
            'fast_period': {
                'type': 'number',
                'label': 'Fast Length',
                'value': self.params['fast_period'],
                'min': 5,
                'max': 50
            },
            'slow_period': {
                'type': 'number',
                'label': 'Slow Length',
                'value': self.params['slow_period'],
                'min': 10,
                'max': 100
            },
            'signal_period': {
                'type': 'number',
                'label': 'Signal Length',
                'value': self.params['signal_period'],
                'min': 5,
                'max': 30
            },
            'ma_type': {
                'type': 'dropdown',
                'label': 'Average Type',
                'options': [
                    {'label': 'Exponential', 'value': 'exponential'},
                    {'label': 'Simple', 'value': 'simple'},
                    {'label': 'Weighted', 'value': 'weighted'},
                    {'label': 'Wilders', 'value': 'wilders'}
                ],
                'value': self.params['ma_type']
            },
            'macd_color': {
                'type': 'color',
                'label': 'MACD Line Color',
                'value': self.params['colors']['macd']
            },
            'signal_color': {
                'type': 'color',
                'label': 'Signal Line Color',
                'value': self.params['colors']['signal']
            },
            'histogram_positive_color': {
                'type': 'color',
                'label': 'Histogram Positive',
                'value': self.params['colors']['histogram_positive']
            },
            'histogram_negative_color': {
                'type': 'color',
                'label': 'Histogram Negative',
                'value': self.params['colors']['histogram_negative']
            }
        }


class AC(BaseIndicator):
    """Accelerator/Decelerator Oscillator indicator"""

    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 34,
        signal_period: int = 5,
        colors: Dict[str, str] = None
    ):
        """
        Initialize AC indicator

        Args:
            fast_period: Fast SMA period for Awesome Oscillator
            slow_period: Slow SMA period for Awesome Oscillator
            signal_period: SMA period for AC calculation
            colors: Colors for positive and negative values
        """
        super().__init__("AC")

        if colors is None:
            colors = {
                'positive': '#27AE60',
                'negative': '#E74C3C'
            }

        self.params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'colors': colors
        }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate AC values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with AC values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for AC calculation")

        # Calculate median price (HL/2)
        median_price = (df['high'] + df['low']) / 2

        # Calculate Awesome Oscillator (AO)
        fast_sma = median_price.rolling(window=self.params['fast_period']).mean()
        slow_sma = median_price.rolling(window=self.params['slow_period']).mean()
        ao = fast_sma - slow_sma

        # Calculate AC = AO - SMA(AO, signal_period)
        ao_sma = ao.rolling(window=self.params['signal_period']).mean()
        ac = ao - ao_sma

        # Store in DataFrame
        result = pd.DataFrame(index=df.index)
        result['AC'] = ac
        result['AO'] = ao  # Store AO for reference

        # Add color coding based on value and change
        result['AC_Color'] = 'green'
        result.loc[ac < 0, 'AC_Color'] = 'red'

        # Enhanced coloring: brighter if accelerating
        ac_diff = ac.diff()
        result.loc[(ac > 0) & (ac_diff > 0), 'AC_Color'] = 'bright_green'
        result.loc[(ac < 0) & (ac_diff < 0), 'AC_Color'] = 'bright_red'

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for AC"""
        return {
            'name': 'AC',
            'type': 'bar',
            'panel': 'ac',  # Separate panel for AC
            'y_axis': 'value',
            'color_map': {
                'green': self.params['colors']['positive'],
                'red': self.params['colors']['negative'],
                'bright_green': '#2ECC71',  # Brighter green
                'bright_red': '#C0392B'  # Brighter red
            },
            'zero_line': True
        }

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for AC parameters"""
        return {
            'fast_period': {
                'type': 'number',
                'label': 'Fast Period',
                'value': self.params['fast_period'],
                'min': 3,
                'max': 20
            },
            'slow_period': {
                'type': 'number',
                'label': 'Slow Period',
                'value': self.params['slow_period'],
                'min': 20,
                'max': 100
            },
            'signal_period': {
                'type': 'number',
                'label': 'Signal Period',
                'value': self.params['signal_period'],
                'min': 3,
                'max': 20
            },
            'positive_color': {
                'type': 'color',
                'label': 'Positive Color',
                'value': self.params['colors']['positive']
            },
            'negative_color': {
                'type': 'color',
                'label': 'Negative Color',
                'value': self.params['colors']['negative']
            }
        }

    def get_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on AC

        Args:
            df: DataFrame with AC values

        Returns:
            DataFrame with buy/sell signals
        """
        if self.data is None:
            self.calculate(df)

        signals = pd.DataFrame(index=df.index)
        ac = self.data['AC']

        # Signal when AC crosses zero
        signals['signal'] = 0
        signals.loc[(ac > 0) & (ac.shift(1) <= 0), 'signal'] = 1  # Buy signal
        signals.loc[(ac < 0) & (ac.shift(1) >= 0), 'signal'] = -1  # Sell signal

        return signals