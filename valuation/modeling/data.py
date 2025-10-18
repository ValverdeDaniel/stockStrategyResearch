

from __future__ import annotations

import os
import re
from typing import Dict, Any, List, Optional, TypedDict, Protocol, runtime_checkable
from datetime import datetime, timedelta

import requests


# =========================
# Configuration & helpers
# =========================

_EOD_BASE = "https://eodhd.com/api"

# Period mapping: keep CLI 'annual'/'quarter' public; map internally to EOD's 'yearly'/'quarterly'
_PERIOD_MAP = {"annual": "yearly", "quarter": "quarterly"}
def _map_period(period: str) -> str:
    p = (period or "annual").strip().lower()
    return _PERIOD_MAP.get(p, p)  

_DEFAULT_SUFFIX = os.environ.get("DEFAULT_EXCHANGE_SUFFIX", "US")  # 'US', 'DE', 'PA', etc.
_TICKER_WITH_SUFFIX = re.compile(r".+\.[A-Za-z]{1,4}$")
def _normalize_ticker(ticker: str, default_suffix: str = _DEFAULT_SUFFIX) -> str:
    if not ticker:
        return ticker
    t = ticker.strip().upper()
    return t if _TICKER_WITH_SUFFIX.match(t) else f"{t}.{default_suffix}"


_CAPEX_ABS = os.environ.get("DCF_CAPEX_ABS", "1") == "1"

def _eod_get(path: str, params: Dict[str, Any]) -> Any:
    """requests.get wrapper with basic error handling & JSON parse."""
    url = f"{_EOD_BASE}/{path.lstrip('/')}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"Failed parsing JSON from {url} ({e})")

def _ensure_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        return float(str(x).replace(",", "")) 
    except Exception:
        return None

def _as_date(s: str) -> Optional[datetime]:
    """Accept 'YYYY-MM-DD' or 'YYYYMMDD'."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None

def _format_yyyymmdd(d: datetime) -> str:
    return d.strftime("%Y%m%d")

def _closest_on_or_before(target: datetime, available: List[datetime]) -> Optional[datetime]:
    res = None
    for d in available:
        if d <= target:
            res = d
        else:
            break
    return res

def _normalize_date_key(k: str) -> str:
    # Accept '2024-09-28' or '2024' → coerce bare year to Dec-31
    if isinstance(k, str) and len(k) == 4 and k.isdigit():
        return f"{k}-12-31"
    return k

def _lower_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    return { (k.lower() if isinstance(k, str) else k): v for k, v in (d or {}).items() }

def _ci_get(d: Dict[str, Any], *candidates: str) -> Any:
    """Case-insensitive get across a set of candidate names."""
    if not isinstance(d, dict):
        return None
    ld = _lower_keys(d)
    for name in candidates:
        if name and name.lower() in ld:
            return ld[name.lower()]
    return None


# =========================
# Types your DCF expects
# =========================

class IncomeRow(TypedDict, total=False):
    date: str
    EBIT: float
    Income_Tax_Expense: float  # internal alias if you prefer; we expose "Income Tax Expense" in dict below
    # We will actually store the exact key "Income Tax Expense"
    # but TypedDicts cannot have spaces; this is informational.

class CashFlowRow(TypedDict, total=False):
    date: str
    Depreciation_And_Amortization: float  # see note above
    Capital_Expenditure: float

class BalanceRow(TypedDict, total=False):
    date: str
    Total_assets: float
    Total_non_current_assets: float

class EVStatement(TypedDict, total=False):
    # Keep the exact keys your DCF uses:
    # '+ Total Debt', '- Cash & Cash Equivalents', 'Number of Shares'
    pass


# =========================
# Provider protocol
# =========================

@runtime_checkable
class DataProvider(Protocol):
    def get_income_statement(self, ticker: str, period: str, apikey: str) -> List[Dict[str, Any]]: ...
    def get_cashflow_statement(self, ticker: str, period: str, apikey: str) -> List[Dict[str, Any]]: ...
    def get_balance_statement(self, ticker: str, period: str, apikey: str) -> List[Dict[str, Any]]: ...
    def get_EV_statement(self, ticker: str, period: str, apikey: str) -> Dict[str, float]: ...
    def get_stock_price(self, ticker: str, apikey: str) -> Dict[str, Any]: ...
    def get_batch_stock_prices(self, tickers: List[str], apikey: str) -> Dict[str, float]: ...
    def get_historical_share_prices(self, ticker: str, dates: List[str], apikey: str) -> Dict[str, float]: ...


# =========================
# Fundamentals extraction
# =========================

def _extract_financials_section_generic(
    fundamentals_blob: Dict[str, Any],
    section_name: str,        # "Income_Statement" | "Cash_Flow" | "Balance_Sheet"
    period_mode: str          # "yearly" | "quarterly"
) -> Dict[str, Dict[str, Any]]:
    """
    Works with BOTH:
    - Full fundamentals blob (with 'Financials' envelope), and
    - Filtered response (already the dict for the section or directly {date->row}).
    Returns: {'YYYY-MM-DD': row_dict, ...}
    """
    obj = fundamentals_blob or {}

    # Case A: full blob with Financials/Section/period
    fin = obj.get("Financials") or {}
    if isinstance(fin, dict) and fin:
        sec = fin.get(section_name) or {}
        per = sec.get(period_mode) or {}
        if isinstance(per, dict) and per:
            return { _normalize_date_key(k): (v if isinstance(v, dict) else {}) for k, v in per.items() }

    # Case B: filtered to the section => may contain {'yearly': {...}, 'quarterly': {...}}
    if isinstance(obj, dict) and (("yearly" in obj) or ("quarterly" in obj)):
        per = obj.get(period_mode) or obj
        if isinstance(per, dict) and per:
            return { _normalize_date_key(k): (v if isinstance(v, dict) else {}) for k, v in per.items() }

    # Case C: filtered directly to the period mapping {date -> row}
    if isinstance(obj, dict):
        sample_key = next(iter(obj.keys()), None)
        if sample_key and (isinstance(sample_key, str) and (sample_key[:4].isdigit() or "-" in sample_key)):
            return { _normalize_date_key(k): (v if isinstance(v, dict) else {}) for k, v in obj.items() }

    return {}


# =========================
# EOD Provider
# =========================

class EODProvider(DataProvider):
    """Pulls from EODHD endpoints and RETURNS the same shapes/keys your DCF already expects."""

    def _fundamentals(self, ticker: str, apikey: str, filter_: Optional[str] = None) -> Dict[str, Any]:
        """
        GET /api/fundamentals/{TICKER}?api_token=... [&filter=...]
        Returns a dict (handles list edge-case by taking first item).
        """
        params = {"api_token": apikey, "fmt": "json"}
        if filter_:
            params["filter"] = filter_
        blob = _eod_get(f"fundamentals/{ticker}", params=params)
        if isinstance(blob, list) and blob:
            blob = blob[0]
        if not isinstance(blob, dict):
            raise RuntimeError("Unexpected fundamentals payload")
        return blob

    # ---------- Financial Statements ----------

    def get_income_statement(self, ticker: str, period: str, apikey: str) -> List[Dict[str, Any]]:
        t = _normalize_ticker(ticker)
        per = _map_period(period)
        blob = self._fundamentals(t, apikey, filter_=f"Financials::Income_Statement::{per}")
        sec = _extract_financials_section_generic(blob, "Income_Statement", per)

        out: List[Dict[str, Any]] = []
        for dstr, row in sec.items():
            out.append({
                "date": dstr,
                "EBIT": _ensure_float(_ci_get(row, "OperatingIncome", "operatingIncome", "EBIT", "ebit")),
                "Income Tax Expense": _ensure_float(_ci_get(row, "IncomeTaxExpense", "incomeTaxExpense", "ProvisionForIncomeTaxes")),
                "Earnings before Tax": _ensure_float(_ci_get(row, "EarningsBeforeTax", "earningsBeforeTax", "IncomeBeforeTax", "incomeBeforeTax")),
            })
        out.sort(key=lambda r: r["date"], reverse=True)
        return out

    def get_cashflow_statement(self, ticker: str, period: str, apikey: str) -> List[Dict[str, Any]]:
        t = _normalize_ticker(ticker)
        per = _map_period(period)
        blob = self._fundamentals(t, apikey, filter_=f"Financials::Cash_Flow::{per}")
        sec = _extract_financials_section_generic(blob, "Cash_Flow", per)

        out: List[Dict[str, Any]] = []
        for dstr, row in sec.items():
            capex_raw = _ensure_float(_ci_get(
                row, "CapitalExpenditures", "capitalExpenditures",
                "InvestmentsInPropertyPlantAndEquipment", "investmentsInPropertyPlantAndEquipment"
            ))
            capex_norm = None if capex_raw is None else (abs(capex_raw) if _CAPEX_ABS else capex_raw)

            da = _ensure_float(_ci_get(
                row, "DepreciationAndAmortization", "depreciationAndAmortization",
                "Depreciation", "depreciation"
            ))

            out.append({
                "date": dstr,
                "Depreciation & Amortization": da,
                "Capital Expenditure": capex_norm,
            })
        out.sort(key=lambda r: r["date"], reverse=True)
        return out

    def get_balance_statement(self, ticker: str, period: str, apikey: str) -> List[Dict[str, Any]]:
        t = _normalize_ticker(ticker)
        per = _map_period(period)
        blob = self._fundamentals(t, apikey, filter_=f"Financials::Balance_Sheet::{per}")
        sec = _extract_financials_section_generic(blob, "Balance_Sheet", per)

        out: List[Dict[str, Any]] = []
        for dstr, row in sec.items():
            out.append({
                "date": dstr,
                "Total assets": _ensure_float(_ci_get(row, "TotalAssets", "totalAssets")),
                "Total non-current assets": _ensure_float(_ci_get(row, "nonCurrentAssetsTotal", "totalNonCurrentAssets",
                                                                 "NonCurrentAssets", "nonCurrentAssets")),
            })
        out.sort(key=lambda r: r["date"], reverse=True)
        return out

    def get_EV_statement(self, ticker: str, period: str, apikey: str) -> Dict[str, float]:
        """
        Returns:
          {
            '+ Total Debt': float,
            '- Cash & Cash Equivalents': float,
            'Number of Shares': float
          }
        """
        t = _normalize_ticker(ticker)
        blob = self._fundamentals(t, apikey, filter_=None)

        highlights = blob.get("Highlights") or {}
        shares_stats = blob.get("SharesStats") or {}
        bs = (blob.get("Financials") or {}).get("Balance_Sheet") or {}
        yearly = bs.get("yearly") if isinstance(bs, dict) else {}

        # Shares outstanding
        shares = _ensure_float(_ci_get(highlights, "SharesOutstanding", "sharesOutstanding"))
        if shares is None:
            shares = _ensure_float(_ci_get(shares_stats, "SharesOutstanding", "sharesOutstanding"))

        # Total debt (prefer direct; else long+short from latest BS row)
        total_debt = _ensure_float(_ci_get(highlights, "TotalDebt", "totalDebt"))
        if total_debt is None and isinstance(yearly, dict) and yearly:
            latest_key = sorted(yearly.keys())[-1]
            last_row = yearly.get(latest_key) or {}
            long_debt = _ensure_float(_ci_get(last_row, "LongTermDebtTotal", "longTermDebtTotal",
                                              "LongTermDebt", "longTermDebt"))
            short_debt = _ensure_float(_ci_get(last_row, "ShortTermDebt", "shortTermDebt",
                                               "CurrentPortionOfLongTermDebt", "currentPortionOfLongTermDebt"))
            if long_debt is not None or short_debt is not None:
                total_debt = (long_debt or 0.0) + (short_debt or 0.0)

        # Cash & equivalents
        cash_eq = _ensure_float(_ci_get(highlights, "CashAndCashEquivalents", "cashAndEquivalents",
                                        "CashAndCashEquivalentsUSD"))
        if cash_eq is None and isinstance(yearly, dict) and yearly:
            latest_key = sorted(yearly.keys())[-1]
            last_row = yearly.get(latest_key) or {}
            cash_eq = _ensure_float(_ci_get(last_row, "CashAndCashEquivalents", "cashAndEquivalents",
                                            "Cash", "cash"))
        # ... after computing 'shares' from Highlights / SharesStats ...
        if shares is None and isinstance(yearly, dict) and yearly:
            latest_key = sorted(yearly.keys())[-1]
            last_row = yearly.get(latest_key) or {}
            shares = _ensure_float(_ci_get(
                last_row,
                "CommonStockSharesOutstanding", "commonStockSharesOutstanding",
                "OrdinarySharesNumber", "ordinarySharesNumber",
                "ShareIssued", "shareIssued",
                "WeightedAverageDilutedSharesOutstanding", "weightedAverageDilutedSharesOutstanding",
                "WeightedAverageSharesOutstandingDiluted", "weightedAverageSharesOutstandingDiluted",
                "WeightedAverageSharesOutstanding", "weightedAverageSharesOutstanding"
            ))

        # Unit sanity: if shares looks implausibly small for a US large-cap, assume 'millions'
        if shares is not None and shares < 1e5:
            shares = shares * 1_000_000.0

        return {
            "+ Total Debt": total_debt or 0.0,
            "- Cash & Cash Equivalents": cash_eq or 0.0,
            "Number of Shares": shares or 0.0,
        }

    # ---------- Prices ----------

    def get_stock_price(self, ticker: str, apikey: str) -> Dict[str, Any]:
        """
        Returns {'symbol': <ticker_with_suffix>, 'price': <float>}.
        Tries real-time first; if missing, falls back to latest EOD close.
        """
        t = _normalize_ticker(ticker)

        # 1) Real-time (delayed on some tiers)
        try:
            data = _eod_get(f"real-time/{t}", {"api_token": apikey, "fmt": "json"})
            if isinstance(data, list) and data:
                data = data[0]
            price = _ensure_float((data or {}).get("price"))
            if price is not None and price > 0:
                return {"symbol": t, "price": price}
        except Exception:
            pass

        # 2) Fallback: last EOD close
        try:
            today = datetime.utcnow().date()
            params = {
                "from": (today - timedelta(days=14)).strftime("%Y-%m-%d"),
                "to": today.strftime("%Y-%m-%d"),
                "order": "a",
                "api_token": apikey,
                "fmt": "json",
            }
            arr = _eod_get(f"eod/{t}", params=params)
            if isinstance(arr, list) and arr:
                last = arr[-1]
                close = _ensure_float(last.get("close"))
                if close is not None and close > 0:
                    return {"symbol": t, "price": close}
        except Exception:
            pass

        return {"symbol": t, "price": None}

    def get_batch_stock_prices(self, tickers: List[str], apikey: str) -> Dict[str, float]:
        """Simple loop batch to stay universal across EOD tiers."""
        out: Dict[str, float] = {}
        for tk in tickers:
            try:
                px = self.get_stock_price(tk, apikey)
                if px["price"] is not None:
                    out[_normalize_ticker(tk)] = float(px["price"])
            except Exception:
                pass
        return out

    def get_historical_share_prices(self, ticker: str, dates: List[str], apikey: str) -> Dict[str, float]:
        """
        Build { 'YYYYMMDD': adjusted_close }. Uses adjusted closes to handle splits/dividends.
        Maps each target date to the closest available trading day on or before that date.
        """
        t = _normalize_ticker(ticker)
        parsed_dates = [d for d in (_as_date(s) for s in dates) if d]
        if not parsed_dates:
            return {}

        start = min(parsed_dates) - timedelta(days=5)   # small buffer
        end = max(parsed_dates) + timedelta(days=1)

        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
            "order": "a",
            "adjusted": "1",            # <<— ask EOD for adjusted data
            "api_token": apikey,
            "fmt": "json",
        }
        arr = _eod_get(f"eod/{t}", params=params)
        if not isinstance(arr, list):
            arr = []

        series: Dict[datetime, float] = {}
        for row in arr:
            d = _as_date(row.get("date"))
            # Prefer adjusted close; fall back to regular close if not present
            adj = _ensure_float(_ci_get(row, "adjusted_close", "adjustedClose", "adjClose"))
            if adj is None:
                adj = _ensure_float(row.get("close"))
            if d and adj is not None:
                series[d] = float(adj)

        available = sorted(series.keys())
        out: Dict[str, float] = {}
        for target_raw in parsed_dates:
            nearest = _closest_on_or_before(target_raw, available)
            if nearest is None:
                continue
            out[_format_yyyymmdd(target_raw)] = series[nearest]
        return out



# =========================
# Public functions (same names/signatures)
# =========================

_provider: DataProvider = EODProvider()

def get_income_statement(ticker, period='annual', apikey=''):
    return _provider.get_income_statement(ticker, period, apikey)

def get_cashflow_statement(ticker, period='annual', apikey=''):
    return _provider.get_cashflow_statement(ticker, period, apikey)

def get_balance_statement(ticker, period='annual', apikey=''):
    return _provider.get_balance_statement(ticker, period, apikey)

def get_EV_statement(ticker, period='annual', apikey=''):
    return _provider.get_EV_statement(ticker, period, apikey)

def get_stock_price(ticker, apikey=''):
    return _provider.get_stock_price(ticker, apikey)

def get_batch_stock_prices(tickers, apikey=''):
    return _provider.get_batch_stock_prices(tickers, apikey)

def get_historical_share_prices(ticker, dates, apikey=''):
    return _provider.get_historical_share_prices(ticker, dates, apikey)
