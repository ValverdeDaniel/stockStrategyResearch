"""
Gross Domestic Product (GDP) Visualization Module
Creates interactive graphs for GDP data from FRED
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


class GDPVisualizer:
    """
    Creates visualizations for GDP data
    Following pattern from fundamentals_macd_historical.py
    """

    def __init__(self, fetcher: FREDDataFetcher = None):
        """Initialize GDP Visualizer"""
        self.fetcher = fetcher or FREDDataFetcher()
        self.series_id = FRED_SERIES_IDS['gdp']

    def fetch_gdp_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch GDP data with calculated metrics

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with GDP and calculated metrics
        """
        # Fetch nominal GDP
        df = self.fetcher.fetch_series(self.series_id, start_date, end_date)

        # Calculate quarter-over-quarter growth
        df['QoQ_Growth'] = self.fetcher.calculate_growth_rate(df, self.series_id, periods=1)

        # Calculate year-over-year growth
        df['YoY_Growth'] = self.fetcher.calculate_yoy_growth(df, self.series_id)

        # Calculate moving averages
        df['MA_4Q'] = df[self.series_id].rolling(window=4).mean()
        df['MA_8Q'] = df[self.series_id].rolling(window=8).mean()

        # Calculate GDP in trillions
        df['GDP_Trillions'] = df[self.series_id] / 1000

        return df

    def create_interactive_graph(self, start_date: str = None,
                                end_date: str = None) -> go.Figure:
        """
        Create comprehensive interactive GDP visualization

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_gdp_data(start_date, end_date)

        # Get series info
        info = self.fetcher.get_series_info(self.series_id)

        # Create figure with subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'US Gross Domestic Product',
                'GDP Growth Rate (Year-over-Year)',
                'GDP Growth Rate (Quarter-over-Quarter)'
            ),
            vertical_spacing=0.12,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. Main GDP Chart
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['GDP_Trillions'],
                mode='lines',
                name='GDP',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>GDP: $%{y:.2f}T<extra></extra>'
            ),
            row=1, col=1
        )

        # Add moving averages
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['GDP_Trillions'].rolling(window=4).mean(),
                mode='lines',
                name='4-Quarter MA',
                line=dict(color='#A23B72', width=1, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>4Q MA: $%{y:.2f}T<extra></extra>'
            ),
            row=1, col=1
        )

        # 2. Year-over-Year Growth
        colors_yoy = ['red' if x < 0 else 'green' for x in df['YoY_Growth'].fillna(0)]
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

        # Add zero line for growth charts
        fig.add_hline(y=0, row=2, col=1, line_dash="dash", line_color="gray", line_width=1)

        # 3. Quarter-over-Quarter Growth
        colors_qoq = ['red' if x < 0 else 'green' for x in df['QoQ_Growth'].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['QoQ_Growth'],
                name='QoQ Growth',
                marker_color=colors_qoq,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>QoQ Growth: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )

        # Add zero line
        fig.add_hline(y=0, row=3, col=1, line_dash="dash", line_color="gray", line_width=1)

        # Add recession shading (major recessions)
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
                'text': f"US Gross Domestic Product Analysis<br><sub>{info.get('title', '')}</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            template=PLOT_THEME,
            height=FIGURE_HEIGHT + 200,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(title="Date"),
            yaxis=dict(title="GDP (Trillions USD)"),
            xaxis2=dict(title="Date"),
            yaxis2=dict(title="Growth Rate (%)"),
            xaxis3=dict(title="Date"),
            yaxis3=dict(title="Growth Rate (%)")
        )

        # Add annotations for latest values
        if len(df) > 0:
            latest_date = df.index[-1]
            latest_gdp = df['GDP_Trillions'].iloc[-1]
            latest_yoy = df['YoY_Growth'].iloc[-1]

            fig.add_annotation(
                text=f"Latest: ${latest_gdp:.2f}T ({latest_date.strftime('%Y-%m-%d')})",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1
            )

            if not pd.isna(latest_yoy):
                fig.add_annotation(
                    text=f"YoY Growth: {latest_yoy:.2f}%",
                    xref="paper", yref="paper",
                    x=0.02, y=0.94,
                    showarrow=False,
                    bgcolor="white",
                    bordercolor="gray",
                    borderwidth=1
                )

        return fig

    def create_comparison_graph(self, start_date: str = None,
                              end_date: str = None) -> go.Figure:
        """
        Create graph comparing nominal and real GDP

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch both nominal and real GDP
        nominal_df = self.fetcher.fetch_series('GDP', start_date, end_date)
        real_df = self.fetcher.fetch_series('GDPC1', start_date, end_date)

        # Combine data
        df = pd.concat([nominal_df, real_df], axis=1)
        df.columns = ['Nominal_GDP', 'Real_GDP']

        # Convert to trillions
        df = df / 1000

        # Create figure
        fig = go.Figure()

        # Add nominal GDP
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Nominal_GDP'],
            mode='lines',
            name='Nominal GDP',
            line=dict(color='#2E86AB', width=2),
            hovertemplate='Date: %{x|%Y-%m-%d}<br>Nominal: $%{y:.2f}T<extra></extra>'
        ))

        # Add real GDP
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Real_GDP'],
            mode='lines',
            name='Real GDP (2017 $)',
            line=dict(color='#A23B72', width=2),
            hovertemplate='Date: %{x|%Y-%m-%d}<br>Real: $%{y:.2f}T<extra></extra>'
        ))

        # Update layout
        fig.update_layout(
            title="Nominal vs Real GDP Comparison",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT,
            width=FIGURE_WIDTH,
            xaxis_title="Date",
            yaxis_title="GDP (Trillions USD)",
            hovermode='x unified',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        return fig

    def save_graph(self, fig: go.Figure = None, filename: str = 'gdp_graph.html',
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
                   filename: str = 'gdp_data.csv'):
        """
        Export GDP data to CSV

        Args:
            start_date: Start date for data
            end_date: End date for data
            filename: Output filename
        """
        df = self.fetch_gdp_data(start_date, end_date)

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path)
        logger.info(f"Data exported to {output_path}")


def main():
    """Main function to create and save GDP visualizations"""
    print("Creating GDP Visualizations...")

    # Initialize visualizer
    viz = GDPVisualizer()

    # Create main GDP graph
    fig1 = viz.create_interactive_graph(start_date='2000-01-01')
    viz.save_graph(fig1, 'gdp_analysis.html')

    # Create comparison graph
    fig2 = viz.create_comparison_graph(start_date='2000-01-01')
    viz.save_graph(fig2, 'gdp_nominal_vs_real.html')

    # Export data
    viz.export_data(start_date='2000-01-01', filename='gdp_data.csv')

    print("GDP visualizations completed successfully!")


if __name__ == "__main__":
    main()