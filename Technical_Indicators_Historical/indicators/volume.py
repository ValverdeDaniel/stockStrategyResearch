"""
Volume indicators: Volume bars and VWAP (Volume Weighted Average Price)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base_indicator import BaseIndicator


class Volume(BaseIndicator):
    """Volume bars indicator"""

    def __init__(
        self,
        colors: Dict[str, str] = None,
        show_ma: bool = False,
        ma_period: int = 20
    ):
        """
        Initialize Volume indicator

        Args:
            colors: Colors for up and down volume bars
            show_ma: Whether to show volume moving average
            ma_period: Period for volume moving average
        """
        super().__init__("Volume")

        if colors is None:
            colors = {
                'up': '#27AE60',
                'down': '#E74C3C',
                'ma': '#3498DB'
            }

        self.params = {
            'colors': colors,
            'show_ma': show_ma,
            'ma_period': ma_period
        }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume data with color coding

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with volume and color information
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for Volume calculation")

        # Store volume data
        result = pd.DataFrame(index=df.index)
        result['Volume'] = df['volume']

        # Determine color based on price movement
        result['Volume_Color'] = self.params['colors']['up']
        result.loc[df['close'] < df['open'], 'Volume_Color'] = self.params['colors']['down']

        # Calculate volume moving average if requested
        if self.params['show_ma']:
            result['Volume_MA'] = df['volume'].rolling(window=self.params['ma_period']).mean()

        # Calculate volume metrics
        result['Volume_Ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()
        result['Volume_Percentile'] = df['volume'].rolling(window=50).rank(pct=True)

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for Volume"""
        config = {
            'name': 'Volume',
            'type': 'bar',
            'panel': 'volume',  # Separate panel for volume
            'y_axis': 'volume',
            'traces': [
                {
                    'name': 'Volume',
                    'type': 'bar',
                    'color_column': 'Volume_Color'
                }
            ]
        }

        if self.params['show_ma']:
            config['traces'].append({
                'name': 'Volume MA',
                'type': 'line',
                'color': self.params['colors']['ma'],
                'width': 1
            })

        return config

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for Volume parameters"""
        return {
            'up_color': {
                'type': 'color',
                'label': 'Up Volume Color',
                'value': self.params['colors']['up']
            },
            'down_color': {
                'type': 'color',
                'label': 'Down Volume Color',
                'value': self.params['colors']['down']
            },
            'show_ma': {
                'type': 'checkbox',
                'label': 'Show Volume MA',
                'value': self.params['show_ma']
            },
            'ma_period': {
                'type': 'slider',
                'label': 'MA Period',
                'min': 5,
                'max': 50,
                'value': self.params['ma_period'],
                'step': 1,
                'disabled': not self.params['show_ma']
            },
            'ma_color': {
                'type': 'color',
                'label': 'MA Color',
                'value': self.params['colors']['ma'],
                'disabled': not self.params['show_ma']
            }
        }


class VWAP(BaseIndicator):
    """Volume Weighted Average Price indicator"""

    def __init__(
        self,
        anchor: str = 'session',
        show_bands: bool = False,
        band_multiplier: float = 1.0,
        colors: Dict[str, str] = None
    ):
        """
        Initialize VWAP indicator

        Args:
            anchor: Anchor period ('session', 'week', 'month', 'quarter', 'year')
            show_bands: Whether to show standard deviation bands
            band_multiplier: Multiplier for standard deviation bands
            colors: Colors for VWAP line and bands
        """
        super().__init__("VWAP")

        if colors is None:
            colors = {
                'vwap': '#9B59B6',
                'upper_band': '#E74C3C',
                'lower_band': '#27AE60',
                'fill': 'rgba(155, 89, 182, 0.1)'
            }

        self.params = {
            'anchor': anchor,
            'show_bands': show_bands,
            'band_multiplier': band_multiplier,
            'colors': colors
        }

    def _get_anchor_groups(self, df: pd.DataFrame) -> pd.Series:
        """
        Get grouping based on anchor period

        Args:
            df: DataFrame with datetime index

        Returns:
            Series with group identifiers
        """
        if self.params['anchor'] == 'session':
            # Daily VWAP (resets each day)
            return df.index.date
        elif self.params['anchor'] == 'week':
            # Weekly VWAP
            return df.index.to_period('W')
        elif self.params['anchor'] == 'month':
            # Monthly VWAP
            return df.index.to_period('M')
        elif self.params['anchor'] == 'quarter':
            # Quarterly VWAP
            return df.index.to_period('Q')
        elif self.params['anchor'] == 'year':
            # Yearly VWAP
            return df.index.to_period('Y')
        else:
            # Default to daily
            return df.index.date

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate VWAP values

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with VWAP values
        """
        if not self.validate_data(df):
            raise ValueError("Invalid data for VWAP calculation")

        # Calculate typical price (HLC/3)
        typical_price = (df['high'] + df['low'] + df['close']) / 3

        # Get anchor groups
        groups = self._get_anchor_groups(df)

        # Initialize result DataFrame
        result = pd.DataFrame(index=df.index)

        # Calculate VWAP for each group
        vwap_values = []
        cumulative_pv = []
        cumulative_volume = []

        # Get unique groups (convert to pandas Series if needed)
        if hasattr(groups, 'unique'):
            unique_groups = groups.unique()
        else:
            unique_groups = pd.Series(groups).unique()

        for group in unique_groups:
            mask = groups == group
            group_df = df[mask]
            group_tp = typical_price[mask]
            group_volume = group_df['volume']

            # Calculate cumulative price*volume and cumulative volume
            cum_pv = (group_tp * group_volume).cumsum()
            cum_vol = group_volume.cumsum()

            # Calculate VWAP
            group_vwap = cum_pv / cum_vol

            vwap_values.extend(group_vwap.values)
            cumulative_pv.extend(cum_pv.values)
            cumulative_volume.extend(cum_vol.values)

        result['VWAP'] = vwap_values

        # Calculate standard deviation bands if requested
        if self.params['show_bands']:
            # Calculate squared deviations
            squared_diff = []
            vwap_series = pd.Series(vwap_values, index=df.index)

            for group in unique_groups:
                mask = groups == group
                group_tp = typical_price[mask]
                group_volume = df[mask]['volume']
                group_vwap = vwap_series[mask]

                # Calculate variance
                deviation = group_tp - group_vwap
                weighted_sq_dev = deviation ** 2 * group_volume
                cum_weighted_sq_dev = weighted_sq_dev.cumsum()
                cum_vol = group_volume.cumsum()

                # Standard deviation
                variance = cum_weighted_sq_dev / cum_vol
                std_dev = np.sqrt(variance)

                squared_diff.extend(std_dev.values)

            result['VWAP_StdDev'] = squared_diff
            result['VWAP_Upper'] = result['VWAP'] + (result['VWAP_StdDev'] * self.params['band_multiplier'])
            result['VWAP_Lower'] = result['VWAP'] - (result['VWAP_StdDev'] * self.params['band_multiplier'])

        self.data = result
        return result

    def get_plot_config(self) -> Dict[str, Any]:
        """Get plot configuration for VWAP"""
        config = {
            'name': 'VWAP',
            'type': 'multi_trace',
            'panel': 'price',  # Plot on main price panel
            'y_axis': 'price',
            'traces': [
                {
                    'name': 'VWAP',
                    'type': 'line',
                    'color': self.params['colors']['vwap'],
                    'width': 2
                }
            ]
        }

        if self.params['show_bands']:
            config['traces'].extend([
                {
                    'name': 'VWAP Upper',
                    'type': 'line',
                    'color': self.params['colors']['upper_band'],
                    'width': 1,
                    'dash': 'dash'
                },
                {
                    'name': 'VWAP Lower',
                    'type': 'line',
                    'color': self.params['colors']['lower_band'],
                    'width': 1,
                    'dash': 'dash'
                }
            ])
            config['fill'] = {
                'between': ['VWAP_Upper', 'VWAP_Lower'],
                'color': self.params['colors']['fill']
            }

        return config

    def get_parameter_controls(self) -> Dict[str, Any]:
        """Get UI controls for VWAP parameters"""
        return {
            'anchor': {
                'type': 'dropdown',
                'label': 'Anchor Period',
                'options': [
                    {'label': 'Session (Daily)', 'value': 'session'},
                    {'label': 'Week', 'value': 'week'},
                    {'label': 'Month', 'value': 'month'},
                    {'label': 'Quarter', 'value': 'quarter'},
                    {'label': 'Year', 'value': 'year'}
                ],
                'value': self.params['anchor']
            },
            'show_bands': {
                'type': 'checkbox',
                'label': 'Show Bands',
                'value': self.params['show_bands']
            },
            'band_multiplier': {
                'type': 'number',
                'label': 'Band Multiplier',
                'value': self.params['band_multiplier'],
                'min': 0.5,
                'max': 3.0,
                'step': 0.5,
                'disabled': not self.params['show_bands']
            },
            'vwap_color': {
                'type': 'color',
                'label': 'VWAP Color',
                'value': self.params['colors']['vwap']
            },
            'upper_band_color': {
                'type': 'color',
                'label': 'Upper Band Color',
                'value': self.params['colors']['upper_band'],
                'disabled': not self.params['show_bands']
            },
            'lower_band_color': {
                'type': 'color',
                'label': 'Lower Band Color',
                'value': self.params['colors']['lower_band'],
                'disabled': not self.params['show_bands']
            }
        }

    def get_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on VWAP

        Args:
            df: DataFrame with price data

        Returns:
            DataFrame with buy/sell signals
        """
        if self.data is None:
            self.calculate(df)

        signals = pd.DataFrame(index=df.index)
        price = df['close']

        # Buy signal when price crosses above VWAP
        # Sell signal when price crosses below VWAP
        signals['signal'] = 0
        signals.loc[(price > self.data['VWAP']) & (price.shift(1) <= self.data['VWAP'].shift(1)), 'signal'] = 1
        signals.loc[(price < self.data['VWAP']) & (price.shift(1) >= self.data['VWAP'].shift(1)), 'signal'] = -1

        return signals