# MACD Analysis Tools

This folder contains comprehensive MACD (Moving Average Convergence Divergence) analysis tools for stock market research.

## Files Overview

### Core Python Scripts

1. **`fundamentals_macd.py`**
   - Main MACD analysis tool
   - Calculates 25 comprehensive MACD metrics including:
     - Basic MACD values (MACD, Signal, Histogram)
     - Normalized metrics for cross-stock comparison
     - Crossover detection and timing
     - Momentum and trend analysis
     - **MACD Scoring System (NEW):**
       - Bullish Score (0-100)
       - Bearish Score (0-100)
       - Net Score (-100 to +100)
   - Generates current snapshot analysis for multiple stocks
   - Outputs: Console display + CSV file

2. **`fundamentals_macd_historical.py`**
   - Historical MACD analysis and backtesting system
   - Features:
     - Calculates daily historical MACD scores
     - Backtests multiple trading strategies
     - Interactive Plotly visualizations
     - Parameter optimization
     - Performance metrics (Sharpe ratio, win rate, drawdown)
   - Outputs per stock:
     - HTML report with interactive charts
     - CSV with historical scores
     - CSV with trade log
     - JSON with performance metrics

## Usage

### Current MACD Analysis
```bash
# Run from this directory
python fundamentals_macd.py

# The ticker list is at line 1534-1538 in main() function
# Modify the list to analyze your desired stocks
```

### Historical Analysis
```bash
# Single stock
python fundamentals_macd_historical.py --ticker AAPL --period 6M

# Multiple stocks
python fundamentals_macd_historical.py --tickers AAPL,MSFT,NVDA --period 1Y

# With parameter optimization
python fundamentals_macd_historical.py --ticker AAPL --period 3M --optimize
```

## Output Files

### From `fundamentals_macd.py`:
- `fundamentals_macd_output.csv` - Current analysis for all stocks

### From `fundamentals_macd_historical.py`:
- `{TICKER}_macd_historical_report.html` - Interactive report
- `{TICKER}_macd_historical_scores.csv` - Daily historical scores
- `{TICKER}_macd_historical_trades.csv` - Trade log
- `{TICKER}_macd_performance.json` - Performance metrics

## MACD Scoring System

### Bullish Score (0-100)
Components:
- Position & Strength (35 pts): MACD above signal + Z-score
- Crossover Timing (30 pts): How recent was bullish cross
- Momentum Direction (20 pts): Trend and acceleration
- Quality & Opportunity (15 pts): Signal quality

### Bearish Score (0-100)
Mirror structure for bearish signals

### Net Score (-100 to +100)
- Net = Bullish - Bearish
- +50 to +100: Strong bullish signal
- -50 to -100: Strong bearish signal
- -20 to +20: Neutral/transition zone

## Trading Strategy (Default)

**Adaptive Zone Strategy:**
- **Entry:** Bullish Score > 60 AND Net Score > 30
- **Exit:** Bearish Score > 60 OR Net Score < -10 OR 15% profit OR 5% stop loss
- **Minimum Hold:** 3 days (avoid whipsaws)

## Configuration

Key parameters can be adjusted at the top of each file:
- MACD periods (12, 26, 9)
- Score thresholds
- Trading strategy parameters
- Analysis timeframes

## Dependencies

- pandas
- numpy
- requests
- plotly (for historical analysis)
- Python 3.7+

## API

Uses EODHD API for market data (API token included in scripts)