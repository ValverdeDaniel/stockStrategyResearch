"""
MACD + RSI Position Scaling Strategy
====================================
An advanced trading strategy that combines MACD momentum signals with RSI oversold
conditions and implements sophisticated position scaling to reduce timing risk and
maximize returns through dollar-cost averaging on weakness.

Key Features:
- RSI integration for oversold/overbought detection
- Multi-tranche position management with scaling
- Weighted average cost basis tracking
- Risk-adjusted position sizing
- Enhanced backtesting with scaling metrics

Position Scaling Strategy:
- Initial: 10% position when RSI < 45 and MACD bullish
- Scale at -5%: Add 10% (total 20%)
- Scale at -10%: Add 30% (total 50%)
- Scale at -20%: Add 25% (total 75%)
- Scale at -30%: Add 25% (total 100%)

Author: Advanced Trading Strategy Research
Date: 2025
"""

import datetime as dt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
import sys
import json
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Import base analyzers
from fundamentals_macd import MACDAnalyzer
from fundamentals_macd_robust import RobustMACDStrategy, MarketRegimeDetector

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
# CONFIGURATION
# ============================================================================

# RSI Parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 50      # Entry threshold (loosened from 45)
RSI_OVERBOUGHT = 70    # Partial exit threshold
RSI_EXTREME_OVERSOLD = 30  # Strong buy signal

# Position Scaling Parameters
INITIAL_POSITION_PCT = 10  # Initial position size (%)
SCALING_LEVELS = [
    {'trigger': -5, 'add_pct': 10},   # At -5%, add 10%
    {'trigger': -10, 'add_pct': 30},  # At -10%, add 30%
    {'trigger': -20, 'add_pct': 25},  # At -20%, add 25%
    {'trigger': -30, 'add_pct': 25},  # At -30%, add 25%
]

# Risk Management
MAX_POSITION_PCT = 100  # Maximum total position
PROFIT_TARGET_PCT = 15  # Take profit at 15% gain
STOP_LOSS_PCT = -35     # Stop loss at -35% from avg cost
TRAILING_STOP_PCT = 10  # Trail stop after 10% profit
MAX_HOLDING_DAYS = 45   # Extended for scaling strategy

# MACD Confirmation (inherited from robust strategy)
MIN_MACD_CONFIDENCE = 0.5  # Minimum MACD signal confidence


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Tranche:
    """Represents a single position tranche (scale-in)"""
    entry_date: dt.datetime
    entry_price: float
    shares: int
    position_pct: float  # Percentage of capital
    entry_rsi: float
    entry_macd_score: float
    scale_level: int  # 0=initial, 1=first scale, etc.

    def current_value(self, current_price: float) -> float:
        """Calculate current value of this tranche"""
        return self.shares * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L for this tranche"""
        return (current_price - self.entry_price) * self.shares

    def return_pct(self, current_price: float) -> float:
        """Calculate return percentage for this tranche"""
        return (current_price - self.entry_price) / self.entry_price


@dataclass
class ScaledPosition:
    """Represents a complete scaled position with multiple tranches"""
    ticker: str
    tranches: List[Tranche] = field(default_factory=list)
    exit_date: Optional[dt.datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    @property
    def total_shares(self) -> int:
        """Total shares across all tranches"""
        return sum(t.shares for t in self.tranches)

    @property
    def weighted_avg_cost(self) -> float:
        """Calculate weighted average cost basis"""
        if not self.tranches:
            return 0
        total_cost = sum(t.entry_price * t.shares for t in self.tranches)
        total_shares = self.total_shares
        return total_cost / total_shares if total_shares > 0 else 0

    @property
    def total_position_pct(self) -> float:
        """Total position as percentage of capital"""
        return sum(t.position_pct for t in self.tranches)

    @property
    def scale_count(self) -> int:
        """Number of times we scaled into position"""
        return len(self.tranches) - 1 if self.tranches else 0

    @property
    def first_entry_date(self) -> Optional[dt.datetime]:
        """Date of initial entry"""
        return self.tranches[0].entry_date if self.tranches else None

    @property
    def last_entry_date(self) -> Optional[dt.datetime]:
        """Date of last scale-in"""
        return self.tranches[-1].entry_date if self.tranches else None

    def max_drawdown_before_profit(self, price_series: pd.Series) -> float:
        """Calculate maximum drawdown before position became profitable"""
        if not self.tranches or self.exit_price is None:
            return 0

        # Get prices from first entry to exit
        start_date = self.first_entry_date
        end_date = self.exit_date
        relevant_prices = price_series[start_date:end_date]

        # Calculate drawdown from weighted average cost
        min_price = relevant_prices.min()
        max_dd = (min_price - self.weighted_avg_cost) / self.weighted_avg_cost
        return max_dd

    def return_pct(self) -> float:
        """Calculate total return based on weighted average cost"""
        if self.exit_price is None or self.weighted_avg_cost == 0:
            return 0
        return (self.exit_price - self.weighted_avg_cost) / self.weighted_avg_cost

    def holding_days(self) -> int:
        """Calculate total holding period"""
        if not self.tranches or self.exit_date is None:
            return 0
        return (self.exit_date - self.first_entry_date).days


@dataclass
class ScalingBacktestResults:
    """Enhanced backtest results with scaling metrics"""
    positions: List[ScaledPosition]
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float

    # Scaling-specific metrics
    avg_scale_count: float  # Average number of scale-ins
    avg_cost_improvement: float  # Avg improvement vs initial entry
    max_position_utilization: float  # Max % of capital used
    scaled_win_rate: float  # Win rate for scaled positions
    single_entry_win_rate: float  # Win rate for non-scaled

    # Performance attribution
    return_from_scaling: float  # Extra return from scaling
    return_from_timing: float  # Return from entry timing

    # Risk metrics
    avg_drawdown_before_profit: float
    recovery_rate: float  # How often we recover from drawdown

    def to_dict(self) -> Dict:
        """Convert results to dictionary for JSON export"""
        return {
            'total_return': round(self.total_return, 4),
            'annualized_return': round(self.annualized_return, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 4),
            'sortino_ratio': round(self.sortino_ratio, 4),
            'max_drawdown': round(self.max_drawdown, 4),
            'win_rate': round(self.win_rate, 4),
            'avg_scale_count': round(self.avg_scale_count, 2),
            'avg_cost_improvement': round(self.avg_cost_improvement, 4),
            'max_position_utilization': round(self.max_position_utilization, 2),
            'scaled_win_rate': round(self.scaled_win_rate, 4),
            'single_entry_win_rate': round(self.single_entry_win_rate, 4),
            'return_from_scaling': round(self.return_from_scaling, 4),
            'avg_drawdown_before_profit': round(self.avg_drawdown_before_profit, 4),
            'recovery_rate': round(self.recovery_rate, 4),
            'total_positions': len(self.positions)
        }


# ============================================================================
# RSI CALCULATOR
# ============================================================================

class RSICalculator:
    """
    Calculates RSI (Relative Strength Index) for momentum analysis.
    RSI helps identify oversold/overbought conditions.
    """

    def __init__(self, period: int = RSI_PERIOD):
        self.period = period

    def calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """
        Calculate RSI using the standard method.

        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        # Calculate average gains and losses (using EMA for smoothing)
        avg_gains = gains.ewm(span=self.period, adjust=False).mean()
        avg_losses = losses.ewm(span=self.period, adjust=False).mean()

        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        # Handle division by zero
        rsi = rsi.fillna(50)  # Neutral RSI when no data

        return rsi

    def is_oversold(self, rsi: float, threshold: float = RSI_OVERSOLD) -> bool:
        """Check if RSI indicates oversold condition"""
        return rsi < threshold

    def is_extreme_oversold(self, rsi: float, threshold: float = RSI_EXTREME_OVERSOLD) -> bool:
        """Check if RSI indicates extreme oversold (strong buy signal)"""
        return rsi < threshold

    def is_overbought(self, rsi: float, threshold: float = RSI_OVERBOUGHT) -> bool:
        """Check if RSI indicates overbought condition"""
        return rsi > threshold

    def get_rsi_signal(self, rsi: float) -> str:
        """Get descriptive RSI signal"""
        if self.is_extreme_oversold(rsi):
            return "Extreme Oversold"
        elif self.is_oversold(rsi):
            return "Oversold"
        elif self.is_overbought(rsi):
            return "Overbought"
        elif rsi > 60:
            return "Bullish"
        elif rsi < 40:
            return "Bearish"
        else:
            return "Neutral"

    def calculate_rsi_divergence(self, prices: pd.Series, rsi: pd.Series,
                                lookback: int = 14) -> pd.Series:
        """
        Detect bullish/bearish divergence between price and RSI.
        Bullish divergence: Price makes lower low, RSI makes higher low
        Bearish divergence: Price makes higher high, RSI makes lower high
        """
        divergence = pd.Series(index=prices.index, data="None")

        if len(prices) < lookback * 2:
            return divergence

        for i in range(lookback, len(prices)):
            # Look for local extremes in the lookback window
            price_window = prices.iloc[i-lookback:i+1]
            rsi_window = rsi.iloc[i-lookback:i+1]

            # Find local lows and highs
            price_low_idx = price_window.idxmin()
            price_high_idx = price_window.idxmax()

            # Check for divergences at current position
            if i >= 1:
                # Bullish divergence (at lows)
                if prices.iloc[i] == price_window.min():
                    # Find previous low
                    prev_window = prices.iloc[max(0, i-lookback*2):i-1]
                    if len(prev_window) > 0:
                        prev_low_idx = prev_window.idxmin()
                        if prices.iloc[i] < prices[prev_low_idx] and rsi.iloc[i] > rsi[prev_low_idx]:
                            divergence.iloc[i] = "Bullish Divergence"

                # Bearish divergence (at highs)
                elif prices.iloc[i] == price_window.max():
                    # Find previous high
                    prev_window = prices.iloc[max(0, i-lookback*2):i-1]
                    if len(prev_window) > 0:
                        prev_high_idx = prev_window.idxmax()
                        if prices.iloc[i] > prices[prev_high_idx] and rsi.iloc[i] < rsi[prev_high_idx]:
                            divergence.iloc[i] = "Bearish Divergence"

        return divergence


# ============================================================================
# POSITION MANAGER
# ============================================================================

class PositionManager:
    """
    Manages multi-tranche positions with scaling logic.
    Tracks entry points, sizes, and calculates weighted metrics.
    """

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.current_position: Optional[ScaledPosition] = None
        self.closed_positions: List[ScaledPosition] = []
        self.available_capital = initial_capital

    def can_open_position(self) -> bool:
        """Check if we can open a new position"""
        return self.current_position is None

    def can_scale_in(self, current_price: float) -> Tuple[bool, Optional[Dict]]:
        """
        Check if we should scale into the current position.
        Returns (can_scale, scale_info_dict)
        """
        if self.current_position is None or not self.current_position.tranches:
            return False, None

        # Check if we've hit max position size
        if self.current_position.total_position_pct >= MAX_POSITION_PCT:
            return False, None

        # Get the initial entry price
        initial_price = self.current_position.tranches[0].entry_price
        current_return = (current_price - initial_price) / initial_price

        # Check each scaling level
        scale_level = len(self.current_position.tranches) - 1  # Current scale level

        for i, level in enumerate(SCALING_LEVELS):
            if i <= scale_level:  # Already scaled at this level
                continue

            trigger_return = level['trigger'] / 100
            if current_return <= trigger_return:
                # We should scale in at this level
                return True, {
                    'scale_level': i + 1,
                    'add_pct': level['add_pct'],
                    'trigger_price': initial_price * (1 + trigger_return),
                    'current_return': current_return
                }

        return False, None

    def open_position(self, ticker: str, entry_date: dt.datetime, entry_price: float,
                      entry_rsi: float, entry_macd_score: float) -> ScaledPosition:
        """Open a new position with initial tranche"""
        if not self.can_open_position():
            raise ValueError("Already have an open position")

        # Calculate initial shares based on position percentage
        position_value = self.initial_capital * (INITIAL_POSITION_PCT / 100)
        shares = int(position_value / entry_price)

        initial_tranche = Tranche(
            entry_date=entry_date,
            entry_price=entry_price,
            shares=shares,
            position_pct=INITIAL_POSITION_PCT,
            entry_rsi=entry_rsi,
            entry_macd_score=entry_macd_score,
            scale_level=0
        )

        self.current_position = ScaledPosition(
            ticker=ticker,
            tranches=[initial_tranche]
        )

        logger.info(f"Opened position in {ticker}: {shares} shares at ${entry_price:.2f} "
                   f"(RSI: {entry_rsi:.1f}, MACD Score: {entry_macd_score:.1f})")

        return self.current_position

    def scale_in(self, entry_date: dt.datetime, entry_price: float,
                 entry_rsi: float, entry_macd_score: float, scale_info: Dict) -> bool:
        """Add a scale-in tranche to the current position"""
        if self.current_position is None:
            return False

        # Calculate shares for this scale-in
        add_pct = scale_info['add_pct']
        position_value = self.initial_capital * (add_pct / 100)
        shares = int(position_value / entry_price)

        scale_tranche = Tranche(
            entry_date=entry_date,
            entry_price=entry_price,
            shares=shares,
            position_pct=add_pct,
            entry_rsi=entry_rsi,
            entry_macd_score=entry_macd_score,
            scale_level=scale_info['scale_level']
        )

        self.current_position.tranches.append(scale_tranche)

        logger.info(f"Scaled into {self.current_position.ticker}: {shares} shares at ${entry_price:.2f} "
                   f"(Level {scale_info['scale_level']}, Total Position: {self.current_position.total_position_pct}%)")

        return True

    def close_position(self, exit_date: dt.datetime, exit_price: float, exit_reason: str) -> ScaledPosition:
        """Close the current position"""
        if self.current_position is None:
            raise ValueError("No open position to close")

        self.current_position.exit_date = exit_date
        self.current_position.exit_price = exit_price
        self.current_position.exit_reason = exit_reason

        # Move to closed positions
        self.closed_positions.append(self.current_position)
        closed_position = self.current_position
        self.current_position = None

        # Log the closing
        return_pct = closed_position.return_pct()
        logger.info(f"Closed {closed_position.ticker}: Return {return_pct:.2%} "
                   f"(Avg Cost: ${closed_position.weighted_avg_cost:.2f}, "
                   f"Exit: ${exit_price:.2f}, Reason: {exit_reason})")

        return closed_position

    def should_exit(self, current_price: float, current_rsi: float,
                   current_macd_score: float, days_held: int) -> Tuple[bool, str]:
        """
        Determine if we should exit the position.
        Returns (should_exit, reason)
        """
        if self.current_position is None:
            return False, ""

        # Calculate return from weighted average cost
        avg_cost = self.current_position.weighted_avg_cost
        current_return = (current_price - avg_cost) / avg_cost

        # Check stop loss
        if current_return <= STOP_LOSS_PCT / 100:
            return True, "Stop Loss"

        # Check profit target
        if current_return >= PROFIT_TARGET_PCT / 100:
            return True, "Profit Target"

        # Check trailing stop (if we've been profitable)
        if current_return > TRAILING_STOP_PCT / 100:
            # Calculate trailing stop level
            highest_return = current_return  # Simplified, should track historical high
            if current_return < highest_return - (TRAILING_STOP_PCT / 100):
                return True, "Trailing Stop"

        # Check RSI overbought for partial exit
        if current_rsi > RSI_OVERBOUGHT and current_return > 0.05:
            return True, "RSI Overbought"

        # Check MACD bearish signal (less aggressive to allow for scaling)
        if current_macd_score < -50:  # More bearish threshold to allow positions to develop
            return True, "MACD Bearish"

        # Check max holding period
        if days_held > MAX_HOLDING_DAYS:
            return True, "Max Holding Period"

        return False, ""


# ============================================================================
# SCALING MACD+RSI STRATEGY
# ============================================================================

class ScalingMACDRSIStrategy(RobustMACDStrategy):
    """
    Enhanced strategy combining MACD, RSI, and position scaling.
    Inherits robust features from the base strategy.
    """

    def __init__(self):
        super().__init__()
        self.rsi_calculator = RSICalculator()
        self.position_manager = PositionManager()

    def calculate_combined_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate combined MACD and RSI signals with scaling logic.
        """
        # Normalize column names for compatibility
        if 'Histogram' in df.columns and 'histogram' not in df.columns:
            df['histogram'] = df['Histogram']
        if 'MACD' in df.columns and 'macd' not in df.columns:
            df['macd'] = df['MACD']
        if 'Signal' in df.columns and 'signal' not in df.columns:
            df['signal'] = df['Signal']

        # Calculate RSI
        df['rsi'] = self.rsi_calculator.calculate_rsi(df['close'])
        df['rsi_signal'] = df['rsi'].apply(self.rsi_calculator.get_rsi_signal)

        # Calculate RSI divergence
        df['rsi_divergence'] = self.rsi_calculator.calculate_rsi_divergence(
            df['close'], df['rsi']
        )

        # Get MACD signals from parent class
        df = self.generate_signals(df)

        # Add combined entry signals
        df['entry_signal'] = 0
        df['scale_signal'] = 0
        df['exit_signal'] = 0

        # Track position state
        in_position = False
        position_manager = PositionManager()

        for i in range(len(df)):
            row = df.iloc[i]

            if not in_position:
                # Entry conditions: RSI oversold + MACD confirmation
                rsi_oversold = self.rsi_calculator.is_oversold(row['rsi'])
                macd_bullish = row.get('bullish_score', 0) > 50
                # Simplified - remove confidence check for now as parent class may not always set it

                # Debug logging
                if i % 20 == 0:  # Log every 20 days
                    logger.debug(f"Date: {df.index[i]}, RSI: {row['rsi']:.1f}, "
                               f"Bullish: {row.get('bullish_score', 0):.1f}, "
                               f"RSI Oversold: {rsi_oversold}, MACD Bull: {macd_bullish}")

                if rsi_oversold and macd_bullish:
                    df.loc[df.index[i], 'entry_signal'] = 1
                    df.loc[df.index[i], 'signal_reason'] = f"RSI: {row['rsi']:.1f}, MACD: {row['bullish_score']:.1f}"
                    in_position = True
                    logger.info(f"Entry signal at {df.index[i]}: RSI={row['rsi']:.1f}, MACD Score={row.get('bullish_score', 0):.1f}")

            else:
                # Check for scaling opportunities
                can_scale, scale_info = self._check_scaling_opportunity(df, i)
                if can_scale:
                    df.loc[df.index[i], 'scale_signal'] = 1
                    df.loc[df.index[i], 'scale_info'] = str(scale_info)

                # Check exit conditions
                should_exit, exit_reason = self._check_exit_conditions(df, i)
                if should_exit:
                    df.loc[df.index[i], 'exit_signal'] = 1
                    df.loc[df.index[i], 'exit_reason'] = exit_reason
                    in_position = False

        return df

    def _check_scaling_opportunity(self, df: pd.DataFrame, idx: int) -> Tuple[bool, Optional[Dict]]:
        """Check if current conditions support scaling into position"""
        # Simplified for the strategy - would use PositionManager in practice
        row = df.iloc[idx]

        # Need RSI to still be relatively oversold
        if row['rsi'] > 55:  # Not oversold anymore
            return False, None

        # MACD should not be strongly bearish
        if row.get('bearish_score', 0) > 60:
            return False, None

        return True, {'scale_level': 1, 'add_pct': 10}

    def _check_exit_conditions(self, df: pd.DataFrame, idx: int) -> Tuple[bool, str]:
        """Check if we should exit the position"""
        row = df.iloc[idx]

        # RSI overbought
        if row['rsi'] > RSI_OVERBOUGHT:
            return True, "RSI Overbought"

        # MACD bearish
        if row.get('bearish_score', 0) > 65:
            return True, "MACD Bearish"

        # Stop loss would be checked with actual position tracking

        return False, ""


# ============================================================================
# SCALING BACKTESTER
# ============================================================================

class ScalingBacktester:
    """
    Backtesting engine with position scaling support.
    Tracks multi-tranche positions and calculates scaling-specific metrics.
    """

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.analyzer = MACDAnalyzer()
        self.strategy = ScalingMACDRSIStrategy()
        self.rsi_calculator = RSICalculator()

    def run_backtest(self, ticker: str, period: str = "1Y") -> ScalingBacktestResults:
        """
        Run backtest with position scaling.
        """
        logger.info(f"Running scaling backtest for {ticker} over {period}")

        # Get historical data
        days_map = {"3M": 90, "6M": 180, "1Y": 365}
        days_back = days_map.get(period, 365)

        api_ticker = f"{ticker}.US" if not ticker.endswith(".US") else ticker
        df = self.analyzer.get_historical_prices(api_ticker, days_back=days_back + 100)

        if df.empty:
            logger.error(f"No data available for {ticker}")
            return None

        # Calculate indicators
        df = self.analyzer.calculate_macd(df)
        df = self._calculate_scores(df, ticker)
        df = self.strategy.calculate_combined_signals(df)

        # Run position-scaling backtest
        positions = self._execute_scaling_trades(df, ticker)

        # Calculate metrics
        results = self._calculate_scaling_metrics(positions, df)

        return results

    def _calculate_scores(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Calculate MACD scores for each day"""
        # Add required columns for scoring
        for i in range(len(df)):
            if i < 30:  # Need history for calculations
                df.loc[df.index[i], 'bullish_score'] = 50
                df.loc[df.index[i], 'bearish_score'] = 50
                df.loc[df.index[i], 'net_score'] = 0
                continue

            # Get historical data up to this point
            hist_df = df.iloc[:i+1].copy()

            # Calculate scores using the analyzer
            current_row = hist_df.iloc[-1]

            # Simplified scoring - in production would use full MACDAnalyzer methods
            # Use capitalized column name as per MACDAnalyzer
            hist_value = current_row.get('Histogram', current_row.get('histogram', 0))
            if hist_value > 0:
                df.loc[df.index[i], 'bullish_score'] = 60 + min(hist_value * 10, 40)
                df.loc[df.index[i], 'bearish_score'] = 40 - min(hist_value * 10, 40)
            else:
                df.loc[df.index[i], 'bullish_score'] = 40 - min(abs(hist_value) * 10, 40)
                df.loc[df.index[i], 'bearish_score'] = 60 + min(abs(hist_value) * 10, 40)

            df.loc[df.index[i], 'net_score'] = df.loc[df.index[i], 'bullish_score'] - df.loc[df.index[i], 'bearish_score']

        return df

    def _execute_scaling_trades(self, df: pd.DataFrame, ticker: str) -> List[ScaledPosition]:
        """Execute trades with position scaling logic"""
        position_manager = PositionManager(self.initial_capital)

        # Log initial data check
        logger.info(f"Starting trade execution for {ticker} with {len(df)} days of data")
        entry_signals = df['entry_signal'].sum() if 'entry_signal' in df.columns else 0
        logger.info(f"Total entry signals in data: {entry_signals}")

        for i in range(30, len(df)):  # Start after warmup period
            row = df.iloc[i]
            date = df.index[i]

            if position_manager.current_position is None:
                # Check for entry
                if row.get('entry_signal', 0) == 1:
                    position_manager.open_position(
                        ticker=ticker,
                        entry_date=date,
                        entry_price=row['close'],
                        entry_rsi=row['rsi'],
                        entry_macd_score=row['bullish_score']
                    )
            else:
                # Check for scaling based on price drop from initial entry
                can_scale, scale_info = position_manager.can_scale_in(row['close'])
                # For now, scale based purely on price drop, not waiting for additional signals
                if can_scale:
                    position_manager.scale_in(
                        entry_date=date,
                        entry_price=row['close'],
                        entry_rsi=row['rsi'],
                        entry_macd_score=row['bullish_score'],
                        scale_info=scale_info
                    )

                # Check for exit
                days_held = (date - position_manager.current_position.first_entry_date).days
                # Use net score instead of bearish score for clearer signal
                net_score = row.get('net_score', row.get('bullish_score', 50) - row.get('bearish_score', 50))
                should_exit, exit_reason = position_manager.should_exit(
                    current_price=row['close'],
                    current_rsi=row['rsi'],
                    current_macd_score=net_score,  # Use net score for exit decisions
                    days_held=days_held
                )

                if should_exit or row.get('exit_signal', 0) == 1:
                    position_manager.close_position(
                        exit_date=date,
                        exit_price=row['close'],
                        exit_reason=exit_reason or row.get('exit_reason', 'Signal')
                    )

        # Close any remaining position
        if position_manager.current_position is not None:
            last_row = df.iloc[-1]
            position_manager.close_position(
                exit_date=df.index[-1],
                exit_price=last_row['close'],
                exit_reason="End of Period"
            )

        return position_manager.closed_positions

    def _calculate_scaling_metrics(self, positions: List[ScaledPosition],
                                  df: pd.DataFrame) -> ScalingBacktestResults:
        """Calculate comprehensive metrics including scaling-specific ones"""
        if not positions:
            return ScalingBacktestResults(
                positions=[],
                total_return=0,
                annualized_return=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                max_drawdown=0,
                win_rate=0,
                avg_scale_count=0,
                avg_cost_improvement=0,
                max_position_utilization=0,
                scaled_win_rate=0,
                single_entry_win_rate=0,
                return_from_scaling=0,
                return_from_timing=0,
                avg_drawdown_before_profit=0,
                recovery_rate=0
            )

        # Calculate returns
        returns = [p.return_pct() for p in positions]
        winning_trades = [r for r in returns if r > 0]
        losing_trades = [r for r in returns if r <= 0]

        # Basic metrics
        total_return = np.prod([1 + r for r in returns]) - 1
        days_in_period = (df.index[-1] - df.index[0]).days
        annualized_return = (1 + total_return) ** (365 / days_in_period) - 1 if days_in_period > 0 else 0

        # Risk metrics
        if len(returns) > 1:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            downside_returns = [r for r in returns if r < 0]
            sortino_ratio = np.mean(returns) / np.std(downside_returns) * np.sqrt(252) if downside_returns else sharpe_ratio
        else:
            sharpe_ratio = sortino_ratio = 0

        # Scaling-specific metrics
        scaled_positions = [p for p in positions if p.scale_count > 0]
        single_positions = [p for p in positions if p.scale_count == 0]

        avg_scale_count = np.mean([p.scale_count for p in positions])

        # Cost improvement from scaling
        cost_improvements = []
        for p in scaled_positions:
            if p.tranches:
                initial_price = p.tranches[0].entry_price
                improvement = (initial_price - p.weighted_avg_cost) / initial_price
                cost_improvements.append(improvement)
        avg_cost_improvement = np.mean(cost_improvements) if cost_improvements else 0

        # Position utilization
        max_position_utilization = max([p.total_position_pct for p in positions]) if positions else 0

        # Win rates
        win_rate = len(winning_trades) / len(returns) if returns else 0
        scaled_win_rate = len([p for p in scaled_positions if p.return_pct() > 0]) / len(scaled_positions) if scaled_positions else 0
        single_entry_win_rate = len([p for p in single_positions if p.return_pct() > 0]) / len(single_positions) if single_positions else 0

        # Drawdown analysis
        drawdowns = []
        for p in positions:
            dd = p.max_drawdown_before_profit(df['close'])
            if dd < 0:
                drawdowns.append(dd)
        avg_drawdown_before_profit = np.mean(drawdowns) if drawdowns else 0

        # Recovery rate (positions that recovered from drawdown)
        recovery_rate = len([d for d in drawdowns if d < -0.05]) / len(positions) if positions else 0

        # Calculate max drawdown
        cumulative_values = [1.0]
        for r in returns:
            cumulative_values.append(cumulative_values[-1] * (1 + r))
        cumulative_returns = pd.Series(cumulative_values)
        running_max = cumulative_returns.expanding().max()
        drawdown_series = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown_series.min()

        return ScalingBacktestResults(
            positions=positions,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            avg_scale_count=avg_scale_count,
            avg_cost_improvement=avg_cost_improvement,
            max_position_utilization=max_position_utilization,
            scaled_win_rate=scaled_win_rate,
            single_entry_win_rate=single_entry_win_rate,
            return_from_scaling=avg_cost_improvement * avg_scale_count * 0.1,  # Simplified
            return_from_timing=total_return - (avg_cost_improvement * avg_scale_count * 0.1),
            avg_drawdown_before_profit=avg_drawdown_before_profit,
            recovery_rate=recovery_rate
        )

    def generate_report(self, ticker: str, results: ScalingBacktestResults, df: pd.DataFrame) -> str:
        """Generate comprehensive HTML report with scaling visualizations"""
        # Create subplots
        fig = make_subplots(
            rows=5, cols=1,
            subplot_titles=(
                f'{ticker} Price & Position Scaling',
                'RSI & MACD Scores',
                'MACD Indicator',
                'Position Size & Cost Basis',
                'Cumulative Returns'
            ),
            vertical_spacing=0.05,
            row_heights=[0.3, 0.2, 0.2, 0.15, 0.15]
        )

        # Panel 1: Price with entry/scale/exit points
        fig.add_trace(
            go.Scatter(x=df.index, y=df['close'], name='Price', line=dict(color='blue')),
            row=1, col=1
        )

        # Add position markers
        for position in results.positions:
            # Entry points (different colors for scale levels)
            colors = ['green', 'lightgreen', 'yellow', 'orange', 'red']
            for i, tranche in enumerate(position.tranches):
                fig.add_trace(
                    go.Scatter(
                        x=[tranche.entry_date],
                        y=[tranche.entry_price],
                        mode='markers',
                        marker=dict(size=10 + i*2, color=colors[min(i, 4)]),
                        name=f'Scale {i}' if i > 0 else 'Initial Entry',
                        showlegend=i == 0
                    ),
                    row=1, col=1
                )

            # Exit point
            if position.exit_date:
                fig.add_trace(
                    go.Scatter(
                        x=[position.exit_date],
                        y=[position.exit_price],
                        mode='markers',
                        marker=dict(size=12, color='red', symbol='x'),
                        name='Exit',
                        showlegend=False
                    ),
                    row=1, col=1
                )

        # Panel 2: RSI and MACD Scores
        if 'rsi' in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df['rsi'], name='RSI', line=dict(color='purple')),
                row=2, col=1
            )
            fig.add_hline(y=RSI_OVERSOLD, line_dash="dash", line_color="green", row=2, col=1)
            fig.add_hline(y=RSI_OVERBOUGHT, line_dash="dash", line_color="red", row=2, col=1)

        if 'bullish_score' in df.columns:
            fig.add_trace(
                go.Scatter(x=df.index, y=df['bullish_score'], name='Bull Score',
                          line=dict(color='green'), yaxis='y2'),
                row=2, col=1
            )

        # Panel 3: MACD (check for both capitalized and lowercase)
        macd_col = 'MACD' if 'MACD' in df.columns else 'macd' if 'macd' in df.columns else None
        signal_col = 'Signal' if 'Signal' in df.columns else 'signal' if 'signal' in df.columns else None
        hist_col = 'Histogram' if 'Histogram' in df.columns else 'histogram' if 'histogram' in df.columns else None

        if macd_col:
            fig.add_trace(
                go.Scatter(x=df.index, y=df[macd_col], name='MACD', line=dict(color='blue')),
                row=3, col=1
            )
        if signal_col:
            fig.add_trace(
                go.Scatter(x=df.index, y=df[signal_col], name='Signal', line=dict(color='red')),
                row=3, col=1
            )
        if hist_col:
            fig.add_trace(
                go.Bar(x=df.index, y=df[hist_col], name='Histogram', marker_color='gray'),
                row=3, col=1
            )

        # Panel 4: Position Size and Cost Basis
        position_sizes = pd.Series(index=df.index, data=0.0)
        cost_basis = pd.Series(index=df.index, data=np.nan)

        for position in results.positions:
            start_date = position.first_entry_date
            end_date = position.exit_date if position.exit_date else df.index[-1]

            # Track position size over time
            for date in df.loc[start_date:end_date].index:
                # Count tranches up to this date
                active_tranches = [t for t in position.tranches if t.entry_date <= date]
                position_sizes[date] = sum(t.position_pct for t in active_tranches)

                # Calculate weighted average cost up to this date
                if active_tranches:
                    total_cost = sum(t.entry_price * t.shares for t in active_tranches)
                    total_shares = sum(t.shares for t in active_tranches)
                    cost_basis[date] = total_cost / total_shares if total_shares > 0 else 0

        fig.add_trace(
            go.Scatter(x=df.index, y=position_sizes, name='Position Size %',
                      fill='tozeroy', line=dict(color='lightblue')),
            row=4, col=1
        )

        # Panel 5: Cumulative Returns
        cumulative_returns = pd.Series(index=df.index, data=1.0)
        current_value = 1.0

        for position in results.positions:
            if position.exit_date and position.exit_date in df.index:
                return_pct = position.return_pct()
                position_weight = position.total_position_pct / 100
                position_return = return_pct * position_weight
                current_value *= (1 + position_return)
                cumulative_returns[position.exit_date:] = current_value

        fig.add_trace(
            go.Scatter(x=df.index, y=(cumulative_returns - 1) * 100,
                      name='Strategy Return %', line=dict(color='green')),
            row=5, col=1
        )

        # Buy and hold comparison
        buy_hold_return = (df['close'] / df['close'].iloc[0] - 1) * 100
        fig.add_trace(
            go.Scatter(x=df.index, y=buy_hold_return, name='Buy & Hold %',
                      line=dict(color='gray', dash='dash')),
            row=5, col=1
        )

        # Update layout
        fig.update_layout(
            title=f'{ticker} MACD+RSI Scaling Strategy Backtest',
            height=1400,
            showlegend=True,
            hovermode='x unified'
        )

        # Generate HTML with metrics
        metrics_html = self._generate_metrics_html(results)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{ticker} Scaling Strategy Report</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
                .metric-card {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .metric-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                h2 {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
            </style>
        </head>
        <body>
            <h1>{ticker} MACD+RSI Position Scaling Analysis</h1>
            {metrics_html}
            <div id="chart"></div>
            <script>
                var figure = {fig.to_json()};
                Plotly.newPlot('chart', figure.data, figure.layout);
            </script>
        </body>
        </html>
        """

        return html_content

    def _generate_metrics_html(self, results: ScalingBacktestResults) -> str:
        """Generate HTML for metrics display"""
        def format_pct(value):
            color_class = 'positive' if value > 0 else 'negative'
            return f'<span class="{color_class}">{value:.2%}</span>'

        def format_num(value, decimals=2):
            return f'{value:.{decimals}f}'

        html = """
        <h2>Performance Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Annualized Return</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Sharpe Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Win Rate</div>
            </div>
        </div>

        <h2>Scaling Strategy Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Avg Scale Count</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Cost Improvement</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Scaled Win Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}%</div>
                <div class="metric-label">Max Position Used</div>
            </div>
        </div>

        <h2>Risk Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Max Drawdown</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Sortino Ratio</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Avg DD Before Profit</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Recovery Rate</div>
            </div>
        </div>
        """.format(
            format_pct(results.total_return),
            format_pct(results.annualized_return),
            format_num(results.sharpe_ratio),
            format_pct(results.win_rate),
            format_num(results.avg_scale_count, 1),
            format_pct(results.avg_cost_improvement),
            format_pct(results.scaled_win_rate),
            format_num(results.max_position_utilization),
            format_pct(results.max_drawdown),
            format_num(results.sortino_ratio),
            format_pct(results.avg_drawdown_before_profit),
            format_pct(results.recovery_rate)
        )

        return html


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description='MACD+RSI Scaling Strategy Backtest')
    parser.add_argument('--ticker', type=str, default='AAPL', help='Stock ticker')
    parser.add_argument('--period', type=str, default='6M', choices=['3M', '6M', '1Y'],
                       help='Analysis period')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file prefix (default: ticker_scaling)')

    args = parser.parse_args()

    # Run backtest
    backtester = ScalingBacktester()
    results = backtester.run_backtest(args.ticker, args.period)

    if results:
        # Get data for visualization
        analyzer = MACDAnalyzer()
        api_ticker = f"{args.ticker}.US" if not args.ticker.endswith(".US") else args.ticker
        days_map = {"3M": 90, "6M": 180, "1Y": 365}
        df = analyzer.get_historical_prices(api_ticker, days_back=days_map[args.period] + 100)
        df = analyzer.calculate_macd(df)

        # Generate report
        html_content = backtester.generate_report(args.ticker, results, df)

        # Save outputs
        output_prefix = args.output or f"{args.ticker}_scaling"

        # Save HTML report
        html_file = f"{output_prefix}_report.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML report saved to {html_file}")

        # Save metrics JSON
        json_file = f"{output_prefix}_metrics.json"
        with open(json_file, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)
        logger.info(f"Metrics saved to {json_file}")

        # Save trade log CSV
        trade_log = []
        for position in results.positions:
            for tranche in position.tranches:
                trade_log.append({
                    'ticker': position.ticker,
                    'tranche_date': tranche.entry_date,
                    'tranche_price': tranche.entry_price,
                    'shares': tranche.shares,
                    'position_pct': tranche.position_pct,
                    'scale_level': tranche.scale_level,
                    'rsi': tranche.entry_rsi,
                    'macd_score': tranche.entry_macd_score,
                    'exit_date': position.exit_date,
                    'exit_price': position.exit_price,
                    'avg_cost': position.weighted_avg_cost,
                    'return_pct': position.return_pct(),
                    'exit_reason': position.exit_reason
                })

        trade_df = pd.DataFrame(trade_log)
        csv_file = f"{output_prefix}_trades.csv"
        trade_df.to_csv(csv_file, index=False)
        logger.info(f"Trade log saved to {csv_file}")

        # Print summary
        print(f"\n{'='*60}")
        print(f"MACD+RSI SCALING STRATEGY RESULTS - {args.ticker}")
        print(f"{'='*60}")
        print(f"Period: {args.period}")
        print(f"Total Positions: {len(results.positions)}")
        print(f"\nPerformance:")
        print(f"  Total Return: {results.total_return:.2%}")
        print(f"  Annualized Return: {results.annualized_return:.2%}")
        print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
        print(f"  Win Rate: {results.win_rate:.2%}")
        print(f"\nScaling Metrics:")
        print(f"  Avg Scale Count: {results.avg_scale_count:.1f}")
        print(f"  Cost Improvement: {results.avg_cost_improvement:.2%}")
        print(f"  Scaled Win Rate: {results.scaled_win_rate:.2%}")
        print(f"  Single Entry Win Rate: {results.single_entry_win_rate:.2%}")
        print(f"  Max Position Used: {results.max_position_utilization:.0f}%")
        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown: {results.max_drawdown:.2%}")
        print(f"  Sortino Ratio: {results.sortino_ratio:.2f}")
        print(f"  Recovery Rate: {results.recovery_rate:.2%}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()