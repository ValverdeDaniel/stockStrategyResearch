"""
Real Potential GDP Visualization Module
Creates interactive graphs comparing Real GDP and Real Potential GDP from FRED
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


class RealPotentialGDPVisualizer:
    """
    Creates visualizations for Real Potential GDP data
    Compares actual Real GDP with Potential GDP to show output gap
    """

    def __init__(self, fetcher: FREDDataFetcher = None):
        """Initialize Real Potential GDP Visualizer"""
        self.fetcher = fetcher or FREDDataFetcher()
        self.potential_series_id = FRED_SERIES_IDS['real_potential_gdp']
        self.real_gdp_series_id = 'GDPC1'  # Real GDP series

    def fetch_gdp_comparison_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch Real GDP and Real Potential GDP data with calculated metrics

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with both GDP measures and calculated metrics
        """
        # Fetch Real Potential GDP
        potential_df = self.fetcher.fetch_series(self.potential_series_id, start_date, end_date)

        # Fetch Real GDP
        real_df = self.fetcher.fetch_series(self.real_gdp_series_id, start_date, end_date)

        # Combine data
        df = pd.concat([real_df, potential_df], axis=1)
        df.columns = ['Real_GDP', 'Potential_GDP']

        # Convert to trillions
        df['Real_GDP_Trillions'] = df['Real_GDP'] / 1000
        df['Potential_GDP_Trillions'] = df['Potential_GDP'] / 1000

        # Calculate output gap (percentage)
        df['Output_Gap'] = ((df['Real_GDP'] - df['Potential_GDP']) / df['Potential_GDP']) * 100

        # Calculate output gap in dollars
        df['Output_Gap_Billions'] = (df['Real_GDP'] - df['Potential_GDP'])

        # Calculate growth rates
        df['Real_GDP_YoY'] = self.fetcher.calculate_yoy_growth(df, 'Real_GDP')
        df['Potential_GDP_YoY'] = self.fetcher.calculate_yoy_growth(df, 'Potential_GDP')

        # Identify economic phases based on output gap
        df['Economic_Phase'] = 'Normal'
        df.loc[df['Output_Gap'] > 2, 'Economic_Phase'] = 'Overheating'
        df.loc[df['Output_Gap'] < -2, 'Economic_Phase'] = 'Slack'

        return df

    def create_interactive_graph(self, start_date: str = None,
                                end_date: str = None) -> go.Figure:
        """
        Create comprehensive interactive Real vs Potential GDP visualization

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_gdp_comparison_data(start_date, end_date)

        # Get series info
        info = self.fetcher.get_series_info(self.potential_series_id)

        # Create figure with subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'Real GDP vs Real Potential GDP',
                'Output Gap (% of Potential GDP)',
                'Year-over-Year Growth Rates'
            ),
            vertical_spacing=0.12,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. Main GDP Comparison Chart
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Real_GDP_Trillions'],
                mode='lines',
                name='Real GDP',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Real GDP: $%{y:.2f}T<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Potential_GDP_Trillions'],
                mode='lines',
                name='Potential GDP',
                line=dict(color='#A23B72', width=2, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Potential: $%{y:.2f}T<extra></extra>'
            ),
            row=1, col=1
        )

        # Add shading between actual and potential
        fig.add_trace(
            go.Scatter(
                x=df.index.tolist() + df.index.tolist()[::-1],
                y=df['Real_GDP_Trillions'].tolist() + df['Potential_GDP_Trillions'].tolist()[::-1],
                fill='toself',
                fillcolor='rgba(0,100,80,0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=1, col=1
        )

        # 2. Output Gap Chart
        colors_gap = ['green' if x > 0 else 'red' for x in df['Output_Gap'].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Output_Gap'],
                name='Output Gap',
                marker_color=colors_gap,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Gap: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Add zero line and threshold lines
        fig.add_hline(y=0, row=2, col=1, line_dash="solid", line_color="black", line_width=1)
        fig.add_hline(y=2, row=2, col=1, line_dash="dash", line_color="orange", line_width=1,
                     annotation_text="Overheating threshold")
        fig.add_hline(y=-2, row=2, col=1, line_dash="dash", line_color="blue", line_width=1,
                     annotation_text="Slack threshold")

        # 3. Growth Rates Comparison
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Real_GDP_YoY'],
                mode='lines',
                name='Real GDP Growth',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Real Growth: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Potential_GDP_YoY'],
                mode='lines',
                name='Potential GDP Growth',
                line=dict(color='#A23B72', width=2, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Potential Growth: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )

        # Add zero line for growth chart
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
                'text': f"Real GDP vs Real Potential GDP Analysis<br><sub>Output Gap and Economic Cycles</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            template=PLOT_THEME,
            height=FIGURE_HEIGHT + 200,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(title="Date"),
            yaxis=dict(title="GDP (Trillions, Chained 2017 $)"),
            xaxis2=dict(title="Date"),
            yaxis2=dict(title="Output Gap (%)"),
            xaxis3=dict(title="Date"),
            yaxis3=dict(title="Growth Rate (%)")
        )

        # Add annotations for latest values
        if len(df) > 0:
            latest_date = df.index[-1]
            latest_real = df['Real_GDP_Trillions'].iloc[-1]
            latest_potential = df['Potential_GDP_Trillions'].iloc[-1]
            latest_gap = df['Output_Gap'].iloc[-1]

            # Latest values annotation
            fig.add_annotation(
                text=f"Latest ({latest_date.strftime('%Y-%m-%d')})<br>"
                     f"Real: ${latest_real:.2f}T<br>"
                     f"Potential: ${latest_potential:.2f}T",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

            # Output gap status
            gap_status = "Normal"
            if latest_gap > 2:
                gap_status = "Overheating"
            elif latest_gap < -2:
                gap_status = "Slack"

            fig.add_annotation(
                text=f"Output Gap: {latest_gap:.2f}%<br>Status: {gap_status}",
                xref="paper", yref="paper",
                x=0.02, y=0.90,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

        return fig

    def create_historical_analysis(self, start_date: str = None,
                                  end_date: str = None) -> go.Figure:
        """
        Create historical analysis of output gap patterns

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_gdp_comparison_data(start_date, end_date)

        # Create figure
        fig = go.Figure()

        # Create filled area chart for output gap
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Output_Gap'],
            mode='lines',
            name='Output Gap',
            line=dict(color='#1F77B4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.3)',
            hovertemplate='Date: %{x|%Y-%m-%d}<br>Output Gap: %{y:.2f}%<extra></extra>'
        ))

        # Add moving average
        df['Output_Gap_MA'] = df['Output_Gap'].rolling(window=4).mean()
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Output_Gap_MA'],
            mode='lines',
            name='4-Quarter MA',
            line=dict(color='#FF7F0E', width=2, dash='dash'),
            hovertemplate='Date: %{x|%Y-%m-%d}<br>MA: %{y:.2f}%<extra></extra>'
        ))

        # Add threshold lines
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=2)
        fig.add_hline(y=2, line_dash="dash", line_color="red", line_width=1,
                     annotation_text="Overheating (>2%)")
        fig.add_hline(y=-2, line_dash="dash", line_color="blue", line_width=1,
                     annotation_text="Economic Slack (<-2%)")

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
                    layer="below", line_width=0,
                    annotation_text=name, annotation_position="top left"
                )

        # Update layout
        fig.update_layout(
            title="Output Gap Historical Analysis<br><sub>Economic Cycles and Recessions</sub>",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT,
            width=FIGURE_WIDTH,
            xaxis_title="Date",
            yaxis_title="Output Gap (% of Potential GDP)",
            hovermode='x unified',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        return fig

    def save_graph(self, fig: go.Figure = None, filename: str = 'real_potential_gdp_graph.html',
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
                   filename: str = 'real_potential_gdp_data.csv'):
        """
        Export GDP comparison data to CSV

        Args:
            start_date: Start date for data
            end_date: End date for data
            filename: Output filename
        """
        df = self.fetch_gdp_comparison_data(start_date, end_date)

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path)
        logger.info(f"Data exported to {output_path}")


def main():
    """Main function to create and save Real Potential GDP visualizations"""
    print("Creating Real Potential GDP Visualizations...")

    # Initialize visualizer
    viz = RealPotentialGDPVisualizer()

    # Create main comparison graph
    fig1 = viz.create_interactive_graph(start_date='2000-01-01')
    viz.save_graph(fig1, 'real_potential_gdp_analysis.html')

    # Create historical analysis
    fig2 = viz.create_historical_analysis(start_date='1985-01-01')
    viz.save_graph(fig2, 'output_gap_historical.html')

    # Export data
    viz.export_data(start_date='2000-01-01', filename='real_potential_gdp_data.csv')

    print("Real Potential GDP visualizations completed successfully!")


if __name__ == "__main__":
    main()