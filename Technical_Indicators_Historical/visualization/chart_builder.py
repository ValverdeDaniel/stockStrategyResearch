"""
Chart builder for creating multi-panel technical indicator charts
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional


class TechnicalChartBuilder:
    """Builds multi-panel charts with technical indicators"""

    def __init__(self, ticker: str, data: pd.DataFrame, timeframe: str = "1Y"):
        """
        Initialize chart builder

        Args:
            ticker: Stock symbol
            data: DataFrame with OHLCV data
            timeframe: Time period for the chart
        """
        self.ticker = ticker
        self.data = data
        self.timeframe = timeframe
        self.indicators = {}
        self.panel_config = {
            'price': {'height': 0.4, 'row': 1},
            'volume': {'height': 0.15, 'row': 2},
            'rsi': {'height': 0.15, 'row': 3},
            'macd': {'height': 0.15, 'row': 4},
            'ac': {'height': 0.15, 'row': 5}
        }

    def add_indicator(self, indicator_name: str, indicator_obj: Any) -> None:
        """
        Add an indicator to the chart

        Args:
            indicator_name: Name of the indicator
            indicator_obj: Indicator object with calculated data
        """
        self.indicators[indicator_name] = indicator_obj

    def _determine_panels(self) -> Dict[str, Any]:
        """
        Determine which panels to show based on active indicators

        Returns:
            Dictionary with panel configuration
        """
        panels = {'price': True}  # Always show price panel

        for name, indicator in self.indicators.items():
            config = indicator.get_plot_config()

            if isinstance(config, list):
                # Handle multiple configs (like Multi-SMA)
                for c in config:
                    if 'panel' in c:
                        panels[c['panel']] = True
            elif 'panel' in config:
                panels[config['panel']] = True

        return panels

    def build_chart(self) -> go.Figure:
        """
        Build the complete chart with all indicators

        Returns:
            Plotly figure object
        """
        # Determine panels to show
        active_panels = self._determine_panels()
        num_panels = len(active_panels)

        # Calculate row heights
        row_heights = []
        subplot_titles = []

        if 'price' in active_panels:
            row_heights.append(0.4)
            subplot_titles.append(f"{self.ticker} - {self.timeframe}")

        if 'volume' in active_panels:
            row_heights.append(0.15)
            subplot_titles.append("Volume")

        if 'rsi' in active_panels:
            row_heights.append(0.15)
            subplot_titles.append("RSI")

        if 'macd' in active_panels:
            row_heights.append(0.15)
            subplot_titles.append("MACD")

        if 'ac' in active_panels:
            row_heights.append(0.15)
            subplot_titles.append("Accelerator/Decelerator")

        # Normalize heights
        total_height = sum(row_heights)
        row_heights = [h / total_height for h in row_heights]

        # Create subplots
        fig = make_subplots(
            rows=num_panels,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=row_heights,
            subplot_titles=subplot_titles
        )

        # Track current row for each panel
        panel_rows = {}
        current_row = 1

        for panel in ['price', 'volume', 'rsi', 'macd', 'ac']:
            if panel in active_panels:
                panel_rows[panel] = current_row
                current_row += 1

        # Add candlestick chart to price panel
        if 'price' in active_panels:
            self._add_candlesticks(fig, panel_rows['price'])

        # Add indicators
        for name, indicator in self.indicators.items():
            self._add_indicator_to_chart(fig, indicator, panel_rows)

        # Update layout
        self._update_layout(fig)

        return fig

    def _add_candlesticks(self, fig: go.Figure, row: int) -> None:
        """
        Add candlestick chart to the figure

        Args:
            fig: Plotly figure
            row: Row number for the candlesticks
        """
        fig.add_trace(
            go.Candlestick(
                x=self.data.index,
                open=self.data['open'],
                high=self.data['high'],
                low=self.data['low'],
                close=self.data['close'],
                name='Price',
                increasing_line_color='#27AE60',
                decreasing_line_color='#E74C3C',
                showlegend=True
            ),
            row=row,
            col=1
        )

    def _add_indicator_to_chart(
        self,
        fig: go.Figure,
        indicator: Any,
        panel_rows: Dict[str, int]
    ) -> None:
        """
        Add an indicator to the chart

        Args:
            fig: Plotly figure
            indicator: Indicator object
            panel_rows: Mapping of panel names to row numbers
        """
        config = indicator.get_plot_config()

        # Handle multiple configurations (like Multi-SMA)
        if isinstance(config, list):
            for c in config:
                self._add_single_indicator(fig, indicator, c, panel_rows)
        else:
            self._add_single_indicator(fig, indicator, config, panel_rows)

    def _add_single_indicator(
        self,
        fig: go.Figure,
        indicator: Any,
        config: Dict[str, Any],
        panel_rows: Dict[str, int]
    ) -> None:
        """
        Add a single indicator trace to the chart

        Args:
            fig: Plotly figure
            indicator: Indicator object
            config: Plot configuration
            panel_rows: Mapping of panel names to row numbers
        """
        if indicator.data is None:
            return

        panel = config.get('panel', 'price')
        row = panel_rows.get(panel, 1)

        plot_type = config.get('type', 'line')

        if plot_type == 'line':
            # Simple line plot
            data_column = indicator.name if indicator.name in indicator.data.columns else indicator.data.columns[0]
            fig.add_trace(
                go.Scatter(
                    x=indicator.data.index,
                    y=indicator.data[data_column],
                    name=config.get('name', indicator.name),
                    line=dict(color=config.get('color', '#3498DB'), width=config.get('width', 1)),
                    mode='lines'
                ),
                row=row,
                col=1
            )

        elif plot_type == 'multi_line':
            # Multiple lines (like RSI with overbought/oversold)
            lines = config.get('lines', [])
            for line_config in lines:
                column_name = line_config['name']
                if column_name in indicator.data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=indicator.data.index,
                            y=indicator.data[column_name],
                            name=column_name,
                            line=dict(
                                color=line_config.get('color', '#3498DB'),
                                width=line_config.get('width', 1),
                                dash=line_config.get('dash', 'solid')
                            ),
                            mode='lines'
                        ),
                        row=row,
                        col=1
                    )

            # Add fills if specified
            fills = config.get('fills', [])
            for fill in fills:
                fig.add_hrect(
                    y0=fill['y0'],
                    y1=fill['y1'],
                    fillcolor=fill['color'],
                    layer="below",
                    line_width=0,
                    row=row,
                    col=1
                )

        elif plot_type == 'multi_trace':
            # Multiple traces (like MACD)
            traces = config.get('traces', [])
            for trace_config in traces:
                trace_type = trace_config.get('type', 'line')
                trace_name = trace_config.get('name')

                if trace_type == 'line' and trace_name in indicator.data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=indicator.data.index,
                            y=indicator.data[trace_name],
                            name=trace_name,
                            line=dict(
                                color=trace_config.get('color', '#3498DB'),
                                width=trace_config.get('width', 1)
                            ),
                            mode='lines'
                        ),
                        row=row,
                        col=1
                    )
                elif trace_type == 'bar' and 'Histogram' in indicator.data.columns:
                    # MACD histogram
                    colors = ['green' if val >= 0 else 'red' for val in indicator.data['Histogram']]
                    fig.add_trace(
                        go.Bar(
                            x=indicator.data.index,
                            y=indicator.data['Histogram'],
                            name='Histogram',
                            marker_color=colors
                        ),
                        row=row,
                        col=1
                    )

        elif plot_type == 'bar':
            # Bar chart (like Volume or AC)
            if 'Volume' in indicator.data.columns:
                # Volume bars
                colors = indicator.data.get('Volume_Color', '#3498DB')
                fig.add_trace(
                    go.Bar(
                        x=indicator.data.index,
                        y=indicator.data['Volume'],
                        name='Volume',
                        marker_color=colors,
                        showlegend=False
                    ),
                    row=row,
                    col=1
                )

                # Add volume MA if present
                if 'Volume_MA' in indicator.data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=indicator.data.index,
                            y=indicator.data['Volume_MA'],
                            name='Volume MA',
                            line=dict(color='#3498DB', width=1),
                            mode='lines'
                        ),
                        row=row,
                        col=1
                    )
            elif 'AC' in indicator.data.columns:
                # AC bars
                colors = ['green' if val >= 0 else 'red' for val in indicator.data['AC']]
                fig.add_trace(
                    go.Bar(
                        x=indicator.data.index,
                        y=indicator.data['AC'],
                        name='AC',
                        marker_color=colors
                    ),
                    row=row,
                    col=1
                )

        elif plot_type == 'bands':
            # Bands (like Bollinger Bands)
            traces = config.get('traces', [])
            for trace in traces:
                column_name = trace['name'].replace(' ', '_')
                if column_name in indicator.data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=indicator.data.index,
                            y=indicator.data[column_name],
                            name=trace['name'],
                            line=dict(
                                color=trace.get('color', '#3498DB'),
                                width=trace.get('width', 1),
                                dash=trace.get('dash', 'solid')
                            ),
                            mode='lines'
                        ),
                        row=row,
                        col=1
                    )

            # Add fill between bands
            fill_config = config.get('fill')
            if fill_config and 'BB_Upper' in indicator.data.columns and 'BB_Lower' in indicator.data.columns:
                # Add invisible traces for fill
                fig.add_trace(
                    go.Scatter(
                        x=indicator.data.index,
                        y=indicator.data['BB_Upper'],
                        fill=None,
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo='skip'
                    ),
                    row=row,
                    col=1
                )

                fig.add_trace(
                    go.Scatter(
                        x=indicator.data.index,
                        y=indicator.data['BB_Lower'],
                        fill='tonexty',
                        mode='lines',
                        line=dict(width=0),
                        fillcolor=fill_config['color'],
                        showlegend=False,
                        hoverinfo='skip'
                    ),
                    row=row,
                    col=1
                )

    def _update_layout(self, fig: go.Figure) -> None:
        """
        Update the chart layout

        Args:
            fig: Plotly figure
        """
        fig.update_layout(
            title={
                'text': f"{self.ticker} Technical Analysis - {self.timeframe}",
                'x': 0.5,
                'xanchor': 'center'
            },
            xaxis_rangeslider_visible=False,
            height=800,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255,255,255,0.8)"
            ),
            hovermode='x unified',
            template='plotly_white',
            margin=dict(l=50, r=50, t=80, b=50)
        )

        # Update x-axis
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            showline=True,
            linewidth=1,
            linecolor='black'
        )

        # Update y-axis
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            showline=True,
            linewidth=1,
            linecolor='black'
        )

    def save_chart(self, filename: str = None) -> str:
        """
        Save the chart to an HTML file

        Args:
            filename: Output filename (optional)

        Returns:
            Path to saved file
        """
        if filename is None:
            filename = f"{self.ticker}_technical_chart_{self.timeframe}.html"

        fig = self.build_chart()
        fig.write_html(filename)

        return filename