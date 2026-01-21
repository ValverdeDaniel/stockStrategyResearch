"""
Create a demo chart showing all indicators
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.data_fetcher import DataFetcher
from indicators.trend import MultiSMA, EMA
from indicators.momentum import RSI, MACD, AC
from indicators.volatility import BollingerBands
from indicators.volume import Volume, VWAP
from visualization.chart_builder import TechnicalChartBuilder


def create_demo_chart(ticker='NVDA'):
    """Create a demo chart with all indicators"""

    print(f"Creating demo chart for {ticker}...")

    # Fetch data
    fetcher = DataFetcher()
    df = fetcher.fetch_historical_data(ticker, period='1y', interval='1d')

    if df is None or df.empty:
        print(f"Failed to fetch data for {ticker}")
        return

    print(f"Fetched {len(df)} days of data")

    # Create chart builder
    chart_builder = TechnicalChartBuilder(ticker, df, '1Y')

    # Calculate and add all indicators
    print("Adding indicators...")

    # SMA
    sma = MultiSMA(periods=[50, 200, 720])
    sma.calculate(df)
    chart_builder.add_indicator('SMA', sma)

    # EMA
    ema = EMA(period=20, color='#FF69B4')
    ema.calculate(df)
    chart_builder.add_indicator('EMA', ema)

    # Bollinger Bands
    bb = BollingerBands()
    bb.calculate(df)
    chart_builder.add_indicator('BB', bb)

    # RSI
    rsi = RSI()
    rsi.calculate(df)
    chart_builder.add_indicator('RSI', rsi)

    # MACD
    macd = MACD()
    macd.calculate(df)
    chart_builder.add_indicator('MACD', macd)

    # Volume
    volume = Volume()
    volume.calculate(df)
    chart_builder.add_indicator('Volume', volume)

    # VWAP
    vwap = VWAP()
    vwap.calculate(df)
    chart_builder.add_indicator('VWAP', vwap)

    # AC
    ac = AC()
    ac.calculate(df)
    chart_builder.add_indicator('AC', ac)

    # Build and save chart
    filename = f"{ticker}_demo_chart.html"
    chart_builder.save_chart(filename)

    print(f"Demo chart created: {filename}")
    print(f"Open {filename} in your browser to view the chart")

    # Print some statistics
    print(f"\nStatistics for {ticker}:")
    print(f"  Current Price: ${df['close'].iloc[-1]:.2f}")
    print(f"  1Y Return: {((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100:.2f}%")
    print(f"  Current RSI: {rsi.data['RSI'].iloc[-1]:.2f}")
    print(f"  Current MACD: {macd.data['MACD'].iloc[-1]:.4f}")
    print(f"  Current Volume: {volume.data['Volume'].iloc[-1]:,.0f}")


if __name__ == '__main__':
    # Create demo charts for multiple tickers
    tickers = ['NVDA', 'AAPL', 'TSLA']

    for ticker in tickers:
        print(f"\n{'='*60}")
        create_demo_chart(ticker)
        print('='*60)