# bokeh_cursor_deltas.py
from bokeh.plotting import figure, show, output_file
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, HoverTool, CrosshairTool, CustomJS, Div
import pandas as pd
import numpy as np

def _to_ms(ts):
    # Convert pandas/np datetime to JS milliseconds since epoch
    return int(pd.to_datetime(ts).value // 10**6)

def plot_with_prev_deltas(df, trendlines, title="Trendlines with Δ% panel",
                          outfile="trend_with_deltas.html"):
    """
    df: pandas.DataFrame with columns ['Date','Open','High','Low','Close'] and Date tz-naive or tz-aware.
        Must be ascending by Date.
    trendlines: list of dicts like:
        {'kind': 'res'|'sup', 'x0': Timestamp, 'y0': float, 'x1': Timestamp, 'y1': float}
        (Adapt mapping from pytrendline results—see note below.)

    Creates an interactive HTML where moving the cursor shows:
      - % change from the previous resistance at cursor x
      - % change from the previous support at cursor x
    """
    # --- Clean time
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_convert(None)
    df = df.sort_values("Date").reset_index(drop=True)

    # --- Candles source (basic OHLC render)
    cds = ColumnDataSource({
        "date": df["Date"],
        "open": df["Open"].astype(float),
        "high": df["High"].astype(float),
        "low": df["Low"].astype(float),
        "close": df["Close"].astype(float),
    })

    # --- Build line sources (and JS-ready slope/intercept in ms space)
    res_lines, sup_lines = [], []
    for tl in trendlines:
        x0ms = _to_ms(tl["x0"]); x1ms = _to_ms(tl["x1"])
        y0   = float(tl["y0"]);  y1   = float(tl["y1"])
        if x1ms == x0ms:
            continue
        m = (y1 - y0) / (x1ms - x0ms)
        b = y0 - m * x0ms
        rec = dict(
            x0=pd.to_datetime(tl["x0"]),
            y0=y0,
            x1=pd.to_datetime(tl["x1"]),
            y1=y1,
            x0ms=x0ms,
            x1ms=x1ms,
            m=m,
            b=b,
            x_end=max(x0ms, x1ms),
        )
        (res_lines if tl["kind"] == "res" else sup_lines).append(rec)

    def _mk_source(recs):
        if not recs:
            # Empty-but-valid source to keep JS simple
            return ColumnDataSource(dict(x0=[], y0=[], x1=[], y1=[], x0ms=[], x1ms=[], m=[], b=[], x_end=[]))
        return ColumnDataSource({k: [r[k] for r in recs] for k in recs[0].keys()})

    res_src = _mk_source(res_lines)
    sup_src = _mk_source(sup_lines)

    # --- Figure
    p = figure(title=title, x_axis_type="datetime", width=1100, height=520,
               tools="pan,wheel_zoom,reset,save")
    p.add_tools(CrosshairTool(dimensions="both"))

    # --- Candlesticks (simple)
    w = (df["Date"].iloc[1] - df["Date"].iloc[0]).total_seconds() * 1000 if len(df) > 1 else 24*3600*1000
    p.segment("date", "high", "date", "low", source=cds)
    inc = df["Close"] >= df["Open"]
    dec = ~inc
    inc_src = ColumnDataSource(df.loc[inc, ["Date","Open","Close"]].rename(columns={"Date":"date"}))
    dec_src = ColumnDataSource(df.loc[dec, ["Date","Open","Close"]].rename(columns={"Date":"date"}))
    p.vbar("date", w*0.6, "open", "close", source=inc_src)  # up bars
    p.vbar("date", w*0.6, "open", "close", source=dec_src)  # down bars

    # --- Trendlines
    p.segment("x0", "y0", "x1", "y1", source=res_src, line_width=2)  # resistance
    p.segment("x0", "y0", "x1", "y1", source=sup_src, line_width=2)  # support

    # --- Usual hover on candles (date/close)
    p.add_tools(HoverTool(
        tooltips=[("Date", "@date{%F}"), ("Close", "@close{0.000}")],
        formatters={"@date": "datetime"},
        mode="vline",
        renderers=[]
    ))

    # --- Live Δ% display
    info = Div(text="<b>Move mouse over the chart</b>",
               width=700, height=24, styles={"font-family": "monospace"})

    callback = CustomJS(args=dict(res=res_src, sup=sup_src, div=info), code="""
        const x = cb_obj.x, y = cb_obj.y;
        function prevY(src) {
            const d = src.data; const n = d['x_end'].length;
            let best = -Infinity, yAt = null;
            for (let i = 0; i < n; i++) {
                const x_end = d['x_end'][i];
                if (x >= x_end && x_end > best) {
                    best = x_end;
                    yAt = d['m'][i] * x + d['b'][i];
                }
            }
            return yAt;  // may be null if none
        }
        function pct(y, yref){
            if (yref === null || !isFinite(yref) || yref === 0) return '—';
            const p = (y - yref) / yref * 100.0;
            const sign = p > 0 ? '+' : '';
            return sign + p.toFixed(2) + '%';
        }
        const yRes = prevY(res);
        const ySup = prevY(sup);
        const text = `<b>Δ vs prev RES:</b> ${pct(y, yRes)} &nbsp; | &nbsp; <b>Δ vs prev SUP:</b> ${pct(y, ySup)}`;
        div.text = text;
    """)
    p.js_on_event("mousemove", callback)

    output_file(outfile)
    show(column(p, info))

