"""
Unemployment Rate Visualization Module
Creates interactive graphs for unemployment data from FRED
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


class UnemploymentVisualizer:
    """
    Creates visualizations for unemployment data
    """

    def __init__(self, fetcher: FREDDataFetcher = None):
        """Initialize Unemployment Visualizer"""
        self.fetcher = fetcher or FREDDataFetcher()
        self.series_id = FRED_SERIES_IDS['unemployment']

    def fetch_unemployment_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch unemployment data with calculated metrics

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with unemployment rate and calculated metrics
        """
        # Fetch unemployment rate
        df = self.fetcher.fetch_series(self.series_id, start_date, end_date)

        # Calculate month-over-month change
        df['MoM_Change'] = df[self.series_id].diff()

        # Calculate year-over-year change
        df['YoY_Change'] = df[self.series_id].diff(12)

        # Calculate moving averages
        df['MA_3M'] = df[self.series_id].rolling(window=3).mean()
        df['MA_6M'] = df[self.series_id].rolling(window=6).mean()
        df['MA_12M'] = df[self.series_id].rolling(window=12).mean()

        # Calculate rate of change
        df['Rate_of_Change'] = (df[self.series_id] - df[self.series_id].shift(3)) / df[self.series_id].shift(3) * 100

        # Identify trend (simple classification)
        df['Trend'] = 'Stable'
        df.loc[df['Rate_of_Change'] > 5, 'Trend'] = 'Rising'
        df.loc[df['Rate_of_Change'] < -5, 'Trend'] = 'Falling'

        return df

    def create_interactive_graph(self, start_date: str = None,
                                end_date: str = None) -> go.Figure:
        """
        Create comprehensive interactive unemployment visualization

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_unemployment_data(start_date, end_date)

        # Get series info
        info = self.fetcher.get_series_info(self.series_id)

        # Create figure with subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'US Unemployment Rate',
                'Month-over-Month Change',
                'Year-over-Year Change'
            ),
            vertical_spacing=0.12,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. Main Unemployment Rate Chart
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[self.series_id],
                mode='lines',
                name='Unemployment Rate',
                line=dict(color='#1F77B4', width=2),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.2)',
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Rate: %{y:.1f}%<extra></extra>'
            ),
            row=1, col=1
        )

        # Add moving averages
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MA_3M'],
                mode='lines',
                name='3-Month MA',
                line=dict(color='#FF7F0E', width=1, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>3M MA: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['MA_12M'],
                mode='lines',
                name='12-Month MA',
                line=dict(color='#2CA02C', width=1, dash='dot'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>12M MA: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=1
        )

        # Add historical average line
        historical_avg = df[self.series_id].mean()
        fig.add_hline(
            y=historical_avg, row=1, col=1,
            line_dash="dash", line_color="red", line_width=1,
            annotation_text=f"Historical Avg: {historical_avg:.1f}%"
        )

        # 2. Month-over-Month Change
        colors_mom = ['red' if x > 0 else 'green' for x in df['MoM_Change'].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['MoM_Change'],
                name='MoM Change',
                marker_color=colors_mom,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>MoM Change: %{y:+.2f}pp<extra></extra>'
            ),
            row=2, col=1
        )

        # Add zero line
        fig.add_hline(y=0, row=2, col=1, line_dash="dash", line_color="gray", line_width=1)

        # 3. Year-over-Year Change
        colors_yoy = ['red' if x > 0 else 'green' for x in df['YoY_Change'].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['YoY_Change'],
                name='YoY Change',
                marker_color=colors_yoy,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>YoY Change: %{y:+.2f}pp<extra></extra>'
            ),
            row=3, col=1
        )

        # Add zero line
        fig.add_hline(y=0, row=3, col=1, line_dash="dash", line_color="gray", line_width=1)

        # Add recession shading
        recessions = [
            ('2001-03-01', '2001-11-01', 'Dot-com Recession'),
            ('2007-12-01', '2009-06-01', 'Great Recession'),
            ('2020-02-01', '2020-04-01', 'COVID-19 Recession')
        ]

        for start, end, name in recessions:
            if pd.to_datetime(start) >= df.index[0]:
                for row in [1, 2, 3]:
                    fig.add_vrect(
                        x0=start, x1=end,
                        fillcolor="gray", opacity=0.2,
                        layer="below", line_width=0,
                        row=row, col=1
                    )

        # Update layout
        fig.update_layout(
            title={
                'text': f"US Unemployment Rate Analysis<br><sub>{info.get('title', '')}</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            template=PLOT_THEME,
            height=FIGURE_HEIGHT + 200,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(title="Date"),
            yaxis=dict(title="Unemployment Rate (%)"),
            xaxis2=dict(title="Date"),
            yaxis2=dict(title="Change (percentage points)"),
            xaxis3=dict(title="Date"),
            yaxis3=dict(title="Change (percentage points)")
        )

        # Add annotations for latest values and key statistics
        if len(df) > 0:
            latest_date = df.index[-1]
            latest_rate = df[self.series_id].iloc[-1]
            min_rate = df[self.series_id].min()
            max_rate = df[self.series_id].max()

            # Latest value annotation
            fig.add_annotation(
                text=f"Latest: {latest_rate:.1f}% ({latest_date.strftime('%Y-%m-%d')})",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1
            )

            # Min/Max annotation
            fig.add_annotation(
                text=f"Range: {min_rate:.1f}% - {max_rate:.1f}%",
                xref="paper", yref="paper",
                x=0.02, y=0.94,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1
            )

        return fig

    def create_historical_comparison(self, start_date: str = None,
                                    end_date: str = None) -> go.Figure:
        """
        Create historical comparison with different unemployment measures

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch different unemployment measures
        u3_df = self.fetcher.fetch_series('UNRATE', start_date, end_date)  # U-3 (Official)
        u6_df = self.fetcher.fetch_series('U6RATE', start_date, end_date)  # U-6 (Broad)

        # Combine data
        df = pd.concat([u3_df, u6_df], axis=1)
        df.columns = ['U3_Official', 'U6_Broad']

        # Create figure
        fig = go.Figure()

        # Add U-3 (Official)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['U3_Official'],
            mode='lines',
            name='U-3 (Official Rate)',
            line=dict(color='#1F77B4', width=2),
            hovertemplate='Date: %{x|%Y-%m-%d}<br>U-3: %{y:.1f}%<extra></extra>'
        ))

        # Add U-6 (Broad)
        if 'U6_Broad' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['U6_Broad'],
                mode='lines',
                name='U-6 (Broad Measure)',
                line=dict(color='#FF7F0E', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>U-6: %{y:.1f}%<extra></extra>'
            ))

        # Update layout
        fig.update_layout(
            title="Unemployment Rate Measures Comparison<br><sub>U-3 (Official) vs U-6 (Including Underemployment)</sub>",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT,
            width=FIGURE_WIDTH,
            xaxis_title="Date",
            yaxis_title="Unemployment Rate (%)",
            hovermode='x unified',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        # Add recession shading
        recessions = [
            ('2001-03-01', '2001-11-01', 'Dot-com Recession'),
            ('2007-12-01', '2009-06-01', 'Great Recession'),
            ('2020-02-01', '2020-04-01', 'COVID-19 Recession')
        ]

        for start, end, name in recessions:
            if pd.to_datetime(start) >= df.index[0]:
                fig.add_vrect(
                    x0=start, x1=end,
                    fillcolor="gray", opacity=0.2,
                    layer="below", line_width=0
                )

        return fig

    def save_graph(self, fig: go.Figure = None, filename: str = 'unemployment_graph.html',
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
                   filename: str = 'unemployment_data.csv'):
        """
        Export unemployment data to CSV

        Args:
            start_date: Start date for data
            end_date: End date for data
            filename: Output filename
        """
        df = self.fetch_unemployment_data(start_date, end_date)

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path)
        logger.info(f"Data exported to {output_path}")


def main():
    """Main function to create and save unemployment visualizations"""
    print("Creating Unemployment Rate Visualizations...")

    # Initialize visualizer
    viz = UnemploymentVisualizer()

    # Create main unemployment graph
    fig1 = viz.create_interactive_graph(start_date='2000-01-01')
    viz.save_graph(fig1, 'unemployment_analysis.html')

    # Create comparison graph
    fig2 = viz.create_historical_comparison(start_date='1994-01-01')
    viz.save_graph(fig2, 'unemployment_comparison.html')

    # Export data
    viz.export_data(start_date='2000-01-01', filename='unemployment_data.csv')

    print("Unemployment visualizations completed successfully!")


if __name__ == "__main__":
    main()