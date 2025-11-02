import pytrendline
from pytrendline import util
import pandas as pd
import os
import time



SENSITIVITY = "tight"  


SENSITIVITY_PRESETS = {
    "tight": {
        "name": "Tight (Many small supports)",
        "max_error_multiplier": 0.06,  
        "pivot_separation_multiplier": 0.2,  
        "pivot_grouping_multiplier": 0.1,  # 10% grouping
        "min_points": 3,
    },
    "medium": {
        "name": "Medium (Balanced - recommended)",
        "max_error_multiplier": 0.12,  # ±12% of avg candle range
        "pivot_separation_multiplier": 0.4,  # 40% separation
        "pivot_grouping_multiplier": 0.2,  # 20% grouping
        "min_points": 4,
    },
    "loose": {
        "name": "Loose (Few big supports)",
        "max_error_multiplier": 0.20,  # ±20% of avg candle range
        "pivot_separation_multiplier": 0.6,  # 60% separation
        "pivot_grouping_multiplier": 0.4,  # 30% grouping
        "min_points": 5,
    },
}

# Get selected preset
preset = SENSITIVITY_PRESETS[SENSITIVITY]
print(f"\n{'='*60}")
print(f"Using sensitivity: {preset['name']}")
print(f"  - Tolerance band: ±{preset['max_error_multiplier']*100:.0f}% of avg candle range")
print(f"  - Minimum touches required: {preset['min_points']}")
print(f"{'='*60}\n")


candles_df = pd.read_csv('./data/amd_1year_daily.csv')
candles_df.set_index('Idx')
candles_df['Date'] = pd.to_datetime(candles_df['Date'])

print(f"Loaded {len(candles_df)} candles")
print(f"Date range: {candles_df['Date'].iloc[0]} to {candles_df['Date'].iloc[-1]}")
print(f"Price range: ${candles_df['Low'].min():.2f} to ${candles_df['High'].max():.2f}")

candlestick_data = pytrendline.CandlestickData(
  df=candles_df,
  time_interval="1d",
  open_col="Open",
  high_col="High",
  low_col="Low",
  close_col="Close",
  datetime_col="Date"
)

# ============================================================================
# Configure Detection Parameters
# ============================================================================
custom_config = {
    # Main parameter: How far from the line can a price be and still count as "touching"
    "max_allowable_error_pt_to_trend": lambda candles: util.avg_candle_range(candles) * preset["max_error_multiplier"],

    # How far apart pivot points must be to be considered separate
    "pivot_seperation_threshold": lambda candles: util.avg_candle_range(candles) * preset["pivot_separation_multiplier"],

    # How close pivots can be to group them together
    "pivot_grouping_threshold": lambda candles: util.avg_candle_range(candles) * preset["pivot_grouping_multiplier"],
}

print("\nStarting pytrendline.detect...")
detect_start_time = time.time()

# ============================================================================
# Detect Trendlines
# ============================================================================
results = pytrendline.detect(
  candlestick_data=candlestick_data,
  trend_type=pytrendline.TrendlineTypes.BOTH,
  first_pt_must_be_pivot=False,
  last_pt_must_be_pivot=False,
  all_pts_must_be_pivots=False,
  trendline_must_include_global_maxmin_pt=False,
  min_points_required=preset["min_points"],  # Use preset minimum touches
  scan_from_date=None,
  ignore_breakouts=True,
  config=custom_config  # Use custom sensitivity config
)

detect_end_time = time.time()
print(f"pytrendline.detect took {detect_end_time - detect_start_time:.4f}s")

# Print summary
if 'support_trendlines' in results:
    print(f"\nFound {len(results['support_trendlines'])} support trendlines")
if 'resistance_trendlines' in results:
    print(f"Found {len(results['resistance_trendlines'])} resistance trendlines")

# ============================================================================
# Plot Results
# ============================================================================
outf = pytrendline.plot(
  results=results,
  filedir='.',
  filename=f'test_cursor_output_{SENSITIVITY}.html',
)

print(f"\nTrendline results saved in {outf}")
print("Opening file...")
os.system("start " + outf)
