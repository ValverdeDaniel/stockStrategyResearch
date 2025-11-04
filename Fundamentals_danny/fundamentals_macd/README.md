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

3. **`fundamentals_macd_robust.py`**
   - Robust principle-based MACD strategy to avoid overfitting
   - Features:
     - Adaptive thresholds using rolling percentiles
     - Market regime detection
     - Walk-forward analysis
     - Monte Carlo simulation
     - Cross-validation across multiple stocks

4. **`fundamentals_macd_rsi_scaling.py`** ⭐ NEW
   - Advanced MACD+RSI strategy with position scaling
   - Features:
     - **RSI Integration**: Entry on oversold conditions (RSI < 50)
     - **Position Scaling**: Start with 10%, scale up to 100%
     - **Scaling Levels**:
       - -5%: Add 10% (total 20%)
       - -10%: Add 30% (total 50%)
       - -20%: Add 25% (total 75%)
       - -30%: Add 25% (total 100%)
     - **Weighted Cost Basis**: Tracks average entry price
     - **Smart Exits**: Based on RSI overbought or MACD bearish
   - Benefits:
     - Reduces timing risk through averaging
     - Improves cost basis on weakness
     - Higher returns with controlled risk
   - Results with AAPL (1Y):
     - Total Return: +1.46% (vs -9.26% without scaling)
     - Cost Improvement: 10.56% when scaling triggered
     - Win Rate: 50%

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

### MACD+RSI with Position Scaling
```bash
# Run scaling strategy backtest
python fundamentals_macd_rsi_scaling.py --ticker AAPL --period 1Y

# Different time periods
python fundamentals_macd_rsi_scaling.py --ticker MSFT --period 6M
python fundamentals_macd_rsi_scaling.py --ticker NVDA --period 3M

# Custom output prefix
python fundamentals_macd_rsi_scaling.py --ticker AAPL --period 1Y --output AAPL_test
```

## Output Files

### From `fundamentals_macd.py`:
- `fundamentals_macd_output.csv` - Current analysis for all stocks

### From `fundamentals_macd_historical.py`:
- `{TICKER}_macd_historical_report.html` - Interactive report
- `{TICKER}_macd_historical_scores.csv` - Daily historical scores
- `{TICKER}_macd_historical_trades.csv` - Trade log
- `{TICKER}_macd_performance.json` - Performance metrics

### From `fundamentals_macd_rsi_scaling.py`:
- `{TICKER}_scaling_report.html` - Interactive report with scaling visualization
- `{TICKER}_scaling_trades.csv` - Detailed trade log with tranches
- `{TICKER}_scaling_metrics.json` - Performance metrics including scaling stats

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