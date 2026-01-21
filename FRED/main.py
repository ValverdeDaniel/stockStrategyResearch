"""
Main runner script for FRED economic data visualizations
Fetches data from FRED API and creates interactive visualizations
"""

import os
import sys
import argparse
from datetime import datetime
import logging

# Import visualizers
from visualizations import (
    GDPVisualizer,
    UnemploymentVisualizer,
    RealPotentialGDPVisualizer,
    RealGDPPerCapitaVisualizer,
    NominalPotentialGDPVisualizer,
    CPIVisualizer,
    PCEVisualizer
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_all_visualizations(start_date: str = '2000-01-01', end_date: str = None):
    """
    Create all economic indicator visualizations

    Args:
        start_date: Start date for data (YYYY-MM-DD format)
        end_date: End date for data (YYYY-MM-DD format)
    """
    print("\n" + "="*60)
    print("FRED Economic Data Visualization Suite")
    print("="*60 + "\n")

    # Create output directory
    output_dir = os.path.join('FRED', 'outputs')
    os.makedirs(output_dir, exist_ok=True)

    # Track success/failure
    results = []

    # 1. GDP Visualizations
    print("\n[1/7] Creating GDP visualizations...")
    try:
        gdp_viz = GDPVisualizer()
        fig1 = gdp_viz.create_interactive_graph(start_date, end_date)
        gdp_viz.save_graph(fig1, 'gdp_analysis.html')

        fig2 = gdp_viz.create_comparison_graph(start_date, end_date)
        gdp_viz.save_graph(fig2, 'gdp_nominal_vs_real.html')

        gdp_viz.export_data(start_date, end_date, 'gdp_data.csv')
        print("✓ GDP visualizations completed")
        results.append(('GDP', True))
    except Exception as e:
        print(f"✗ GDP visualization failed: {e}")
        results.append(('GDP', False))

    # 2. Unemployment Visualizations
    print("\n[2/7] Creating Unemployment Rate visualizations...")
    try:
        unemp_viz = UnemploymentVisualizer()
        fig1 = unemp_viz.create_interactive_graph(start_date, end_date)
        unemp_viz.save_graph(fig1, 'unemployment_analysis.html')

        fig2 = unemp_viz.create_historical_comparison('1994-01-01', end_date)
        unemp_viz.save_graph(fig2, 'unemployment_comparison.html')

        unemp_viz.export_data(start_date, end_date, 'unemployment_data.csv')
        print("✓ Unemployment visualizations completed")
        results.append(('Unemployment', True))
    except Exception as e:
        print(f"✗ Unemployment visualization failed: {e}")
        results.append(('Unemployment', False))

    # 3. Real Potential GDP Visualizations
    print("\n[3/7] Creating Real Potential GDP visualizations...")
    try:
        real_pot_viz = RealPotentialGDPVisualizer()
        fig1 = real_pot_viz.create_interactive_graph(start_date, end_date)
        real_pot_viz.save_graph(fig1, 'real_potential_gdp_analysis.html')

        fig2 = real_pot_viz.create_historical_analysis('1985-01-01', end_date)
        real_pot_viz.save_graph(fig2, 'output_gap_historical.html')

        real_pot_viz.export_data(start_date, end_date, 'real_potential_gdp_data.csv')
        print("✓ Real Potential GDP visualizations completed")
        results.append(('Real Potential GDP', True))
    except Exception as e:
        print(f"✗ Real Potential GDP visualization failed: {e}")
        results.append(('Real Potential GDP', False))

    # 4. Real GDP per Capita Visualizations
    print("\n[4/7] Creating Real GDP per Capita visualizations...")
    try:
        per_capita_viz = RealGDPPerCapitaVisualizer()
        fig1 = per_capita_viz.create_interactive_graph('1980-01-01', end_date)
        per_capita_viz.save_graph(fig1, 'real_gdp_per_capita_analysis.html')

        fig2 = per_capita_viz.create_comparison_graph('1960-01-01', end_date)
        per_capita_viz.save_graph(fig2, 'gdp_per_capita_historical.html')

        per_capita_viz.export_data(start_date, end_date, 'real_gdp_per_capita_data.csv')
        print("✓ Real GDP per Capita visualizations completed")
        results.append(('Real GDP per Capita', True))
    except Exception as e:
        print(f"✗ Real GDP per Capita visualization failed: {e}")
        results.append(('Real GDP per Capita', False))

    # 5. Nominal Potential GDP Visualizations
    print("\n[5/7] Creating Nominal Potential GDP visualizations...")
    try:
        nom_pot_viz = NominalPotentialGDPVisualizer()
        fig1 = nom_pot_viz.create_interactive_graph(start_date, end_date)
        nom_pot_viz.save_graph(fig1, 'nominal_potential_gdp_analysis.html')

        fig2 = nom_pot_viz.create_inflation_analysis(start_date, end_date)
        nom_pot_viz.save_graph(fig2, 'nominal_gdp_inflation_analysis.html')

        nom_pot_viz.export_data(start_date, end_date, 'nominal_potential_gdp_data.csv')
        print("✓ Nominal Potential GDP visualizations completed")
        results.append(('Nominal Potential GDP', True))
    except Exception as e:
        print(f"✗ Nominal Potential GDP visualization failed: {e}")
        results.append(('Nominal Potential GDP', False))

    # 6. CPI Visualizations
    print("\n[6/7] Creating CPI visualizations...")
    try:
        cpi_viz = CPIVisualizer()
        fig1 = cpi_viz.create_interactive_graph(start_date, end_date)
        cpi_viz.save_graph(fig1, 'cpi_analysis.html')

        fig2 = cpi_viz.create_historical_analysis('1970-01-01', end_date)
        cpi_viz.save_graph(fig2, 'cpi_historical.html')

        fig3 = cpi_viz.create_purchasing_power_analysis(start_date, end_date, 100)
        cpi_viz.save_graph(fig3, 'purchasing_power.html')

        cpi_viz.export_data(start_date, end_date, 'cpi_data.csv')
        print("✓ CPI visualizations completed")
        results.append(('CPI', True))
    except Exception as e:
        print(f"✗ CPI visualization failed: {e}")
        results.append(('CPI', False))

    # 7. PCE Visualizations
    print("\n[7/7] Creating PCE visualizations...")
    try:
        pce_viz = PCEVisualizer()
        fig1 = pce_viz.create_interactive_graph(start_date, end_date)
        pce_viz.save_graph(fig1, 'pce_analysis.html')

        fig2 = pce_viz.create_fed_policy_analysis(start_date, end_date)
        pce_viz.save_graph(fig2, 'pce_fed_policy.html')

        fig3 = pce_viz.create_comparison_table(start_date, end_date)
        pce_viz.save_graph(fig3, 'pce_vs_cpi_table.html')

        pce_viz.export_data(start_date, end_date, 'pce_data.csv')
        print("✓ PCE visualizations completed")
        results.append(('PCE', True))
    except Exception as e:
        print(f"✗ PCE visualization failed: {e}")
        results.append(('PCE', False))

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    successful = sum(1 for _, success in results if success)
    failed = len(results) - successful

    for indicator, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {indicator}")

    print(f"\nCompleted: {successful}/{len(results)} visualizations")
    if failed > 0:
        print(f"Failed: {failed} visualizations")

    print(f"\nOutput files saved to: {os.path.abspath(output_dir)}")

    return successful == len(results)


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Create FRED economic data visualizations'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        default='2000-01-01',
        help='Start date for data (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='End date for data (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--indicator',
        type=str,
        choices=['gdp', 'unemployment', 'real-potential', 'per-capita',
                'nominal-potential', 'cpi', 'pce', 'all'],
        default='all',
        help='Which indicator to visualize'
    )

    args = parser.parse_args()

    # Validate dates
    try:
        if args.start_date:
            datetime.strptime(args.start_date, '%Y-%m-%d')
        if args.end_date:
            datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        return 1

    # Create visualizations based on selection
    if args.indicator == 'all':
        success = create_all_visualizations(args.start_date, args.end_date)
    else:
        # Create output directory
        output_dir = os.path.join('FRED', 'outputs')
        os.makedirs(output_dir, exist_ok=True)

        success = True
        try:
            if args.indicator == 'gdp':
                print("Creating GDP visualizations...")
                viz = GDPVisualizer()
                fig = viz.create_interactive_graph(args.start_date, args.end_date)
                viz.save_graph(fig, 'gdp_analysis.html')

            elif args.indicator == 'unemployment':
                print("Creating Unemployment visualizations...")
                viz = UnemploymentVisualizer()
                fig = viz.create_interactive_graph(args.start_date, args.end_date)
                viz.save_graph(fig, 'unemployment_analysis.html')

            elif args.indicator == 'real-potential':
                print("Creating Real Potential GDP visualizations...")
                viz = RealPotentialGDPVisualizer()
                fig = viz.create_interactive_graph(args.start_date, args.end_date)
                viz.save_graph(fig, 'real_potential_gdp_analysis.html')

            elif args.indicator == 'per-capita':
                print("Creating Real GDP per Capita visualizations...")
                viz = RealGDPPerCapitaVisualizer()
                fig = viz.create_interactive_graph(args.start_date, args.end_date)
                viz.save_graph(fig, 'real_gdp_per_capita_analysis.html')

            elif args.indicator == 'nominal-potential':
                print("Creating Nominal Potential GDP visualizations...")
                viz = NominalPotentialGDPVisualizer()
                fig = viz.create_interactive_graph(args.start_date, args.end_date)
                viz.save_graph(fig, 'nominal_potential_gdp_analysis.html')

            elif args.indicator == 'cpi':
                print("Creating CPI visualizations...")
                viz = CPIVisualizer()
                fig = viz.create_interactive_graph(args.start_date, args.end_date)
                viz.save_graph(fig, 'cpi_analysis.html')

            elif args.indicator == 'pce':
                print("Creating PCE visualizations...")
                viz = PCEVisualizer()
                fig = viz.create_interactive_graph(args.start_date, args.end_date)
                viz.save_graph(fig, 'pce_analysis.html')

            print(f"✓ {args.indicator.upper()} visualization completed")
            print(f"Output saved to: {os.path.abspath(output_dir)}")

        except Exception as e:
            print(f"✗ Visualization failed: {e}")
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())