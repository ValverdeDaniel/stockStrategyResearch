"""
Dash application for interactive technical indicators charting
"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import json
from typing import Dict, List, Any

# Import our modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from data.data_fetcher import DataFetcher
from visualization.chart_builder import TechnicalChartBuilder
from indicators.trend import SMA, EMA, MultiSMA
from indicators.momentum import RSI, MACD, AC
from indicators.volatility import BollingerBands
from indicators.volume import Volume, VWAP
from ui.components import create_indicator_controls, create_ticker_controls


def create_app() -> dash.Dash:
    """
    Create and configure the Dash application

    Returns:
        Configured Dash app
    """
    # Create Dash app with Bootstrap theme
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )

    # Define the app layout
    app.layout = dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H1("Technical Indicators Historical Chart", className="text-center mb-4"),
                html.P("Interactive charting system with customizable technical indicators",
                       className="text-center text-muted")
            ])
        ]),

        # Main controls row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Chart Controls"),
                    dbc.CardBody([
                        # Ticker and timeframe controls
                        create_ticker_controls(),

                        html.Hr(),

                        # Indicator selection
                        html.H5("Select Indicators", className="mb-3"),
                        dbc.Checklist(
                            id="indicator-toggles",
                            options=[
                                {"label": "Simple Moving Average (50/200/720)", "value": "SMA"},
                                {"label": "Exponential Moving Average", "value": "EMA"},
                                {"label": "Bollinger Bands", "value": "BB"},
                                {"label": "RSI (Relative Strength Index)", "value": "RSI"},
                                {"label": "MACD", "value": "MACD"},
                                {"label": "Volume", "value": "VOL"},
                                {"label": "VWAP (Volume Weighted Average Price)", "value": "VWAP"},
                                {"label": "AC (Accelerator/Decelerator)", "value": "AC"}
                            ],
                            value=["SMA", "RSI", "MACD", "VOL"],
                            inline=False,
                            switch=True
                        )
                    ])
                ])
            ], width=3),

            dbc.Col([
                # Main chart area
                dbc.Card([
                    dbc.CardBody([
                        dcc.Loading(
                            id="loading-chart",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="main-chart",
                                    style={"height": "800px"},
                                    config={
                                        'displayModeBar': True,
                                        'displaylogo': False,
                                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
                                    }
                                )
                            ]
                        )
                    ])
                ])
            ], width=9)
        ], className="mb-4"),

        # Parameter controls row (collapsible)
        dbc.Row([
            dbc.Col([
                dbc.Accordion([
                    dbc.AccordionItem(
                        id="parameter-controls",
                        title="Indicator Parameters",
                        children=[
                            html.Div(id="dynamic-parameter-controls")
                        ]
                    )
                ], start_collapsed=False)
            ])
        ], className="mb-4"),

        # Data storage components
        dcc.Store(id="data-store"),
        dcc.Store(id="indicators-store"),
        dcc.Store(id="params-store"),

        # Status message area
        dbc.Row([
            dbc.Col([
                html.Div(id="status-message", className="text-center")
            ])
        ])

    ], fluid=True)

    # Register callbacks
    register_callbacks(app)

    return app


def register_callbacks(app: dash.Dash) -> None:
    """
    Register all callbacks for the app

    Args:
        app: Dash application instance
    """

    @app.callback(
        [Output("data-store", "data"),
         Output("status-message", "children")],
        [Input("load-button", "n_clicks")],
        [State("ticker-input", "value"),
         State("timeframe-dropdown", "value")]
    )
    def load_data(n_clicks, ticker, timeframe):
        """Load stock data for the selected ticker and timeframe"""
        if n_clicks is None:
            return None, ""

        try:
            # Create data fetcher
            fetcher = DataFetcher()

            # Fetch data
            status_msg = dbc.Alert(f"Loading data for {ticker}...", color="info")
            df = fetcher.fetch_historical_data(ticker, period=timeframe, interval="1d")

            if df is None or df.empty:
                return None, dbc.Alert(f"No data found for {ticker}", color="danger")

            # Convert to JSON for storage
            data = {
                'ticker': ticker,
                'timeframe': timeframe,
                'ohlcv': df.to_json(orient='split', date_format='iso'),
                'stats': {
                    'start_date': str(df.index[0]),
                    'end_date': str(df.index[-1]),
                    'num_days': len(df),
                    'current_price': float(df['close'].iloc[-1]),
                    'change_pct': float((df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100)
                }
            }

            success_msg = dbc.Alert(
                f"Loaded {data['stats']['num_days']} days of data for {ticker} "
                f"({data['stats']['start_date'][:10]} to {data['stats']['end_date'][:10]})",
                color="success"
            )

            return data, success_msg

        except Exception as e:
            error_msg = dbc.Alert(f"Error loading data: {str(e)}", color="danger")
            return None, error_msg

    @app.callback(
        Output("dynamic-parameter-controls", "children"),
        [Input("indicator-toggles", "value")]
    )
    def update_parameter_controls(selected_indicators):
        """Update parameter controls based on selected indicators"""
        if not selected_indicators:
            return html.P("Select indicators to see parameters", className="text-muted")

        return create_indicator_controls(selected_indicators)

    @app.callback(
        Output("main-chart", "figure"),
        [Input("data-store", "data"),
         Input("indicator-toggles", "value"),
         Input({'type': 'indicator-param', 'indicator': ALL, 'param': ALL}, 'value')]
    )
    def update_chart(data, selected_indicators, param_values):
        """Update the main chart with selected indicators"""
        if data is None:
            # Return empty figure with instructions
            fig = go.Figure()
            fig.add_annotation(
                text="Enter a ticker symbol and click 'Load Data' to begin",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color="gray")
            )
            fig.update_layout(
                height=800,
                template='plotly_white',
                xaxis=dict(visible=False),
                yaxis=dict(visible=False)
            )
            return fig

        try:
            # Parse data
            df = pd.read_json(data['ohlcv'], orient='split')
            df.index = pd.to_datetime(df.index)

            # Create chart builder
            chart_builder = TechnicalChartBuilder(
                ticker=data['ticker'],
                data=df,
                timeframe=data['timeframe']
            )

            # Calculate and add selected indicators
            if selected_indicators:
                for indicator_name in selected_indicators:
                    indicator_obj = create_indicator_instance(indicator_name, param_values)
                    if indicator_obj:
                        indicator_obj.calculate(df)
                        chart_builder.add_indicator(indicator_name, indicator_obj)

            # Build and return the chart
            return chart_builder.build_chart()

        except Exception as e:
            print(f"Error updating chart: {e}")
            # Return error figure
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error creating chart: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="red")
            )
            fig.update_layout(height=800, template='plotly_white')
            return fig


def create_indicator_instance(indicator_name: str, param_values: List) -> Any:
    """
    Create an indicator instance with current parameters

    Args:
        indicator_name: Name of the indicator
        param_values: List of parameter values

    Returns:
        Indicator instance or None
    """
    # Default indicator instances
    default_indicators = {
        'SMA': lambda: MultiSMA(periods=[50, 200, 720]),
        'EMA': lambda: EMA(period=20),
        'BB': lambda: BollingerBands(),
        'RSI': lambda: RSI(),
        'MACD': lambda: MACD(),
        'VOL': lambda: Volume(),
        'VWAP': lambda: VWAP(),
        'AC': lambda: AC()
    }

    if indicator_name in default_indicators:
        return default_indicators[indicator_name]()

    return None