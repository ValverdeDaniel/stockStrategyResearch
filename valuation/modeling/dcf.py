# modeling/dcf.py
import argparse, traceback
from decimal import Decimal

from modeling.data import *


def DCF(ticker,
        ev_statement,
        income_statement,
        balance_statement,
        cashflow_statement,
        discount_rate,
        forecast,
        earnings_growth_rate,
        cap_ex_growth_rate,
        perpetual_growth_rate):
    """
    A very basic 2-stage DCF implemented for learning purposes.

    Returns a dict:
      {
        'date': <anchor statement date, e.g., '2024-12-31'>,
        'enterprise_value': float,
        'equity_value': float,
        'share_price': float
      }
    """
    enterprise_val = enterprise_value(
        income_statement,
        cashflow_statement,
        balance_statement,
        forecast,
        discount_rate,
        earnings_growth_rate,
        cap_ex_growth_rate,
        perpetual_growth_rate
    )

    equity_val, share_price = equity_value(enterprise_val, ev_statement)

    print(
        '\nEnterprise Value for {}: ${}.'.format(ticker, '%.2E' % Decimal(str(enterprise_val))),
        '\nEquity Value for {}: ${}.'.format(ticker, '%.2E' % Decimal(str(equity_val))),
        '\nPer share value for {}: ${}.\n'.format(ticker, '%.2E' % Decimal(str(share_price))),
    )

    return {
        'date': income_statement[0]['date'],  # statement date used as anchor
        'enterprise_value': enterprise_val,
        'equity_value': equity_val,
        'share_price': share_price
    }


def historical_DCF(ticker, years, forecast, discount_rate, earnings_growth_rate,
                   cap_ex_growth_rate, perpetual_growth_rate, interval='annual', apikey=''):
    """
    Wrap DCF to fetch valuations across a history of anchors.

    Args mirror DCF; extra:
      - years: how many anchors back (annual) or years*4 (quarter) we attempt
      - interval: 'annual' or 'quarter'

    Returns: dict keyed by anchor date -> DCF dict
    """
    dcfs = {}

    # --------- provider-agnostic unwrappers (EOD list vs FMP {'financials': list}) ---------
    def _unwrap_financials(x):
        if isinstance(x, dict) and 'financials' in x and isinstance(x['financials'], list):
            return x['financials']
        return x

    def _unwrap_ev(x):
        # EOD: single dict with '+ Total Debt', '- Cash & Cash Equivalents', 'Number of Shares'
        # FMP: {'enterpriseValues': list[dict]}
        if isinstance(x, dict) and 'enterpriseValues' in x and isinstance(x['enterpriseValues'], list):
            return x['enterpriseValues']  # legacy path (unused with current EOD layer)
        return x

    # --------- fetch inputs via data layer ---------
    income_statement = _unwrap_financials(get_income_statement(ticker=ticker, period=interval, apikey=apikey))
    balance_statement = _unwrap_financials(get_balance_statement(ticker=ticker, period=interval, apikey=apikey))
    cashflow_statement = _unwrap_financials(get_cashflow_statement(ticker=ticker, period=interval, apikey=apikey))
    ev_stmt = get_EV_statement(ticker=ticker, period=interval, apikey=apikey)

    # Sanity: lists
    income_statement = income_statement or []
    balance_statement = balance_statement or []
    cashflow_statement = cashflow_statement or []

    # How many anchors to attempt
    if interval == 'quarter':
        intervals_to_try = years * 4
    else:
        intervals_to_try = years

    # --------- helpers for TTM quarterly path ---------
    def _sum_field(rows, field):
        s = 0.0
        for r in rows:
            v = r.get(field)
            s += float(v if v is not None else 0.0)
        return s

    def _current_assets(row):
        ta = float(row.get('Total assets', 0.0) or 0.0)
        tnca = float(row.get('Total non-current assets', 0.0) or 0.0)
        return ta - tnca

    use_quarter_ttm = (interval == 'quarter')

    # IMPORTANT: don't shadow 'interval' (string) with loop index
    for idx in range(0, intervals_to_try):
        try:
            if use_quarter_ttm:
                # Need: q..q+3 for IS/CF TTM, and q+4 for ΔWC over 4 quarters
                need_inc = (idx + 3) < len(income_statement)
                need_cf  = (idx + 3) < len(cashflow_statement)
                need_bs  = (idx + 4) < len(balance_statement)
                if not (need_inc and need_cf and need_bs):
                    print(f"Interval {idx} unavailable for TTM (need 5 BS quarters and 4 IS/CF).")
                    raise IndexError("Not enough quarterly rows for TTM window")

                # TTM aggregates for EBIT, D&A, CapEx (annual-scale base)
                inc_win = income_statement[idx:idx+4]
                cf_win  = cashflow_statement[idx:idx+4]

                ebit_ttm = _sum_field(inc_win, 'EBIT')
                tax_ttm  = _sum_field(inc_win, 'Income Tax Expense')
                ebt_ttm  = _sum_field(inc_win, 'Earnings before Tax')

                da_ttm     = _sum_field(cf_win,  'Depreciation & Amortization')
                capex_ttm  = _sum_field(cf_win,  'Capital Expenditure')  # keep data-layer sign

                # ΔWC over 4 quarters (q vs q-4)
                ca_now  = _current_assets(balance_statement[idx])
                ca_prev = _current_assets(balance_statement[idx+4])
                delta_wc_ttm = ca_now - ca_prev  # used via BS rows below

                # Synthesize the rows the DCF expects:
                # - DCF reads EBIT/Tax/EBT from income_statement[0]
                # - DCF reads D&A/CapEx from cashflow_statement[0]
                # - DCF computes ΔWC from balance_statement[0] vs [1]
                #   => Provide q (as [0]) and q-4 (as [1])
                inc_rows = [{
                    'date': income_statement[idx]['date'],
                    'EBIT': ebit_ttm,
                    'Income Tax Expense': tax_ttm,
                    'Earnings before Tax': ebt_ttm,
                }]
                # pad a 2nd row to satisfy slices (not used for EBIT/Tax/EBT)
                inc_rows.append(inc_rows[0].copy())

                cf_rows = [{
                    'date': cashflow_statement[idx]['date'],
                    'Depreciation & Amortization': da_ttm,
                    'Capital Expenditure': capex_ttm,
                }]
                cf_rows.append(cf_rows[0].copy())

                # Keep the actual balance rows (q and q-4) so the DCF's ΔWC formula reads the correct CA proxy.
                bs_rows = [balance_statement[idx], balance_statement[idx+4]]

                dcf = DCF(
                    ticker,
                    ev_stmt,
                    inc_rows,
                    bs_rows,
                    cf_rows,
                    discount_rate,
                    forecast,
                    earnings_growth_rate,
                    cap_ex_growth_rate,
                    perpetual_growth_rate
                )

            else:
                # Original annual path: need at least 2 rows for ΔWC
                if (idx + 1) >= len(balance_statement):
                    print(f"Interval {idx} unavailable (need 2 annual BS rows).")
                    raise IndexError("Not enough annual rows")
                dcf = DCF(
                    ticker,
                    ev_stmt,
                    income_statement[idx:idx+2],   # IS: [t, t-1] (only [0] used for EBIT/tax)
                    balance_statement[idx:idx+2],  # BS: [t, t-1] (used for ΔWC)
                    cashflow_statement[idx:idx+2], # CF: [t, t-1] (only [0] used for D&A/CapEx)
                    discount_rate,
                    forecast,
                    earnings_growth_rate,
                    cap_ex_growth_rate,
                    perpetual_growth_rate
                )

        except (Exception, IndexError):
            print(traceback.format_exc())
            print('Interval {} unavailable, no historical statement.'.format(idx))
        else:
            dcfs[dcf['date']] = dcf
        print('-' * 60)

    return dcfs


def ulFCF(ebit, tax_rate, non_cash_charges, cwc, cap_ex):
    """
    Unlevered Free Cash Flow to Firm:

      FCFF = EBIT * (1 - tax_rate) + D&A + ΔWC + CapEx

    NOTE: In this project CapEx and ΔWC are **added**.
          That means outflows should be **negative** in the data layer
          (so they reduce FCFF). Ensure your data layer’s CapEx sign matches this.
    """
    return ebit * (1 - tax_rate) + non_cash_charges + cwc + cap_ex


def get_discount_rate():
    """
    Placeholder for WACC. CLI provides --d so we don’t compute it here.
    """
    return .1  # TODO: implement if you want dynamic WACC


def equity_value(enterprise_value, enterprise_value_statement):
    """
    Equity = EV - Debt + Cash ;  Price = Equity / SharesOutstanding
    """
    equity_val = enterprise_value - enterprise_value_statement['+ Total Debt']
    equity_val += enterprise_value_statement['- Cash & Cash Equivalents']
    share_price = equity_val / float(enterprise_value_statement['Number of Shares'])
    return equity_val, share_price


def enterprise_value(income_statement, cashflow_statement, balance_statement,
                     period, discount_rate, earnings_growth_rate,
                     cap_ex_growth_rate, perpetual_growth_rate):
    """
    EV = NPV(explicit FCFF over 'period' years) + NPV(Terminal Value)
    All discounted at WACC, end-of-year convention (no mid-year adjustment).
    """
    # --- Inputs from most recent row (index 0) ---
    # EBIT (prompt if missing)
    if income_statement[0].get('EBIT') is not None:
        ebit = float(income_statement[0]['EBIT'])
    else:
        ebit = float(input(f"EBIT missing. Enter EBIT on {income_statement[0]['date']} or skip: "))

    # Effective tax rate = Tax / EBT (guard against /0 and None)
    tax_exp = float(income_statement[0].get('Income Tax Expense', 0.0) or 0.0)
    ebt_val = float(income_statement[0].get('Earnings before Tax', 0.0) or 0.0)
    tax_rate = (tax_exp / ebt_val) if ebt_val not in (0.0, 0) else 0.0

    # D&A
    non_cash_charges = float(cashflow_statement[0].get('Depreciation & Amortization', 0.0) or 0.0)

    # ΔWC using Current Assets proxy = (TA - TNCA)
    ca_now = (float(balance_statement[0].get('Total assets', 0.0) or 0.0) -
              float(balance_statement[0].get('Total non-current assets', 0.0) or 0.0))
    ca_prev = (float(balance_statement[1].get('Total assets', 0.0) or 0.0) -
               float(balance_statement[1].get('Total non-current assets', 0.0) or 0.0))
    cwc = ca_now - ca_prev

    # CapEx (respect sign from data layer)
    cap_ex = float(cashflow_statement[0].get('Capital Expenditure', 0.0) or 0.0)

    discount = discount_rate

    flows = []

    # --- Forecast & discount ---
    print('Forecasting flows for {} years out, starting at {}.'.format(period, income_statement[0]['date']),
          ('\n         DFCF   |    EBIT   |    D&A    |    CWC     |   CAP_EX   |'))

    for yr in range(1, period + 1):
        # increment each value by growth rate (linear, not compounding)
        ebit = ebit * (1 + (yr * earnings_growth_rate))
        non_cash_charges = non_cash_charges * (1 + (yr * earnings_growth_rate))
        cwc = cwc * 0.7  # decay working capital change (project-specific heuristic)
        cap_ex = cap_ex * (1 + (yr * cap_ex_growth_rate))

        # discount by WACC
        flow = ulFCF(ebit, tax_rate, non_cash_charges, cwc, cap_ex)
        PV_flow = flow / ((1 + discount) ** yr)
        flows.append(PV_flow)

        print(str(int(income_statement[0]['date'][0:4]) + yr) + '  ',
              '%.2E' % Decimal(PV_flow) + ' | ',
              '%.2E' % Decimal(ebit) + ' | ',
              '%.2E' % Decimal(non_cash_charges) + ' | ',
              '%.2E' % Decimal(cwc) + ' | ',
              '%.2E' % Decimal(cap_ex) + ' | ')

    NPV_FCF = sum(flows)

    # Terminal value (project’s original convention: uses discounted flow as base and discounts TV an extra year)
    final_cashflow = flows[-1] * (1 + perpetual_growth_rate)
    TV = final_cashflow / (discount - perpetual_growth_rate) if discount != perpetual_growth_rate else 0.0
    NPV_TV = TV / (1 + discount) ** (1 + period)

    return NPV_TV + NPV_FCF
