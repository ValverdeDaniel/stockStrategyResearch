"""
AMD Financial Table Generator
Creates a comprehensive financial table with historical data (2019-2024) and forecasts (2025-2026)
for Revenue Per Share, Cash Flow Per Share, and Earnings Per Share.

Uses EODHD API for data fetching.
"""

import requests
import pandas as pd
from datetime import datetime
import json
import sys
import os
import numpy as np

# Add parent directory to path for imports if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API Configuration
EODHD_API_KEY = "67ffece4b2ae08.94077168"
EODHD_BASE = "https://eodhd.com/api"

class FinancialTableGenerator:
    """Generate financial tables with historical and forecast data for a given ticker."""

    def __init__(self, ticker, api_key=EODHD_API_KEY):
        """
        Initialize the generator.

        Args:
            ticker: Stock ticker symbol (e.g., 'AMD')
            api_key: EODHD API key
        """
        self.ticker = ticker
        self.api_key = api_key
        self.ticker_formatted = f"{ticker}.US"  # EODHD format
        self.fundamentals_data = None
        self.shares_outstanding = None

    def fetch_fundamentals(self):
        """Fetch comprehensive fundamentals data from EODHD."""
        url = f"{EODHD_BASE}/fundamentals/{self.ticker_formatted}"
        params = {
            "api_token": self.api_key,
            "fmt": "json"
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            self.fundamentals_data = response.json()

            # Get shares outstanding
            if "SharesStats" in self.fundamentals_data:
                shares = self.fundamentals_data["SharesStats"].get("SharesOutstanding", 0)
            else:
                # Fallback to outstanding shares from highlights
                shares = self.fundamentals_data.get("Highlights", {}).get("SharesOutstanding", 0)

            # Convert shares to float
            if shares:
                try:
                    self.shares_outstanding = float(shares)
                except (ValueError, TypeError):
                    self.shares_outstanding = 0
            else:
                self.shares_outstanding = 0

            if self.shares_outstanding == 0:
                print("Warning: Could not find shares outstanding, using 1 billion as estimate")
                self.shares_outstanding = 1_000_000_000  # Default to 1B shares

            return True
        except Exception as e:
            print(f"Error fetching fundamentals: {e}")
            return False

    def fetch_historical_data(self, start_year=2019, end_year=2024):
        """
        Fetch historical financial data.

        Returns:
            dict: Historical data with years as keys
        """
        historical_data = {}

        if not self.fundamentals_data:
            print("No fundamentals data available. Call fetch_fundamentals() first.")
            return historical_data

        # Get Income Statement data
        income_stmt = self.fundamentals_data.get("Financials", {}).get("Income_Statement", {}).get("yearly", {})

        # Get Cash Flow data
        cash_flow = self.fundamentals_data.get("Financials", {}).get("Cash_Flow", {}).get("yearly", {})

        # Get Earnings data for EPS
        earnings_annual = self.fundamentals_data.get("Earnings", {}).get("Annual", {})

        for year in range(start_year, end_year + 1):
            year_str = f"{year}-12-31"
            year_data = {}

            # Find the actual date key for this year (handles different fiscal year ends)
            income_year_key = None
            cash_year_key = None
            earnings_year_key = None

            # Search for this year's data in income statement
            for date_key in income_stmt.keys():
                if date_key.startswith(str(year)):
                    income_year_key = date_key
                    break

            # Search for this year's data in cash flow
            for date_key in cash_flow.keys():
                if date_key.startswith(str(year)):
                    cash_year_key = date_key
                    break

            # Search for this year's data in earnings
            for date_key in earnings_annual.keys():
                if date_key.startswith(str(year)):
                    earnings_year_key = date_key
                    break

            # Revenue
            if income_year_key and income_year_key in income_stmt:
                revenue = income_stmt[income_year_key].get("totalRevenue", 0)
                # Convert to float if it's a string
                if revenue:
                    try:
                        revenue = float(revenue)
                        if self.shares_outstanding:
                            year_data["revenue_per_share"] = revenue / self.shares_outstanding
                        else:
                            year_data["revenue_per_share"] = None
                    except (ValueError, TypeError):
                        year_data["revenue_per_share"] = None
                else:
                    year_data["revenue_per_share"] = None

                # Net Income for EPS calculation
                net_income = income_stmt[income_year_key].get("netIncome", 0)
                if net_income:
                    try:
                        net_income = float(net_income)
                        if self.shares_outstanding:
                            year_data["eps_calculated"] = net_income / self.shares_outstanding
                        else:
                            year_data["eps_calculated"] = None
                    except (ValueError, TypeError):
                        year_data["eps_calculated"] = None
                else:
                    year_data["eps_calculated"] = None

            # Operating Cash Flow
            if cash_year_key and cash_year_key in cash_flow:
                operating_cf = cash_flow[cash_year_key].get("totalCashFromOperatingActivities", 0)
                if operating_cf:
                    try:
                        operating_cf = float(operating_cf)
                        if self.shares_outstanding:
                            year_data["cf_per_share"] = operating_cf / self.shares_outstanding
                        else:
                            year_data["cf_per_share"] = None
                    except (ValueError, TypeError):
                        year_data["cf_per_share"] = None
                else:
                    year_data["cf_per_share"] = None

            # EPS from Earnings (preferred over calculated)
            if earnings_year_key and earnings_year_key in earnings_annual:
                eps_actual = earnings_annual[earnings_year_key].get("epsActual")
                if eps_actual:
                    try:
                        year_data["eps"] = float(eps_actual)
                    except (ValueError, TypeError):
                        year_data["eps"] = year_data.get("eps_calculated")
                else:
                    year_data["eps"] = year_data.get("eps_calculated")
            elif "eps_calculated" in year_data:
                year_data["eps"] = year_data["eps_calculated"]
            else:
                year_data["eps"] = None

            if year_data:
                historical_data[year] = year_data

        return historical_data

    def fetch_forecast_data(self):
        """
        Fetch forecast data for 2025-2026 from EODHD Earnings.Trend.

        Returns:
            dict: Forecast data with years as keys
        """
        forecast_data = {}

        if not self.fundamentals_data:
            print("No fundamentals data available. Call fetch_fundamentals() first.")
            return forecast_data

        # Get Earnings Trend data
        earnings_trend = self.fundamentals_data.get("Earnings", {}).get("Trend", {})

        # Map period codes to years
        period_mapping = {
            "+1y": 2025,  # Next year
            "+2y": 2026,  # Year after next
            "0y": 2024,   # Current year (for reference)
        }

        # Try different period formats EODHD might use
        alternative_mappings = {
            "2025-12-31": 2025,
            "2026-12-31": 2026,
            "2025-Q4": 2025,
            "2026-Q4": 2026,
        }

        for period_key, year in period_mapping.items():
            if period_key in earnings_trend and year >= 2025:
                trend = earnings_trend[period_key]

                year_data = {}

                # Revenue estimate
                revenue_est = trend.get("revenueEstimateAvg", 0)
                if revenue_est:
                    try:
                        revenue_est = float(revenue_est)
                        if self.shares_outstanding:
                            year_data["revenue_per_share"] = revenue_est / self.shares_outstanding
                    except (ValueError, TypeError):
                        pass

                # EPS estimate
                eps_est = trend.get("earningsEstimateAvg")
                if eps_est:
                    try:
                        year_data["eps"] = float(eps_est)
                        # Cash Flow estimate (use 1.3x EPS for tech companies)
                        year_data["cf_per_share"] = year_data["eps"] * 1.3
                    except (ValueError, TypeError):
                        year_data["eps"] = None

                # Add metadata
                year_data["number_of_analysts"] = trend.get("earningsEstimateNumberOfAnalysts", 0)
                year_data["eps_low"] = trend.get("earningsEstimateLow")
                year_data["eps_high"] = trend.get("earningsEstimateHigh")
                year_data["revenue_low"] = trend.get("revenueEstimateLow")
                year_data["revenue_high"] = trend.get("revenueEstimateHigh")

                if year_data:
                    forecast_data[year] = year_data

        # Check alternative period formats
        for period_key, year in alternative_mappings.items():
            if period_key in earnings_trend and year not in forecast_data:
                trend = earnings_trend[period_key]

                year_data = {}

                # Revenue estimate
                revenue_est = trend.get("revenueEstimateAvg", 0)
                if revenue_est:
                    try:
                        revenue_est = float(revenue_est)
                        if self.shares_outstanding:
                            year_data["revenue_per_share"] = revenue_est / self.shares_outstanding
                    except (ValueError, TypeError):
                        pass

                # EPS estimate
                eps_est = trend.get("earningsEstimateAvg")
                if eps_est:
                    try:
                        year_data["eps"] = float(eps_est)
                        # Cash Flow estimate (use 1.3x EPS for tech companies)
                        year_data["cf_per_share"] = year_data["eps"] * 1.3
                    except (ValueError, TypeError):
                        year_data["eps"] = None

                # Add metadata
                year_data["number_of_analysts"] = trend.get("earningsEstimateNumberOfAnalysts", 0)

                if year_data:
                    forecast_data[year] = year_data

        return forecast_data

    def fetch_stock_prices(self, start_year=2019, end_year=2024):
        """
        Fetch year-end stock prices for the ticker.

        Returns:
            dict: Year-end closing prices {year: price}
        """
        stock_prices = {}

        # Fetch historical price data
        for year in range(start_year, end_year + 1):
            # Get the last trading day of the year (approximately Dec 31)
            date_str = f"{year}-12-31"
            # Fetch a range around year-end to ensure we get the last trading day
            start_date = f"{year}-12-20"
            end_date = f"{year + 1}-01-10" if year < datetime.now().year else datetime.now().strftime("%Y-%m-%d")

            url = f"{EODHD_BASE}/eod/{self.ticker_formatted}"
            params = {
                "api_token": self.api_key,
                "from": start_date,
                "to": end_date,
                "fmt": "json"
            }

            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                price_data = response.json()

                if price_data:
                    # Filter to get the last trading day of the year
                    year_prices = [p for p in price_data if p['date'].startswith(str(year))]
                    if year_prices:
                        # Get the last available price for the year
                        last_price = year_prices[-1]['adjusted_close']
                        stock_prices[year] = float(last_price)
                        print(f"  {year}: ${last_price:.2f}")
                    else:
                        stock_prices[year] = None
                else:
                    stock_prices[year] = None

            except Exception as e:
                print(f"  Error fetching {year} price: {e}")
                stock_prices[year] = None

        # Get current price for reference
        try:
            url = f"{EODHD_BASE}/real-time/{self.ticker_formatted}"
            params = {
                "api_token": self.api_key,
                "fmt": "json"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            current_data = response.json()
            if current_data and 'close' in current_data:
                stock_prices['current'] = float(current_data['close'])
                print(f"  Current: ${current_data['close']:.2f}")
        except Exception as e:
            print(f"  Error fetching current price: {e}")
            stock_prices['current'] = None

        return stock_prices

    def create_dataframe(self, historical_data, forecast_data, stock_prices=None):
        """
        Create a pandas DataFrame from historical and forecast data with YoY analysis.

        Args:
            historical_data: Dict of historical financial data
            forecast_data: Dict of forecast financial data
            stock_prices: Dict of year-end stock prices

        Returns:
            pd.DataFrame: Combined financial table with YoY changes
        """
        all_data = []

        # Combine all years for easier processing
        all_years_data = {}
        for year, data in historical_data.items():
            all_years_data[year] = {"type": "Historical", **data}
        for year, data in forecast_data.items():
            all_years_data[year] = {"type": "Forecast", **data}

        # Process each year in order
        sorted_years = sorted(all_years_data.keys())
        prev_data = None
        prev_price = None

        for i, year in enumerate(sorted_years):
            data = all_years_data[year]
            year_row = {
                "Year": year,
                "Type": data["type"],
                "Stock Price": stock_prices.get(year) if stock_prices else None
            }

            # Add fundamental metrics
            year_row["Revenue Per Share"] = data.get("revenue_per_share")
            year_row["Cash Flow Per Share"] = data.get("cf_per_share")
            year_row["Earnings Per Share"] = data.get("eps")

            # Calculate YoY changes
            if i > 0 and prev_data:
                # Revenue YoY
                if year_row["Revenue Per Share"] and prev_data.get("revenue_per_share"):
                    year_row["Revenue YoY %"] = ((year_row["Revenue Per Share"] - prev_data["revenue_per_share"]) /
                                                 prev_data["revenue_per_share"]) * 100
                else:
                    year_row["Revenue YoY %"] = None

                # Cash Flow YoY
                if year_row["Cash Flow Per Share"] and prev_data.get("cf_per_share"):
                    year_row["CF YoY %"] = ((year_row["Cash Flow Per Share"] - prev_data["cf_per_share"]) /
                                            prev_data["cf_per_share"]) * 100
                else:
                    year_row["CF YoY %"] = None

                # EPS YoY
                if year_row["Earnings Per Share"] and prev_data.get("eps"):
                    year_row["EPS YoY %"] = ((year_row["Earnings Per Share"] - prev_data["eps"]) /
                                             abs(prev_data["eps"])) * 100  # abs() to handle negative EPS
                else:
                    year_row["EPS YoY %"] = None

                # Stock Price YoY
                if stock_prices and year_row["Stock Price"] and prev_price:
                    year_row["Stock Price YoY %"] = ((year_row["Stock Price"] - prev_price) / prev_price) * 100
                else:
                    year_row["Stock Price YoY %"] = None

                # Calculate median fundamentals growth
                growth_rates = [g for g in [year_row.get("Revenue YoY %"),
                                           year_row.get("CF YoY %"),
                                           year_row.get("EPS YoY %")] if g is not None]
                if growth_rates:
                    year_row["Median Fundamentals Growth %"] = sorted(growth_rates)[len(growth_rates)//2]
                else:
                    year_row["Median Fundamentals Growth %"] = None

                # Calculate Price/Fundamentals Ratio
                if year_row.get("Stock Price YoY %") is not None and year_row.get("Median Fundamentals Growth %") is not None:
                    if abs(year_row["Median Fundamentals Growth %"]) > 0.1:  # Avoid division by near-zero
                        year_row["Price/Fundamentals Ratio"] = year_row["Stock Price YoY %"] / year_row["Median Fundamentals Growth %"]
                    else:
                        year_row["Price/Fundamentals Ratio"] = None
                else:
                    year_row["Price/Fundamentals Ratio"] = None
            else:
                # First year has no YoY changes
                year_row["Revenue YoY %"] = None
                year_row["CF YoY %"] = None
                year_row["EPS YoY %"] = None
                year_row["Stock Price YoY %"] = None
                year_row["Median Fundamentals Growth %"] = None
                year_row["Price/Fundamentals Ratio"] = None

            # Add metadata
            if data["type"] == "Forecast":
                year_row["Number of Analysts"] = data.get("number_of_analysts", "-")
            else:
                year_row["Number of Analysts"] = "-"

            all_data.append(year_row)

            # Update previous data for next iteration
            prev_data = data
            if stock_prices and year in stock_prices:
                prev_price = stock_prices[year]

        df = pd.DataFrame(all_data)
        return df

    def calculate_correlation_metrics(self, df):
        """
        Calculate correlation between fundamentals growth and stock price growth.

        Args:
            df: DataFrame with YoY changes

        Returns:
            dict: Correlation metrics and insights
        """
        metrics = {}

        # Filter to historical data with YoY changes
        historical_yoy = df[(df['Type'] == 'Historical') & (df['Stock Price YoY %'].notna())]

        if len(historical_yoy) > 1:
            # Calculate correlation if we have enough data points
            fund_growth = historical_yoy['Median Fundamentals Growth %'].dropna()
            price_growth = historical_yoy['Stock Price YoY %'].dropna()

            # Align the data
            aligned = pd.DataFrame({
                'fundamentals': historical_yoy['Median Fundamentals Growth %'],
                'price': historical_yoy['Stock Price YoY %']
            }).dropna()

            if len(aligned) > 1:
                correlation = np.corrcoef(aligned['fundamentals'], aligned['price'])[0, 1]
                metrics['correlation'] = correlation

                # Calculate average ratio
                ratios = historical_yoy['Price/Fundamentals Ratio'].dropna()
                if len(ratios) > 0:
                    metrics['avg_ratio'] = ratios.mean()
                    metrics['best_ratio_year'] = historical_yoy.loc[ratios.idxmax(), 'Year']
                    metrics['worst_ratio_year'] = historical_yoy.loc[ratios.idxmin(), 'Year']

                # Find best and worst performing years
                if len(price_growth) > 0:
                    metrics['best_price_year'] = historical_yoy.loc[price_growth.idxmax(), 'Year']
                    metrics['best_price_growth'] = price_growth.max()
                    metrics['worst_price_year'] = historical_yoy.loc[price_growth.idxmin(), 'Year']
                    metrics['worst_price_growth'] = price_growth.min()

                if len(fund_growth) > 0:
                    metrics['avg_fundamentals_growth'] = fund_growth.mean()
                    metrics['avg_price_growth'] = price_growth.mean()

        return metrics

    def generate_html_report(self, df, correlation_metrics=None, output_file="AMD_financial_table.html"):
        """
        Generate an enhanced HTML report with financial table and correlation analysis.

        Args:
            df: pandas DataFrame with financial data
            correlation_metrics: dict with correlation analysis results
            output_file: Output HTML file path
        """
        # Format the dataframe for display
        df_display = df.copy()

        # Format currency columns
        df_display['Stock Price'] = df_display['Stock Price'].apply(
            lambda x: f"${x:.2f}" if pd.notna(x) else "-"
        )

        for col in ["Revenue Per Share", "Cash Flow Per Share", "Earnings Per Share"]:
            df_display[col] = df_display[col].apply(
                lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
            )

        # Format percentage columns
        pct_cols = ["Revenue YoY %", "CF YoY %", "EPS YoY %", "Stock Price YoY %",
                    "Median Fundamentals Growth %"]
        for col in pct_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(
                    lambda x: f"{x:+.1f}%" if pd.notna(x) else "-"
                )

        # Format ratio column
        if "Price/Fundamentals Ratio" in df_display.columns:
            df_display["Price/Fundamentals Ratio"] = df_display["Price/Fundamentals Ratio"].apply(
                lambda x: f"{x:.2f}x" if pd.notna(x) else "-"
            )

        # Reorder columns for better presentation
        column_order = [
            "Year", "Type", "Stock Price", "Stock Price YoY %",
            "Revenue Per Share", "Revenue YoY %",
            "Cash Flow Per Share", "CF YoY %",
            "Earnings Per Share", "EPS YoY %",
            "Median Fundamentals Growth %", "Price/Fundamentals Ratio",
            "Number of Analysts"
        ]

        # Only include columns that exist
        column_order = [col for col in column_order if col in df_display.columns]
        df_display = df_display[column_order]

        # Convert to HTML table
        table_html = df_display.to_html(
            index=False,
            classes='financial-table',
            escape=False,
            table_id='amd-financial-table'
        )

        # Add asterisks to forecast values
        table_html = table_html.replace('<td>Forecast</td>', '<td class="forecast-type">Forecast</td>')

        # Build correlation insights HTML
        correlation_html = ""
        if correlation_metrics:
            insights = []
            if 'correlation' in correlation_metrics:
                corr = correlation_metrics['correlation']
                insights.append(f"<p><strong>Correlation (Fundamentals vs Price):</strong> {corr:.2f}</p>")

            if 'avg_ratio' in correlation_metrics:
                insights.append(f"<p><strong>Average Price/Fundamentals Ratio:</strong> {correlation_metrics['avg_ratio']:.2f}x</p>")

            if 'avg_fundamentals_growth' in correlation_metrics:
                insights.append(f"<p><strong>Average Fundamentals Growth:</strong> {correlation_metrics['avg_fundamentals_growth']:+.1f}%</p>")

            if 'avg_price_growth' in correlation_metrics:
                insights.append(f"<p><strong>Average Stock Price Growth:</strong> {correlation_metrics['avg_price_growth']:+.1f}%</p>")

            if 'best_price_year' in correlation_metrics:
                insights.append(f"<p><strong>Best Stock Performance:</strong> {correlation_metrics['best_price_year']} ({correlation_metrics['best_price_growth']:+.1f}%)</p>")

            if 'worst_price_year' in correlation_metrics:
                insights.append(f"<p><strong>Worst Stock Performance:</strong> {correlation_metrics['worst_price_year']} ({correlation_metrics['worst_price_growth']:+.1f}%)</p>")

            correlation_html = f"""
            <div class="insights-box">
                <h3>Correlation Analysis Insights</h3>
                {''.join(insights)}
            </div>
            """

        # Create full HTML document
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.ticker} Financial Fundamentals Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
            color: #333;
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #e74c3c;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}

        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}

        h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}

        .insights-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .insights-box h3 {{
            color: white;
            margin-top: 0;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
        }}

        .insights-box p {{
            margin: 10px 0;
            font-size: 14px;
        }}

        .insights-box strong {{
            color: #ffd700;
        }}

        .metadata {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .metadata p {{
            margin: 8px 0;
        }}

        .financial-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}

        .financial-table th {{
            background: #2c3e50;
            color: white;
            padding: 14px;
            text-align: right;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }}

        .financial-table th:first-child {{
            text-align: left;
        }}

        .financial-table td {{
            padding: 12px 14px;
            text-align: right;
            border-bottom: 1px solid #e0e0e0;
        }}

        .financial-table td:first-child {{
            text-align: left;
            font-weight: 600;
            color: #2c3e50;
        }}

        .financial-table tr:hover {{
            background-color: #f8f9fa;
        }}

        .financial-table tr:last-child td {{
            border-bottom: none;
        }}

        /* Highlight forecast rows */
        .financial-table tr:has(.forecast-type) {{
            background-color: #e8f4fd;
            font-style: italic;
        }}

        .financial-table tr:has(.forecast-type):hover {{
            background-color: #d4ebfc;
        }}

        .forecast-type {{
            color: #3498db;
            font-weight: 600;
        }}

        .note {{
            font-size: 13px;
            color: #7f8c8d;
            margin-top: 20px;
            padding: 15px;
            background: #fef9e7;
            border-left: 4px solid #f39c12;
            border-radius: 4px;
        }}

        .note strong {{
            color: #e67e22;
        }}

        .chart-container {{
            margin: 40px 0;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <h1>{self.ticker} Financial Fundamentals Analysis</h1>

    <div class="metadata">
        <p><strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Data Source:</strong> EODHD API</p>
        <p><strong>Ticker:</strong> {self.ticker}</p>
        <p><strong>Shares Outstanding:</strong> {self.shares_outstanding:,.0f}</p>
    </div>

    {correlation_html}

    <h2>Historical and Forecast Financial Metrics (Per Share)</h2>

    {table_html}

    <div class="note">
        <strong>Important Notes:</strong><br>
        • <strong>Forecast values (2025-2026)</strong> are based on analyst consensus estimates<br>
        • <strong>Historical data (2019-2024)</strong> sourced from EODHD fundamentals API<br>
        • <strong>Cash Flow Per Share</strong> represents Operating Cash Flow per share<br>
        • <strong>Forecast Cash Flow</strong> estimated using industry standard multiplier (1.3x EPS) for technology companies<br>
        • <strong>Number of Analysts</strong> indicates the consensus strength for forecast values
    </div>

    <div class="chart-container" id="chart-section">
        <h2>Trend Visualization</h2>
        <div id="plotly-chart"></div>
    </div>

    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script>
        // Prepare data for Plotly chart
        const years = {list([int(y) for y in df['Year'].tolist()])};
        const stockPrices = {[float(v) if isinstance(v, (int, float)) and pd.notna(v) else 'null' for v in df['Stock Price'].tolist()]};
        const revenuePerShare = {[float(v) if isinstance(v, (int, float)) and pd.notna(v) else 'null' for v in df['Revenue Per Share'].tolist()]};
        const cfPerShare = {[float(v) if isinstance(v, (int, float)) and pd.notna(v) else 'null' for v in df['Cash Flow Per Share'].tolist()]};
        const epsData = {[float(v) if isinstance(v, (int, float)) and pd.notna(v) else 'null' for v in df['Earnings Per Share'].tolist()]};
        const types = {df['Type'].tolist()};

        // Split into historical and forecast
        const historicalYears = years.filter((y, i) => types[i] === 'Historical');
        const forecastYears = years.filter((y, i) => types[i] === 'Forecast');

        const historicalPrices = stockPrices.filter((v, i) => types[i] === 'Historical');

        const historicalRevenue = revenuePerShare.filter((v, i) => types[i] === 'Historical');
        const forecastRevenue = revenuePerShare.filter((v, i) => types[i] === 'Forecast');

        const historicalCF = cfPerShare.filter((v, i) => types[i] === 'Historical');
        const forecastCF = cfPerShare.filter((v, i) => types[i] === 'Forecast');

        const historicalEPS = epsData.filter((v, i) => types[i] === 'Historical');
        const forecastEPS = epsData.filter((v, i) => types[i] === 'Forecast');

        // Create traces
        const traces = [
            // Stock Price (on secondary y-axis)
            {{
                x: historicalYears,
                y: historicalPrices,
                name: 'Stock Price',
                type: 'scatter',
                mode: 'lines+markers',
                line: {{color: '#ff6b6b', width: 3}},
                marker: {{size: 10, symbol: 'diamond'}},
                yaxis: 'y2'
            }},
            // Historical data
            {{
                x: historicalYears,
                y: historicalRevenue,
                name: 'Revenue/Share (Historical)',
                type: 'scatter',
                mode: 'lines+markers',
                line: {{color: '#3498db', width: 2}},
                marker: {{size: 8}}
            }},
            {{
                x: historicalYears,
                y: historicalCF,
                name: 'Cash Flow/Share (Historical)',
                type: 'scatter',
                mode: 'lines+markers',
                line: {{color: '#2ecc71', width: 2}},
                marker: {{size: 8}}
            }},
            {{
                x: historicalYears,
                y: historicalEPS,
                name: 'EPS (Historical)',
                type: 'scatter',
                mode: 'lines+markers',
                line: {{color: '#e74c3c', width: 2}},
                marker: {{size: 8}}
            }},
            // Forecast data
            {{
                x: forecastYears,
                y: forecastRevenue,
                name: 'Revenue/Share (Forecast)',
                type: 'scatter',
                mode: 'lines+markers',
                line: {{color: '#3498db', width: 2, dash: 'dash'}},
                marker: {{size: 8, symbol: 'diamond'}}
            }},
            {{
                x: forecastYears,
                y: forecastCF,
                name: 'Cash Flow/Share (Forecast)',
                type: 'scatter',
                mode: 'lines+markers',
                line: {{color: '#2ecc71', width: 2, dash: 'dash'}},
                marker: {{size: 8, symbol: 'diamond'}}
            }},
            {{
                x: forecastYears,
                y: forecastEPS,
                name: 'EPS (Forecast)',
                type: 'scatter',
                mode: 'lines+markers',
                line: {{color: '#e74c3c', width: 2, dash: 'dash'}},
                marker: {{size: 8, symbol: 'diamond'}}
            }}
        ];

        const layout = {{
            title: {{
                text: '{self.ticker} Financial Metrics & Stock Price Trend',
                font: {{size: 20}}
            }},
            xaxis: {{
                title: 'Year',
                showgrid: true,
                dtick: 1
            }},
            yaxis: {{
                title: 'Value per Share ($)',
                showgrid: true,
                zeroline: true,
                side: 'left'
            }},
            yaxis2: {{
                title: 'Stock Price ($)',
                overlaying: 'y',
                side: 'right',
                showgrid: false,
                color: '#ff6b6b'
            }},
            hovermode: 'x unified',
            legend: {{
                x: 0.02,
                y: 0.98,
                bgcolor: 'rgba(255, 255, 255, 0.8)',
                bordercolor: '#333',
                borderwidth: 1
            }},
            margin: {{
                l: 60,
                r: 30,
                t: 60,
                b: 60
            }}
        }};

        const config = {{
            responsive: true,
            displayModeBar: true,
            displaylogo: false
        }};

        // Create the plot
        Plotly.newPlot('plotly-chart', traces, layout, config);
    </script>
</body>
</html>"""

        # Write to file
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"Report generated successfully: {output_path}")
        return output_path

    def run(self, output_file="AMD_financial_table.html"):
        """
        Main execution method to generate the financial table.

        Args:
            output_file: Name of the output HTML file

        Returns:
            str: Path to generated HTML file
        """
        print(f"Generating financial table for {self.ticker}...")

        # Fetch fundamentals data
        print("Fetching fundamentals data from EODHD...")
        if not self.fetch_fundamentals():
            print("Failed to fetch fundamentals data")
            return None

        print(f"Shares Outstanding: {self.shares_outstanding:,.0f}")

        # Fetch historical data
        print("Fetching historical data (2019-2024)...")
        historical_data = self.fetch_historical_data()
        print(f"Found historical data for {len(historical_data)} years")

        # Fetch forecast data
        print("Fetching forecast data (2025-2026)...")
        forecast_data = self.fetch_forecast_data()
        print(f"Found forecast data for {len(forecast_data)} years")

        if not historical_data and not forecast_data:
            print("No data found to generate report")
            return None

        # Fetch stock prices
        print("Fetching stock prices...")
        stock_prices = self.fetch_stock_prices()
        print(f"Found price data for {len([p for p in stock_prices.values() if p is not None])} years")

        # Create DataFrame with YoY analysis
        print("Creating data table with YoY analysis...")
        df = self.create_dataframe(historical_data, forecast_data, stock_prices)

        # Calculate correlation metrics
        print("Calculating correlation metrics...")
        correlation_metrics = self.calculate_correlation_metrics(df)
        if correlation_metrics and 'correlation' in correlation_metrics:
            print(f"  Correlation (Fundamentals vs Price): {correlation_metrics['correlation']:.2f}")
            if 'avg_ratio' in correlation_metrics:
                print(f"  Average Price/Fundamentals Ratio: {correlation_metrics['avg_ratio']:.2f}x")

        # Generate HTML report
        print("Generating HTML report...")
        output_path = self.generate_html_report(df, correlation_metrics, output_file)

        return output_path


def main():
    """Main function to generate financial table for any ticker."""
    # Check if ticker was provided as command-line argument
    if len(sys.argv) > 1:
        TICKER = sys.argv[1].upper()
    else:
        # Default ticker if none provided
        TICKER = "AMD"  # <-- CHANGE THIS DEFAULT (e.g., "NVDA", "MSFT", "AAPL", "GOOGL", etc.)

    print(f"\n=== Generating Financial Table for {TICKER} ===\n")

    generator = FinancialTableGenerator(TICKER)
    output_file = generator.run(f"{TICKER}_financial_table.html")

    if output_file:
        print(f"\n[SUCCESS] Successfully generated {TICKER} financial table report")
        print(f"  View report: {output_file}")
    else:
        print("\n[FAILED] Failed to generate report")


if __name__ == "__main__":
    main()