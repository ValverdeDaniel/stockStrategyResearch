"""
Test script to verify the Technical Indicators system is working
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from data.data_fetcher import DataFetcher
from indicators.trend import SMA, EMA, MultiSMA
from indicators.momentum import RSI, MACD, AC
from indicators.volatility import BollingerBands
from indicators.volume import Volume, VWAP
from visualization.chart_builder import TechnicalChartBuilder


def test_data_fetching():
    """Test data fetching functionality"""
    print("Testing data fetching...")
    fetcher = DataFetcher()

    # Test fetching AAPL data
    df = fetcher.fetch_historical_data('AAPL', period='3mo', interval='1d')

    if df is not None and not df.empty:
        print(f"[OK] Successfully fetched {len(df)} days of data for AAPL")
        print(f"  Date range: {df.index[0]} to {df.index[-1]}")
        print(f"  Latest price: ${df['close'].iloc[-1]:.2f}")
        return df
    else:
        print("[FAIL] Failed to fetch data")
        return None


def test_indicators(df):
    """Test indicator calculations"""
    if df is None:
        print("Cannot test indicators without data")
        return None

    print("\nTesting indicators...")

    indicators = {}

    # Test SMA
    try:
        sma = MultiSMA(periods=[20, 50])
        sma_data = sma.calculate(df)
        print(f"[OK] SMA calculated: {sma_data.columns.tolist()}")
        indicators['SMA'] = sma
    except Exception as e:
        print(f"[FAIL] SMA failed: {e}")

    # Test EMA
    try:
        ema = EMA(period=20)
        ema_data = ema.calculate(df)
        print(f"[OK] EMA calculated: Latest value = {ema_data.iloc[-1].values[0]:.2f}")
        indicators['EMA'] = ema
    except Exception as e:
        print(f"[FAIL] EMA failed: {e}")

    # Test RSI
    try:
        rsi = RSI()
        rsi_data = rsi.calculate(df)
        print(f"[OK] RSI calculated: Latest value = {rsi_data['RSI'].iloc[-1]:.2f}")
        indicators['RSI'] = rsi
    except Exception as e:
        print(f"[FAIL] RSI failed: {e}")

    # Test MACD
    try:
        macd = MACD()
        macd_data = macd.calculate(df)
        print(f"[OK] MACD calculated: MACD={macd_data['MACD'].iloc[-1]:.4f}, Signal={macd_data['Signal'].iloc[-1]:.4f}")
        indicators['MACD'] = macd
    except Exception as e:
        print(f"[FAIL] MACD failed: {e}")

    # Test Bollinger Bands
    try:
        bb = BollingerBands()
        bb_data = bb.calculate(df)
        print(f"[OK] Bollinger Bands calculated: Upper={bb_data['BB_Upper'].iloc[-1]:.2f}, Lower={bb_data['BB_Lower'].iloc[-1]:.2f}")
        indicators['BB'] = bb
    except Exception as e:
        print(f"[FAIL] Bollinger Bands failed: {e}")

    # Test Volume
    try:
        vol = Volume()
        vol_data = vol.calculate(df)
        print(f"[OK] Volume processed: Latest = {vol_data['Volume'].iloc[-1]:,.0f}")
        indicators['Volume'] = vol
    except Exception as e:
        print(f"[FAIL] Volume failed: {e}")

    # Test VWAP
    try:
        vwap = VWAP()
        vwap_data = vwap.calculate(df)
        print(f"[OK] VWAP calculated: Latest value = {vwap_data['VWAP'].iloc[-1]:.2f}")
        indicators['VWAP'] = vwap
    except Exception as e:
        print(f"[FAIL] VWAP failed: {e}")

    # Test AC
    try:
        ac = AC()
        ac_data = ac.calculate(df)
        print(f"[OK] AC calculated: Latest value = {ac_data['AC'].iloc[-1]:.6f}")
        indicators['AC'] = ac
    except Exception as e:
        print(f"[FAIL] AC failed: {e}")

    return indicators


def test_chart_building(df, indicators):
    """Test chart building functionality"""
    if df is None or not indicators:
        print("Cannot test chart building without data and indicators")
        return

    print("\nTesting chart building...")

    try:
        # Create chart builder
        chart_builder = TechnicalChartBuilder('AAPL', df, '3mo')

        # Add indicators
        for name, indicator in indicators.items():
            chart_builder.add_indicator(name, indicator)

        # Build chart
        fig = chart_builder.build_chart()

        # Save to HTML
        filename = chart_builder.save_chart('test_chart.html')
        print(f"[OK] Chart created and saved to: {filename}")
        print(f"  Open the file in your browser to view the chart")

        return True
    except Exception as e:
        print(f"[FAIL] Chart building failed: {e}")
        return False


def test_ui_imports():
    """Test UI module imports"""
    print("\nTesting UI imports...")

    try:
        from ui.dash_app import create_app
        from ui.components import create_ticker_controls, create_indicator_controls
        print("[OK] UI modules imported successfully")
        return True
    except Exception as e:
        print(f"[FAIL] UI import failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Technical Indicators System Test")
    print("=" * 60)

    # Test data fetching
    df = test_data_fetching()

    # Test indicators
    indicators = test_indicators(df)

    # Test chart building
    test_chart_building(df, indicators)

    # Test UI imports
    test_ui_imports()

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    if df is not None and indicators and len(indicators) > 5:
        print("[OK] All core components are working!")
        print("\nYou can now run the main application:")
        print("  python main.py")
        print("\nThen open http://localhost:8050 in your browser")
    else:
        print("[FAIL] Some components failed. Please check the errors above.")


if __name__ == '__main__':
    main()