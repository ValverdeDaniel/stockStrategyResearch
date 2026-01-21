"""
Enhanced Semiconductor Sector Cash Flow Analysis with Historical Trends
Analyzes 10-year historical CF patterns, growth rates, and stock price correlations
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys
import os
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# API Configuration
EODHD_API_KEY = "67ffece4b2ae08.94077168"
EODHD_BASE = "https://eodhd.com/api"

# Semiconductor companies to analyze
SEMICONDUCTOR_TICKERS = {
    "NVDA": {"type": "fabless", "segment": "GPU/AI", "name": "NVIDIA"},
    "AMD": {"type": "fabless", "segment": "CPU/GPU", "name": "AMD"},
    "MU": {"type": "fab", "segment": "Memory", "name": "Micron"},
    "INTC": {"type": "fab", "segment": "CPU/Foundry", "name": "Intel"},
    "MRVL": {"type": "fabless", "segment": "Infrastructure", "name": "Marvell"},
    "AVGO": {"type": "fabless", "segment": "Diversified/Software", "name": "Broadcom"},
    "TSM": {"type": "fab", "segment": "Foundry", "name": "TSMC"}
}

class EnhancedSemiconductorAnalyzer:
    """Enhanced analyzer with 10-year history and correlation analysis."""

    def __init__(self):
        self.api_key = EODHD_API_KEY
        self.company_data = {}
        self.correlation_data = {}

    def fetch_company_fundamentals(self, ticker):
        """Fetch comprehensive fundamentals for a ticker."""
        url = f"{EODHD_BASE}/fundamentals/{ticker}.US"
        params = {
            "api_token": self.api_key,
            "fmt": "json"
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    def fetch_stock_prices(self, ticker, start_year=2014):
        """Fetch historical stock prices for a ticker."""
        end_year = datetime.now().year
        stock_prices = {}

        for year in range(start_year, end_year + 1):
            # Fetch year-end prices
            start_date = f"{year}-12-20"
            end_date = f"{year + 1}-01-10" if year < datetime.now().year else datetime.now().strftime("%Y-%m-%d")

            url = f"{EODHD_BASE}/eod/{ticker}.US"
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
                    # Get last trading day of the year
                    year_prices = [p for p in price_data if p['date'].startswith(str(year))]
                    if year_prices:
                        last_price = float(year_prices[-1]['adjusted_close'])
                        stock_prices[year] = last_price
            except:
                pass

        return stock_prices

    def extract_10year_metrics(self, ticker, fundamentals_data):
        """Extract 10 years of cash flow metrics."""
        if not fundamentals_data:
            return None

        metrics = {
            "ticker": ticker,
            "info": SEMICONDUCTOR_TICKERS[ticker],
            "yearly_data": {},
            "cf_growth": [],
            "stock_growth": [],
            "correlation": None
        }

        # Get financial statements
        income_stmt = fundamentals_data.get("Financials", {}).get("Income_Statement", {}).get("yearly", {})
        cash_flow = fundamentals_data.get("Financials", {}).get("Cash_Flow", {}).get("yearly", {})

        # Get shares outstanding
        shares = fundamentals_data.get("SharesStats", {}).get("SharesOutstanding", 1000000000)
        if shares:
            shares = float(shares)
        else:
            shares = 1000000000

        # Process 10 years (2014-2024)
        for year in range(2014, 2025):
            year_data = {}

            # Find date keys for this year
            income_key = None
            cf_key = None

            for date_key in income_stmt.keys():
                if date_key.startswith(str(year)):
                    income_key = date_key
                    break

            for date_key in cash_flow.keys():
                if date_key.startswith(str(year)):
                    cf_key = date_key
                    break

            if income_key and cf_key:
                try:
                    # Extract data
                    revenue = float(income_stmt[income_key].get("totalRevenue", 0))
                    net_income = float(income_stmt[income_key].get("netIncome", 0))
                    operating_cf = float(cash_flow[cf_key].get("totalCashFromOperatingActivities", 0))
                    capex = abs(float(cash_flow[cf_key].get("capitalExpenditures", 0)))
                    free_cf = operating_cf - capex

                    # Calculate per-share metrics
                    year_data = {
                        "year": year,
                        "revenue": revenue,
                        "net_income": net_income,
                        "operating_cf": operating_cf,
                        "cf_per_share": operating_cf / shares if shares > 0 else 0,
                        "free_cf": free_cf,
                        "free_cf_per_share": free_cf / shares if shares > 0 else 0,
                        "eps": net_income / shares if shares > 0 else 0,
                        "capex": capex,
                        "shares": shares
                    }

                    metrics["yearly_data"][year] = year_data

                except Exception as e:
                    print(f"    Error processing {ticker} year {year}: {e}")
                    continue

        # Get stock prices
        stock_prices = self.fetch_stock_prices(ticker, 2014)

        # Calculate year-over-year growth rates
        years = sorted(metrics["yearly_data"].keys())
        for i in range(1, len(years)):
            curr_year = years[i]
            prev_year = years[i-1]

            if curr_year in metrics["yearly_data"] and prev_year in metrics["yearly_data"]:
                # CF growth
                curr_cf = metrics["yearly_data"][curr_year]["cf_per_share"]
                prev_cf = metrics["yearly_data"][prev_year]["cf_per_share"]
                if prev_cf != 0:
                    cf_growth = ((curr_cf - prev_cf) / abs(prev_cf)) * 100
                    metrics["cf_growth"].append({
                        "year": curr_year,
                        "growth": cf_growth,
                        "cf_per_share": curr_cf
                    })

                # Stock price growth
                if curr_year in stock_prices and prev_year in stock_prices:
                    curr_price = stock_prices[curr_year]
                    prev_price = stock_prices[prev_year]
                    if prev_price > 0:
                        price_growth = ((curr_price - prev_price) / prev_price) * 100
                        metrics["stock_growth"].append({
                            "year": curr_year,
                            "growth": price_growth,
                            "price": curr_price
                        })

        # Calculate correlation between CF growth and stock growth
        if len(metrics["cf_growth"]) > 2 and len(metrics["stock_growth"]) > 2:
            # Align years
            cf_years = {g["year"]: g["growth"] for g in metrics["cf_growth"]}
            stock_years = {g["year"]: g["growth"] for g in metrics["stock_growth"]}

            common_years = sorted(set(cf_years.keys()) & set(stock_years.keys()))
            if len(common_years) > 2:
                cf_growth_aligned = [cf_years[year] for year in common_years]
                stock_growth_aligned = [stock_years[year] for year in common_years]

                # Calculate correlation
                if len(cf_growth_aligned) > 2:
                    correlation = np.corrcoef(cf_growth_aligned, stock_growth_aligned)[0, 1]
                    metrics["correlation"] = correlation

                    # Calculate median growths
                    metrics["median_cf_growth"] = np.median(cf_growth_aligned)
                    metrics["median_stock_growth"] = np.median(stock_growth_aligned)

        # Add stock prices to yearly data
        for year in stock_prices:
            if year in metrics["yearly_data"]:
                metrics["yearly_data"][year]["stock_price"] = stock_prices[year]

        return metrics

    def create_visualizations(self, all_data):
        """Create interactive visualizations for the analysis."""
        figures = []

        # Create individual company charts
        for ticker, data in all_data.items():
            if not data or "yearly_data" not in data:
                continue

            years = sorted(data["yearly_data"].keys())
            cf_per_share = [data["yearly_data"][y].get("cf_per_share", 0) for y in years]
            stock_prices = [data["yearly_data"][y].get("stock_price", 0) for y in years if "stock_price" in data["yearly_data"][y]]
            stock_years = [y for y in years if "stock_price" in data["yearly_data"][y]]

            # Create subplot figure
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    f'{ticker} - Cash Flow Per Share Trend',
                    f'{ticker} - Stock Price Trend',
                    f'{ticker} - CF Growth vs Stock Growth',
                    f'{ticker} - Correlation Analysis'
                ),
                specs=[[{"type": "scatter"}, {"type": "scatter"}],
                       [{"type": "scatter"}, {"type": "scatter"}]]
            )

            # 1. CF per share trend
            fig.add_trace(
                go.Scatter(x=years, y=cf_per_share, mode='lines+markers',
                          name='CF/Share', line=dict(color='blue', width=2)),
                row=1, col=1
            )

            # 2. Stock price trend
            if stock_prices:
                fig.add_trace(
                    go.Scatter(x=stock_years, y=stock_prices, mode='lines+markers',
                              name='Stock Price', line=dict(color='green', width=2)),
                    row=1, col=2
                )

            # 3. Growth comparison
            cf_growth = [g["growth"] for g in data.get("cf_growth", [])]
            stock_growth = [g["growth"] for g in data.get("stock_growth", [])]
            growth_years = [g["year"] for g in data.get("cf_growth", [])]

            if cf_growth and stock_growth:
                fig.add_trace(
                    go.Scatter(x=growth_years, y=cf_growth, mode='lines+markers',
                              name='CF Growth %', line=dict(color='blue')),
                    row=2, col=1
                )
                fig.add_trace(
                    go.Scatter(x=growth_years, y=stock_growth, mode='lines+markers',
                              name='Stock Growth %', line=dict(color='green')),
                    row=2, col=1
                )

            # 4. Correlation scatter
            if cf_growth and stock_growth:
                fig.add_trace(
                    go.Scatter(x=cf_growth, y=stock_growth, mode='markers',
                              text=[str(y) for y in growth_years],
                              name='Correlation',
                              marker=dict(size=10, color='purple')),
                    row=2, col=2
                )

                # Add trend line if correlation exists
                if data.get("correlation"):
                    z = np.polyfit(cf_growth, stock_growth, 1)
                    p = np.poly1d(z)
                    x_trend = np.linspace(min(cf_growth), max(cf_growth), 100)
                    y_trend = p(x_trend)

                    fig.add_trace(
                        go.Scatter(x=x_trend, y=y_trend, mode='lines',
                                  name=f'Trend (r={data["correlation"]:.2f})',
                                  line=dict(color='red', dash='dash')),
                        row=2, col=2
                    )

            # Update layout
            fig.update_layout(
                title_text=f"{ticker} - {SEMICONDUCTOR_TICKERS[ticker]['name']} Analysis",
                height=800,
                showlegend=True
            )

            # Update axes labels
            fig.update_xaxes(title_text="Year", row=1, col=1)
            fig.update_xaxes(title_text="Year", row=1, col=2)
            fig.update_xaxes(title_text="Year", row=2, col=1)
            fig.update_xaxes(title_text="CF Growth %", row=2, col=2)

            fig.update_yaxes(title_text="CF/Share ($)", row=1, col=1)
            fig.update_yaxes(title_text="Stock Price ($)", row=1, col=2)
            fig.update_yaxes(title_text="Growth %", row=2, col=1)
            fig.update_yaxes(title_text="Stock Growth %", row=2, col=2)

            figures.append((ticker, fig))

        return figures

    def generate_enhanced_report(self, all_data, output_file="semiconductor_enhanced.html"):
        """Generate comprehensive HTML report with visualizations."""

        # Create comparison DataFrame
        comparison_data = []
        for ticker, data in all_data.items():
            if not data:
                continue

            # Get 10-year CF history
            years = sorted(data.get("yearly_data", {}).keys())
            cf_history = []
            for year in years[-10:]:
                if year in data["yearly_data"]:
                    cf = data["yearly_data"][year].get("cf_per_share", 0)
                    cf_history.append(f"{year}: ${cf:.2f}")

            row = {
                "Ticker": ticker,
                "Company": SEMICONDUCTOR_TICKERS[ticker]["name"],
                "Type": SEMICONDUCTOR_TICKERS[ticker]["type"],
                "Median CF Growth": f"{data.get('median_cf_growth', 0):.1f}%",
                "Median Stock Growth": f"{data.get('median_stock_growth', 0):.1f}%",
                "Correlation": f"{data.get('correlation', 0):.2f}" if data.get('correlation') else "N/A",
                "10-Year CF History": ", ".join(cf_history[-5:]) if cf_history else "N/A"  # Show last 5 years
            }
            comparison_data.append(row)

        df_comparison = pd.DataFrame(comparison_data)

        # Create visualizations
        figures = self.create_visualizations(all_data)

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Semiconductor Cash Flow Analysis</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
            color: #333;
        }}

        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}

        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .metric-card h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}

        .correlation-high {{
            color: #27ae60;
            font-weight: bold;
        }}

        .correlation-low {{
            color: #e74c3c;
            font-weight: bold;
        }}

        .correlation-medium {{
            color: #f39c12;
            font-weight: bold;
        }}

        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}

        .comparison-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: left;
        }}

        .comparison-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .comparison-table tr:hover {{
            background-color: #f8f9fa;
        }}

        .visualization-container {{
            margin: 30px 0;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        .insight-box {{
            background: #e8f4fd;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <h1>Enhanced Semiconductor Cash Flow Analysis</h1>
    <p><strong>Analysis Period:</strong> 2014-2024 (10 Years) | <strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Key Findings: CF Growth vs Stock Price Growth Correlation</h2>

    <div class="summary-grid">"""

        # Add summary cards for each company
        for ticker, data in all_data.items():
            if not data:
                continue

            correlation = data.get('correlation', 0)
            corr_class = 'correlation-high' if abs(correlation) > 0.5 else 'correlation-medium' if abs(correlation) > 0.3 else 'correlation-low'

            html_content += f"""
        <div class="metric-card">
            <h3>{ticker} - {SEMICONDUCTOR_TICKERS[ticker]['name']}</h3>
            <p><strong>Type:</strong> {SEMICONDUCTOR_TICKERS[ticker]['type'].title()}</p>
            <p><strong>Median CF Growth:</strong> {data.get('median_cf_growth', 0):.1f}%</p>
            <p><strong>Median Stock Growth:</strong> {data.get('median_stock_growth', 0):.1f}%</p>
            <p><strong>Correlation:</strong> <span class="{corr_class}">{correlation:.2f}</span></p>
        </div>"""

        html_content += """
    </div>

    <div class="insight-box">
        <h3>📊 Correlation Interpretation</h3>
        <ul>
            <li><strong>Strong Positive (>0.5):</strong> Cash flow growth strongly predicts stock price growth</li>
            <li><strong>Moderate (0.3-0.5):</strong> Some relationship between CF and stock performance</li>
            <li><strong>Weak (<0.3):</strong> Stock price driven more by sentiment than fundamentals</li>
        </ul>
    </div>

    <h2>Comparative Analysis Table</h2>"""

        html_content += df_comparison.to_html(index=False, classes='comparison-table', escape=False)

        # Add visualizations
        html_content += """
    <h2>Individual Company Analysis</h2>"""

        for ticker, fig in figures:
            html_content += f"""
    <div class="visualization-container">
        <div id="chart-{ticker}"></div>
    </div>"""

        html_content += """
    <script>"""

        # Add Plotly JavaScript
        for ticker, fig in figures:
            html_content += f"""
        Plotly.newPlot('chart-{ticker}', {fig.to_json()});"""

        html_content += """
    </script>

    <h2>Historical Cash Flow Trends (10 Years)</h2>
    <div class="visualization-container">
        <div id="cf-trends-chart"></div>
    </div>

    <script>
        // Create combined CF trends chart
        var traces = ["""

        # Add traces for CF trends
        for ticker, data in all_data.items():
            if data and "yearly_data" in data:
                years = sorted(data["yearly_data"].keys())
                cf_values = [data["yearly_data"][y].get("cf_per_share", 0) for y in years]

                html_content += f"""
            {{
                x: {years},
                y: {cf_values},
                name: '{ticker}',
                type: 'scatter',
                mode: 'lines+markers'
            }},"""

        html_content += """
        ];

        var layout = {
            title: 'Cash Flow Per Share Trends (2014-2024)',
            xaxis: { title: 'Year' },
            yaxis: { title: 'Cash Flow Per Share ($)' },
            hovermode: 'x unified'
        };

        Plotly.newPlot('cf-trends-chart', traces, layout);
    </script>

</body>
</html>"""

        # Write to file
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\nEnhanced report generated: {output_path}")
        return output_path

    def analyze_all_companies(self):
        """Analyze all semiconductor companies with 10-year history."""
        print("\n=== Enhanced Semiconductor Analysis (10-Year History) ===\n")

        results = {}

        for ticker in SEMICONDUCTOR_TICKERS.keys():
            print(f"Analyzing {ticker} ({SEMICONDUCTOR_TICKERS[ticker]['name']})...")

            # Fetch fundamentals
            fundamentals = self.fetch_company_fundamentals(ticker)
            if not fundamentals:
                print(f"  Failed to fetch data for {ticker}")
                continue

            # Extract 10-year metrics
            metrics = self.extract_10year_metrics(ticker, fundamentals)
            if metrics:
                results[ticker] = metrics

                # Print summary
                if metrics.get("correlation") is not None:
                    print(f"  CF/Stock Correlation: {metrics['correlation']:.2f}")
                if metrics.get("median_cf_growth") is not None:
                    print(f"  Median CF Growth: {metrics['median_cf_growth']:.1f}%")
                if metrics.get("median_stock_growth") is not None:
                    print(f"  Median Stock Growth: {metrics['median_stock_growth']:.1f}%")
            print()

        return results


def main():
    """Main function to run enhanced semiconductor analysis."""
    analyzer = EnhancedSemiconductorAnalyzer()

    # Analyze all companies
    all_data = analyzer.analyze_all_companies()

    # Generate enhanced report
    if all_data:
        analyzer.generate_enhanced_report(all_data)


if __name__ == "__main__":
    main()