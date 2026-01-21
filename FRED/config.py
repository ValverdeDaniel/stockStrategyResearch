"""
FRED API Configuration File
"""

# FRED API Configuration
# Get your free API key from: https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY = "YOUR_FRED_API_KEY_HERE"  # Replace with your actual FRED API key

# FRED Series IDs for Economic Indicators
FRED_SERIES_IDS = {
    'gdp': 'GDP',                           # Gross Domestic Product (Nominal, Quarterly)
    'unemployment': 'UNRATE',               # Unemployment Rate (Monthly)
    'real_potential_gdp': 'GDPPOT',        # Real Potential GDP (Quarterly)
    'real_gdp_per_capita': 'A939RX0Q048SBEA',  # Real GDP per Capita (Quarterly)
    'nominal_potential_gdp': 'NGDPPOT',    # Nominal Potential GDP (Quarterly)
    'cpi': 'CPIAUCSL',                     # Consumer Price Index (Monthly)
    'pce': 'PCEPI',                        # Personal Consumption Expenditures (Monthly)

    # Additional useful series
    'real_gdp': 'GDPC1',                   # Real GDP (Quarterly)
    'core_cpi': 'CPILFESL',                # Core CPI excluding food and energy (Monthly)
    'core_pce': 'PCEPILFE',                # Core PCE Price Index (Monthly)
}

# Default date range for data fetching
DEFAULT_START_DATE = '2000-01-01'
DEFAULT_END_DATE = None  # None means fetch up to most recent data

# Caching configuration
ENABLE_CACHE = True
CACHE_EXPIRY_HOURS = 24  # Cache expires after 24 hours

# Output settings
OUTPUT_FORMAT = 'html'  # Options: 'html', 'png', 'svg'
AUTO_OPEN_BROWSER = False  # Whether to auto-open HTML files in browser

# Visualization settings
PLOT_THEME = 'plotly_white'  # Plotly theme
FIGURE_WIDTH = 1200
FIGURE_HEIGHT = 700

# Data directory
DATA_CACHE_DIR = 'FRED/data/cache/'