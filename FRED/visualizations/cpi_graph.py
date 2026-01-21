"""
Consumer Price Index (CPI) Visualization Module
Creates interactive graphs for CPI data from FRED
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


class CPIVisualizer:
    """
    Creates visualizations for Consumer Price Index data
    Shows inflation trends and price level changes
    """

    def __init__(self, fetcher: FREDDataFetcher = None):
        """Initialize CPI Visualizer"""
        self.fetcher = fetcher or FREDDataFetcher()
        self.cpi_series_id = FRED_SERIES_IDS['cpi']
        self.core_cpi_series_id = 'CPILFESL'  # Core CPI (excluding food and energy)

    def fetch_cpi_data(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch CPI data with calculated metrics

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with CPI and calculated metrics
        """
        # Fetch CPI data
        df = self.fetcher.fetch_series(self.cpi_series_id, start_date, end_date)

        # Try to fetch Core CPI
        try:
            core_df = self.fetcher.fetch_series(self.core_cpi_series_id, start_date, end_date)
            df['Core_CPI'] = core_df[self.core_cpi_series_id]
        except:
            logger.warning("Core CPI data not available")
            df['Core_CPI'] = np.nan

        # Calculate month-over-month inflation (annualized)
        df['MoM_Inflation'] = df[self.cpi_series_id].pct_change() * 12 * 100

        # Calculate year-over-year inflation
        df['YoY_Inflation'] = df[self.cpi_series_id].pct_change(12) * 100

        # Calculate core inflation if available
        if 'Core_CPI' in df.columns:
            df['Core_YoY_Inflation'] = df['Core_CPI'].pct_change(12) * 100
            df['Core_MoM_Inflation'] = df['Core_CPI'].pct_change() * 12 * 100

        # Calculate 3-month annualized inflation
        df['3M_Annualized'] = (df[self.cpi_series_id].pct_change(3) * 4) * 100

        # Calculate 6-month annualized inflation
        df['6M_Annualized'] = (df[self.cpi_series_id].pct_change(6) * 2) * 100

        # Calculate moving averages of inflation
        df['YoY_MA_3M'] = df['YoY_Inflation'].rolling(window=3).mean()
        df['YoY_MA_12M'] = df['YoY_Inflation'].rolling(window=12).mean()

        # Index to base year (set first value = 100)
        base_value = df[self.cpi_series_id].iloc[0] if len(df) > 0 else 100
        df['CPI_Index'] = (df[self.cpi_series_id] / base_value) * 100

        # Classify inflation regime
        df['Inflation_Regime'] = 'Normal'
        df.loc[df['YoY_Inflation'] < 0, 'Inflation_Regime'] = 'Deflation'
        df.loc[df['YoY_Inflation'] > 4, 'Inflation_Regime'] = 'High Inflation'
        df.loc[df['YoY_Inflation'] > 8, 'Inflation_Regime'] = 'Very High Inflation'

        return df

    def create_interactive_graph(self, start_date: str = None,
                                end_date: str = None) -> go.Figure:
        """
        Create comprehensive interactive CPI visualization

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_cpi_data(start_date, end_date)

        # Get series info
        info = self.fetcher.get_series_info(self.cpi_series_id)

        # Create figure with subplots
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=(
                'Consumer Price Index Level',
                'Year-over-Year Inflation Rate',
                'Headline vs Core Inflation',
                'Short-term Inflation Trends (Annualized)'
            ),
            vertical_spacing=0.08,
            specs=[[{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}],
                  [{"secondary_y": False}]]
        )

        # 1. CPI Level Chart
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[self.cpi_series_id],
                mode='lines',
                name='CPI',
                line=dict(color='#1F77B4', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>CPI: %{y:.1f}<extra></extra>'
            ),
            row=1, col=1
        )

        if 'Core_CPI' in df.columns and not df['Core_CPI'].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Core_CPI'],
                    mode='lines',
                    name='Core CPI',
                    line=dict(color='#FF7F0E', width=2, dash='dash'),
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>Core CPI: %{y:.1f}<extra></extra>'
                ),
                row=1, col=1
            )

        # 2. Year-over-Year Inflation
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['YoY_Inflation'],
                mode='lines',
                name='YoY Inflation',
                line=dict(color='#2CA02C', width=2),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)',
                hovertemplate='Date: %{x|%Y-%m-%d}<br>YoY Inflation: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Add 2% target line
        fig.add_hline(y=2, row=2, col=1, line_dash="dash", line_color="red", line_width=2,
                     annotation_text="2% Target")

        # Add moving average
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['YoY_MA_12M'],
                mode='lines',
                name='12-Month MA',
                line=dict(color='#D62728', width=1, dash='dot'),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>12M MA: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # 3. Headline vs Core Inflation
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['YoY_Inflation'],
                mode='lines',
                name='Headline CPI',
                line=dict(color='#1F77B4', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Headline: %{y:.2f}%<extra></extra>'
            ),
            row=3, col=1
        )

        if 'Core_YoY_Inflation' in df.columns and not df['Core_YoY_Inflation'].isna().all():
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['Core_YoY_Inflation'],
                    mode='lines',
                    name='Core CPI',
                    line=dict(color='#FF7F0E', width=2),
                    hovertemplate='Date: %{x|%Y-%m-%d}<br>Core: %{y:.2f}%<extra></extra>'
                ),
                row=3, col=1
            )

        # Add 2% target
        fig.add_hline(y=2, row=3, col=1, line_dash="dash", line_color="gray", line_width=1)

        # 4. Short-term Inflation Trends
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['3M_Annualized'],
                mode='lines',
                name='3-Month Annualized',
                line=dict(color='#9467BD', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>3M Ann: %{y:.2f}%<extra></extra>'
            ),
            row=4, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['6M_Annualized'],
                mode='lines',
                name='6-Month Annualized',
                line=dict(color='#8C564B', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>6M Ann: %{y:.2f}%<extra></extra>'
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
                'text': f"US Consumer Price Index Analysis<br><sub>Inflation Trends and Price Levels</sub>",
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
            latest_cpi = df[self.cpi_series_id].iloc[-1]
            latest_yoy = df['YoY_Inflation'].iloc[-1]
            latest_3m = df['3M_Annualized'].iloc[-1]
            latest_regime = df['Inflation_Regime'].iloc[-1]

            # Latest values annotation
            fig.add_annotation(
                text=f"Latest ({latest_date.strftime('%Y-%m-%d')})<br>"
                     f"CPI: {latest_cpi:.1f}<br>"
                     f"YoY: {latest_yoy:.2f}%",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                align="left"
            )

            # Inflation regime annotation
            fig.add_annotation(
                text=f"3M Ann: {latest_3m:.2f}%<br>"
                     f"Regime: {latest_regime}",
                xref="paper", yref="paper",
                x=0.02, y=0.92,
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
        Create historical inflation analysis with decade comparisons

        Args:
            start_date: Start date for data
            end_date: End date for data

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_cpi_data(start_date, end_date)

        # Create decade averages
        df['Decade'] = (df.index.year // 10) * 10
        decade_inflation = df.groupby('Decade')['YoY_Inflation'].agg(['mean', 'std', 'max', 'min'])

        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Historical Inflation Rates with Regime Periods',
                'Inflation Statistics by Decade'
            ),
            vertical_spacing=0.15
        )

        # 1. Long-term inflation with regime shading
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['YoY_Inflation'],
                mode='lines',
                name='YoY Inflation',
                line=dict(color='#1F77B4', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Inflation: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=1
        )

        # Add regime shading based on inflation levels
        high_inflation_periods = df[df['YoY_Inflation'] > 4].index
        very_high_periods = df[df['YoY_Inflation'] > 8].index
        deflation_periods = df[df['YoY_Inflation'] < 0].index

        # Add horizontal lines for thresholds
        fig.add_hline(y=0, row=1, col=1, line_dash="solid", line_color="black", line_width=1)
        fig.add_hline(y=2, row=1, col=1, line_dash="dash", line_color="green", line_width=1,
                     annotation_text="2% Target")
        fig.add_hline(y=4, row=1, col=1, line_dash="dash", line_color="orange", line_width=1,
                     annotation_text="High Inflation")
        fig.add_hline(y=8, row=1, col=1, line_dash="dash", line_color="red", line_width=1,
                     annotation_text="Very High")

        # 2. Decade statistics
        x_labels = [f"{int(d)}s" for d in decade_inflation.index]

        # Mean inflation by decade
        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=decade_inflation['mean'],
                name='Average Inflation',
                marker_color='#2CA02C',
                error_y=dict(type='data', array=decade_inflation['std']),
                hovertemplate='Decade: %{x}<br>Avg: %{y:.2f}%<br>Std: %{error_y.array:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Add 2% target line
        fig.add_hline(y=2, row=2, col=1, line_dash="dash", line_color="red", line_width=1)

        # Update layout
        fig.update_layout(
            title="Historical CPI Inflation Analysis",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT,
            width=FIGURE_WIDTH,
            showlegend=True,
            xaxis=dict(title="Date"),
            yaxis=dict(title="Inflation Rate (%)"),
            xaxis2=dict(title="Decade"),
            yaxis2=dict(title="Average Inflation Rate (%)")
        )

        return fig

    def create_purchasing_power_analysis(self, start_date: str = None,
                                        end_date: str = None,
                                        base_amount: float = 100) -> go.Figure:
        """
        Create purchasing power analysis showing dollar value erosion

        Args:
            start_date: Start date for data
            end_date: End date for data
            base_amount: Base dollar amount to track

        Returns:
            Plotly Figure object
        """
        # Fetch data
        df = self.fetch_cpi_data(start_date, end_date)

        # Calculate purchasing power
        base_cpi = df[self.cpi_series_id].iloc[0]
        df['Purchasing_Power'] = base_amount * (base_cpi / df[self.cpi_series_id])
        df['Cumulative_Inflation'] = ((df[self.cpi_series_id] / base_cpi) - 1) * 100

        # Create figure
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                f'Purchasing Power of ${base_amount:.0f} Over Time',
                'Cumulative Inflation Since Start'
            ),
            vertical_spacing=0.15
        )

        # 1. Purchasing Power
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Purchasing_Power'],
                mode='lines',
                name='Purchasing Power',
                line=dict(color='#D62728', width=2),
                fill='tozeroy',
                fillcolor='rgba(214, 39, 40, 0.2)',
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Value: $%{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        # Add base line
        fig.add_hline(y=base_amount, row=1, col=1, line_dash="dash", line_color="gray", line_width=1,
                     annotation_text=f"Original ${base_amount}")

        # 2. Cumulative Inflation
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Cumulative_Inflation'],
                mode='lines',
                name='Cumulative Inflation',
                line=dict(color='#FF7F0E', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 127, 14, 0.2)',
                hovertemplate='Date: %{x|%Y-%m-%d}<br>Total: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        # Update layout
        fig.update_layout(
            title=f"Purchasing Power Analysis<br><sub>Value of ${base_amount} from {df.index[0].strftime('%Y')}</sub>",
            template=PLOT_THEME,
            height=FIGURE_HEIGHT,
            width=FIGURE_WIDTH,
            showlegend=True,
            xaxis=dict(title=""),
            yaxis=dict(title="Dollar Value"),
            xaxis2=dict(title="Date"),
            yaxis2=dict(title="Cumulative Inflation (%)")
        )

        # Add final value annotation
        if len(df) > 0:
            final_value = df['Purchasing_Power'].iloc[-1]
            total_inflation = df['Cumulative_Inflation'].iloc[-1]

            fig.add_annotation(
                text=f"${base_amount} in {df.index[0].strftime('%Y')} = "
                     f"${final_value:.2f} in {df.index[-1].strftime('%Y')}<br>"
                     f"Total Inflation: {total_inflation:.1f}%",
                xref="paper", yref="paper",
                x=0.5, y=1.05,
                showarrow=False,
                bgcolor="white",
                bordercolor="gray",
                borderwidth=1,
                xanchor="center"
            )

        return fig

    def save_graph(self, fig: go.Figure = None, filename: str = 'cpi_graph.html',
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
                   filename: str = 'cpi_data.csv'):
        """
        Export CPI data to CSV

        Args:
            start_date: Start date for data
            end_date: End date for data
            filename: Output filename
        """
        df = self.fetch_cpi_data(start_date, end_date)

        output_path = os.path.join('FRED', 'outputs', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        df.to_csv(output_path)
        logger.info(f"Data exported to {output_path}")


def main():
    """Main function to create and save CPI visualizations"""
    print("Creating CPI Visualizations...")

    # Initialize visualizer
    viz = CPIVisualizer()

    # Create main CPI graph
    fig1 = viz.create_interactive_graph(start_date='2000-01-01')
    viz.save_graph(fig1, 'cpi_analysis.html')

    # Create historical analysis
    fig2 = viz.create_historical_analysis(start_date='1970-01-01')
    viz.save_graph(fig2, 'cpi_historical.html')

    # Create purchasing power analysis
    fig3 = viz.create_purchasing_power_analysis(start_date='2000-01-01', base_amount=100)
    viz.save_graph(fig3, 'purchasing_power.html')

    # Export data
    viz.export_data(start_date='2000-01-01', filename='cpi_data.csv')

    print("CPI visualizations completed successfully!")


if __name__ == "__main__":
    main()