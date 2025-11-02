"""
MACD Historical Score Analysis & Backtesting System
====================================================
Analyzes historical MACD scores, performs backtesting, and generates
interactive visualizations to understand strategy performance over time.

Features:
- Calculate daily historical MACD scores
- Backtest multiple trading strategies
- Interactive Plotly visualizations
- Parameter optimization
- Comprehensive performance reports

Author: Created for stock strategy research
Date: 2025
"""

import datetime as dt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
import logging
import sys
import json
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# Import our existing MACD analyzer
from fundamentals_macd import MACDAnalyzer, MACD_FAST, MACD_SLOW, MACD_SIGNAL

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

# Strategy Parameters
DEFAULT_BUY_THRESHOLD_BULLISH = 60
DEFAULT_BUY_THRESHOLD_NET = 30
DEFAULT_SELL_THRESHOLD_BEARISH = 60
DEFAULT_SELL_THRESHOLD_NET = -10
DEFAULT_PROFIT_TARGET = 0.15  # 15% profit
DEFAULT_STOP_LOSS = -0.05     # 5% stop loss
DEFAULT_MIN_HOLD_DAYS = 3      # Minimum days to hold position

# Timeframe mappings
PERIOD_DAYS = {
    '3M': 90,
    '6M': 180,
    '1Y': 365
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Trade:
    """Represents a single trade"""
    entry_date: dt.datetime
    exit_date: dt.datetime
    entry_price: float
    exit_price: float
    entry_bull_score: float
    entry_bear_score: float
    entry_net_score: float
    exit_bull_score: float
    exit_bear_score: float
    exit_net_score: float
    return_pct: float
    holding_days: int
    exit_reason: str


@dataclass
class BacktestResults:
    """Container for backtest results"""
    trades: List[Trade]
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    avg_winning_trade: float
    avg_losing_trade: float
    total_trades: int
    avg_holding_days: float
    buy_and_hold_return: float


@dataclass
class SignalConfig:
    """Configuration for signal generation"""
    strategy: str = 'adaptive'
    buy_bull_threshold: float = DEFAULT_BUY_THRESHOLD_BULLISH
    buy_net_threshold: float = DEFAULT_BUY_THRESHOLD_NET
    sell_bear_threshold: float = DEFAULT_SELL_THRESHOLD_BEARISH
    sell_net_threshold: float = DEFAULT_SELL_THRESHOLD_NET
    profit_target: float = DEFAULT_PROFIT_TARGET
    stop_loss: float = DEFAULT_STOP_LOSS
    min_hold_days: int = DEFAULT_MIN_HOLD_DAYS


# ============================================================================
# HISTORICAL ANALYZER CLASS
# ============================================================================

class MACDHistoricalAnalyzer:
    """
    Analyzes historical MACD scores and performs backtesting
    """

    def __init__(self, ticker: str, period: str = '6M'):
        """
        Initialize the historical analyzer.

        Args:
            ticker: Stock ticker symbol
            period: Analysis period ('3M', '6M', '1Y')
        """
        self.ticker = ticker
        self.period = period
        self.days_back = PERIOD_DAYS.get(period, 180)
        self.analyzer = MACDAnalyzer()
        self.api_ticker = f"{ticker}.US" if not ticker.endswith(".US") else ticker
        self.clean_ticker = self._strip_suffix(self.api_ticker)

        # Data containers
        self.price_data = None
        self.historical_scores = None
        self.signals = None
        self.backtest_results = None

    def _strip_suffix(self, ticker: str) -> str:
        """Remove .US suffix from ticker"""
        return ticker.rsplit(".", 1)[0]

    def fetch_historical_data(self) -> pd.DataFrame:
        """
        Fetch historical price data for the specified period.

        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Fetching {self.period} historical data for {self.clean_ticker}")

        # Add extra days for MACD calculation warmup
        extra_days = 50  # Need extra for 26-day slow EMA
        total_days = self.days_back + extra_days

        df = self.analyzer.get_historical_prices(
            self.api_ticker,
            days_back=total_days
        )

        if df.empty:
            raise ValueError(f"No historical data available for {self.ticker}")

        self.price_data = df
        return df

    def calculate_historical_scores(self) -> pd.DataFrame:
        """
        Calculate MACD scores for each day in the historical period.

        Returns:
            DataFrame with date index and score columns

        Note:
            This avoids look-ahead bias by calculating scores using only
            data available up to each specific date.
        """
        logger.info(f"Calculating historical MACD scores for {self.clean_ticker}")

        if self.price_data is None:
            self.fetch_historical_data()

        results = []
        df = self.price_data.copy()

        # Need at least 26 days for MACD calculation
        min_required = 30
        dates_to_analyze = df.index[-self.days_back:]

        for current_date in dates_to_analyze:
            # Get all data up to and including current date (no future data)
            historical_df = df.loc[:current_date].copy()

            if len(historical_df) < min_required:
                continue

            try:
                # Calculate MACD up to this point
                historical_df = self.analyzer.calculate_macd(historical_df)

                # Detect crossovers in historical data
                historical_df = self.analyzer.detect_crossovers(historical_df)

                # Get current values
                current_price = historical_df['close'].iloc[-1]
                current_values = historical_df.iloc[-1]

                # Calculate normalized metrics
                norm_metrics = self.analyzer.calculate_normalized_metrics(
                    historical_df, current_price
                )

                # Find last crossover
                days_since_cross, cross_type, cross_macd = \
                    self.analyzer.find_last_crossover(historical_df)

                # Analyze trend
                trend_metrics = self.analyzer.analyze_histogram_trend(historical_df)

                # Calculate various metrics
                histogram = norm_metrics['histogram_value']
                strength_score = norm_metrics['macd_strength_score']
                macd_position = "Above Signal" if histogram > 0 else "Below Signal"

                # Estimate days to cross
                days_to_cross = self.analyzer.estimate_days_to_cross(
                    histogram, trend_metrics['histogram_change']
                )

                # Calculate probability
                probability_score = self.analyzer.calculate_cross_probability(
                    histogram,
                    norm_metrics['normalized_distance_pct'],
                    trend_metrics['histogram_trend'],
                    trend_metrics['histogram_acceleration'],
                    days_to_cross
                )

                # Determine if approaching
                approaching = self.analyzer.determine_approaching_cross(
                    histogram,
                    norm_metrics['normalized_distance_pct'],
                    trend_metrics['histogram_trend'],
                    days_since_cross,
                    probability_score
                )

                # Calculate MACD scores
                bullish_score = self.analyzer.calculate_macd_bullish_score(
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
                    df=historical_df
                )

                bearish_score = self.analyzer.calculate_macd_bearish_score(
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
                    df=historical_df
                )

                net_score = bullish_score - bearish_score

                # Store results
                results.append({
                    'date': current_date,
                    'close': current_price,
                    'macd': norm_metrics['macd_value'],
                    'signal': norm_metrics['signal_value'],
                    'histogram': histogram,
                    'bullish_score': bullish_score,
                    'bearish_score': bearish_score,
                    'net_score': net_score,
                    'macd_position': macd_position,
                    'days_since_cross': days_since_cross,
                    'cross_probability': probability_score,
                    'approaching_cross': approaching
                })

            except Exception as e:
                logger.debug(f"Could not calculate scores for {current_date}: {e}")
                continue

        # Create DataFrame from results
        scores_df = pd.DataFrame(results)
        if not scores_df.empty:
            scores_df.set_index('date', inplace=True)
            scores_df.sort_index(inplace=True)

        self.historical_scores = scores_df
        logger.info(f"Calculated scores for {len(scores_df)} days")

        return scores_df

    def generate_signals(self, config: SignalConfig = None) -> pd.DataFrame:
        """
        Generate trading signals based on MACD scores.

        Args:
            config: Signal configuration parameters

        Returns:
            DataFrame with signals added
        """
        if config is None:
            config = SignalConfig()

        if self.historical_scores is None:
            self.calculate_historical_scores()

        df = self.historical_scores.copy()

        # Initialize signal columns
        df['signal'] = 0  # 0=no position, 1=long
        df['trade_entry'] = False
        df['trade_exit'] = False
        df['exit_reason'] = ''

        # Track position state
        in_position = False
        entry_price = 0
        entry_date = None
        days_held = 0

        for i in range(len(df)):
            current_date = df.index[i]
            row = df.iloc[i]

            # Check if we should exit position
            if in_position:
                days_held += 1
                current_return = (row['close'] - entry_price) / entry_price

                exit_signal = False
                exit_reason = ''

                # Check exit conditions
                if config.strategy == 'adaptive':
                    # Exit conditions for adaptive strategy
                    if row['bearish_score'] >= config.sell_bear_threshold:
                        exit_signal = True
                        exit_reason = 'Bearish Signal'
                    elif row['net_score'] <= config.sell_net_threshold:
                        exit_signal = True
                        exit_reason = 'Net Score Negative'
                    elif current_return >= config.profit_target:
                        exit_signal = True
                        exit_reason = 'Profit Target'
                    elif current_return <= config.stop_loss:
                        exit_signal = True
                        exit_reason = 'Stop Loss'

                elif config.strategy == 'simple':
                    # Simple threshold strategy
                    if row['bearish_score'] >= config.sell_bear_threshold:
                        exit_signal = True
                        exit_reason = 'Bearish Threshold'

                elif config.strategy == 'net':
                    # Net score strategy
                    if row['net_score'] <= config.sell_net_threshold:
                        exit_signal = True
                        exit_reason = 'Net Score Threshold'

                # Apply minimum holding period
                if exit_signal and days_held >= config.min_hold_days:
                    df.loc[current_date, 'trade_exit'] = True
                    df.loc[current_date, 'exit_reason'] = exit_reason
                    in_position = False
                    entry_price = 0
                    entry_date = None
                    days_held = 0
                else:
                    df.loc[current_date, 'signal'] = 1

            # Check if we should enter position
            elif not in_position:
                entry_signal = False

                if config.strategy == 'adaptive':
                    # Entry conditions for adaptive strategy
                    if (row['bullish_score'] >= config.buy_bull_threshold and
                        row['net_score'] >= config.buy_net_threshold and
                        row['bearish_score'] < 30):
                        entry_signal = True

                elif config.strategy == 'simple':
                    # Simple threshold strategy
                    if row['bullish_score'] >= config.buy_bull_threshold:
                        entry_signal = True

                elif config.strategy == 'net':
                    # Net score strategy
                    if row['net_score'] >= config.buy_net_threshold:
                        entry_signal = True

                if entry_signal:
                    df.loc[current_date, 'trade_entry'] = True
                    df.loc[current_date, 'signal'] = 1
                    in_position = True
                    entry_price = row['close']
                    entry_date = current_date
                    days_held = 1

        self.signals = df
        return df

    def run_backtest(self, config: SignalConfig = None) -> BacktestResults:
        """
        Run backtest on generated signals.

        Args:
            config: Signal configuration

        Returns:
            BacktestResults object with performance metrics
        """
        if self.signals is None:
            self.generate_signals(config)

        df = self.signals.copy()
        trades = []

        # Extract trades
        entry_date = None
        entry_price = None
        entry_scores = None

        for i in range(len(df)):
            if df.iloc[i]['trade_entry']:
                entry_date = df.index[i]
                entry_price = df.iloc[i]['close']
                entry_scores = {
                    'bull': df.iloc[i]['bullish_score'],
                    'bear': df.iloc[i]['bearish_score'],
                    'net': df.iloc[i]['net_score']
                }

            elif df.iloc[i]['trade_exit'] and entry_date is not None:
                exit_date = df.index[i]
                exit_price = df.iloc[i]['close']
                exit_scores = {
                    'bull': df.iloc[i]['bullish_score'],
                    'bear': df.iloc[i]['bearish_score'],
                    'net': df.iloc[i]['net_score']
                }

                return_pct = (exit_price - entry_price) / entry_price
                holding_days = (exit_date - entry_date).days

                trade = Trade(
                    entry_date=entry_date,
                    exit_date=exit_date,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    entry_bull_score=entry_scores['bull'],
                    entry_bear_score=entry_scores['bear'],
                    entry_net_score=entry_scores['net'],
                    exit_bull_score=exit_scores['bull'],
                    exit_bear_score=exit_scores['bear'],
                    exit_net_score=exit_scores['net'],
                    return_pct=return_pct,
                    holding_days=holding_days,
                    exit_reason=df.iloc[i]['exit_reason']
                )
                trades.append(trade)

                # Reset for next trade
                entry_date = None
                entry_price = None
                entry_scores = None

        # Calculate performance metrics
        if trades:
            trade_returns = [t.return_pct for t in trades]
            winning_trades = [r for r in trade_returns if r > 0]
            losing_trades = [r for r in trade_returns if r <= 0]

            # Calculate cumulative return
            cumulative_return = 1.0
            for r in trade_returns:
                cumulative_return *= (1 + r)
            total_return = cumulative_return - 1

            # Annualized return
            days_in_market = sum([t.holding_days for t in trades])
            years = days_in_market / 365.0
            annualized_return = (cumulative_return ** (1/years) - 1) if years > 0 else 0

            # Sharpe ratio (simplified - assuming 0% risk-free rate)
            if len(trade_returns) > 1:
                returns_std = np.std(trade_returns)
                sharpe_ratio = (np.mean(trade_returns) / returns_std * np.sqrt(252)) if returns_std > 0 else 0
            else:
                sharpe_ratio = 0

            # Maximum drawdown
            cumulative = np.cumprod(1 + np.array(trade_returns))
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0

            # Win rate
            win_rate = len(winning_trades) / len(trades) if trades else 0

            # Profit factor
            gross_profit = sum(winning_trades) if winning_trades else 0
            gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0001
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

            # Average returns
            avg_trade = np.mean(trade_returns) if trade_returns else 0
            avg_win = np.mean(winning_trades) if winning_trades else 0
            avg_loss = np.mean(losing_trades) if losing_trades else 0

            # Average holding days
            avg_holding = np.mean([t.holding_days for t in trades]) if trades else 0

        else:
            # No trades executed
            total_return = 0
            annualized_return = 0
            sharpe_ratio = 0
            max_drawdown = 0
            win_rate = 0
            profit_factor = 0
            avg_trade = 0
            avg_win = 0
            avg_loss = 0
            avg_holding = 0

        # Calculate buy and hold return
        buy_hold_return = (df.iloc[-1]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']

        results = BacktestResults(
            trades=trades,
            total_return=total_return,
            annualized_return=annualized_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_return=avg_trade,
            avg_winning_trade=avg_win,
            avg_losing_trade=avg_loss,
            total_trades=len(trades),
            avg_holding_days=avg_holding,
            buy_and_hold_return=buy_hold_return
        )

        self.backtest_results = results
        return results

    def create_interactive_chart(self) -> go.Figure:
        """
        Create interactive Plotly chart with price, scores, and signals.

        Returns:
            Plotly Figure object
        """
        if self.signals is None:
            self.generate_signals()

        df = self.signals

        # Create subplots
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.35, 0.25, 0.25, 0.15],
            subplot_titles=(
                f'{self.clean_ticker} Price & Trading Signals',
                'MACD Scores (Bullish/Bearish/Net)',
                'MACD Technical Indicators',
                'Strategy Performance'
            )
        )

        # Panel 1: Price with signals
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['close'],
                name='Price',
                line=dict(color='blue', width=1.5),
                hovertemplate='Date: %{x}<br>Price: $%{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        # Add buy signals
        buy_signals = df[df['trade_entry']]
        if not buy_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals['close'],
                    mode='markers',
                    name='Buy Signal',
                    marker=dict(
                        symbol='triangle-up',
                        size=12,
                        color='green',
                        line=dict(width=1, color='darkgreen')
                    ),
                    hovertemplate='BUY<br>Date: %{x}<br>Price: $%{y:.2f}<br>' +
                                  'Bull Score: %{customdata[0]:.1f}<br>' +
                                  'Bear Score: %{customdata[1]:.1f}<br>' +
                                  'Net Score: %{customdata[2]:.1f}<extra></extra>',
                    customdata=buy_signals[['bullish_score', 'bearish_score', 'net_score']].values
                ),
                row=1, col=1
            )

        # Add sell signals
        sell_signals = df[df['trade_exit']]
        if not sell_signals.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals['close'],
                    mode='markers',
                    name='Sell Signal',
                    marker=dict(
                        symbol='triangle-down',
                        size=12,
                        color='red',
                        line=dict(width=1, color='darkred')
                    ),
                    hovertemplate='SELL<br>Date: %{x}<br>Price: $%{y:.2f}<br>' +
                                  'Exit Reason: %{customdata}<extra></extra>',
                    customdata=sell_signals['exit_reason']
                ),
                row=1, col=1
            )

        # Shade position periods
        in_position = False
        position_start = None
        for i in range(len(df)):
            if df.iloc[i]['trade_entry']:
                in_position = True
                position_start = df.index[i]
            elif df.iloc[i]['trade_exit'] and in_position:
                fig.add_vrect(
                    x0=position_start, x1=df.index[i],
                    fillcolor="green", opacity=0.1,
                    layer="below", line_width=0,
                    row=1, col=1
                )
                in_position = False

        # Panel 2: MACD Scores
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bullish_score'],
                name='Bullish Score',
                line=dict(color='green', width=2),
                hovertemplate='Date: %{x}<br>Bullish: %{y:.1f}<extra></extra>'
            ),
            row=2, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['bearish_score'],
                name='Bearish Score',
                line=dict(color='red', width=2),
                hovertemplate='Date: %{x}<br>Bearish: %{y:.1f}<extra></extra>'
            ),
            row=2, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['net_score'],
                name='Net Score',
                line=dict(color='blue', width=2, dash='dot'),
                hovertemplate='Date: %{x}<br>Net: %{y:.1f}<extra></extra>'
            ),
            row=2, col=1
        )

        # Add threshold lines
        fig.add_hline(y=60, line_dash="dash", line_color="gray", opacity=0.5, row=2, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.3, row=2, col=1)

        # Panel 3: MACD Technical
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['macd'],
                name='MACD',
                line=dict(color='blue', width=1.5),
                hovertemplate='Date: %{x}<br>MACD: %{y:.4f}<extra></extra>'
            ),
            row=3, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['signal'],
                name='Signal',
                line=dict(color='red', width=1.5),
                hovertemplate='Date: %{x}<br>Signal: %{y:.4f}<extra></extra>'
            ),
            row=3, col=1
        )

        # Histogram bars
        colors = ['green' if h > 0 else 'red' for h in df['histogram']]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['histogram'],
                name='Histogram',
                marker_color=colors,
                opacity=0.4,
                hovertemplate='Date: %{x}<br>Histogram: %{y:.4f}<extra></extra>'
            ),
            row=3, col=1
        )

        # Panel 4: Cumulative Performance
        if self.backtest_results and self.backtest_results.trades:
            # Calculate cumulative returns
            cumulative_strategy = [1.0]
            cumulative_buyhold = [1.0]

            for i in range(1, len(df)):
                # Buy and hold
                buyhold_return = (df.iloc[i]['close'] - df.iloc[0]['close']) / df.iloc[0]['close']
                cumulative_buyhold.append(1 + buyhold_return)

                # Strategy (simplified - only when trades occur)
                strategy_value = cumulative_strategy[-1]
                if df.iloc[i]['signal'] == 1 and i > 0:
                    daily_return = (df.iloc[i]['close'] - df.iloc[i-1]['close']) / df.iloc[i-1]['close']
                    strategy_value *= (1 + daily_return)
                cumulative_strategy.append(strategy_value)

            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=[(c - 1) * 100 for c in cumulative_strategy],
                    name='Strategy Return',
                    line=dict(color='blue', width=2),
                    hovertemplate='Date: %{x}<br>Strategy: %{y:.1f}%<extra></extra>'
                ),
                row=4, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=[(c - 1) * 100 for c in cumulative_buyhold],
                    name='Buy & Hold',
                    line=dict(color='gray', width=2, dash='dash'),
                    hovertemplate='Date: %{x}<br>Buy & Hold: %{y:.1f}%<extra></extra>'
                ),
                row=4, col=1
            )

        # Update layout
        fig.update_layout(
            title=f'{self.clean_ticker} - MACD Historical Analysis ({self.period})',
            height=1000,
            showlegend=True,
            hovermode='x unified',
            xaxis_rangeslider_visible=False,
            template='plotly_white'
        )

        # Update axes labels
        fig.update_xaxes(title_text="Date", row=4, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Score", row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        fig.update_yaxes(title_text="Return (%)", row=4, col=1)

        return fig

    def optimize_parameters(self,
                           bull_range: Tuple[int, int] = (50, 80),
                           net_range: Tuple[int, int] = (20, 50),
                           step: int = 5) -> pd.DataFrame:
        """
        Optimize strategy parameters through grid search.

        Args:
            bull_range: Range for bullish threshold
            net_range: Range for net threshold
            step: Step size for grid search

        Returns:
            DataFrame with optimization results
        """
        logger.info(f"Running parameter optimization for {self.clean_ticker}")

        results = []

        for bull_thresh in range(bull_range[0], bull_range[1] + 1, step):
            for net_thresh in range(net_range[0], net_range[1] + 1, step):
                for min_hold in [1, 3, 5]:
                    # Create config
                    config = SignalConfig(
                        strategy='adaptive',
                        buy_bull_threshold=bull_thresh,
                        buy_net_threshold=net_thresh,
                        min_hold_days=min_hold
                    )

                    # Run backtest
                    self.generate_signals(config)
                    backtest = self.run_backtest(config)

                    # Store results
                    results.append({
                        'bull_threshold': bull_thresh,
                        'net_threshold': net_thresh,
                        'min_hold_days': min_hold,
                        'total_return': backtest.total_return,
                        'sharpe_ratio': backtest.sharpe_ratio,
                        'win_rate': backtest.win_rate,
                        'total_trades': backtest.total_trades,
                        'avg_holding_days': backtest.avg_holding_days,
                        'profit_factor': backtest.profit_factor
                    })

        opt_df = pd.DataFrame(results)
        opt_df.sort_values('sharpe_ratio', ascending=False, inplace=True)

        return opt_df

    def generate_report(self, save_path: str = None) -> str:
        """
        Generate comprehensive HTML report with all analyses.

        Args:
            save_path: Optional path to save report

        Returns:
            HTML string of the report
        """
        logger.info(f"Generating report for {self.clean_ticker}")

        # Ensure we have all necessary data
        if self.historical_scores is None:
            self.calculate_historical_scores()
        if self.backtest_results is None:
            self.run_backtest()

        # Create interactive chart
        chart = self.create_interactive_chart()
        chart_html = chart.to_html(include_plotlyjs='cdn', div_id='main_chart')

        # Get current MACD status
        current_scores = self.historical_scores.iloc[-1]

        # Format trade log
        trade_log_html = ""
        if self.backtest_results.trades:
            trade_rows = []
            for i, trade in enumerate(self.backtest_results.trades, 1):
                trade_rows.append(f"""
                <tr>
                    <td>{i}</td>
                    <td>{trade.entry_date.strftime('%Y-%m-%d')}</td>
                    <td>{trade.exit_date.strftime('%Y-%m-%d')}</td>
                    <td>{trade.holding_days}</td>
                    <td>${trade.entry_price:.2f}</td>
                    <td>${trade.exit_price:.2f}</td>
                    <td>{trade.entry_bull_score:.1f}</td>
                    <td>{trade.entry_net_score:.1f}</td>
                    <td class="{'positive' if trade.return_pct > 0 else 'negative'}">
                        {trade.return_pct*100:.2f}%
                    </td>
                    <td>{trade.exit_reason}</td>
                </tr>
                """)
            trade_log_html = """
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Entry Date</th>
                        <th>Exit Date</th>
                        <th>Days Held</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>Entry Bull</th>
                        <th>Entry Net</th>
                        <th>Return</th>
                        <th>Exit Reason</th>
                    </tr>
                </thead>
                <tbody>
                    {}
                </tbody>
            </table>
            """.format(''.join(trade_rows))

        # Generate HTML report
        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{ticker} - MACD Historical Analysis Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                    border-bottom: 1px solid #ecf0f1;
                    padding-bottom: 5px;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .metric-card {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                }}
                .metric-label {{
                    color: #7f8c8d;
                    font-size: 0.9em;
                    margin-bottom: 5px;
                }}
                .metric-value {{
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .positive {{ color: #27ae60; }}
                .negative {{ color: #e74c3c; }}
                .neutral {{ color: #95a5a6; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid #ecf0f1;
                }}
                th {{
                    background: #34495e;
                    color: white;
                }}
                tr:hover {{
                    background: #f8f9fa;
                }}
                .current-status {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
                .status-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    margin-top: 15px;
                }}
                .status-item {{
                    text-align: center;
                }}
                .status-label {{
                    font-size: 0.9em;
                    opacity: 0.9;
                }}
                .status-value {{
                    font-size: 2em;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{ticker} - MACD Historical Analysis Report</h1>
                <p>Period: {period} | Generated: {timestamp}</p>

                <div class="current-status">
                    <h2 style="color: white; border: none;">Current MACD Status</h2>
                    <div class="status-grid">
                        <div class="status-item">
                            <div class="status-label">Bullish Score</div>
                            <div class="status-value">{current_bull:.1f}</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">Bearish Score</div>
                            <div class="status-value">{current_bear:.1f}</div>
                        </div>
                        <div class="status-item">
                            <div class="status-label">Net Score</div>
                            <div class="status-value">{current_net:.1f}</div>
                        </div>
                    </div>
                </div>

                <h2>Backtest Performance Summary</h2>
                <div class="summary-grid">
                    <div class="metric-card">
                        <div class="metric-label">Strategy Return</div>
                        <div class="metric-value {return_class}">{total_return:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Buy & Hold Return</div>
                        <div class="metric-value {buyhold_class}">{buyhold_return:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total Trades</div>
                        <div class="metric-value">{total_trades}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value {winrate_class}">{win_rate:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value">{sharpe_ratio:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Drawdown</div>
                        <div class="metric-value negative">{max_drawdown:.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Profit Factor</div>
                        <div class="metric-value">{profit_factor:.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Holding Days</div>
                        <div class="metric-value">{avg_holding:.1f}</div>
                    </div>
                </div>

                <h2>Interactive Chart</h2>
                <div style="margin: 20px 0;">
                    {chart_html}
                </div>

                <h2>Trade Log</h2>
                {trade_log_html}

                <h2>Score Statistics</h2>
                <div class="summary-grid">
                    <div class="metric-card">
                        <div class="metric-label">Avg Bullish Score</div>
                        <div class="metric-value">{avg_bull:.1f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Avg Bearish Score</div>
                        <div class="metric-value">{avg_bear:.1f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Bullish Score</div>
                        <div class="metric-value">{max_bull:.1f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Bearish Score</div>
                        <div class="metric-value">{max_bear:.1f}</div>
                    </div>
                </div>

                <h2>Strategy Parameters</h2>
                <p>
                    <strong>Strategy Type:</strong> Adaptive Zone Strategy<br>
                    <strong>Buy Threshold (Bullish):</strong> {buy_bull_thresh}<br>
                    <strong>Buy Threshold (Net):</strong> {buy_net_thresh}<br>
                    <strong>Sell Threshold (Bearish):</strong> {sell_bear_thresh}<br>
                    <strong>Sell Threshold (Net):</strong> {sell_net_thresh}<br>
                    <strong>Profit Target:</strong> {profit_target:.1f}%<br>
                    <strong>Stop Loss:</strong> {stop_loss:.1f}%<br>
                    <strong>Min Holding Days:</strong> {min_hold_days}
                </p>
            </div>
        </body>
        </html>
        """

        # Calculate additional metrics
        return_class = 'positive' if self.backtest_results.total_return > 0 else 'negative'
        buyhold_class = 'positive' if self.backtest_results.buy_and_hold_return > 0 else 'negative'
        winrate_class = 'positive' if self.backtest_results.win_rate > 50 else 'negative'

        # Fill template
        html_report = html_template.format(
            ticker=self.clean_ticker,
            period=self.period,
            timestamp=dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            current_bull=current_scores['bullish_score'],
            current_bear=current_scores['bearish_score'],
            current_net=current_scores['net_score'],
            total_return=self.backtest_results.total_return * 100,
            buyhold_return=self.backtest_results.buy_and_hold_return * 100,
            total_trades=self.backtest_results.total_trades,
            win_rate=self.backtest_results.win_rate * 100,
            sharpe_ratio=self.backtest_results.sharpe_ratio,
            max_drawdown=self.backtest_results.max_drawdown * 100,
            profit_factor=self.backtest_results.profit_factor,
            avg_holding=self.backtest_results.avg_holding_days,
            return_class=return_class,
            buyhold_class=buyhold_class,
            winrate_class=winrate_class,
            chart_html=chart_html,
            trade_log_html=trade_log_html if trade_log_html else '<p>No trades executed</p>',
            avg_bull=self.historical_scores['bullish_score'].mean(),
            avg_bear=self.historical_scores['bearish_score'].mean(),
            max_bull=self.historical_scores['bullish_score'].max(),
            max_bear=self.historical_scores['bearish_score'].max(),
            buy_bull_thresh=DEFAULT_BUY_THRESHOLD_BULLISH,
            buy_net_thresh=DEFAULT_BUY_THRESHOLD_NET,
            sell_bear_thresh=DEFAULT_SELL_THRESHOLD_BEARISH,
            sell_net_thresh=DEFAULT_SELL_THRESHOLD_NET,
            profit_target=DEFAULT_PROFIT_TARGET * 100,
            stop_loss=DEFAULT_STOP_LOSS * 100,
            min_hold_days=DEFAULT_MIN_HOLD_DAYS
        )

        # Save report if path provided
        if save_path is None:
            save_path = f"{self.clean_ticker}_macd_historical_report.html"

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_report)

        logger.info(f"Report saved to {save_path}")
        return html_report

    def save_data(self, base_path: str = None) -> Dict[str, str]:
        """
        Save all analysis data to CSV files.

        Args:
            base_path: Base path for saving files

        Returns:
            Dictionary of saved file paths
        """
        if base_path is None:
            base_path = self.clean_ticker

        saved_files = {}

        # Save historical scores
        if self.historical_scores is not None:
            scores_path = f"{base_path}_macd_historical_scores.csv"
            self.historical_scores.to_csv(scores_path)
            saved_files['scores'] = scores_path
            logger.info(f"Saved historical scores to {scores_path}")

        # Save trade log
        if self.backtest_results and self.backtest_results.trades:
            trades_data = []
            for trade in self.backtest_results.trades:
                trades_data.append({
                    'entry_date': trade.entry_date,
                    'exit_date': trade.exit_date,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'entry_bull_score': trade.entry_bull_score,
                    'entry_bear_score': trade.entry_bear_score,
                    'entry_net_score': trade.entry_net_score,
                    'exit_bull_score': trade.exit_bull_score,
                    'exit_bear_score': trade.exit_bear_score,
                    'exit_net_score': trade.exit_net_score,
                    'return_pct': trade.return_pct,
                    'holding_days': trade.holding_days,
                    'exit_reason': trade.exit_reason
                })

            trades_df = pd.DataFrame(trades_data)
            trades_path = f"{base_path}_macd_historical_trades.csv"
            trades_df.to_csv(trades_path, index=False)
            saved_files['trades'] = trades_path
            logger.info(f"Saved trade log to {trades_path}")

        # Save performance metrics
        if self.backtest_results:
            metrics = {
                'ticker': self.clean_ticker,
                'period': self.period,
                'total_return': self.backtest_results.total_return,
                'annualized_return': self.backtest_results.annualized_return,
                'sharpe_ratio': self.backtest_results.sharpe_ratio,
                'max_drawdown': self.backtest_results.max_drawdown,
                'win_rate': self.backtest_results.win_rate,
                'profit_factor': self.backtest_results.profit_factor,
                'avg_trade_return': self.backtest_results.avg_trade_return,
                'avg_winning_trade': self.backtest_results.avg_winning_trade,
                'avg_losing_trade': self.backtest_results.avg_losing_trade,
                'total_trades': self.backtest_results.total_trades,
                'avg_holding_days': self.backtest_results.avg_holding_days,
                'buy_and_hold_return': self.backtest_results.buy_and_hold_return
            }

            metrics_path = f"{base_path}_macd_performance.json"
            with open(metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2)
            saved_files['metrics'] = metrics_path
            logger.info(f"Saved performance metrics to {metrics_path}")

        return saved_files


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def analyze_single_ticker(ticker: str, period: str = '6M', optimize: bool = False) -> MACDHistoricalAnalyzer:
    """
    Analyze a single ticker.

    Args:
        ticker: Stock ticker symbol
        period: Analysis period
        optimize: Whether to run parameter optimization

    Returns:
        MACDHistoricalAnalyzer instance
    """
    print(f"\n{'='*80}")
    print(f"Analyzing {ticker} - {period} Historical MACD Scores")
    print(f"{'='*80}")

    # Create analyzer
    analyzer = MACDHistoricalAnalyzer(ticker, period)

    # Run analysis
    analyzer.calculate_historical_scores()
    analyzer.generate_signals()
    results = analyzer.run_backtest()

    # Display results
    print(f"\nBacktest Results:")
    print(f"  Strategy Return: {results.total_return*100:.2f}%")
    print(f"  Buy & Hold Return: {results.buy_and_hold_return*100:.2f}%")
    print(f"  Total Trades: {results.total_trades}")
    print(f"  Win Rate: {results.win_rate*100:.1f}%")
    print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {results.max_drawdown*100:.2f}%")
    print(f"  Avg Holding Days: {results.avg_holding_days:.1f}")

    # Run optimization if requested
    if optimize:
        print("\nRunning parameter optimization...")
        opt_results = analyzer.optimize_parameters()
        print("\nTop 5 Parameter Combinations (by Sharpe Ratio):")
        print(opt_results.head())

    # Generate report
    analyzer.generate_report()
    analyzer.save_data()

    print(f"\n✓ Report saved: {ticker}_macd_historical_report.html")
    print(f"✓ Data saved: {ticker}_macd_historical_scores.csv")

    return analyzer


def main():
    """
    Main function to run historical MACD analysis.
    """
    import argparse

    parser = argparse.ArgumentParser(description='MACD Historical Analysis Tool')
    parser.add_argument('--ticker', type=str, help='Single ticker to analyze')
    parser.add_argument('--tickers', type=str, help='Comma-separated list of tickers')
    parser.add_argument('--period', type=str, default='6M', choices=['3M', '6M', '1Y'],
                        help='Analysis period (default: 6M)')
    parser.add_argument('--optimize', action='store_true',
                        help='Run parameter optimization')

    args = parser.parse_args()

    # Default tickers if none specified
    if not args.ticker and not args.tickers:
        tickers = ['AAPL', 'MSFT', 'NVDA']
        print(f"No tickers specified. Using defaults: {', '.join(tickers)}")
    elif args.ticker:
        tickers = [args.ticker]
    else:
        tickers = [t.strip() for t in args.tickers.split(',')]

    print("="*80)
    print("MACD HISTORICAL ANALYSIS TOOL")
    print("="*80)
    print(f"Period: {args.period}")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Optimization: {'Yes' if args.optimize else 'No'}")
    print("-"*80)

    # Analyze each ticker
    for ticker in tickers:
        try:
            analyze_single_ticker(ticker, args.period, args.optimize)
        except Exception as e:
            logger.error(f"Failed to analyze {ticker}: {e}")
            print(f"\n✗ Error analyzing {ticker}: {e}")

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)


if __name__ == "__main__":
    main()