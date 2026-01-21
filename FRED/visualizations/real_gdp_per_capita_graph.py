"""
Real GDP per Capita Visualization Module
Creates interactive graphs for Real GDP per Capita data from FRED
"""

import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.fred_fetcher import FREDDataFetcher
from config import FRED_SERIES_IDS, PLOT_THEME, FIGURE_WIDTH, FIGURE_HEIGHT

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealGDPPerCapitaVisualizer:
    """
    Creates visualizations for Real GDP per Capita data
    Shows economic output per person, adjusted for inflation
    """

    def __init__(self, fetcher: FREDDataFetcher = None):
        """Initialize Real GDP per Capita Visualizer"""
        self.fetcher = fetcher or FREDDataFetcher()
        self.series_id = FRED_SERIES_IDS['real_gdp_per_capita']

    def fetch_gdp_per_capita_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch Real GDP per Capita data with calculated metrics

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with GDP per capita and calculated metrics
        """
        # Fetch Real GDP per Capita
        df = self.fetcher.fetch_series(self.series_id, start_date, end_date)

        # Calculate quarter-over-quarter growth
        df['QoQ_Growth'] = self.fetcher.calculate_growth_rate(df, self.series_id, periods=1)

        # Calculate year-over-year growth
        df['YoY_Growth'] = self.fetcher.calculate_yoy_growth(df, self.series_id)

        # Calculate moving averages
        df['MA_4Q'] = df[self.series_id].rolling(window=4).mean()
        df['MA_8Q'] = df[self.series_id].rolling(window=8).mean()

        # Calculate compound annual growth rate (CAGR) over rolling periods
        df['CAGR_5Y'] = self._calculate_rolling_cagr(df[self.series_id], periods=20)  # 5 years of quarters
        df['CAGR_10Y'] = self._calculate_rolling_cagr(df[self.series_id], periods=40)  # 10 years of quarters

        # Calculate relative to base year (normalize to 100)
        base_year_value = df[self.series_id].iloc[0] if len(df) > 0 else 100
        df['Index_Base100'] = (df[self.series_id] / base_year_value) * 100

        # Identify growth phases
        df['Growth_Phase'] = 'Normal'
        df.loc[df['YoY_Growth'] > 3, 'Growth_Phase'] = 'Strong Growth'
        df.loc[df['YoY_Growth'] < 0, 'Growth_Phase'] = 'Contraction'
        df.loc[(df['YoY_Growth'] >= 0) & (df['YoY_Growth'] < 1), 'Growth_Phase'] = 'Slow Growth'

        return df

    def _calculate_rolling_cagr(self, series: pd.Series, periods: int) -> pd.Series:
        """Calculate rolling Compound Annual Growth Rate"""
        cagr = pd.Series(index=series.index, dtype=float)
        for i in range(periods, len(series)):
            start_val = series.iloc[i - periods]
            end_val = series.iloc[i]
            years = periods / 4  # Convert quarters to years
            if start_val > 0:
                cagr.iloc[i] = ((end_val / start_val) ** (1 / years) - 1) * 100
        return cagr

    def create_interactive_graph(self, start_date: str = None,
                                end_date: str = None) -> go.Figure:
        """
        Create comprehensive interactive Real GDP per Capita visualization

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_gdp_per_capita_data(start_date, end_date)

        # Get series info
        info = self.fetcher.get_series_info(self.series_id)

        # Create figure with subplots
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=(
                'Real GDP per Capita (Chained 2017 Dollars)',
                'Year-over-Year Growth Rate',
                'Indexed Growth (Base = 100)',
                'Rolling 5-Year CAGR'
            ),
            vertical_spacing=0.08,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. Main GDP per Capita Chart
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[self.series_id],
                mode='lines',
                name='Real GDP per Capita',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>GDP/Capita: $%{y:,.0f}<extra></extra>'
            ),
            row=1, col=1
        )

        # Add trend line (moving average)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MA_8Q'],
                mode='lines',
                name='8-Quarter MA',
                line=dict(color='#A23B72', width=1, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>8Q MA: $%{y:,.0f}<extra></extra>'
            ),
            row=1, col=1
        )

        # 2. Year-over-Year Growth
        colors_yoy = ['green' if x > 0 else 'red' for x in df['YoY_Growth'].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['YoY_Growth'],
                name='YoY Growth',
                marker_color=colors_yoy,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>YoY Growth: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Add zero line and average growth line
        fig.add_hline(y=0, row=2, col=1, line_dash="solid", line_color="black", line_width=1)
        avg_growth = df['YoY_Growth'].mean()
        fig.add_hline(y=avg_growth, row=2, col=1, line_dash="dash", line_color="blue", line_width=1,
                     annotation_text=f"Avg: {avg_growth:.1f}%")

        # 3. Indexed Growth
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Index_Base100'],
                mode='lines',
                name='Growth Index',
                line=dict(color='#FF7F0E', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 127, 14, 0.1)',
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Index: %{y:.1f}<extra></extra>'
            ),
            row=3, col=1
        )

        # Add base line
        fig.add_hline(y=100, row=3, col=1, line_dash="dash", line_color="gray", line_width=1)

        # 4. Rolling CAGR
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['CAGR_5Y'],
                mode='lines',
                name='5-Year CAGR',
                line=dict(color='#2CA02C', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>5Y CAGR: %{y:.2f}%<extra></extra>'
            ),
            row=4, col=1
        )

        # Add long-term average CAGR
        long_term_cagr = df['CAGR_5Y'].mean()
        fig.add_hline(y=long_term_cagr, row=4, col=1, line_dash="dash", line_color="gray", line_width=1,
                     annotation_text=f"LT Avg: {long_term_cagr:.1f}%")

        # Add recession shading
        recessions = [
            ('2001-03-01', '2001-11-01', 'Dot-com Recession'),
            ('2007-12-01', '2009-06-01', 'Great Recession'),
            ('2020-02-01', '2020-04-01', 'COVID-19 Recession')
        ]

        for start, end, name in recessions:
            if pd.to_datetime(start) >= df.index[0]:
                for row in [1, 2, 3, 4]:
                    fig.add_vrect(
                        x0=start, x1=end,
                        fillcolor="gray", opacity=0.2,
                        layer="below", line_width=0,
                        row=row, col=1
                    )

        # Update layout
        fig.update_layout(
            title={
                'text': f"US Real GDP per Capita Analysis<br><sub>Economic Output per Person (Inflation-Adjusted)</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            template=PLOT_THEME,
            height=FIGURE_HEIGHT + 400,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(title=""),
            yaxis=dict(title="Dollars (2017)"),
            xaxis2=dict(title=""),
            yaxis2=dict(title="Growth Rate (%)"),
            xaxis3=dict(title=""),
            yaxis3=dict(title="Index Value"),
            xaxis4=dict(title="Date"),
            yaxis4=dict(title="CAGR (%)")
        )

        # Add annotations for latest values and statistics
        if len(df) > 0:
            latest_date = df.index[-1]
            latest_value = df[self.series_id].iloc[-1]
            latest_yoy = df['YoY_Growth'].iloc[-1]
            first_value = df[self.series_id].iloc[0]
            total_growth = ((latest_value / first_value) - 1) * 100

            # Latest value annotation
            fig.add_annotation(
                text=f"Latest ({latest_date.strftime('%Y-%m-%d')})<br>"
                     f"${latest_value:,.0f} per capita<br>"
                     f"YoY: {latest_yoy:.1f}%",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

            # Total growth annotation
            fig.add_annotation(
                text=f"Total Growth: {total_growth:.1f}%<br>"
                     f"Since {df.index[0].strftime('%Y')}",
                xref="paper", yref="paper",
                x=0.02, y=0.92,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

        return fig

    def create_comparison_graph(self, start_date: str = None,
                               end_date: str = None) -> go.Figure:
        """
        Create comparison of GDP per capita growth across different time periods

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_gdp_per_capita_data(start_date, end_date)

        # Create decade averages
        df['Decade'] = (df.index.year // 10) * 10
        decade_growth = df.groupby('Decade')['YoY_Growth'].mean()

        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Real GDP per Capita - Long-term Trend',
                'Average Growth by Decade'
            ),
            vertical_spacing=0.15
        )

        # 1. Long-term trend with regression
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[self.series_id],
                mode='lines',
                name='Actual',
                line=dict(color='#1F77B4', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Value: $%{y:,.0f}<extra></extra>'
            ),
            row=1, col=1
        )

        # Add exponential trend line
        x_numeric = np.arange(len(df))
        z = np.polyfit(x_numeric, np.log(df[self.series_id].values), 1)
        p = np.poly1d(z)
        trend_values = np.exp(p(x_numeric))

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=trend_values,
                mode='lines',
                name='Exponential Trend',
                line=dict(color='#FF7F0E', width=2, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Trend: $%{y:,.0f}<extra></extra>'
            ),
            row=1, col=1
        )

        # 2. Decade averages
        fig.add_trace(
            go.Bar(
                x=[f"{d}s" for d in decade_growth.index],
                y=decade_growth.values,
                name='Avg Growth by Decade',
                marker_color=['green' if x > 0 else 'red' for x in decade_growth.values],
                hovertemplate='Decade: %{x}<br>Avg Growth: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Add zero line
        fig.add_hline(y=0, row=2, col=1, line_dash="solid", line_color="black", line_width=1)

        # Update layout
        fig.update_layout(
            title="Real GDP per Capita - Historical Perspective",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT,
            width=FIGURE_WIDTH,
            showlegend=True,
            xaxis=dict(title="Date"),
            yaxis=dict(title="Dollars (2017)"),
            xaxis2=dict(title="Decade"),
            yaxis2=dict(title="Average Growth Rate (%)")
        )

        return fig

    def save_graph(self, fig: go.Figure = None, filename: str = 'real_gdp_per_capita_graph.html',
                  auto_open: bool = False):
        """
        Save interactive graph to HTML file

        Args:
            fig: Plotly figure to save (creates new if None)
            filename: Output filename
            auto_open: Whether to open in browser
        """
        if fig is None:
            fig = self.create_interactive_graph()

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        pyo.plot(fig, filename=output_path, auto_open=auto_open)
        logger.info(f"Graph saved to {output_path}")

    def export_data(self, start_date: str = None, end_date: str = None,
                   filename: str = 'real_gdp_per_capita_data.csv'):
        """
        Export GDP per capita data to CSV

        Args:
            start_date: Start date for data
            end_date: End date for data
            filename: Output filename
        """
        df = self.fetch_gdp_per_capita_data(start_date, end_date)

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path)
        logger.info(f"Data exported to {output_path}")


def main():
    """Main function to create and save Real GDP per Capita visualizations"""
    print("Creating Real GDP per Capita Visualizations...")

    # Initialize visualizer
    viz = RealGDPPerCapitaVisualizer()

    # Create main graph
    fig1 = viz.create_interactive_graph(start_date='1980-01-01')
    viz.save_graph(fig1, 'real_gdp_per_capita_analysis.html')

    # Create comparison graph
    fig2 = viz.create_comparison_graph(start_date='1960-01-01')
    viz.save_graph(fig2, 'gdp_per_capita_historical.html')

    # Export data
    viz.export_data(start_date='1980-01-01', filename='real_gdp_per_capita_data.csv')

    print("Real GDP per Capita visualizations completed successfully!")


if __name__ == "__main__":
    main()