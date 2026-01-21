"""
Technical Indicators Historical Charting System
Main entry point for the application

This system provides an interactive charting interface with customizable technical indicators,
similar to Robinhood's interface. Users can select and configure multiple indicators including:
- Moving Averages (SMA, EMA)
- Bollinger Bands
- RSI (Relative Strength Index)
- MACD
- Volume and VWAP
- Accelerator/Decelerator Oscillator

Usage:
    python main.py

The application will start a Dash server on http://localhost:8050
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ui.dash_app import create_app


def main():
    """
    Main entry point for the application
    """
    print("=" * 60)
    print("Technical Indicators Historical Charting System")
    print("=" * 60)
    print("\nStarting application...")

    # Create and run the Dash app
    app = create_app()

    print("\nApplication is running!")
    print("Open your browser and navigate to: http://localhost:8050")
    print("\nPress CTRL+C to stop the server")
    print("-" * 60)

    # Run the server
    app.run(
        debug=True,
        host='127.0.0.1',
        port=8050
    )


if __name__ == '__main__':
    main()