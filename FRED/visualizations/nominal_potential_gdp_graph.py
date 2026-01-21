"""
Nominal Potential GDP Visualization Module
Creates interactive graphs for Nominal Potential GDP data from FRED
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


class NominalPotentialGDPVisualizer:
    """
    Creates visualizations for Nominal Potential GDP data
    Compares actual Nominal GDP with Potential GDP (not adjusted for inflation)
    """

    def __init__(self, fetcher: FREDDataFetcher = None):
        """Initialize Nominal Potential GDP Visualizer"""
        self.fetcher = fetcher or FREDDataFetcher()
        self.potential_series_id = FRED_SERIES_IDS['nominal_potential_gdp']
        self.nominal_gdp_series_id = 'GDP'  # Nominal GDP series

    def fetch_nominal_gdp_comparison(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch Nominal GDP and Nominal Potential GDP data with calculated metrics

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with both GDP measures and calculated metrics
        """
        # Fetch Nominal Potential GDP
        potential_df = self.fetcher.fetch_series(self.potential_series_id, start_date, end_date)

        # Fetch Nominal GDP
        nominal_df = self.fetcher.fetch_series(self.nominal_gdp_series_id, start_date, end_date)

        # Combine data
        df = pd.concat([nominal_df, potential_df], axis=1)
        df.columns = ['Nominal_GDP', 'Nominal_Potential_GDP']

        # Convert to trillions
        df['Nominal_GDP_Trillions'] = df['Nominal_GDP'] / 1000
        df['Potential_GDP_Trillions'] = df['Nominal_Potential_GDP'] / 1000

        # Calculate nominal output gap (percentage)
        df['Nominal_Output_Gap'] = ((df['Nominal_GDP'] - df['Nominal_Potential_GDP']) /
                                    df['Nominal_Potential_GDP']) * 100

        # Calculate nominal output gap in billions
        df['Output_Gap_Billions'] = df['Nominal_GDP'] - df['Nominal_Potential_GDP']

        # Calculate growth rates
        df['Nominal_GDP_YoY'] = self.fetcher.calculate_yoy_growth(df, 'Nominal_GDP')
        df['Potential_GDP_YoY'] = self.fetcher.calculate_yoy_growth(df, 'Nominal_Potential_GDP')

        # Calculate quarter-over-quarter growth
        df['Nominal_GDP_QoQ'] = self.fetcher.calculate_growth_rate(df, 'Nominal_GDP', periods=1)
        df['Potential_GDP_QoQ'] = self.fetcher.calculate_growth_rate(df, 'Nominal_Potential_GDP', periods=1)

        # Identify inflationary pressure periods
        df['Inflation_Pressure'] = 'Normal'
        df.loc[df['Nominal_Output_Gap'] > 2, 'Inflation_Pressure'] = 'High'
        df.loc[df['Nominal_Output_Gap'] < -2, 'Inflation_Pressure'] = 'Low'

        return df

    def create_interactive_graph(self, start_date: str = None,
                                end_date: str = None) -> go.Figure:
        """
        Create comprehensive interactive Nominal vs Potential GDP visualization

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_nominal_gdp_comparison(start_date, end_date)

        # Get series info
        info = self.fetcher.get_series_info(self.potential_series_id)

        # Create figure with subplots
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=(
                'Nominal GDP vs Nominal Potential GDP',
                'Nominal Output Gap (% of Potential)',
                'Year-over-Year Growth Comparison',
                'Growth Rate Differential'
            ),
            vertical_spacing=0.08,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. Main GDP Comparison Chart
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Nominal_GDP_Trillions'],
                mode='lines',
                name='Nominal GDP',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Nominal GDP: $%{y:.2f}T<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Potential_GDP_Trillions'],
                mode='lines',
                name='Nominal Potential GDP',
                line=dict(color='#A23B72', width=2, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Potential: $%{y:.2f}T<extra></extra>'
            ),
            row=1, col=1
        )

        # Add shading for gap
        fig.add_trace(
            go.Scatter(
                x=df.index.tolist() + df.index.tolist()[::-1],
                y=df['Nominal_GDP_Trillions'].tolist() + df['Potential_GDP_Trillions'].tolist()[::-1],
                fill='toself',
                fillcolor='rgba(0,100,80,0.1)',
                line=dict(color='rgba(255,255,255,0)'),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=1, col=1
        )

        # 2. Nominal Output Gap
        colors_gap = ['#2CA02C' if x > 0 else '#D62728' for x in df['Nominal_Output_Gap'].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Nominal_Output_Gap'],
                name='Nominal Output Gap',
                marker_color=colors_gap,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Gap: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Add threshold lines
        fig.add_hline(y=0, row=2, col=1, line_dash="solid", line_color="black", line_width=1)
        fig.add_hline(y=2, row=2, col=1, line_dash="dash", line_color="orange", line_width=1,
                     annotation_text="Inflation Risk")
        fig.add_hline(y=-2, row=2, col=1, line_dash="dash", line_color="blue", line_width=1,
                     annotation_text="Deflationary Risk")

        # 3. Year-over-Year Growth Comparison
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Nominal_GDP_YoY'],
                mode='lines',
                name='Nominal GDP YoY',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Nominal YoY: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Potential_GDP_YoY'],
                mode='lines',
                name='Potential GDP YoY',
                line=dict(color='#A23B72', width=2, dash='dash'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Potential YoY: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )

        # Add zero line
        fig.add_hline(y=0, row=3, col=1, line_dash="dash", line_color="gray", line_width=1)

        # 4. Growth Rate Differential
        df['Growth_Differential'] = df['Nominal_GDP_YoY'] - df['Potential_GDP_YoY']
        colors_diff = ['#2CA02C' if x > 0 else '#D62728' for x in df['Growth_Differential'].fillna(0)]

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Growth_Differential'],
                name='Growth Differential',
                marker_color=colors_diff,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Differential: %{y:.2f}pp<extra></extra>'
            ),
            row=4, col=1
        )

        # Add zero line
        fig.add_hline(y=0, row=4, col=1, line_dash="solid", line_color="black", line_width=1)

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
                'text': f"Nominal GDP vs Nominal Potential GDP Analysis<br><sub>Inflation Pressure and Economic Cycles</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            template=PLOT_THEME,
            height=FIGURE_HEIGHT + 400,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(title=""),
            yaxis=dict(title="GDP (Trillions USD)"),
            xaxis2=dict(title=""),
            yaxis2=dict(title="Output Gap (%)"),
            xaxis3=dict(title=""),
            yaxis3=dict(title="Growth Rate (%)"),
            xaxis4=dict(title="Date"),
            yaxis4=dict(title="Differential (pp)")
        )

        # Add annotations for latest values
        if len(df) > 0:
            latest_date = df.index[-1]
            latest_nominal = df['Nominal_GDP_Trillions'].iloc[-1]
            latest_potential = df['Potential_GDP_Trillions'].iloc[-1]
            latest_gap = df['Nominal_Output_Gap'].iloc[-1]
            latest_pressure = df['Inflation_Pressure'].iloc[-1]

            # Latest values annotation
            fig.add_annotation(
                text=f"Latest ({latest_date.strftime('%Y-%m-%d')})<br>"
                     f"Nominal: ${latest_nominal:.2f}T<br>"
                     f"Potential: ${latest_potential:.2f}T",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

            # Inflation pressure annotation
            fig.add_annotation(
                text=f"Output Gap: {latest_gap:.2f}%<br>"
                     f"Inflation Pressure: {latest_pressure}",
                xref="paper", yref="paper",
                x=0.02, y=0.92,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

        return fig

    def create_inflation_analysis(self, start_date: str = None,
                                 end_date: str = None) -> go.Figure:
        """
        Create analysis of nominal output gap and inflation implications

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch GDP data
        df = self.fetch_nominal_gdp_comparison(start_date, end_date)

        # Also fetch CPI for comparison
        try:
            cpi_df = self.fetcher.fetch_series('CPIAUCSL', start_date, end_date)
            cpi_df['CPI_YoY'] = self.fetcher.calculate_yoy_growth(cpi_df, 'CPIAUCSL')
            # Merge with main dataframe
            df = df.join(cpi_df['CPI_YoY'], how='left')
        except:
            df['CPI_YoY'] = np.nan

        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Nominal Output Gap and Inflation Rate',
                'Nominal vs Real Growth Differential'
            ),
            vertical_spacing=0.15,
            specs=[[{"secondary_y": True}],
                  [{"secondary_y": False}]]
        )

        # 1. Output Gap vs Inflation
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Nominal_Output_Gap'],
                mode='lines',
                name='Nominal Output Gap',
                line=dict(color='#1F77B4', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Output Gap: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )

        if 'CPI_YoY' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['CPI_YoY'],
                    mode='lines',
                    name='CPI Inflation',
                    line=dict(color='#FF7F0E', width=2),
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>CPI YoY: %{y:.2f}%<extra></extra>'
                ),
                row=1, col=1, secondary_y=True
            )

        # 2. Growth Differential Analysis
        # Calculate implied inflation component
        df['Nominal_Real_Diff'] = df['Nominal_GDP_YoY'] - df['Potential_GDP_YoY']

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Nominal_Real_Diff'],
                name='Nominal-Potential Differential',
                marker_color=['#2CA02C' if x > 0 else '#D62728' for x in df['Nominal_Real_Diff'].fillna(0)],
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Differential: %{y:.2f}pp<extra></extra>'
            ),
            row=2, col=1
        )

        # Add zero lines
        fig.add_hline(y=0, row=1, col=1, line_dash="dash", line_color="gray", line_width=1)
        fig.add_hline(y=0, row=2, col=1, line_dash="solid", line_color="black", line_width=1)

        # Add 2% inflation target line
        fig.add_hline(y=2, row=1, col=1, secondary_y=True,
                     line_dash="dash", line_color="red", line_width=1,
                     annotation_text="2% Target")

        # Update layout
        fig.update_layout(
            title="Nominal Output Gap and Inflation Analysis",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified'
        )

        # Update axes
        fig.update_yaxes(title_text="Output Gap (%)", secondary_y=False, row=1, col=1)
        fig.update_yaxes(title_text="CPI Inflation (%)", secondary_y=True, row=1, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Differential (pp)", row=2, col=1)

        return fig

    def save_graph(self, fig: go.Figure = None, filename: str = 'nominal_potential_gdp_graph.html',
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
                   filename: str = 'nominal_potential_gdp_data.csv'):
        """
        Export Nominal GDP comparison data to CSV

        Args:
            start_date: Start date for data
            end_date: End date for data
            filename: Output filename
        """
        df = self.fetch_nominal_gdp_comparison(start_date, end_date)

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path)
        logger.info(f"Data exported to {output_path}")


def main():
    """Main function to create and save Nominal Potential GDP visualizations"""
    print("Creating Nominal Potential GDP Visualizations...")

    # Initialize visualizer
    viz = NominalPotentialGDPVisualizer()

    # Create main comparison graph
    fig1 = viz.create_interactive_graph(start_date='2000-01-01')
    viz.save_graph(fig1, 'nominal_potential_gdp_analysis.html')

    # Create inflation analysis
    fig2 = viz.create_inflation_analysis(start_date='2000-01-01')
    viz.save_graph(fig2, 'nominal_gdp_inflation_analysis.html')

    # Export data
    viz.export_data(start_date='2000-01-01', filename='nominal_potential_gdp_data.csv')

    print("Nominal Potential GDP visualizations completed successfully!")


if __name__ == "__main__":
    main()