# fetcher.py
import argparse
import sys
from typing import List
import pandas as pd
import yfinance as yf


def _flatten_ohlc(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Normalize yfinance output to 1-D OHLCV columns for a single ticker.
    Keeps only ['Open','High','Low','Close','Volume'].
    """
    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        # Prefer slicing by ticker if present as last level
        lv = df.columns.get_level_values(-1)
        if ticker in lv:
            df = df.xs(ticker, axis=1, level=-1, drop_level=True)
        else:
            # Fall back to first level (Open/High/Low/Close/Volume)
            df.columns = df.columns.get_level_values(0)
    else:
        # Sometimes columns come as "AAPL Open" etc. Normalize.
        def _maybe_strip(c: str) -> str:
            parts = c.split(" ")
            if len(parts) >= 2 and parts[0].upper() == ticker.upper():
                return " ".join(parts[1:])
            return c
        df.columns = [_maybe_strip(c) for c in df.columns]

    keep: List[str] = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns after flattening: {missing}. Got: {list(df.columns)}")
    return df[keep]


def build_df(
    ticker: str,
    start: str,
    end: str,
    interval: str,
    tz_out: str = "America/New_York",
    start_idx: int = 0,
    duplicate_index_col: bool = True,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
    Idx, Open, High, Low, Close, Volume, Date
    - Date is tz-naive datetime64[ns] in tz_out (no mixed offsets).
    - Index is duplicated into 'Idx' to match your sample (can be disabled).
    """
    try:
        df = yf.download(
            tickers=ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=False,
            prepost=False,
            progress=False,
            group_by="column",
        )
    except Exception as e:
        # Fallback: try with Ticker object if download fails
        print(f"Download failed, trying alternative method: {e}")
        ticker_obj = yf.Ticker(ticker)
        # Calculate period in days
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        days = (end_dt - start_dt).days
        period = f"{days}d" if days <= 60 else "max"

        df = ticker_obj.history(start=start, end=end, interval=interval, auto_adjust=False)
        if df.empty:
            df = ticker_obj.history(period=period, interval=interval, auto_adjust=False)

    if df.empty:
        raise ValueError(f"No data for {ticker} between {start} and {end} at {interval} interval.")

    df = _flatten_ohlc(df, ticker)

    # Ensure timezone-aware index (UTC) then convert to desired TZ
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df_local = df.tz_convert(tz_out)

    # Make a tz-naive datetime64[ns] column (avoids mixed-offset strings & FutureWarning)
    date_col = df_local.index.tz_localize(None)

    # Build sequential Idx
    n = len(df_local)
    idx_vals = pd.RangeIndex(start=start_idx, stop=start_idx + n, step=1)

    out = pd.DataFrame({
        "Idx": idx_vals,
        "Open": df_local["Open"].to_numpy(),
        "High": df_local["High"].to_numpy(),
        "Low": df_local["Low"].to_numpy(),
        "Close": df_local["Close"].to_numpy(),
        "Volume": pd.to_numeric(df_local["Volume"], errors="coerce").fillna(0).astype("int64").to_numpy(),
        "Date": date_col,  # dtype: datetime64[ns] (tz-naive)
    })

    if duplicate_index_col:
        out.index = out["Idx"]

    # Column order like your sample
    return out[["Idx", "Open", "High", "Low", "Close", "Volume", "Date"]]


def main():
    ap = argparse.ArgumentParser(description="Fetch OHLCV and format Date properly for pytrendline.")
    ap.add_argument("--ticker", required=True, help="e.g., AAPL")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD or full timestamp")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD or full timestamp")
    ap.add_argument("--interval", default="1h", help="1m,2m,5m,15m,30m,60m,90m,1h,1d,...")
    ap.add_argument("--tz-out", default="America/New_York", help="Output timezone for Date (then made tz-naive).")
    ap.add_argument("--start-idx", type=int, default=0, help="Starting Idx value.")
    ap.add_argument("--no-leading-index", action="store_true", help="Do not duplicate index into a leading column.")
    ap.add_argument("--csv", default="", help="Optional CSV path to save. Date will be 'YYYY-MM-DD HH:MM:SS'.")
    ap.add_argument("--parquet", default="", help="Optional Parquet path (preserves datetime dtype).")
    args = ap.parse_args()

    try:
        df = build_df(
            ticker=args.ticker,
            start=args.start,
            end=args.end,
            interval=args.interval,
            tz_out=args.tz_out,
            start_idx=args.start_idx,
            duplicate_index_col=not args.no_leading_index,
        )

        # Preview
        print(df.head().to_string())

        # Save (CSV writes Date as string but tz-naive; Parquet preserves dtype)
        if args.csv:
            df.to_csv(args.csv, index=True, date_format="%Y-%m-%d %H:%M:%S")
            print(f"\nSaved CSV -> {args.csv}")
        if args.parquet:
            df.to_parquet(args.parquet, index=True)
            print(f"Saved Parquet -> {args.parquet}")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
