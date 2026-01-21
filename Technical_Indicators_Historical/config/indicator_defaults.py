"""
Default parameters for all technical indicators
"""

INDICATOR_DEFAULTS = {
    'SMA': {
        'periods': [50, 200, 720],
        'price': 'close',
        'displace': 0,
        'colors': ['#FF6B6B', '#4ECDC4', '#45B7D1']
    },
    'EMA': {
        'period': 20,
        'price': 'close',
        'displace': 0,
        'color': '#4ECDC4'
    },
    'RSI': {
        'period': 14,
        'overbought': 70,
        'oversold': 30,
        'price': 'close',
        'colors': {
            'rsi': '#8E44AD',
            'overbought': '#E74C3C',
            'oversold': '#27AE60',
            'fill_overbought': 'rgba(231, 76, 60, 0.2)',
            'fill_oversold': 'rgba(39, 174, 96, 0.2)'
        }
    },
    'MACD': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9,
        'ma_type': 'exponential',
        'colors': {
            'macd': '#3498DB',
            'signal': '#E67E22',
            'histogram_positive': '#27AE60',
            'histogram_negative': '#E74C3C'
        }
    },
    'BollingerBands': {
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
    },
    'Volume': {
        'colors': {
            'up': '#27AE60',
            'down': '#E74C3C',
            'ma': '#3498DB'
        },
        'show_ma': False,
        'ma_period': 20
    },
    'VWAP': {
        'anchor': 'session',
        'show_bands': False,
        'band_multiplier': 1.0,
        'colors': {
            'vwap': '#9B59B6',
            'upper_band': '#E74C3C',
            'lower_band': '#27AE60',
            'fill': 'rgba(155, 89, 182, 0.1)'
        }
    },
    'AC': {
        'fast_period': 5,
        'slow_period': 34,
        'signal_period': 5,
        'colors': {
            'positive': '#27AE60',
            'negative': '#E74C3C'
        }
    }
}

# Chart appearance settings
CHART_SETTINGS = {
    'theme': 'plotly_white',
    'height': 800,
    'candlestick_colors': {
        'increasing': '#27AE60',
        'decreasing': '#E74C3C'
    },
    'grid': {
        'show': True,
        'color': 'lightgray',
        'width': 1
    },
    'margins': {
        'l': 50,
        'r': 50,
        't': 80,
        'b': 50
    }
}

# Panel configuration
PANEL_CONFIG = {
    'price': {
        'height_ratio': 0.4,
        'title': 'Price'
    },
    'volume': {
        'height_ratio': 0.15,
        'title': 'Volume'
    },
    'rsi': {
        'height_ratio': 0.15,
        'title': 'RSI',
        'y_range': [0, 100]
    },
    'macd': {
        'height_ratio': 0.15,
        'title': 'MACD'
    },
    'ac': {
        'height_ratio': 0.15,
        'title': 'Accelerator/Decelerator'
    }
}

# Timeframe configurations
TIMEFRAME_CONFIG = {
    '1mo': {'days': 30, 'label': '1 Month'},
    '3mo': {'days': 90, 'label': '3 Months'},
    '6mo': {'days': 180, 'label': '6 Months'},
    '1y': {'days': 365, 'label': '1 Year'},
    '2y': {'days': 730, 'label': '2 Years'},
    '5y': {'days': 1825, 'label': '5 Years'}
}

# API configurations
API_CONFIG = {
    'eodhd': {
        'api_key': '67ffece4b2ae08.94077168',
        'base_url': 'https://eodhd.com/api',
        'timeout': 30
    },
    'yfinance': {
        'default_interval': '1d',
        'max_retries': 3
    }
}