# Algorithmic Trendline Detection - User Guide

## Overview

This project implements an algorithmic trendline detection system that automatically identifies support and resistance trendlines in stock price data. The algorithm analyzes price pivots (peaks and troughs) and uses mathematical precision to find statistically significant trendlines.

**Key Features:**
- Removes subjective bias in drawing trendlines
- Ranks trendlines by statistical strength (more touches = higher confidence)
- Detects breakouts automatically with buffer zones
- Adapts to each asset's volatility

## Project Structure

```
chart_infos/
├── data/
│   ├── fetcher.py          # Script to fetch stock data from Yahoo Finance
│   └── *.csv               # Downloaded stock data files
├── pytrendline/
│   ├── __init__.py
│   ├── detect.py           # Core trendline detection algorithm
│   ├── plot.py             # Visualization functions
│   ├── structs.py          # Data structures
│   ├── util.py             # Utility functions
│   └── bokeh_cursor_deltas.py
├── test_cursor.py          # Main script to run trendline detection
└── requirements.txt        # Python dependencies
```

## Setup Instructions

### 1. Install Dependencies

First, navigate to the `chart_infos` directory and install required packages:

```bash
cd chart_infos
pip install -r requirements.txt
```

**Required packages:**
- numpy>=1.18.5
- pandas>=1.0.4
- datetime>=4.3
- bokeh>=2.0.2
- colour>=0.1.5
- yfinance (for fetcher.py)

If `yfinance` is not installed, run:
```bash
pip install yfinance
```

## How to Run the System

The system works in **two steps**:

### Step 1: Fetch Stock Data

Use `fetcher.py` to download historical price data from Yahoo Finance.

**Command Syntax:**
```bash
python data/fetcher.py --ticker TICKER --start START_DATE --end END_DATE --interval INTERVAL --csv OUTPUT_FILE
```

**Parameters:**
- `--ticker`: Stock ticker symbol (e.g., AAPL, TSLA, SPY)
- `--start`: Start date in YYYY-MM-DD format
- `--end`: End date in YYYY-MM-DD format
- `--interval`: Time interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)
- `--csv`: Output CSV filename (saved in `data/` directory)

**Examples:**

1. **Download AAPL daily data for 2025:**
```bash
python data/fetcher.py --ticker AAPL --start 2025-01-01 --end 2025-10-20 --interval 1d --csv data/aapl_2025.csv
```

2. **Download Tesla hourly data:**
```bash
python data/fetcher.py --ticker TSLA --start 2025-09-01 --end 2025-10-20 --interval 1h --csv data/tsla_hourly.csv
```

3. **Download SPY 5-minute data:**
```bash
python data/fetcher.py --ticker SPY --start 2025-10-15 --end 2025-10-20 --interval 5m --csv data/spy_5min.csv
```

**Note:** Yahoo Finance has limitations:
- Intraday data (1m, 5m, 15m, 30m) is only available for the last 60 days
- For longer historical data, use daily (1d) or weekly (1wk) intervals

### Step 2: Run Trendline Detection

After fetching data, run the detection algorithm using `test_cursor.py`.

**Important:** Before running, you need to modify `test_cursor.py` to point to your data file.

#### Modify test_cursor.py

Open [test_cursor.py](test_cursor.py) and change line 45 to match your CSV file:

```python
# Line 45 - Change this to your data file
candles_df = pd.read_csv('./data/aapl_30.csv')  # ← Change 'aapl_30.csv' to your file
```

For example, if you fetched data to `aapl_2025.csv`, change it to:
```python
candles_df = pd.read_csv('./data/aapl_2025.csv')
```

#### Run the Detection

```bash
python test_cursor.py
```

**What happens:**
1. The script loads your CSV data
2. Detects pivot points (local highs and lows)
3. Finds all valid trendlines connecting these pivots
4. Scores trendlines based on number of touches and fit quality
5. Generates an interactive HTML chart with trendlines
6. Automatically opens the chart in your default browser

**Output:**
- File saved: `test_cursor_output_tight.html` (in the `chart_infos` directory)
- The HTML file contains an interactive Bokeh chart showing:
  - Candlestick price data
  - Detected support and resistance trendlines
  - Pivot points marked as orange circles
  - Trendline scores and metadata

## Understanding Sensitivity Settings

The `test_cursor.py` script has three sensitivity presets that control how strict the algorithm is when detecting trendlines:

### Current Setting (Line 9):
```python
SENSITIVITY = "tight"  # Options: "tight", "medium", "loose"
```

### Preset Details:

| Setting | Max Error | Min Touches | Use Case |
|---------|-----------|-------------|----------|
| **tight** | ±6% of ACR | 3+ | Many small trendlines, day trading, short-term patterns |
| **medium** | ±12% of ACR | 4+ | Balanced approach, swing trading (recommended) |
| **loose** | ±20% of ACR | 5+ | Few major trendlines, long-term investing |

**ACR = Average Candle Range** (adapts to asset volatility)

**To change sensitivity:**
Edit line 9 in `test_cursor.py`:
```python
SENSITIVITY = "medium"  # For balanced detection
```

## Algorithm Concepts (From PDF)

### Key Concepts

1. **Pivot Points**
   - Local highs or lows where price reversed
   - Resistance pivots: High[t] > High[t-j] AND High[t] > High[t+k]
   - Support pivots: Low[t] < Low[t-j] AND Low[t] < Low[t+k]

2. **Volatility Normalization (ACR)**
   - ACR = Average Candle Range = mean(High - Low)
   - All thresholds scale with ACR
   - Makes algorithm work for any asset ($10 stocks or $50,000 Bitcoin)

3. **Trendline Detection Steps**
   - Step 1: Identify valid pivots (separated by >20% of ACR)
   - Step 2: Draw lines between pivot pairs, calculate fit error (<6% ACR tolerance)
   - Step 3: Score trendlines using: Score = (ACR / AvgError) × 2.5^num_points
   - Step 4: Detect breakouts (price beyond trendline by >8% ACR)

4. **Scoring System**
   - 3 touches: multiplier = 15.6
   - 4 touches: multiplier = 39.1
   - 5 touches: multiplier = 97.7
   - **Higher score = more reliable trendline**

### Trading Signals (From PDF)

**1. Trendline Bounce (Mean Reversion)**
- Entry: Price approaches unbroken trendline (score > 100)
- Stop Loss: 1.5× ACR beyond trendline
- Target: 3× ACR profit or next resistance

**2. Breakout Confirmation (Trend Following)**
- Entry: Price closes beyond trendline by >8% ACR, wait for retest
- Stop Loss: 1× ACR beyond trendline
- Target: 4× ACR profit

**3. Multi-Trendline Confluence**
- Entry: 2+ trendlines converge at same zone (within 0.5× ACR)
- Highest probability setups

**4. Global Extrema Rejection**
- Entry: Counter-trend at trendlines containing all-time highs/lows
- Tight stop: 0.75× ACR

## Customizing Detection Parameters

For advanced users, you can modify detection parameters in `test_cursor.py` (lines 66-75):

```python
custom_config = {
    # Tolerance for point-to-line distance (default: 6% of ACR)
    "max_allowable_error_pt_to_trend": lambda candles: util.avg_candle_range(candles) * 0.06,

    # How far apart pivots must be (default: 20% of ACR)
    "pivot_seperation_threshold": lambda candles: util.avg_candle_range(candles) * 0.2,

    # How close pivots can be to group them (default: 10% of ACR)
    "pivot_grouping_threshold": lambda candles: util.avg_candle_range(candles) * 0.1,
}
```

## Quick Start Example

Complete workflow to analyze AAPL:

```bash
# 1. Navigate to chart_infos directory
cd chart_infos

# 2. Fetch AAPL daily data for 2025
python data/fetcher.py --ticker AAPL --start 2025-01-01 --end 2025-10-20 --interval 1d --csv data/aapl_2025.csv

# 3. Edit test_cursor.py line 45:
# candles_df = pd.read_csv('./data/aapl_2025.csv')

# 4. Run detection
python test_cursor.py

# 5. View results in browser (opens automatically)
# File: test_cursor_output_tight.html
```

## Troubleshooting

### Common Issues

**1. "No module named 'yfinance'"**
```bash
pip install yfinance
```

**2. "No data for TICKER between START and END"**
- Check ticker symbol is correct
- For intraday data (1m, 5m, etc.), ensure date range is within last 60 days
- Try using daily (1d) interval for historical data

**3. "FileNotFoundError: data/yourfile.csv"**
- Ensure you ran `fetcher.py` first
- Check the filename in `test_cursor.py` matches your CSV file
- Verify CSV file exists in `data/` directory

**4. Chart doesn't open automatically**
- Manually open `test_cursor_output_tight.html` in your browser
- File is located in the `chart_infos/` directory

**5. No trendlines detected**
- Try using "loose" sensitivity
- Ensure you have enough data points (at least 50+ candles)
- Check your data file has valid OHLC data

## Understanding the Output Chart

The generated HTML file contains:

1. **Candlestick Chart**: Shows price action
2. **Orange Circles**: Detected pivot points
3. **Dashed Lines**: Trendlines (support = green, resistance = red in some themes)
4. **Hover Information**: Score, touches, and trendline details
5. **Right Side Labels**: Trendline IDs and scores

**Interpreting Scores:**
- Score < 100: Low confidence, use for confirmation only
- Score 100-300: Standard confidence, valid for trading
- Score > 300: High confidence, primary trading signals
- Score > 1000: Exceptional strength (like the 1003.6 line in PDF example)

## Example Data Files (Included)

The `data/` directory includes sample files:
- `aapl_30.csv`: AAPL 30-day daily data
- `aapl_1h.csv`: AAPL hourly data
- `aapl_daily.csv`: AAPL daily data
- `aapl_3months_daily.csv`: AAPL 3-month daily data

You can use these to test the system without fetching new data.

## Further Development Notes (From Developer)

The developer mentioned they will:
> "change the structure to something more smooth after so that we run only one thing"

This means future versions may combine the fetcher and detection into a single command.

## Support and Questions

For understanding the algorithm's mathematical foundations and trading strategies, refer to the included PDF: **"Trendlines__Daniel_.pdf"**

The PDF covers:
- Section 1-2: Core concepts and pivot detection
- Section 3: How trendlines are detected (4 steps)
- Section 4: Actionable trading signals (4 entry strategies)
- Section 5: Risk management and position sizing
- Section 6: Advanced filters
- Section 7: Real chart analysis example

---

**Last Updated:** October 2025
**Created for:** Daniel's Stock Strategy Research Project
