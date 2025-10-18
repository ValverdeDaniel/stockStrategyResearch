"""
Quick visualization toolkit. I'd like to build this out to be decently powerful
in terms of enabling quick interpretation of DCF related data.
"""

import sys

import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.pyplot as plt
from modeling.data import get_historical_share_prices

sys.path.append('..')
from modeling.data import *

sns.set()
sns.set_context('paper')


def visualize(dcf_prices, current_share_prices, regress = True):
    """
    2d plot comparing dcf-forecasted per share price with
    where a list of stocks is currently trading

    args:
        dcf_prices: dict of {'ticker': price, ...} for dcf-values
        current_share_prices: dict of {'ticker': price, ...} for (guess)
        regress: regress a line of best fit, because why not

    returns:
        nada
    """
    # TODO: implement
    return NotImplementedError


# visualization/plot.py


def visualize_bulk_historicals(dcfs, ticker, cond, apikey_or_args=None):
    """
    Plot DCF-implied per-share values vs. ACTUAL market closes on the same anchor dates.

    Accepts either:
      - apikey_or_args = argparse.Namespace with .apikey, or
      - apikey_or_args = API key string, or
      - None (will try env vars)
    """
    # ---- resolve API key safely ----
    if isinstance(apikey_or_args, str):
        apikey = apikey_or_args
    elif apikey_or_args is not None:
        apikey = getattr(apikey_or_args, "apikey", "") or ""
    else:
        apikey = ""

    if not apikey:
        # last resort: environment
        apikey = (os.environ.get("APIKEY")
                  or os.environ.get("EOD_API")
                  or os.environ.get("EOD_API_KEY")
                  or os.environ.get("EODHD_API_KEY")
                  or "")

    # ---- collect intrinsic points from dcfs ----
    series = dcfs.get(ticker, {}) or {}
    dcf_points = {}
    for date_str, row in series.items():
        if isinstance(row, dict) and row.get("share_price") is not None:
            dcf_points[date_str] = float(row["share_price"])

    if not dcf_points:
        print("No DCF points to plot.")
        return

    dates_iso = sorted(dcf_points.keys())               # oldest -> newest
    y_dcf = [dcf_points[d] for d in dates_iso]
    dates_compact = [d.replace("-", "") for d in dates_iso]

    # ---- fetch market closes for those anchor dates ----
    px_map = {}
    if apikey:
        try:
            px_map = get_historical_share_prices(ticker, dates_compact, apikey) or {}
        except Exception as e:
            print(f"Could not fetch market prices (skipping overlay): {e}")
            px_map = {}
    else:
        print("No EOD API key found; showing DCF line only. Pass --apikey or set APIKEY env var.")

    y_mkt = [px_map.get(d) for d in dates_compact] if px_map else [None] * len(dates_compact)

    # ---- plot ----
    plt.figure(figsize=(10, 5))
    plt.plot(dates_iso, y_dcf, marker="o", linewidth=1.5, label="DCF intrinsic")

    if any(v is not None for v in y_mkt):
        y_mkt_clean = [v if v is not None else float("nan") for v in y_mkt]
        plt.plot(dates_iso, y_mkt_clean, marker="x", linewidth=1.5, label="Market close")

    plt.title(f"{ticker} — DCF vs. Market (by anchor date)")
    plt.xlabel("Anchor date (statement date)")
    plt.ylabel("Per-share value")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()



def visualize_historicals(dcfs):
    """
    2d plot comparing dcf history to share price history
    """
    pass

    dcf_share_prices = {}
    for k, v in dcfs.items():
        dcf_share_prices[dcfs[k]['date']] = dcfs[k]['share_price']

    xs = list(dcf_share_prices.keys())[::-1]
    ys = list(dcf_share_prices.values())[::-1]

    plt.scatter(xs, ys)
    plt.show()
