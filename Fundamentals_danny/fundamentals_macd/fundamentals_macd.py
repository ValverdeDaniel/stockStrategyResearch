"""
MACD Crossover Analysis Tool
=============================
Detailed MACD analysis for multiple stocks with crossover detection,
momentum classification, and actionable trading signals.

This tool analyzes MACD indicators across multiple stocks to identify:
- Recent crossovers (bullish/bearish)
- Approaching crossovers (predictive signals)
- Momentum strength and direction
- Quality of trading setups

Author: Created for stock strategy research
Compatible with: fundamentals_analyzer.py for future integration
"""

import datetime as dt
import requests
import pandas as pd
import numpy as np
import logging
import sys
from typing import Dict, List, Tuple, Optional

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION PARAMETERS
# ============================================================================
# You can adjust these thresholds to tune the analysis to your preferences

# EODHD API Configuration
API_TOKEN = "67ffece4b2ae08.94077168"
BASE_URL = "https://eodhd.com/api"
HEADERS = {"User-Agent": "Stocktimus-MACD-Analyzer/1.0"}

# MACD Calculation Parameters
MACD_FAST = 12          # Fast EMA period
MACD_SLOW = 26          # Slow EMA period
MACD_SIGNAL = 9         # Signal line EMA period

# Analysis Timeframes
LOOKBACK_DAYS = 365     # 1 year of data for MACD analysis
RANGE_WINDOW = 90       # 90-day window for normalization calculations

# Crossover Detection Thresholds
RECENT_CROSS_DAYS = 3               # Days to consider a cross "recent"
APPROACHING_THRESHOLD_PCT = 15      # % of 90-day range to consider "approaching"
NEAR_ZERO_THRESHOLD_PCT = 10        # % of MACD range to consider cross "near zero"

# Momentum Trend Analysis
TREND_WINDOW = 5        # Days to analyze histogram trend
ACCELERATION_WINDOW = 5 # Days to analyze momentum acceleration

# Probability & Scoring
HIGH_PROBABILITY_THRESHOLD = 70     # Score above this = high probability cross
IMMINENT_DAYS_THRESHOLD = 2         # Days until cross considered "imminent"
APPROACHING_DAYS_THRESHOLD = 10     # Max days to consider "approaching"


# ============================================================================
# MACD ANALYZER CLASS
# ============================================================================

class MACDAnalyzer:
    """
    Comprehensive MACD analysis service for stock crossover detection and
    momentum classification.

    This class provides detailed MACD metrics normalized across different
    stocks for comparative analysis and trading signal generation.
    """

    def __init__(self, api_token: str = None):
        """
        Initialize the MACD Analyzer.

        Args:
            api_token: EODHD API token (uses default if not provided)
        """
        self.api_token = api_token or API_TOKEN
        self.base_url = BASE_URL
        self.headers = HEADERS

    # ========================================================================
    # API DATA FETCHING METHODS
    # ========================================================================

    def _get_json(self, url: str) -> dict:
        """
        Fetch JSON data from URL with error handling.

        Args:
            url: Full API URL to fetch

        Returns:
            Dictionary of JSON response or empty dict on error
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed for {url}: {e}")
            return {}

    def _strip_suffix(self, ticker: str) -> str:
        """Remove .US suffix from ticker for display."""
        return ticker.rsplit(".", 1)[0]

    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current/latest stock price.

        Args:
            ticker: Stock ticker (with .US suffix)

        Returns:
            Current price or None if unavailable
        """
        url = f"{self.base_url}/real-time/{ticker}?api_token={self.api_token}&fmt=json"
        data = self._get_json(url)

        return data.get("close") or data.get("price") or data.get("lastPrice")

    def get_historical_prices(self, ticker: str, days_back: int = None) -> pd.DataFrame:
        """
        Get historical price data for MACD calculation.

        Args:
            ticker: Stock ticker (with .US suffix)
            days_back: Number of days to look back (default: LOOKBACK_DAYS)

        Returns:
            DataFrame with date index and OHLCV columns

        Note:
            - Returns empty DataFrame on error
            - Date is set as index
            - Sorted chronologically
        """
        if days_back is None:
            days_back = LOOKBACK_DAYS

        start_date = (dt.datetime.now() - dt.timedelta(days=days_back)).strftime('%Y-%m-%d')
        end_date = dt.date.today().strftime('%Y-%m-%d')

        url = (
            f"{self.base_url}/eod/{ticker}?from={start_date}&to={end_date}"
            f"&api_token={self.api_token}&fmt=json"
        )

        try:
            data = self._get_json(url)
            df = pd.DataFrame(data)

            if df.empty:
                return df

            df['date'] = pd.to_datetime(df['date'])
            df.sort_values('date', inplace=True)
            df.set_index('date', inplace=True)

            return df
        except Exception as e:
            logger.error(f"Failed to get historical prices for {ticker}: {e}")
            return pd.DataFrame()

    def append_today_price(self, df: pd.DataFrame, today_price: float) -> pd.DataFrame:
        """
        Add today's current price to historical data.

        Args:
            df: Historical price DataFrame with date index
            today_price: Current price to append

        Returns:
            DataFrame with today's price added (if not already present)

        Note:
            - Only adds if today's date not in index
            - Copies last row and updates close price
        """
        if df.empty or today_price is None:
            return df

        today = pd.Timestamp(dt.date.today())
        if today not in df.index:
            df.loc[today] = df.iloc[-1]
            df.loc[today, 'close'] = today_price

        return df

    # ========================================================================
    # MACD CALCULATION METHODS
    # ========================================================================

    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast: int = MACD_FAST,
        slow: int = MACD_SLOW,
        signal: int = MACD_SIGNAL
    ) -> pd.DataFrame:
        """
        Calculate MACD, Signal, and Histogram.

        Args:
            df: DataFrame with 'close' prices and date index
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line EMA period (default: 9)

        Returns:
            DataFrame with added columns:
                - MACD: Fast EMA - Slow EMA
                - Signal: EMA of MACD
                - Histogram: MACD - Signal

        Formula:
            MACD = EMA(close, 12) - EMA(close, 26)
            Signal = EMA(MACD, 9)
            Histogram = MACD - Signal
        """
        if df.empty or 'close' not in df.columns:
            return df

        df['EMA_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['EMA_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['MACD'] = df['EMA_fast'] - df['EMA_slow']
        df['Signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']

        return df

    # ========================================================================
    # CROSSOVER DETECTION METHODS
    # ========================================================================

    def detect_crossovers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect all MACD/Signal line crossovers in the data.

        Args:
            df: DataFrame with MACD and Signal columns

        Returns:
            DataFrame with added column:
                - Crossover: 1 for bullish cross, -1 for bearish cross, 0 for none

        Logic:
            - Bullish cross: MACD crosses above Signal (histogram goes from - to +)
            - Bearish cross: MACD crosses below Signal (histogram goes from + to -)

        Note:
            Uses sign change in histogram to detect crossovers
        """
        if df.empty or 'Histogram' not in df.columns:
            return df

        # Detect sign changes in histogram
        df['Hist_Sign'] = np.sign(df['Histogram'])
        df['Hist_Sign_Prev'] = df['Hist_Sign'].shift(1)

        # Crossover = sign change (excluding first row and zeros)
        df['Crossover'] = 0

        # Bullish cross: was negative, now positive
        bullish = (df['Hist_Sign_Prev'] < 0) & (df['Hist_Sign'] > 0)
        df.loc[bullish, 'Crossover'] = 1

        # Bearish cross: was positive, now negative
        bearish = (df['Hist_Sign_Prev'] > 0) & (df['Hist_Sign'] < 0)
        df.loc[bearish, 'Crossover'] = -1

        return df

    def find_last_crossover(self, df: pd.DataFrame) -> Tuple[Optional[int], Optional[str], Optional[float]]:
        """
        Find the most recent crossover in the data.

        Args:
            df: DataFrame with Crossover column (from detect_crossovers)

        Returns:
            Tuple of (days_ago, cross_type, macd_value):
                - days_ago: Trading days since last cross (None if no cross found)
                - cross_type: "Bullish Cross" or "Bearish Cross"
                - macd_value: MACD value at the crossover point

        Note:
            Counts only trading days (rows in DataFrame)
        """
        if df.empty or 'Crossover' not in df.columns:
            return None, None, None

        # Find all crossover points
        crosses = df[df['Crossover'] != 0]

        if crosses.empty:
            return None, None, None

        # Get last crossover
        last_cross = crosses.iloc[-1]
        last_cross_idx = crosses.index[-1]

        # Calculate days ago (trading days)
        days_ago = len(df) - (df.index.get_loc(last_cross_idx) + 1)

        # Determine cross type
        cross_type = "Bullish Cross" if last_cross['Crossover'] == 1 else "Bearish Cross"

        # Get MACD value at cross
        macd_value = last_cross['MACD']

        return days_ago, cross_type, macd_value

    # ========================================================================
    # NORMALIZATION & DISTANCE METRICS
    # ========================================================================

    def calculate_normalized_metrics(
        self,
        df: pd.DataFrame,
        current_price: float,
        range_window: int = RANGE_WINDOW
    ) -> Dict:
        """
        Calculate normalized MACD metrics for cross-stock comparison.

        Args:
            df: DataFrame with MACD calculations
            current_price: Current stock price
            range_window: Days to use for range calculation (default: 90)

        Returns:
            Dictionary containing:

            **Current Values:**
                - macd_value: Current MACD value
                - signal_value: Current Signal line value
                - histogram_value: Current Histogram value

            **Normalized Metrics:**
                - histogram_pct_price: Histogram as % of current price
                  Formula: (Histogram / Price) * 100

                - histogram_pct_range: Histogram position in 90-day range (0-100 scale)
                  Formula: (Hist - Min) / (Max - Min) * 100

                - macd_strength_score: Statistical Z-score of histogram
                  Formula: Histogram / StdDev(Histogram_90d)
                  Interpretation: How many std deviations from mean

            **Distance Metrics:**
                - distance_to_signal: Absolute distance between MACD and Signal
                - normalized_distance_pct: Distance as % of 90-day MACD range

        Note:
            Returns None for metrics if insufficient data
        """
        if df.empty:
            return {}

        # Get current values
        current = df.iloc[-1]
        macd_val = current['MACD']
        signal_val = current['Signal']
        hist_val = current['Histogram']

        # Get recent window for normalization
        recent_df = df.tail(range_window) if len(df) >= range_window else df

        # Calculate histogram range
        hist_min = recent_df['Histogram'].min()
        hist_max = recent_df['Histogram'].max()
        hist_range = hist_max - hist_min

        # Calculate MACD range
        macd_min = recent_df['MACD'].min()
        macd_max = recent_df['MACD'].max()
        macd_range = macd_max - macd_min

        # Histogram as % of price
        hist_pct_price = (hist_val / current_price * 100) if current_price else None

        # Histogram position in range (0-100 scale)
        if hist_range > 0:
            hist_pct_range = ((hist_val - hist_min) / hist_range * 100)
        else:
            hist_pct_range = 50.0  # Neutral if no range

        # MACD strength score (Z-score)
        hist_std = recent_df['Histogram'].std()
        macd_strength = (hist_val / hist_std) if hist_std > 0 else 0.0

        # Distance to signal
        distance = abs(macd_val - signal_val)

        # Normalized distance as % of MACD range
        norm_distance = (distance / macd_range * 100) if macd_range > 0 else 0.0

        return {
            'macd_value': macd_val,
            'signal_value': signal_val,
            'histogram_value': hist_val,
            'histogram_pct_price': hist_pct_price,
            'histogram_pct_range': hist_pct_range,
            'macd_strength_score': macd_strength,
            'distance_to_signal': distance,
            'normalized_distance_pct': norm_distance,
        }

    # ========================================================================
    # MOMENTUM & TREND ANALYSIS
    # ========================================================================

    def analyze_histogram_trend(
        self,
        df: pd.DataFrame,
        window: int = TREND_WINDOW
    ) -> Dict:
        """
        Analyze histogram trend and momentum direction.

        Args:
            df: DataFrame with Histogram column
            window: Number of days to analyze trend (default: 5)

        Returns:
            Dictionary containing:

            **Trend Metrics:**
                - histogram_trend: "Increasing", "Decreasing", or "Flat"
                  Logic: Compare current to N-day average

                - histogram_change_Nd: Numeric change over N days
                  Formula: Histogram_today - Histogram_N_days_ago

                - histogram_acceleration: "Accelerating" or "Decelerating"
                  Logic: Is recent change larger than earlier change?
                  Formula: Compare (today - 2d ago) vs (2d ago - Nd ago)

        Interpretation:
            - Increasing + Below zero → Approaching bullish cross
            - Decreasing + Above zero → Approaching bearish cross
            - Accelerating → Momentum building
            - Decelerating → Momentum fading
        """
        if df.empty or len(df) < window:
            return {
                'histogram_trend': 'Unknown',
                'histogram_change': None,
                'histogram_acceleration': 'Unknown'
            }

        current_hist = df['Histogram'].iloc[-1]
        prev_hist = df['Histogram'].iloc[-window]
        mid_hist = df['Histogram'].iloc[-2] if len(df) >= 2 else current_hist

        # Calculate change
        hist_change = current_hist - prev_hist

        # Determine trend
        if abs(hist_change) < 0.001:  # Very small change
            trend = "Flat"
        elif hist_change > 0:
            trend = "Increasing"
        else:
            trend = "Decreasing"

        # Calculate acceleration
        recent_change = current_hist - mid_hist
        earlier_change = mid_hist - prev_hist

        if abs(recent_change) > abs(earlier_change):
            acceleration = "Accelerating"
        else:
            acceleration = "Decelerating"

        return {
            'histogram_trend': trend,
            'histogram_change': hist_change,
            'histogram_acceleration': acceleration
        }

    def classify_momentum(
        self,
        histogram: float,
        strength_score: float,
        trend: str
    ) -> str:
        """
        Classify overall momentum strength and direction.

        Args:
            histogram: Current histogram value
            strength_score: MACD strength Z-score
            trend: Histogram trend ("Increasing", "Decreasing", "Flat")

        Returns:
            Classification string from:
                - "Very Strong Bullish": Strong positive momentum
                - "Strong Bullish": Moderate positive momentum
                - "Weak Bullish": Weakening positive momentum
                - "Neutral": Near zero, transitioning
                - "Weak Bearish": Weakening negative momentum
                - "Strong Bearish": Moderate negative momentum
                - "Very Strong Bearish": Strong negative momentum

        Logic:
            Based on Z-score strength and trend direction:
            - Z-score > 2.0 = Very Strong
            - Z-score > 0.5 = Strong
            - Z-score > -0.5 = Weak/Neutral
            - Z-score < -2.0 = Very Strong (opposite direction)

            Considers trend to differentiate strong vs weak within same sign
        """
        if abs(strength_score) < 0.5:
            return "Neutral"

        if histogram > 0:
            # Bullish territory
            if strength_score > 2.0:
                return "Very Strong Bullish"
            elif strength_score > 0.5:
                if trend == "Increasing":
                    return "Strong Bullish"
                else:
                    return "Weak Bullish"
            else:
                return "Weak Bullish"
        else:
            # Bearish territory
            if strength_score < -2.0:
                return "Very Strong Bearish"
            elif strength_score < -0.5:
                if trend == "Decreasing":
                    return "Strong Bearish"
                else:
                    return "Weak Bearish"
            else:
                return "Weak Bearish"

    # ========================================================================
    # CROSSOVER PROXIMITY & PREDICTION
    # ========================================================================

    def estimate_days_to_cross(
        self,
        histogram: float,
        histogram_change: float
    ) -> Optional[float]:
        """
        Estimate trading days until MACD crosses Signal line.

        Args:
            histogram: Current histogram value
            histogram_change: Change in histogram over TREND_WINDOW days

        Returns:
            Estimated days to cross, or None if:
                - Not trending toward zero
                - Change rate is too slow
                - Already at zero

        Formula:
            days = abs(histogram) / abs(change_per_day)

        Note:
            This is linear extrapolation - markets are not linear!
            Use as rough estimate only. Capped at 50 days.

        Interpretation:
            - 0-2 days: Imminent cross
            - 3-5 days: Very near
            - 6-10 days: Approaching
            - 10+ days: Far away
            - None: Not approaching or insufficient data
        """
        if histogram_change is None or abs(histogram_change) < 0.0001:
            return None

        # Check if trending toward zero
        if (histogram > 0 and histogram_change > 0) or (histogram < 0 and histogram_change < 0):
            # Moving away from zero
            return None

        # Calculate change per day
        change_per_day = histogram_change / TREND_WINDOW

        if abs(change_per_day) < 0.0001:
            return None

        # Estimate days to zero
        days = abs(histogram / change_per_day)

        # Cap at reasonable maximum
        return min(days, 50.0) if days > 0 else None

    def calculate_cross_probability(
        self,
        histogram: float,
        normalized_distance: float,
        trend: str,
        acceleration: str,
        days_to_cross: Optional[float]
    ) -> float:
        """
        Calculate probability score (0-100) of cross occurring in next 5 days.

        Args:
            histogram: Current histogram value
            normalized_distance: Distance to signal as % of range
            trend: Histogram trend direction
            acceleration: Momentum acceleration status
            days_to_cross: Estimated days until cross

        Returns:
            Score from 0-100 where:
                - 90-100: Very high probability (imminent)
                - 70-89: High probability
                - 50-69: Moderate probability
                - 30-49: Low probability
                - 0-29: Very low probability

        Factors Considered:
            1. Distance from zero (closer = higher score) - 40% weight
            2. Trend toward zero (stronger = higher score) - 30% weight
            3. Acceleration (accelerating = higher score) - 15% weight
            4. Estimated days (sooner = higher score) - 15% weight

        Logic:
            - Must be trending toward zero to have any probability
            - Accelerating momentum increases probability
            - Very close distance dominates other factors
        """
        score = 0.0

        # Factor 1: Distance score (40 points max)
        # Closer to zero = higher score
        if normalized_distance < 5:
            distance_score = 40.0
        elif normalized_distance < 10:
            distance_score = 35.0
        elif normalized_distance < 20:
            distance_score = 25.0
        elif normalized_distance < 40:
            distance_score = 15.0
        else:
            distance_score = 5.0

        score += distance_score

        # Factor 2: Trend score (30 points max)
        # Must be trending toward zero
        trending_toward_zero = (
            (histogram < 0 and trend == "Increasing") or
            (histogram > 0 and trend == "Decreasing")
        )

        if trending_toward_zero:
            score += 30.0
        elif trend == "Flat":
            score += 10.0
        else:
            # Trending away - very low probability
            score = min(score, 20.0)

        # Factor 3: Acceleration score (15 points max)
        if acceleration == "Accelerating" and trending_toward_zero:
            score += 15.0
        elif acceleration == "Decelerating":
            score += 5.0

        # Factor 4: Days to cross score (15 points max)
        if days_to_cross is not None:
            if days_to_cross <= 2:
                score += 15.0
            elif days_to_cross <= 5:
                score += 10.0
            elif days_to_cross <= 10:
                score += 5.0

        # Cap at 100
        return min(score, 100.0)

    def determine_approaching_cross(
        self,
        histogram: float,
        normalized_distance: float,
        trend: str,
        days_since_cross: Optional[int],
        probability_score: float
    ) -> bool:
        """
        Determine if stock is approaching a crossover.

        Args:
            histogram: Current histogram value
            normalized_distance: Distance as % of range
            trend: Histogram trend
            days_since_cross: Days since last cross
            probability_score: Cross probability score (0-100)

        Returns:
            True if approaching a cross, False otherwise

        Criteria (ALL must be met):
            1. Within threshold distance (normalized_distance < 20%)
            2. Trending toward zero
            3. No recent cross (> 3 days ago or None)
            4. Probability score > 50

        Purpose:
            Filters for stocks that are ABOUT TO cross but haven't yet.
            Excludes stocks that just crossed (recent) or are far away.
        """
        # Must be within distance threshold
        if normalized_distance >= APPROACHING_THRESHOLD_PCT:
            return False

        # Must be trending toward zero
        trending_toward = (
            (histogram < 0 and trend == "Increasing") or
            (histogram > 0 and trend == "Decreasing")
        )
        if not trending_toward:
            return False

        # Must not have just crossed
        if days_since_cross is not None and days_since_cross <= RECENT_CROSS_DAYS:
            return False

        # Must have reasonable probability
        if probability_score < 50:
            return False

        return True

    # ========================================================================
    # SIGNAL QUALITY & CLASSIFICATION
    # ========================================================================

    def classify_trend_phase(
        self,
        days_since_cross: Optional[int],
        cross_type: Optional[str],
        histogram_trend: str,
        strength_score: float
    ) -> str:
        """
        Classify current phase of MACD trend cycle.

        Args:
            days_since_cross: Days since last crossover
            cross_type: Type of last cross ("Bullish" or "Bearish")
            histogram_trend: Current histogram trend
            strength_score: MACD strength Z-score

        Returns:
            Phase classification:
                - "Early Bullish": 0-5 days after bullish cross
                - "Mid Bullish": 6-15 days after bullish cross
                - "Late Bullish": 16+ days, momentum may be exhausting
                - "Early Bearish": 0-5 days after bearish cross
                - "Mid Bearish": 6-15 days after bearish cross
                - "Late Bearish": 16+ days, momentum may be exhausting
                - "Transition": No clear trend or approaching cross

        Usage:
            - Early: Good entry point (just crossed)
            - Mid: Confirmation phase (trend established)
            - Late: Consider exit (trend aging)
            - Transition: Wait for clearer signal
        """
        if days_since_cross is None or cross_type is None:
            return "Transition"

        is_bullish = "Bullish" in cross_type

        if days_since_cross <= 5:
            return "Early Bullish" if is_bullish else "Early Bearish"
        elif days_since_cross <= 15:
            return "Mid Bullish" if is_bullish else "Mid Bearish"
        else:
            return "Late Bullish" if is_bullish else "Late Bearish"

    def determine_setup_type(
        self,
        days_since_cross: Optional[int],
        cross_type: Optional[str],
        approaching: bool,
        histogram: float,
        histogram_trend: str,
        strength_score: float,
        probability_score: float
    ) -> str:
        """
        Identify specific trading setup pattern.

        Args:
            days_since_cross: Days since last cross
            cross_type: Type of last cross
            approaching: Is approaching a cross?
            histogram: Current histogram value
            histogram_trend: Histogram trend direction
            strength_score: MACD strength score
            probability_score: Cross probability score

        Returns:
            Setup pattern name:
                - "Fresh Bullish Cross": Just crossed bullish (0-3 days)
                - "Fresh Bearish Cross": Just crossed bearish (0-3 days)
                - "Approaching Bullish Cross - High Probability": About to cross bullish
                - "Approaching Bearish Cross - High Probability": About to cross bearish
                - "Strong Bullish Momentum": Strong upward momentum established
                - "Strong Bearish Momentum": Strong downward momentum established
                - "Bullish Losing Steam": Positive but weakening
                - "Bearish Losing Steam": Negative but weakening
                - "Neutral/Consolidating": No clear signal

        Purpose:
            Provides actionable pattern name for quick scanning and filtering.
        """
        # Fresh crosses (0-3 days)
        if days_since_cross is not None and days_since_cross <= RECENT_CROSS_DAYS:
            if "Bullish" in cross_type:
                return "Fresh Bullish Cross"
            else:
                return "Fresh Bearish Cross"

        # Approaching crosses (high probability)
        if approaching and probability_score >= HIGH_PROBABILITY_THRESHOLD:
            if histogram < 0:
                return "Approaching Bullish Cross - High Probability"
            else:
                return "Approaching Bearish Cross - High Probability"

        # Strong momentum
        if abs(strength_score) > 1.5:
            if histogram > 0 and histogram_trend == "Increasing":
                return "Strong Bullish Momentum"
            elif histogram < 0 and histogram_trend == "Decreasing":
                return "Strong Bearish Momentum"

        # Losing steam
        if histogram > 0 and histogram_trend == "Decreasing":
            return "Bullish Losing Steam"
        elif histogram < 0 and histogram_trend == "Increasing" and not approaching:
            return "Bearish Losing Steam"

        # Default
        return "Neutral/Consolidating"

    def calculate_watch_priority(
        self,
        setup_type: str,
        probability_score: float,
        days_to_cross: Optional[float],
        strength_score: float
    ) -> int:
        """
        Calculate priority score for watchlist (1-5 scale).

        Args:
            setup_type: Trading setup pattern
            probability_score: Cross probability score
            days_to_cross: Estimated days until cross
            strength_score: MACD strength score

        Returns:
            Priority from 1-5:
                5 = Must watch now (imminent high-probability setup)
                4 = High priority (approaching or fresh cross)
                3 = Medium priority (established momentum)
                2 = Low priority (weak signal or late phase)
                1 = Very low priority (neutral/no clear signal)

        Logic:
            Prioritizes:
            - Imminent crosses (days_to_cross < 3)
            - High probability setups (score > 70)
            - Fresh crosses (recent action)
            - Strong momentum (high Z-score)
        """
        # Priority 5: Imminent high-probability crosses
        if days_to_cross is not None and days_to_cross <= 2 and probability_score >= 70:
            return 5

        # Priority 5: Fresh crosses with strong momentum
        if "Fresh" in setup_type and abs(strength_score) > 1.0:
            return 5

        # Priority 4: Approaching high-probability crosses
        if "Approaching" in setup_type and "High Probability" in setup_type:
            return 4

        # Priority 4: Fresh crosses
        if "Fresh" in setup_type:
            return 4

        # Priority 3: Strong momentum
        if "Strong" in setup_type and "Momentum" in setup_type:
            return 3

        # Priority 2: Losing steam or moderate signals
        if "Losing Steam" in setup_type:
            return 2

        # Priority 2: Approaching but lower probability
        if "Approaching" in setup_type:
            return 2

        # Priority 1: Neutral/consolidating
        return 1

    # ========================================================================
    # MACD SCORING METHODS
    # ========================================================================

    def calculate_macd_bullish_score(
        self,
        histogram: float,
        macd_position: str,
        strength_score: float,
        days_since_cross: Optional[int],
        cross_type: Optional[str],
        cross_macd: Optional[float],
        histogram_trend: str,
        histogram_acceleration: str,
        approaching_cross: bool,
        probability_score: float,
        df: pd.DataFrame
    ) -> float:
        """
        Calculate comprehensive bullish score for MACD (0-100).

        Components (100 points total):
            1. Position & Strength (35 pts): Current position and Z-score
            2. Crossover Timing (30 pts): How recent was bullish cross
            3. Momentum Direction (20 pts): Trend and acceleration
            4. Quality & Opportunity (15 pts): Signal quality and future potential

        Args:
            histogram: Current histogram value
            macd_position: "Above Signal" or "Below Signal"
            strength_score: MACD Z-score strength
            days_since_cross: Days since last cross
            cross_type: Type of last cross
            cross_macd: MACD value at last cross
            histogram_trend: Current trend direction
            histogram_acceleration: Acceleration status
            approaching_cross: If approaching a cross
            probability_score: Cross probability (0-100)
            df: DataFrame with MACD calculations

        Returns:
            Score from 0-100 where higher = more bullish
        """
        score = 0.0

        # Component 1: Position & Strength (35 points)
        if macd_position == "Above Signal":
            score += 15  # Base position points

            # Add strength bonus
            if strength_score >= 2.0:
                score += 20
            elif strength_score >= 1.5:
                score += 15
            elif strength_score >= 1.0:
                score += 10
            elif strength_score >= 0.5:
                score += 5

        # Component 2: Crossover Timing (30 points)
        if cross_type == "Bullish Cross" and days_since_cross is not None:
            if days_since_cross <= 1:
                score += 30  # Just crossed - maximum signal
            elif days_since_cross <= 3:
                score += 25  # Very fresh
            elif days_since_cross <= 5:
                score += 22  # Fresh
            elif days_since_cross <= 10:
                score += 18  # Recent
            elif days_since_cross <= 20:
                score += 12  # Established
            elif days_since_cross <= 30:
                score += 6   # Mature
            else:
                score += 2   # Very old signal

        # Component 3: Momentum Direction (20 points)
        if histogram_trend == "Increasing":
            score += 12
            # Bonus for acceleration
            if histogram_acceleration == "Accelerating":
                score += 8
            else:
                score += 4
        elif histogram_trend == "Flat":
            score += 6

        # Component 4: Quality & Opportunity (15 points)
        quality_points = 0

        # High quality if last cross near zero line
        if cross_macd is not None and not df.empty:
            # Get 90-day MACD range for context
            recent_df = df.tail(RANGE_WINDOW) if len(df) >= RANGE_WINDOW else df
            macd_range = recent_df['MACD'].max() - recent_df['MACD'].min()

            if macd_range > 0 and abs(cross_macd) < (macd_range * 0.15):
                quality_points = 8

        # OR if approaching bullish cross (future opportunity)
        if approaching_cross and histogram < 0:  # Below signal, approaching bullish
            if probability_score >= 80:
                quality_points = max(quality_points, 15)
            elif probability_score >= 60:
                quality_points = max(quality_points, 12)
            elif probability_score >= 40:
                quality_points = max(quality_points, 8)

        score += quality_points

        # Cap at 100
        return min(score, 100.0)

    def calculate_macd_bearish_score(
        self,
        histogram: float,
        macd_position: str,
        strength_score: float,
        days_since_cross: Optional[int],
        cross_type: Optional[str],
        cross_macd: Optional[float],
        histogram_trend: str,
        histogram_acceleration: str,
        approaching_cross: bool,
        probability_score: float,
        df: pd.DataFrame
    ) -> float:
        """
        Calculate comprehensive bearish score for MACD (0-100).

        Components (100 points total):
            1. Position & Strength (35 pts): Current position and negative Z-score
            2. Crossover Timing (30 pts): How recent was bearish cross
            3. Momentum Direction (20 pts): Negative trend and acceleration
            4. Quality & Opportunity (15 pts): Signal quality and future potential

        Args:
            histogram: Current histogram value
            macd_position: "Above Signal" or "Below Signal"
            strength_score: MACD Z-score strength
            days_since_cross: Days since last cross
            cross_type: Type of last cross
            cross_macd: MACD value at last cross
            histogram_trend: Current trend direction
            histogram_acceleration: Acceleration status
            approaching_cross: If approaching a cross
            probability_score: Cross probability (0-100)
            df: DataFrame with MACD calculations

        Returns:
            Score from 0-100 where higher = more bearish
        """
        score = 0.0

        # Component 1: Position & Strength (35 points)
        if macd_position == "Below Signal":
            score += 15  # Base position points

            # Add negative strength bonus
            if strength_score <= -2.0:
                score += 20
            elif strength_score <= -1.5:
                score += 15
            elif strength_score <= -1.0:
                score += 10
            elif strength_score <= -0.5:
                score += 5

        # Component 2: Crossover Timing (30 points)
        if cross_type == "Bearish Cross" and days_since_cross is not None:
            if days_since_cross <= 1:
                score += 30  # Just crossed - maximum signal
            elif days_since_cross <= 3:
                score += 25  # Very fresh
            elif days_since_cross <= 5:
                score += 22  # Fresh
            elif days_since_cross <= 10:
                score += 18  # Recent
            elif days_since_cross <= 20:
                score += 12  # Established
            elif days_since_cross <= 30:
                score += 6   # Mature
            else:
                score += 2   # Very old signal

        # Component 3: Momentum Direction (20 points)
        if histogram_trend == "Decreasing":
            score += 12
            # Bonus for acceleration
            if histogram_acceleration == "Accelerating":
                score += 8
            else:
                score += 4
        elif histogram_trend == "Flat":
            score += 6

        # Component 4: Quality & Opportunity (15 points)
        quality_points = 0

        # High quality if last cross near zero line
        if cross_macd is not None and not df.empty:
            # Get 90-day MACD range for context
            recent_df = df.tail(RANGE_WINDOW) if len(df) >= RANGE_WINDOW else df
            macd_range = recent_df['MACD'].max() - recent_df['MACD'].min()

            if macd_range > 0 and abs(cross_macd) < (macd_range * 0.15):
                quality_points = 8

        # OR if approaching bearish cross (future opportunity)
        if approaching_cross and histogram > 0:  # Above signal, approaching bearish
            if probability_score >= 80:
                quality_points = max(quality_points, 15)
            elif probability_score >= 60:
                quality_points = max(quality_points, 12)
            elif probability_score >= 40:
                quality_points = max(quality_points, 8)

        score += quality_points

        # Cap at 100
        return min(score, 100.0)

    # ========================================================================
    # MAIN ANALYSIS METHOD
    # ========================================================================

    def analyze_macd(self, ticker: str) -> Dict:
        """
        Perform comprehensive MACD analysis for a single stock.

        Args:
            ticker: Stock ticker symbol (without .US suffix)

        Returns:
            Dictionary with all MACD metrics (25 columns - was 22, now adding 3 scores):

            **Basic Info:**
                - Ticker: Clean ticker symbol
                - Current_Price: Latest price

            **Group 1: Current MACD State**
                - MACD_Value: Raw MACD
                - Signal_Value: Raw Signal line
                - Histogram_Value: Raw Histogram
                - MACD_Position: "Above Signal" or "Below Signal"

            **Group 2: Normalized Metrics**
                - Histogram_Pct_Price: Histogram as % of price
                - Histogram_Pct_Range_90d: Position in 90-day range (0-100)
                - MACD_Strength_Score: Z-score (statistical strength)

            **Group 3: Crossover Detection**
                - Days_Since_Last_Cross: Trading days since last cross
                - Last_Cross_Type: "Bullish Cross" or "Bearish Cross"
                - Last_Cross_MACD_Value: MACD value at cross point

            **Group 4: Momentum Trend**
                - Histogram_Trend_5d: "Increasing", "Decreasing", "Flat"
                - Histogram_Change_5d: Numeric change over 5 days
                - Histogram_Acceleration: "Accelerating" or "Decelerating"

            **Group 5: Crossover Proximity**
                - Approaching_Cross: True/False
                - Est_Days_To_Cross: Estimated days until cross
                - Cross_Probability_Score: 0-100 probability score

            **Group 6: Classification**
                - Momentum_Category: Strength classification
                - MACD_Trend_Phase: Cycle phase
                - Setup_Type: Trading pattern name
                - Watch_Priority: 1-5 priority score

        Note:
            Returns error dict if analysis fails.
        """
        try:
            # Prepare ticker with .US suffix
            api_ticker = f"{ticker}.US" if not ticker.endswith(".US") else ticker
            clean_ticker = self._strip_suffix(api_ticker)

            logger.info(f"Analyzing MACD for {clean_ticker}...")

            # Get current price
            current_price = self.get_current_price(api_ticker)
            if not current_price:
                raise Exception(f"No current price data for {ticker}")

            # Get historical data
            df = self.get_historical_prices(api_ticker, days_back=LOOKBACK_DAYS)
            if df.empty:
                raise Exception(f"No historical data for {ticker}")

            # Append today's price
            df = self.append_today_price(df, current_price)

            # Calculate MACD
            df = self.calculate_macd(df)

            # Detect crossovers
            df = self.detect_crossovers(df)

            # Find last crossover
            days_since_cross, cross_type, cross_macd = self.find_last_crossover(df)

            # Calculate normalized metrics
            norm_metrics = self.calculate_normalized_metrics(df, current_price)

            # Analyze histogram trend
            trend_metrics = self.analyze_histogram_trend(df)

            # Get current values
            histogram = norm_metrics['histogram_value']
            strength_score = norm_metrics['macd_strength_score']

            # Classify momentum
            momentum_category = self.classify_momentum(
                histogram,
                strength_score,
                trend_metrics['histogram_trend']
            )

            # Estimate days to cross
            days_to_cross = self.estimate_days_to_cross(
                histogram,
                trend_metrics['histogram_change']
            )

            # Calculate cross probability
            probability_score = self.calculate_cross_probability(
                histogram,
                norm_metrics['normalized_distance_pct'],
                trend_metrics['histogram_trend'],
                trend_metrics['histogram_acceleration'],
                days_to_cross
            )

            # Determine if approaching cross
            approaching = self.determine_approaching_cross(
                histogram,
                norm_metrics['normalized_distance_pct'],
                trend_metrics['histogram_trend'],
                days_since_cross,
                probability_score
            )

            # Classify trend phase
            trend_phase = self.classify_trend_phase(
                days_since_cross,
                cross_type,
                trend_metrics['histogram_trend'],
                strength_score
            )

            # Determine setup type
            setup_type = self.determine_setup_type(
                days_since_cross,
                cross_type,
                approaching,
                histogram,
                trend_metrics['histogram_trend'],
                strength_score,
                probability_score
            )

            # Calculate watch priority
            priority = self.calculate_watch_priority(
                setup_type,
                probability_score,
                days_to_cross,
                strength_score
            )

            # Determine MACD position
            macd_position = "Above Signal" if histogram > 0 else "Below Signal"

            # Calculate MACD scores
            bullish_score = self.calculate_macd_bullish_score(
                histogram=histogram,
                macd_position=macd_position,
                strength_score=strength_score,
                days_since_cross=days_since_cross,
                cross_type=cross_type,
                cross_macd=cross_macd,
                histogram_trend=trend_metrics['histogram_trend'],
                histogram_acceleration=trend_metrics['histogram_acceleration'],
                approaching_cross=approaching,
                probability_score=probability_score,
                df=df
            )

            bearish_score = self.calculate_macd_bearish_score(
                histogram=histogram,
                macd_position=macd_position,
                strength_score=strength_score,
                days_since_cross=days_since_cross,
                cross_type=cross_type,
                cross_macd=cross_macd,
                histogram_trend=trend_metrics['histogram_trend'],
                histogram_acceleration=trend_metrics['histogram_acceleration'],
                approaching_cross=approaching,
                probability_score=probability_score,
                df=df
            )

            net_score = bullish_score - bearish_score

            # Compile results
            result = {
                # Basic Info
                "Ticker": clean_ticker,
                "Current_Price": round(current_price, 2),

                # Group 1: Current State
                "MACD_Value": round(norm_metrics['macd_value'], 4),
                "Signal_Value": round(norm_metrics['signal_value'], 4),
                "Histogram_Value": round(histogram, 4),
                "MACD_Position": macd_position,

                # Group 2: Normalized Metrics
                "Histogram_Pct_Price": round(norm_metrics['histogram_pct_price'], 4) if norm_metrics['histogram_pct_price'] else None,
                "Histogram_Pct_Range_90d": round(norm_metrics['histogram_pct_range'], 2),
                "MACD_Strength_Score": round(strength_score, 2),

                # Group 3: Crossover Detection
                "Days_Since_Last_Cross": days_since_cross,
                "Last_Cross_Type": cross_type,
                "Last_Cross_MACD_Value": round(cross_macd, 4) if cross_macd else None,

                # Group 4: Momentum Trend
                "Histogram_Trend_5d": trend_metrics['histogram_trend'],
                "Histogram_Change_5d": round(trend_metrics['histogram_change'], 4) if trend_metrics['histogram_change'] else None,
                "Histogram_Acceleration": trend_metrics['histogram_acceleration'],

                # Group 5: Crossover Proximity
                "Approaching_Cross": approaching,
                "Est_Days_To_Cross": round(days_to_cross, 1) if days_to_cross else None,
                "Cross_Probability_Score": round(probability_score, 1),

                # Group 6: Classification
                "Momentum_Category": momentum_category,
                "MACD_Trend_Phase": trend_phase,
                "Setup_Type": setup_type,
                "Watch_Priority": priority,

                # Group 7: MACD Scores
                "MACD_Bullish_Score": round(bullish_score, 1),
                "MACD_Bearish_Score": round(bearish_score, 1),
                "MACD_Net_Score": round(net_score, 1),
            }

            return result

        except Exception as e:
            logger.error(f"MACD analysis failed for {ticker}: {e}")
            return {
                "Ticker": ticker,
                "Error": str(e)
            }

    def analyze_multiple_tickers(self, tickers: List[str]) -> pd.DataFrame:
        """
        Analyze MACD for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            DataFrame with all tickers and their MACD metrics

        Note:
            Processes tickers sequentially to avoid API rate limits
        """
        results = []

        for ticker in tickers:
            result = self.analyze_macd(ticker)
            results.append(result)

        df = pd.DataFrame(results)
        return df


# ============================================================================
# DISPLAY & OUTPUT FUNCTIONS
# ============================================================================

def display_summary_table(df: pd.DataFrame) -> None:
    """
    Display key metrics in console-friendly format.

    Shows most important columns for quick scanning:
    - Ticker, Price, MACD Position
    - Setup Type, Priority
    - Days Since Cross, Probability Score
    - Momentum Category
    """
    if df.empty:
        print("No data to display")
        return

    # Select key columns for display
    display_cols = [
        "Ticker",
        "Current_Price",
        "MACD_Position",
        "MACD_Bullish_Score",
        "MACD_Bearish_Score",
        "MACD_Net_Score",
        "Setup_Type",
        "Watch_Priority",
        "Days_Since_Last_Cross",
        "Cross_Probability_Score",
        "Momentum_Category",
        "Approaching_Cross"
    ]

    # Filter to columns that exist
    available_cols = [col for col in display_cols if col in df.columns]

    if not available_cols:
        print(df)
        return

    summary_df = df[available_cols].copy()

    # Sort by priority (descending) then net score (descending)
    sort_cols = []
    ascending = []

    if "Watch_Priority" in summary_df.columns:
        sort_cols.append("Watch_Priority")
        ascending.append(False)

    if "MACD_Net_Score" in summary_df.columns:
        sort_cols.append("MACD_Net_Score")
        ascending.append(False)
    elif "Cross_Probability_Score" in summary_df.columns:
        sort_cols.append("Cross_Probability_Score")
        ascending.append(False)

    if sort_cols:
        summary_df = summary_df.sort_values(sort_cols, ascending=ascending)

    print("\n" + "="*120)
    print("MACD ANALYSIS SUMMARY - KEY METRICS")
    print("="*120)
    print(summary_df.to_string(index=False))
    print("="*120)


def display_detailed_stats(df: pd.DataFrame) -> None:
    """
    Display statistical summary of the analysis.
    """
    if df.empty or 'Error' in df.columns:
        return

    print("\n" + "="*80)
    print("ANALYSIS STATISTICS")
    print("="*80)

    total = len(df)
    print(f"Total Stocks Analyzed: {total}")

    # Breakdown by setup type
    if "Setup_Type" in df.columns:
        print("\nSetup Type Distribution:")
        setup_counts = df["Setup_Type"].value_counts()
        for setup, count in setup_counts.items():
            print(f"  {setup}: {count}")

    # Breakdown by priority
    if "Watch_Priority" in df.columns:
        print("\nPriority Distribution:")
        for priority in sorted(df["Watch_Priority"].unique(), reverse=True):
            count = len(df[df["Watch_Priority"] == priority])
            print(f"  Priority {priority}: {count} stocks")

    # Approaching crosses
    if "Approaching_Cross" in df.columns:
        approaching_count = df["Approaching_Cross"].sum()
        print(f"\nStocks Approaching Crossover: {approaching_count}")

    # Recent crosses
    if "Days_Since_Last_Cross" in df.columns:
        recent_crosses = len(df[df["Days_Since_Last_Cross"] <= RECENT_CROSS_DAYS])
        print(f"Recent Crosses (≤{RECENT_CROSS_DAYS} days): {recent_crosses}")

    # MACD Score Statistics
    if "MACD_Net_Score" in df.columns:
        print("\nMACD Score Analysis:")
        print(f"  Highest Bullish Score: {df['MACD_Bullish_Score'].max():.1f} ({df.loc[df['MACD_Bullish_Score'].idxmax(), 'Ticker']})")
        print(f"  Highest Bearish Score: {df['MACD_Bearish_Score'].max():.1f} ({df.loc[df['MACD_Bearish_Score'].idxmax(), 'Ticker']})")
        print(f"  Highest Net Score: {df['MACD_Net_Score'].max():.1f} ({df.loc[df['MACD_Net_Score'].idxmax(), 'Ticker']})")
        print(f"  Lowest Net Score: {df['MACD_Net_Score'].min():.1f} ({df.loc[df['MACD_Net_Score'].idxmin(), 'Ticker']})")

        # Count by score categories
        strong_bullish = len(df[df['MACD_Net_Score'] >= 50])
        moderate_bullish = len(df[(df['MACD_Net_Score'] >= 20) & (df['MACD_Net_Score'] < 50)])
        neutral = len(df[(df['MACD_Net_Score'] > -20) & (df['MACD_Net_Score'] < 20)])
        moderate_bearish = len(df[(df['MACD_Net_Score'] <= -20) & (df['MACD_Net_Score'] > -50)])
        strong_bearish = len(df[df['MACD_Net_Score'] <= -50])

        print("\nNet Score Distribution:")
        print(f"  Strong Bullish (≥50): {strong_bullish} stocks")
        print(f"  Moderate Bullish (20-49): {moderate_bullish} stocks")
        print(f"  Neutral (-19 to 19): {neutral} stocks")
        print(f"  Moderate Bearish (-49 to -20): {moderate_bearish} stocks")
        print(f"  Strong Bearish (≤-50): {strong_bearish} stocks")

    print("="*80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main function to run MACD analysis.

    MODIFY THE STOCK LIST BELOW TO ANALYZE YOUR DESIRED TICKERS
    """

    # ========================================================================
    # STOCK LIST - MODIFY THIS TO ANALYZE YOUR DESIRED TICKERS
    # ========================================================================
    stocks = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "TSLA", "META", "AMD", "NFLX", "INTC",
        # Add more tickers here as needed
    ]
    # ========================================================================

    print("="*120)
    print("MACD CROSSOVER ANALYSIS TOOL")
    print("="*120)
    print(f"\nAnalyzing {len(stocks)} stocks: {', '.join(stocks)}")
    print(f"Using 1-year lookback period ({LOOKBACK_DAYS} days)")
    print(f"MACD Parameters: Fast={MACD_FAST}, Slow={MACD_SLOW}, Signal={MACD_SIGNAL}")
    print("-"*120)

    # Create analyzer instance
    analyzer = MACDAnalyzer()

    # Analyze all stocks
    df = analyzer.analyze_multiple_tickers(stocks)

    # Display summary
    display_summary_table(df)

    # Display statistics
    display_detailed_stats(df)

    # Save to CSV
    output_file = "fundamentals_macd_output.csv"
    df.to_csv(output_file, index=False)

    print(f"\n✓ Complete analysis saved to: {output_file}")
    print(f"✓ Total columns: {len(df.columns)}")
    print(f"✓ Total rows: {len(df)}")
    print("\n" + "="*120)

    # Configure pandas display for full DataFrame view
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 50)

    print("\nFULL DATAFRAME:")
    print("="*120)
    print(df.to_string(index=False))
    print("="*120)

    return df


if __name__ == "__main__":
    df = main()
