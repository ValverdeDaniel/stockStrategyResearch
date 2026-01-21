"""
Semiconductor Sector Cash Flow Analysis and Forecasting
Analyzes historical patterns and creates custom CF forecasts for semiconductor companies
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys
import os
from scipy import stats

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

class SemiconductorCashFlowAnalyzer:
    """Analyzes and forecasts cash flow for semiconductor companies."""

    def __init__(self):
        self.api_key = EODHD_API_KEY
        self.company_data = {}
        self.sector_metrics = {}

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

    def extract_historical_metrics(self, ticker, fundamentals_data):
        """Extract key metrics for cash flow analysis."""
        if not fundamentals_data:
            return None

        metrics = {
            "ticker": ticker,
            "info": SEMICONDUCTOR_TICKERS[ticker],
            "yearly_data": {},
            "ratios": {},
            "trends": {}
        }

        # Get financial statements
        income_stmt = fundamentals_data.get("Financials", {}).get("Income_Statement", {}).get("yearly", {})
        cash_flow = fundamentals_data.get("Financials", {}).get("Cash_Flow", {}).get("yearly", {})
        balance_sheet = fundamentals_data.get("Financials", {}).get("Balance_Sheet", {}).get("yearly", {})

        # Get shares outstanding
        shares = fundamentals_data.get("SharesStats", {}).get("SharesOutstanding", 1000000000)
        if shares:
            shares = float(shares)
        else:
            shares = 1000000000  # Default 1B

        # Process each year
        years_processed = []
        for year in range(2019, 2025):
            year_data = {}

            # Find the date key for this year
            income_key = None
            cf_key = None
            bs_key = None

            for date_key in income_stmt.keys():
                if date_key.startswith(str(year)):
                    income_key = date_key
                    break

            for date_key in cash_flow.keys():
                if date_key.startswith(str(year)):
                    cf_key = date_key
                    break

            for date_key in balance_sheet.keys():
                if date_key.startswith(str(year)):
                    bs_key = date_key
                    break

            if income_key and cf_key:
                try:
                    # Revenue and margins
                    revenue = float(income_stmt[income_key].get("totalRevenue", 0))
                    gross_profit = float(income_stmt[income_key].get("grossProfit", 0))
                    net_income = float(income_stmt[income_key].get("netIncome", 0))
                    rd_expense = float(income_stmt[income_key].get("researchDevelopment", 0))

                    # Cash flow items
                    operating_cf = float(cash_flow[cf_key].get("totalCashFromOperatingActivities", 0))
                    capex = abs(float(cash_flow[cf_key].get("capitalExpenditures", 0)))
                    free_cf = operating_cf - capex

                    # Working capital (if available)
                    if bs_key:
                        current_assets = float(balance_sheet[bs_key].get("totalCurrentAssets", 0))
                        current_liab = float(balance_sheet[bs_key].get("totalCurrentLiabilities", 0))
                        working_capital = current_assets - current_liab
                    else:
                        working_capital = 0

                    # Calculate per-share metrics
                    if shares > 0:
                        year_data = {
                            "revenue": revenue,
                            "revenue_per_share": revenue / shares,
                            "gross_margin": (gross_profit / revenue * 100) if revenue else 0,
                            "net_income": net_income,
                            "eps": net_income / shares,
                            "operating_cf": operating_cf,
                            "cf_per_share": operating_cf / shares,
                            "capex": capex,
                            "capex_per_share": capex / shares,
                            "free_cf": free_cf,
                            "free_cf_per_share": free_cf / shares,
                            "rd_expense": rd_expense,
                            "rd_as_pct_revenue": (rd_expense / revenue * 100) if revenue else 0,
                            "capex_as_pct_revenue": (capex / revenue * 100) if revenue else 0,
                            "cf_to_eps_ratio": (operating_cf / shares) / (net_income / shares) if net_income != 0 else 0,
                            "cf_to_revenue_ratio": (operating_cf / revenue) if revenue else 0,
                            "working_capital": working_capital,
                            "shares": shares
                        }

                        metrics["yearly_data"][year] = year_data
                        years_processed.append(year)

                except (ValueError, TypeError, KeyError) as e:
                    print(f"  Error processing {ticker} year {year}: {e}")
                    continue

        # Calculate historical ratios and trends
        if years_processed:
            # CF/EPS ratio statistics
            cf_eps_ratios = [metrics["yearly_data"][y]["cf_to_eps_ratio"]
                           for y in years_processed
                           if metrics["yearly_data"][y]["cf_to_eps_ratio"] != 0]

            # CF/Revenue ratio statistics
            cf_rev_ratios = [metrics["yearly_data"][y]["cf_to_revenue_ratio"]
                           for y in years_processed]

            # CapEx trends
            capex_pcts = [metrics["yearly_data"][y]["capex_as_pct_revenue"]
                        for y in years_processed]

            # R&D trends
            rd_pcts = [metrics["yearly_data"][y]["rd_as_pct_revenue"]
                     for y in years_processed]

            metrics["ratios"] = {
                "avg_cf_eps_ratio": np.mean(cf_eps_ratios) if cf_eps_ratios else 1.3,
                "median_cf_eps_ratio": np.median(cf_eps_ratios) if cf_eps_ratios else 1.3,
                "std_cf_eps_ratio": np.std(cf_eps_ratios) if cf_eps_ratios else 0.2,
                "avg_cf_revenue_ratio": np.mean(cf_rev_ratios) if cf_rev_ratios else 0.2,
                "avg_capex_pct": np.mean(capex_pcts) if capex_pcts else 15,
                "avg_rd_pct": np.mean(rd_pcts) if rd_pcts else 20
            }

            # Calculate growth trends
            if len(years_processed) >= 3:
                recent_years = sorted(years_processed)[-3:]
                revenue_growth = []
                cf_growth = []

                for i in range(1, len(recent_years)):
                    prev_year = recent_years[i-1]
                    curr_year = recent_years[i]

                    rev_prev = metrics["yearly_data"][prev_year]["revenue"]
                    rev_curr = metrics["yearly_data"][curr_year]["revenue"]
                    if rev_prev > 0:
                        revenue_growth.append((rev_curr - rev_prev) / rev_prev)

                    cf_prev = metrics["yearly_data"][prev_year]["operating_cf"]
                    cf_curr = metrics["yearly_data"][curr_year]["operating_cf"]
                    if cf_prev > 0:
                        cf_growth.append((cf_curr - cf_prev) / cf_prev)

                metrics["trends"] = {
                    "avg_revenue_growth": np.mean(revenue_growth) if revenue_growth else 0.1,
                    "avg_cf_growth": np.mean(cf_growth) if cf_growth else 0.1
                }

        return metrics

    def calculate_company_specific_multiplier(self, ticker, base_metrics):
        """Calculate company-specific CF/EPS multiplier based on characteristics."""
        info = SEMICONDUCTOR_TICKERS[ticker]
        base_ratio = base_metrics["ratios"]["median_cf_eps_ratio"]

        # Start with historical median
        multiplier = base_ratio

        # Adjust based on business model
        if info["type"] == "fabless":
            multiplier *= 1.1  # Fabless companies have better cash conversion
        else:
            multiplier *= 0.95  # Fab companies have higher CapEx needs

        # Adjust based on segment
        segment_adjustments = {
            "GPU/AI": 1.15,      # AI boom premium
            "CPU/GPU": 1.05,     # Strong market position
            "Memory": 0.85,      # Cyclical, volatile
            "CPU/Foundry": 0.90, # Heavy CapEx
            "Infrastructure": 1.0, # Stable
            "Diversified/Software": 1.2,  # Software mix improves CF
            "Foundry": 0.95      # Capital intensive
        }

        if info["segment"] in segment_adjustments:
            multiplier *= segment_adjustments[info["segment"]]

        # Adjust based on recent trends
        if "trends" in base_metrics and base_metrics["trends"]:
            if base_metrics["trends"].get("avg_cf_growth", 0) > 0.2:
                multiplier *= 1.05  # Growing CF gets premium

        # Company-specific adjustments
        company_adjustments = {
            "NVDA": 1.1,   # Data center dominance
            "AMD": 1.0,    # Market share gains
            "MU": 0.9,     # Memory cycle volatility
            "INTC": 0.85,  # Foundry transition challenges
            "MRVL": 1.0,   # Steady infrastructure play
            "AVGO": 1.15,  # Software acquisitions
            "TSM": 1.0     # Industry leader but CapEx heavy
        }

        if ticker in company_adjustments:
            multiplier *= company_adjustments[ticker]

        return multiplier

    def forecast_cash_flow(self, ticker, base_metrics, eps_forecast_2025, eps_forecast_2026):
        """Generate cash flow forecasts for 2025-2026."""

        # Get company-specific multiplier
        cf_multiplier = self.calculate_company_specific_multiplier(ticker, base_metrics)

        # Calculate base forecasts
        cf_2025_base = eps_forecast_2025 * cf_multiplier if eps_forecast_2025 else None
        cf_2026_base = eps_forecast_2026 * cf_multiplier if eps_forecast_2026 else None

        # Add cycle adjustment
        cycle_position = self.get_cycle_position()
        cycle_adjustment = 1.0

        if cycle_position == "upturn":
            cycle_adjustment = 1.05
        elif cycle_position == "peak":
            cycle_adjustment = 1.0
        elif cycle_position == "downturn":
            cycle_adjustment = 0.95
        elif cycle_position == "trough":
            cycle_adjustment = 0.90

        cf_2025 = cf_2025_base * cycle_adjustment if cf_2025_base else None
        cf_2026 = cf_2026_base * cycle_adjustment if cf_2026_base else None

        # Calculate confidence intervals
        std_ratio = base_metrics["ratios"].get("std_cf_eps_ratio", 0.2)

        forecasts = {
            "2025": {
                "cf_per_share": cf_2025,
                "cf_per_share_low": cf_2025 * (1 - std_ratio) if cf_2025 else None,
                "cf_per_share_high": cf_2025 * (1 + std_ratio) if cf_2025 else None,
                "multiplier_used": cf_multiplier * cycle_adjustment,
                "methodology": f"EPS × {cf_multiplier:.2f} × {cycle_adjustment:.2f} (cycle adj)"
            },
            "2026": {
                "cf_per_share": cf_2026,
                "cf_per_share_low": cf_2026 * (1 - std_ratio) if cf_2026 else None,
                "cf_per_share_high": cf_2026 * (1 + std_ratio) if cf_2026 else None,
                "multiplier_used": cf_multiplier * cycle_adjustment,
                "methodology": f"EPS × {cf_multiplier:.2f} × {cycle_adjustment:.2f} (cycle adj)"
            }
        }

        return forecasts

    def get_cycle_position(self):
        """Determine current position in semiconductor cycle."""
        # Simplified cycle detection
        # In reality, would use SOX index, inventory levels, book-to-bill ratios
        current_month = datetime.now().month
        current_year = datetime.now().year

        # 2024-2025 assumed to be upturn (AI boom)
        if current_year == 2024 or (current_year == 2025 and current_month <= 6):
            return "upturn"
        elif current_year == 2025 and current_month > 6:
            return "peak"
        elif current_year == 2026:
            return "downturn"  # Conservative assumption
        else:
            return "trough"

    def get_eps_forecasts(self, ticker, fundamentals_data):
        """Extract EPS forecasts from fundamentals data."""
        if not fundamentals_data:
            return None, None

        earnings_trend = fundamentals_data.get("Earnings", {}).get("Trend", {})

        eps_2025 = None
        eps_2026 = None

        # Search for 2025 and 2026 forecasts
        for date_key, data in earnings_trend.items():
            if "2025" in date_key:
                if "earningsEstimateAvg" in data:
                    eps_2025 = float(data["earningsEstimateAvg"])

            if "2026" in date_key:
                if "earningsEstimateAvg" in data:
                    eps_2026 = float(data["earningsEstimateAvg"])

        return eps_2025, eps_2026

    def analyze_all_companies(self):
        """Analyze all semiconductor companies and create comparative report."""
        print("=== Semiconductor Cash Flow Analysis ===\n")

        results = {}

        for ticker in SEMICONDUCTOR_TICKERS.keys():
            print(f"Analyzing {ticker} ({SEMICONDUCTOR_TICKERS[ticker]['name']})...")

            # Fetch data
            fundamentals = self.fetch_company_fundamentals(ticker)
            if not fundamentals:
                print(f"  Failed to fetch data for {ticker}")
                continue

            # Extract historical metrics
            metrics = self.extract_historical_metrics(ticker, fundamentals)
            if not metrics:
                print(f"  Failed to extract metrics for {ticker}")
                continue

            # Get EPS forecasts
            eps_2025, eps_2026 = self.get_eps_forecasts(ticker, fundamentals)

            # Generate CF forecasts
            cf_forecasts = self.forecast_cash_flow(ticker, metrics, eps_2025, eps_2026)

            results[ticker] = {
                "company": SEMICONDUCTOR_TICKERS[ticker]["name"],
                "type": SEMICONDUCTOR_TICKERS[ticker]["type"],
                "segment": SEMICONDUCTOR_TICKERS[ticker]["segment"],
                "historical_metrics": metrics,
                "eps_2025": eps_2025,
                "eps_2026": eps_2026,
                "cf_forecasts": cf_forecasts
            }

            # Print summary
            print(f"  Historical CF/EPS Ratio: {metrics['ratios']['median_cf_eps_ratio']:.2f}")
            if cf_forecasts["2025"]["cf_per_share"]:
                print(f"  2025 CF/Share Forecast: ${cf_forecasts['2025']['cf_per_share']:.2f}")
            if cf_forecasts["2026"]["cf_per_share"]:
                print(f"  2026 CF/Share Forecast: ${cf_forecasts['2026']['cf_per_share']:.2f}")
            print()

        self.company_data = results
        return results

    def generate_comparison_report(self, output_file="semiconductor_cf_analysis.html"):
        """Generate HTML comparison report."""
        if not self.company_data:
            print("No data to generate report")
            return

        # Create comparison DataFrame
        comparison_data = []

        for ticker, data in self.company_data.items():
            # Get most recent historical CF/Share
            hist_metrics = data["historical_metrics"]
            recent_year = max(hist_metrics["yearly_data"].keys()) if hist_metrics["yearly_data"] else None
            recent_cf = hist_metrics["yearly_data"][recent_year]["cf_per_share"] if recent_year else None

            row = {
                "Ticker": ticker,
                "Company": data["company"],
                "Type": data["type"],
                "Segment": data["segment"],
                "Hist CF/EPS Ratio": f"{hist_metrics['ratios']['median_cf_eps_ratio']:.2f}",
                "2024 CF/Share": f"${recent_cf:.2f}" if recent_cf else "N/A",
                "2025 EPS Fcst": f"${data['eps_2025']:.2f}" if data['eps_2025'] else "N/A",
                "2025 CF Fcst": f"${data['cf_forecasts']['2025']['cf_per_share']:.2f}"
                               if data['cf_forecasts']['2025']['cf_per_share'] else "N/A",
                "2026 EPS Fcst": f"${data['eps_2026']:.2f}" if data['eps_2026'] else "N/A",
                "2026 CF Fcst": f"${data['cf_forecasts']['2026']['cf_per_share']:.2f}"
                               if data['cf_forecasts']['2026']['cf_per_share'] else "N/A",
                "CF Multiplier": f"{data['cf_forecasts']['2025']['multiplier_used']:.2f}x"
                                if data['cf_forecasts']['2025']['multiplier_used'] else "N/A"
            }
            comparison_data.append(row)

        df = pd.DataFrame(comparison_data)

        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Semiconductor Sector Cash Flow Analysis</title>
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
        }}

        .metadata {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
            font-weight: 600;
            font-size: 0.9em;
        }}

        .comparison-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .comparison-table tr:hover {{
            background-color: #f8f9fa;
        }}

        .comparison-table tr:last-child td {{
            border-bottom: none;
        }}

        .fabless {{
            background-color: #e8f5e9;
        }}

        .fab {{
            background-color: #fff3e0;
        }}

        .methodology {{
            background: #fef9e7;
            padding: 15px;
            margin: 20px 0;
            border-left: 4px solid #f39c12;
            border-radius: 4px;
        }}

        .cycle-indicator {{
            display: inline-block;
            padding: 5px 10px;
            background: #3498db;
            color: white;
            border-radius: 4px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>Semiconductor Sector Cash Flow Analysis</h1>

    <div class="metadata">
        <p><strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Sector:</strong> Semiconductors & Semiconductor Equipment</p>
        <p><strong>Companies Analyzed:</strong> {len(self.company_data)}</p>
        <p><strong>Cycle Position:</strong> <span class="cycle-indicator">{self.get_cycle_position().upper()}</span></p>
    </div>

    <h2>Comparative Cash Flow Forecasts</h2>

    {df.to_html(index=False, classes='comparison-table', escape=False)}

    <div class="methodology">
        <h3>Methodology</h3>
        <p><strong>Base Model:</strong> CF/Share = EPS Forecast × Company-Specific Multiplier × Cycle Adjustment</p>
        <p><strong>Company Multipliers Based On:</strong></p>
        <ul>
            <li>Historical CF/EPS ratios (5-year median)</li>
            <li>Business model (Fabless vs Fab)</li>
            <li>Market segment (GPU/AI, Memory, Foundry, etc.)</li>
            <li>Recent growth trends</li>
            <li>Company-specific factors (market position, product mix)</li>
        </ul>
        <p><strong>Cycle Adjustments:</strong></p>
        <ul>
            <li>Upturn: +5% to base forecast</li>
            <li>Peak: No adjustment</li>
            <li>Downturn: -5% to base forecast</li>
            <li>Trough: -10% to base forecast</li>
        </ul>
    </div>

    <h2>Key Insights</h2>
    <ul>
        <li><strong>Fabless companies</strong> (NVDA, AMD, MRVL, AVGO) generally show higher CF/EPS ratios due to lower CapEx requirements</li>
        <li><strong>Fab companies</strong> (INTC, MU, TSM) have lower ratios due to heavy capital investments</li>
        <li><strong>AI-exposed companies</strong> (NVDA, AMD) receive premium multipliers reflecting strong demand</li>
        <li><strong>Memory companies</strong> (MU) show more volatile CF patterns due to commodity-like pricing</li>
    </ul>
</body>
</html>"""

        # Write to file
        output_path = os.path.join(os.path.dirname(__file__), output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\nReport generated: {output_path}")
        return output_path


def main():
    """Main function to run semiconductor cash flow analysis."""
    analyzer = SemiconductorCashFlowAnalyzer()

    # Analyze all companies
    analyzer.analyze_all_companies()

    # Generate comparison report
    analyzer.generate_comparison_report()


if __name__ == "__main__":
    main()