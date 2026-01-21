"""
UI components for the Dash application
"""

from dash import dcc, html
import dash_bootstrap_components as dbc
from typing import List, Dict, Any


def create_ticker_controls() -> html.Div:
    """
    Create ticker and timeframe selection controls

    Returns:
        Div containing ticker controls
    """
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Label("Ticker Symbol"),
                dbc.Input(
                    id="ticker-input",
                    type="text",
                    placeholder="e.g., AAPL",
                    value="AAPL",
                    className="mb-2"
                )
            ], width=6),
            dbc.Col([
                dbc.Label("Timeframe"),
                dcc.Dropdown(
                    id="timeframe-dropdown",
                    options=[
                        {"label": "1 Month", "value": "1mo"},
                        {"label": "3 Months", "value": "3mo"},
                        {"label": "6 Months", "value": "6mo"},
                        {"label": "1 Year", "value": "1y"},
                        {"label": "2 Years", "value": "2y"},
                        {"label": "5 Years", "value": "5y"}
                    ],
                    value="1y",
                    className="mb-2"
                )
            ], width=6)
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Load Data",
                    id="load-button",
                    color="primary",
                    className="w-100",
                    size="lg"
                )
            ])
        ], className="mt-2")
    ])


def create_indicator_controls(selected_indicators: List[str]) -> html.Div:
    """
    Create parameter controls for selected indicators

    Args:
        selected_indicators: List of selected indicator names

    Returns:
        Div containing parameter controls
    """
    controls = []

    for indicator in selected_indicators:
        control = create_single_indicator_control(indicator)
        if control:
            controls.append(control)

    if not controls:
        return html.P("No parameters available", className="text-muted")

    return html.Div(controls)


def create_single_indicator_control(indicator: str) -> html.Div:
    """
    Create parameter controls for a single indicator

    Args:
        indicator: Indicator name

    Returns:
        Div containing controls for the indicator
    """
    if indicator == "SMA":
        return create_sma_controls()
    elif indicator == "EMA":
        return create_ema_controls()
    elif indicator == "BB":
        return create_bollinger_bands_controls()
    elif indicator == "RSI":
        return create_rsi_controls()
    elif indicator == "MACD":
        return create_macd_controls()
    elif indicator == "VOL":
        return create_volume_controls()
    elif indicator == "VWAP":
        return create_vwap_controls()
    elif indicator == "AC":
        return create_ac_controls()
    else:
        return None


def create_sma_controls() -> html.Div:
    """Create SMA parameter controls"""
    return dbc.Card([
        dbc.CardHeader("Simple Moving Average (SMA)"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("SMA 50"),
                    dbc.Checklist(
                        id={'type': 'indicator-param', 'indicator': 'SMA', 'param': 'sma50_enabled'},
                        options=[{"label": "Enable", "value": True}],
                        value=[True],
                        switch=True
                    ),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'SMA', 'param': 'sma50_color'},
                        type="color",
                        value="#FF6B6B",
                        className="mt-1"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("SMA 200"),
                    dbc.Checklist(
                        id={'type': 'indicator-param', 'indicator': 'SMA', 'param': 'sma200_enabled'},
                        options=[{"label": "Enable", "value": True}],
                        value=[True],
                        switch=True
                    ),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'SMA', 'param': 'sma200_color'},
                        type="color",
                        value="#4ECDC4",
                        className="mt-1"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("SMA 720"),
                    dbc.Checklist(
                        id={'type': 'indicator-param', 'indicator': 'SMA', 'param': 'sma720_enabled'},
                        options=[{"label": "Enable", "value": True}],
                        value=[True],
                        switch=True
                    ),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'SMA', 'param': 'sma720_color'},
                        type="color",
                        value="#45B7D1",
                        className="mt-1"
                    )
                ], width=4)
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("Price Source", className="mt-2"),
                    dcc.Dropdown(
                        id={'type': 'indicator-param', 'indicator': 'SMA', 'param': 'price'},
                        options=[
                            {"label": "Close", "value": "close"},
                            {"label": "Open", "value": "open"},
                            {"label": "High", "value": "high"},
                            {"label": "Low", "value": "low"},
                            {"label": "HL/2", "value": "hl2"},
                            {"label": "HLC/3", "value": "hlc3"},
                            {"label": "OHLC/4", "value": "ohlc4"}
                        ],
                        value="close"
                    )
                ])
            ])
        ])
    ], className="mb-3")


def create_ema_controls() -> html.Div:
    """Create EMA parameter controls"""
    return dbc.Card([
        dbc.CardHeader("Exponential Moving Average (EMA)"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Period"),
                    dcc.Slider(
                        id={'type': 'indicator-param', 'indicator': 'EMA', 'param': 'period'},
                        min=5,
                        max=200,
                        value=20,
                        marks={i: str(i) for i in [5, 20, 50, 100, 200]},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Displace"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'EMA', 'param': 'displace'},
                        type="number",
                        value=0,
                        min=-50,
                        max=50
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Color"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'EMA', 'param': 'color'},
                        type="color",
                        value="#4ECDC4"
                    )
                ], width=3)
            ])
        ])
    ], className="mb-3")


def create_bollinger_bands_controls() -> html.Div:
    """Create Bollinger Bands parameter controls"""
    return dbc.Card([
        dbc.CardHeader("Bollinger Bands"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Length"),
                    dcc.Slider(
                        id={'type': 'indicator-param', 'indicator': 'BB', 'param': 'period'},
                        min=5,
                        max=100,
                        value=20,
                        marks={i: str(i) for i in [5, 20, 50, 100]},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Std Dev Above"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'BB', 'param': 'std_dev_upper'},
                        type="number",
                        value=2.0,
                        min=0.5,
                        max=4.0,
                        step=0.5
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Std Dev Below"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'BB', 'param': 'std_dev_lower'},
                        type="number",
                        value=2.0,
                        min=0.5,
                        max=4.0,
                        step=0.5
                    )
                ], width=3)
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("Price Source", className="mt-2"),
                    dcc.Dropdown(
                        id={'type': 'indicator-param', 'indicator': 'BB', 'param': 'price'},
                        options=[
                            {"label": "Close", "value": "close"},
                            {"label": "Open", "value": "open"},
                            {"label": "OHLC Average", "value": "ohlc4"},
                            {"label": "High", "value": "high"},
                            {"label": "Low", "value": "low"},
                            {"label": "Median (HL/2)", "value": "hl2"}
                        ],
                        value="close"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Average Type", className="mt-2"),
                    dcc.Dropdown(
                        id={'type': 'indicator-param', 'indicator': 'BB', 'param': 'ma_type'},
                        options=[
                            {"label": "Simple", "value": "simple"},
                            {"label": "Exponential", "value": "exponential"},
                            {"label": "Weighted", "value": "weighted"},
                            {"label": "Wilders", "value": "wilders"}
                        ],
                        value="simple"
                    )
                ], width=6)
            ])
        ])
    ], className="mb-3")


def create_rsi_controls() -> html.Div:
    """Create RSI parameter controls"""
    return dbc.Card([
        dbc.CardHeader("RSI (Relative Strength Index)"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Length"),
                    dcc.Slider(
                        id={'type': 'indicator-param', 'indicator': 'RSI', 'param': 'period'},
                        min=5,
                        max=50,
                        value=14,
                        marks={i: str(i) for i in [5, 14, 21, 50]},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("Overbought Level"),
                    dcc.Slider(
                        id={'type': 'indicator-param', 'indicator': 'RSI', 'param': 'overbought'},
                        min=60,
                        max=90,
                        value=70,
                        step=5,
                        marks={i: str(i) for i in range(60, 95, 10)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Oversold Level"),
                    dcc.Slider(
                        id={'type': 'indicator-param', 'indicator': 'RSI', 'param': 'oversold'},
                        min=10,
                        max=40,
                        value=30,
                        step=5,
                        marks={i: str(i) for i in range(10, 45, 10)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    )
                ], width=6)
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("Price Source", className="mt-2"),
                    dcc.Dropdown(
                        id={'type': 'indicator-param', 'indicator': 'RSI', 'param': 'price'},
                        options=[
                            {"label": "Close", "value": "close"},
                            {"label": "Open", "value": "open"},
                            {"label": "OHLC Average", "value": "ohlc4"},
                            {"label": "High", "value": "high"},
                            {"label": "Low", "value": "low"},
                            {"label": "Median (HL/2)", "value": "hl2"}
                        ],
                        value="close"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("RSI Color", className="mt-2"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'RSI', 'param': 'color'},
                        type="color",
                        value="#8E44AD"
                    )
                ], width=6)
            ])
        ])
    ], className="mb-3")


def create_macd_controls() -> html.Div:
    """Create MACD parameter controls"""
    return dbc.Card([
        dbc.CardHeader("MACD"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Fast Length"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'MACD', 'param': 'fast_period'},
                        type="number",
                        value=12,
                        min=5,
                        max=50
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Slow Length"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'MACD', 'param': 'slow_period'},
                        type="number",
                        value=26,
                        min=10,
                        max=100
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Signal Length"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'MACD', 'param': 'signal_period'},
                        type="number",
                        value=9,
                        min=5,
                        max=30
                    )
                ], width=4)
            ]),
            dbc.Row([
                dbc.Col([
                    html.Label("Average Type", className="mt-2"),
                    dcc.Dropdown(
                        id={'type': 'indicator-param', 'indicator': 'MACD', 'param': 'ma_type'},
                        options=[
                            {"label": "Exponential", "value": "exponential"},
                            {"label": "Simple", "value": "simple"},
                            {"label": "Weighted", "value": "weighted"},
                            {"label": "Wilders", "value": "wilders"}
                        ],
                        value="exponential"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("MACD Line Color", className="mt-2"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'MACD', 'param': 'macd_color'},
                        type="color",
                        value="#3498DB"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("Signal Line Color", className="mt-2"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'MACD', 'param': 'signal_color'},
                        type="color",
                        value="#E67E22"
                    )
                ], width=3)
            ])
        ])
    ], className="mb-3")


def create_volume_controls() -> html.Div:
    """Create Volume parameter controls"""
    return dbc.Card([
        dbc.CardHeader("Volume"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Up Volume Color"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'VOL', 'param': 'up_color'},
                        type="color",
                        value="#27AE60"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Down Volume Color"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'VOL', 'param': 'down_color'},
                        type="color",
                        value="#E74C3C"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Show Volume MA"),
                    dbc.Checklist(
                        id={'type': 'indicator-param', 'indicator': 'VOL', 'param': 'show_ma'},
                        options=[{"label": "Enable", "value": True}],
                        value=[],
                        switch=True
                    )
                ], width=4)
            ])
        ])
    ], className="mb-3")


def create_vwap_controls() -> html.Div:
    """Create VWAP parameter controls"""
    return dbc.Card([
        dbc.CardHeader("VWAP (Volume Weighted Average Price)"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Anchor Period"),
                    dcc.Dropdown(
                        id={'type': 'indicator-param', 'indicator': 'VWAP', 'param': 'anchor'},
                        options=[
                            {"label": "Session (Daily)", "value": "session"},
                            {"label": "Week", "value": "week"},
                            {"label": "Month", "value": "month"},
                            {"label": "Quarter", "value": "quarter"},
                            {"label": "Year", "value": "year"}
                        ],
                        value="session"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("VWAP Color"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'VWAP', 'param': 'color'},
                        type="color",
                        value="#9B59B6"
                    )
                ], width=6)
            ])
        ])
    ], className="mb-3")


def create_ac_controls() -> html.Div:
    """Create AC parameter controls"""
    return dbc.Card([
        dbc.CardHeader("AC (Accelerator/Decelerator)"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Positive Color"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'AC', 'param': 'positive_color'},
                        type="color",
                        value="#27AE60"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Negative Color"),
                    dbc.Input(
                        id={'type': 'indicator-param', 'indicator': 'AC', 'param': 'negative_color'},
                        type="color",
                        value="#E74C3C"
                    )
                ], width=6)
            ])
        ])
    ], className="mb-3")