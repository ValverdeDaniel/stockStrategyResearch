"""
Personal Consumption Expenditures (PCE) Visualization Module
Creates interactive graphs for PCE data from FRED
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


class PCEVisualizer:
    """
    Creates visualizations for Personal Consumption Expenditures data
    PCE is the Fed's preferred inflation measure
    """

    def __init__(self, fetcher: FREDDataFetcher = None):
        """Initialize PCE Visualizer"""
        self.fetcher = fetcher or FREDDataFetcher()
        self.pce_series_id = FRED_SERIES_IDS['pce']
        self.core_pce_series_id = 'PCEPILFE'  # Core PCE (excluding food and energy)
        self.cpi_series_id = FRED_SERIES_IDS['cpi']  # For comparison

    def fetch_pce_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch PCE data with calculated metrics

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with PCE and calculated metrics
        """
        # Fetch PCE data
        df = self.fetcher.fetch_series(self.pce_series_id, start_date, end_date)

        # Try to fetch Core PCE
        try:
            core_df = self.fetcher.fetch_series(self.core_pce_series_id, start_date, end_date)
            df['Core_PCE'] = core_df[self.core_pce_series_id]
        except:
            logger.warning("Core PCE data not available")
            df['Core_PCE'] = np.nan

        # Try to fetch CPI for comparison
        try:
            cpi_df = self.fetcher.fetch_series(self.cpi_series_id, start_date, end_date)
            df['CPI'] = cpi_df[self.cpi_series_id]
        except:
            logger.warning("CPI data not available for comparison")
            df['CPI'] = np.nan

        # Calculate month-over-month inflation (annualized)
        df['PCE_MoM_Annualized'] = df[self.pce_series_id].pct_change() * 12 * 100

        # Calculate year-over-year inflation
        df['PCE_YoY'] = df[self.pce_series_id].pct_change(12) * 100

        # Calculate core PCE inflation if available
        if 'Core_PCE' in df.columns:
            df['Core_PCE_YoY'] = df['Core_PCE'].pct_change(12) * 100
            df['Core_PCE_MoM_Annualized'] = df['Core_PCE'].pct_change() * 12 * 100

        # Calculate CPI inflation for comparison
        if 'CPI' in df.columns:
            df['CPI_YoY'] = df['CPI'].pct_change(12) * 100

        # Calculate 3-month annualized PCE inflation
        df['PCE_3M_Annualized'] = (df[self.pce_series_id].pct_change(3) * 4) * 100

        # Calculate 6-month annualized PCE inflation
        df['PCE_6M_Annualized'] = (df[self.pce_series_id].pct_change(6) * 2) * 100

        # Calculate moving averages
        df['PCE_YoY_MA_3M'] = df['PCE_YoY'].rolling(window=3).mean()
        df['PCE_YoY_MA_12M'] = df['PCE_YoY'].rolling(window=12).mean()

        # Index to base year
        base_value = df[self.pce_series_id].iloc[0] if len(df) > 0 else 100
        df['PCE_Index'] = (df[self.pce_series_id] / base_value) * 100

        # Calculate PCE-CPI spread
        if 'CPI_YoY' in df.columns:
            df['PCE_CPI_Spread'] = df['PCE_YoY'] - df['CPI_YoY']

        # Fed target analysis
        df['Above_Target'] = df['PCE_YoY'] > 2.0
        df['Distance_from_Target'] = df['PCE_YoY'] - 2.0

        return df

    def create_interactive_graph(self, start_date: str = None,
                                end_date: str = None) -> go.Figure:
        """
        Create comprehensive interactive PCE visualization

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_pce_data(start_date, end_date)

        # Get series info
        info = self.fetcher.get_series_info(self.pce_series_id)

        # Create figure with subplots
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=(
                'PCE Price Index Level',
                'PCE Inflation: Headline vs Core (Fed\'s Preferred Measure)',
                'PCE vs CPI Inflation Comparison',
                'Short-term PCE Inflation Trends'
            ),
            vertical_spacing=0.08,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. PCE Level Chart
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[self.pce_series_id],
                mode='lines',
                name='PCE',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>PCE: %{y:.1f}<extra></extra>'
            ),
            row=1, col=1
        )

        if 'Core_PCE' in df.columns and not df['Core_PCE'].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Core_PCE'],
                    mode='lines',
                    name='Core PCE',
                    line=dict(color='#A23B72', width=2, dash='dash'),
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>Core PCE: %{y:.1f}<extra></extra>'
                ),
                row=1, col=1
            )

        # 2. Headline vs Core PCE Inflation
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['PCE_YoY'],
                mode='lines',
                name='Headline PCE',
                line=dict(color='#2E86AB', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Headline: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        if 'Core_PCE_YoY' in df.columns and not df['Core_PCE_YoY'].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Core_PCE_YoY'],
                    mode='lines',
                    name='Core PCE',
                    line=dict(color='#A23B72', width=2),
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>Core: %{y:.2f}%<extra></extra>'
                ),
                row=2, col=1
            )

        # Add Fed's 2% target
        fig.add_hline(y=2, row=2, col=1, line_dash="dash", line_color="red", line_width=2,
                     annotation_text="Fed's 2% Target")

        # 3. PCE vs CPI Comparison
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['PCE_YoY'],
                mode='lines',
                name='PCE Inflation',
                line=dict(color='#1F77B4', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>PCE: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )

        if 'CPI_YoY' in df.columns and not df['CPI_YoY'].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['CPI_YoY'],
                    mode='lines',
                    name='CPI Inflation',
                    line=dict(color='#FF7F0E', width=2),
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>CPI: %{y:.2f}%<extra></extra>'
                ),
                row=3, col=1
            )

        # Add 2% target
        fig.add_hline(y=2, row=3, col=1, line_dash="dash", line_color="gray", line_width=1)

        # 4. Short-term Inflation Trends
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['PCE_3M_Annualized'],
                mode='lines',
                name='3-Month Annualized',
                line=dict(color='#2CA02C', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>3M Ann: %{y:.2f}%<extra></extra>'
            ),
            row=4, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['PCE_6M_Annualized'],
                mode='lines',
                name='6-Month Annualized',
                line=dict(color='#D62728', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>6M Ann: %{y:.2f}%<extra></extra>'
            ),
            row=4, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['PCE_YoY'],
                mode='lines',
                name='Year-over-Year',
                line=dict(color='#9467BD', width=1, dash='dot'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>YoY: %{y:.2f}%<extra></extra>'
            ),
            row=4, col=1
        )

        # Add 2% target
        fig.add_hline(y=2, row=4, col=1, line_dash="dash", line_color="gray", line_width=1)

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
                'text': f"US Personal Consumption Expenditures (PCE) Analysis<br><sub>Federal Reserve's Preferred Inflation Measure</sub>",
                'x': 0.5,
                'xanchor': 'center'
            },
            template=PLOT_THEME,
            height=FIGURE_HEIGHT + 400,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(title=""),
            yaxis=dict(title="Index Value"),
            xaxis2=dict(title=""),
            yaxis2=dict(title="Inflation Rate (%)"),
            xaxis3=dict(title=""),
            yaxis3=dict(title="Inflation Rate (%)"),
            xaxis4=dict(title="Date"),
            yaxis4=dict(title="Annualized Rate (%)")
        )

        # Add annotations for latest values
        if len(df) > 0:
            latest_date = df.index[-1]
            latest_pce = df[self.pce_series_id].iloc[-1]
            latest_yoy = df['PCE_YoY'].iloc[-1]
            latest_core = df['Core_PCE_YoY'].iloc[-1] if 'Core_PCE_YoY' in df.columns else np.nan
            latest_3m = df['PCE_3M_Annualized'].iloc[-1]
            distance_from_target = df['Distance_from_Target'].iloc[-1]

            # Latest values annotation
            annotation_text = f"Latest ({latest_date.strftime('%Y-%m-%d')})<br>"
            annotation_text += f"PCE Index: {latest_pce:.1f}<br>"
            annotation_text += f"Headline: {latest_yoy:.2f}%"
            if not pd.isna(latest_core):
                annotation_text += f"<br>Core: {latest_core:.2f}%"

            fig.add_annotation(
                text=annotation_text,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

            # Target distance annotation
            target_text = f"3M Ann: {latest_3m:.2f}%<br>"
            if distance_from_target > 0:
                target_text += f"{distance_from_target:.2f}pp above target"
            else:
                target_text += f"{abs(distance_from_target):.2f}pp below target"

            fig.add_annotation(
                text=target_text,
                xref="paper", yref="paper",
                x=0.02, y=0.92,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

        return fig

    def create_fed_policy_analysis(self, start_date: str = None,
                                  end_date: str = None) -> go.Figure:
        """
        Create analysis focused on Fed policy implications

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_pce_data(start_date, end_date)

        # Create figure with subplots
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=(
                'Core PCE Inflation vs Fed Target',
                'Distance from 2% Target',
                'PCE-CPI Spread (Why the Fed Prefers PCE)'
            ),
            vertical_spacing=0.12,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. Core PCE vs Target with shading
        if 'Core_PCE_YoY' in df.columns and not df['Core_PCE_YoY'].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Core_PCE_YoY'],
                    mode='lines',
                    name='Core PCE',
                    line=dict(color='#1F77B4', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(31, 119, 180, 0.2)',
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>Core PCE: %{y:.2f}%<extra></extra>'
                ),
                row=1, col=1
            )

        # Add target line and bands
        fig.add_hline(y=2, row=1, col=1, line_dash="solid", line_color="red", line_width=2)
        fig.add_hrect(y0=1.5, y1=2.5, row=1, col=1,
                     fillcolor="green", opacity=0.1, layer="below", line_width=0,
                     annotation_text="Comfort Zone", annotation_position="right")

        # 2. Distance from Target
        colors = ['red' if x > 0 else 'blue' for x in df['Distance_from_Target'].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Distance_from_Target'],
                name='Distance from 2%',
                marker_color=colors,
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Distance: %{y:+.2f}pp<extra></extra>'
            ),
            row=2, col=1
        )

        # Add zero line
        fig.add_hline(y=0, row=2, col=1, line_dash="solid", line_color="black", line_width=1)

        # Add acceptable range
        fig.add_hrect(y0=-0.5, y1=0.5, row=2, col=1,
                     fillcolor="green", opacity=0.1, layer="below", line_width=0)

        # 3. PCE-CPI Spread
        if 'PCE_CPI_Spread' in df.columns and not df['PCE_CPI_Spread'].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['PCE_CPI_Spread'],
                    mode='lines',
                    name='PCE-CPI Spread',
                    line=dict(color='#FF7F0E', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(255, 127, 14, 0.2)',
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>Spread: %{y:.2f}pp<extra></extra>'
                ),
                row=3, col=1
            )

            # Add historical average
            avg_spread = df['PCE_CPI_Spread'].mean()
            fig.add_hline(y=avg_spread, row=3, col=1, line_dash="dash", line_color="gray", line_width=1,
                         annotation_text=f"Avg: {avg_spread:.2f}pp")

        # Add zero line
        fig.add_hline(y=0, row=3, col=1, line_dash="solid", line_color="black", line_width=1)

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
            title="PCE Analysis for Fed Policy Implications",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT + 200,
            width=FIGURE_WIDTH,
            showlegend=True,
            hovermode='x unified',
            xaxis=dict(title=""),
            yaxis=dict(title="Inflation Rate (%)"),
            xaxis2=dict(title=""),
            yaxis2=dict(title="Percentage Points"),
            xaxis3=dict(title="Date"),
            yaxis3=dict(title="Spread (pp)")
        )

        return fig

    def create_comparison_table(self, start_date: str = None,
                               end_date: str = None) -> go.Figure:
        """
        Create a comparison table of PCE vs CPI characteristics

        Returns:
            Plotly Figure object with table
        """
        # Fetch data for statistics
        df = self.fetch_pce_data(start_date, end_date)

        # Calculate statistics
        pce_avg = df['PCE_YoY'].mean()
        pce_std = df['PCE_YoY'].std()
        pce_latest = df['PCE_YoY'].iloc[-1]

        cpi_avg = df['CPI_YoY'].mean() if 'CPI_YoY' in df.columns else np.nan
        cpi_std = df['CPI_YoY'].std() if 'CPI_YoY' in df.columns else np.nan
        cpi_latest = df['CPI_YoY'].iloc[-1] if 'CPI_YoY' in df.columns else np.nan

        # Create comparison table
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=['<b>Metric</b>', '<b>PCE</b>', '<b>CPI</b>', '<b>Difference</b>'],
                fill_color='paleturquoise',
                align='left',
                font=dict(size=14)
            ),
            cells=dict(
                values=[
                    ['Latest Value (%)', 'Average (%)', 'Std Dev (%)', 'Coverage',
                     'Housing Weight', 'Fed Preference', 'Update Frequency'],
                    [f'{pce_latest:.2f}', f'{pce_avg:.2f}', f'{pce_std:.2f}',
                     'All consumer spending', '~16%', 'Yes (Primary)', 'Monthly'],
                    [f'{cpi_latest:.2f}' if not np.isnan(cpi_latest) else 'N/A',
                     f'{cpi_avg:.2f}' if not np.isnan(cpi_avg) else 'N/A',
                     f'{cpi_std:.2f}' if not np.isnan(cpi_std) else 'N/A',
                     'Urban consumers only', '~33%', 'No', 'Monthly'],
                    [f'{pce_latest - cpi_latest:.2f}' if not np.isnan(cpi_latest) else 'N/A',
                     f'{pce_avg - cpi_avg:.2f}' if not np.isnan(cpi_avg) else 'N/A',
                     f'{pce_std - cpi_std:.2f}' if not np.isnan(cpi_std) else 'N/A',
                     'PCE broader', 'PCE lower weight', '-', '-']
                ],
                fill_color='lavender',
                align='left',
                font=dict(size=12)
            )
        )])

        fig.update_layout(
            title="PCE vs CPI: Key Differences",
            height=400,
            width=FIGURE_WIDTH
        )

        return fig

    def save_graph(self, fig: go.Figure = None, filename: str = 'pce_graph.html',
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
                   filename: str = 'pce_data.csv'):
        """
        Export PCE data to CSV

        Args:
            start_date: Start date for data
            end_date: End date for data
            filename: Output filename
        """
        df = self.fetch_pce_data(start_date, end_date)

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path)
        logger.info(f"Data exported to {output_path}")


def main():
    """Main function to create and save PCE visualizations"""
    print("Creating PCE Visualizations...")

    # Initialize visualizer
    viz = PCEVisualizer()

    # Create main PCE graph
    fig1 = viz.create_interactive_graph(start_date='2000-01-01')
    viz.save_graph(fig1, 'pce_analysis.html')

    # Create Fed policy analysis
    fig2 = viz.create_fed_policy_analysis(start_date='2000-01-01')
    viz.save_graph(fig2, 'pce_fed_policy.html')

    # Create comparison table
    fig3 = viz.create_comparison_table(start_date='2000-01-01')
    viz.save_graph(fig3, 'pce_vs_cpi_table.html')

    # Export data
    viz.export_data(start_date='2000-01-01', filename='pce_data.csv')

    print("PCE visualizations completed successfully!")


if __name__ == "__main__":
    main()