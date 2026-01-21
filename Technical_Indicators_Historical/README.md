# Technical Indicators Historical Charting System

A comprehensive, interactive charting system for technical analysis with customizable indicators, inspired by Robinhood's interface.

## Features

### Technical Indicators
- **Trend Indicators**
  - Simple Moving Average (SMA) - 50, 200, 720 periods
  - Exponential Moving Average (EMA) - Customizable period

- **Momentum Indicators**
  - RSI (Relative Strength Index) - Customizable period, overbought/oversold levels
  - MACD - Customizable fast/slow/signal periods with histogram
  - AC (Accelerator/Decelerator) - Bill Williams indicator

- **Volatility Indicators**
  - Bollinger Bands - Customizable period and standard deviations

- **Volume Indicators**
  - Volume bars with color coding
  - VWAP (Volume Weighted Average Price) - Multiple anchor periods

### Customizable Parameters
Each indicator has fully customizable parameters including:
- **MACD**: Fast/Slow/Signal lengths, MA type (exponential/simple/weighted/wilders), line colors
- **RSI**: Period, overbought/oversold levels, price source, colors
- **Bollinger Bands**: Period, deviations, price source, MA type
- **SMA/EMA**: Periods, displacement, price source, colors
- **Volume**: Bar colors, MA overlay
- **VWAP**: Anchor period (session/week/month/quarter/year)
- **AC**: Positive/negative colors

### User Interface
- Interactive Dash-based web interface
- Multi-panel layout with separate panels for price, volume, and oscillators
- Real-time parameter adjustment with immediate chart updates
- Toggle indicators on/off
- Color customization for all indicators
- 1-year historical data (configurable: 1mo, 3mo, 6mo, 1y, 2y, 5y)

## Installation

1. Navigate to the Technical_Indicators_Historical folder:
```bash
cd Technical_Indicators_Historical
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python main.py
```

2. Open your browser and navigate to:
```
http://localhost:8050
```

3. Using the interface:
   - Enter a stock ticker (e.g., AAPL, NVDA, TSLA)
   - Select timeframe (1 month to 5 years)
   - Click "Load Data" to fetch historical prices
   - Toggle indicators on/off using the checkboxes
   - Adjust parameters in the "Indicator Parameters" section
   - Chart updates automatically as you change settings

## Project Structure

```
Technical_Indicators_Historical/
├── main.py                      # Entry point
├── requirements.txt             # Dependencies
├── data/
│   ├── data_fetcher.py         # EODHD/YFinance data fetching
│   └── data_cache.py           # Caching layer
├── indicators/
│   ├── base_indicator.py       # Base class for all indicators
│   ├── trend.py                # SMA, EMA implementations
│   ├── momentum.py             # RSI, MACD, AC implementations
│   ├── volatility.py           # Bollinger Bands
│   └── volume.py               # Volume, VWAP
├── visualization/
│   └── chart_builder.py        # Multi-panel Plotly chart builder
├── ui/
│   ├── dash_app.py            # Main Dash application
│   └── components.py          # UI components and controls
└── config/
    └── indicator_defaults.py  # Default parameters
```

## Technical Implementation

### Data Sources
- **Primary**: Yahoo Finance (yfinance) for OHLCV data
- **Backup**: EODHD API for additional data
- **Caching**: Local caching to reduce API calls

### Indicator Calculations
All indicators are manually implemented for full control:
- RSI: Standard 14-period calculation with Wilder's smoothing
- MACD: 12/26/9 EMA with histogram
- Bollinger Bands: 20-period SMA ± 2 standard deviations
- VWAP: Cumulative (price × volume) / cumulative volume
- AC: Awesome Oscillator - SMA(AO, 5)

### Chart Layout
Multi-panel layout using Plotly subplots:
1. **Price Panel** (40% height): Candlesticks, SMA, EMA, Bollinger Bands, VWAP
2. **Volume Panel** (15% height): Volume bars with optional MA
3. **RSI Panel** (15% height): RSI with overbought/oversold zones
4. **MACD Panel** (15% height): MACD, Signal, Histogram
5. **AC Panel** (15% height): Accelerator/Decelerator bars

## Customization

### Adding New Indicators
1. Create indicator class in `indicators/` module
2. Inherit from `BaseIndicator`
3. Implement `calculate()` and `get_plot_config()` methods
4. Add to UI in `dash_app.py`

### Modifying Default Parameters
Edit `config/indicator_defaults.py` to change default values

### Styling
Modify colors and themes in:
- `config/indicator_defaults.py` for indicator colors
- `visualization/chart_builder.py` for chart styling

## API Keys
The system includes an EODHD API key for backup data fetching:
- Key: `67ffece4b2ae08.94077168`
- Primary data source is Yahoo Finance (no key required)

## Requirements
- Python 3.8+
- See `requirements.txt` for full dependency list

## Features Similar to Robinhood
- Stackable indicators on the same chart
- Real-time parameter adjustment
- Clean, modern interface
- Multiple timeframes
- Color customization
- Professional charting with Plotly

## Troubleshooting

### Data not loading?
- Check internet connection
- Verify ticker symbol is valid
- Try different timeframe

### Indicators not showing?
- Ensure data is loaded first
- Check indicator is toggled on
- Verify parameters are valid

### Performance issues?
- Reduce number of active indicators
- Use shorter timeframe
- Clear browser cache

## Future Enhancements
- Real-time data updates
- More indicators (Ichimoku, Stochastic, etc.)
- Pattern recognition
- Alert system
- Strategy backtesting integration
- Export functionality

## License
This project is for educational and research purposes.