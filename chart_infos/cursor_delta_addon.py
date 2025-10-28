# cursor_deltas_addon.py
from bokeh.models import ColumnDataSource, CustomJS, Div
import pandas as pd
def _mk_src(records):
    if not records:
        return ColumnDataSource(dict(x0=[], y0=[], x1=[], y1=[], x0ms=[], x1ms=[], m=[], b=[], x_end=[]))
    # precompute slope/intercept in JS-time (ms)
    out = {k: [] for k in ["x0","y0","x1","y1","x0ms","x1ms","m","b","x_end"]}
    for x0, y0, x1, y1 in records:
        x0ms = int(pd.to_datetime(x0).value // 10**6)
        x1ms = int(pd.to_datetime(x1).value // 10**6)
        if x1ms == x0ms:  # skip verticals
            continue
        m = (float(y1) - float(y0)) / (x1ms - x0ms)
        b = float(y0) - m * x0ms
        out["x0"].append(pd.to_datetime(x0)); out["y0"].append(float(y0))
        out["x1"].append(pd.to_datetime(x1)); out["y1"].append(float(y1))
        out["x0ms"].append(x0ms); out["x1ms"].append(x1ms)
        out["m"].append(m); out["b"].append(b)
        out["x_end"].append(max(x0ms, x1ms))
    return ColumnDataSource(out)

# ---- PUBLIC API ----


def build_sources(res_segments, sup_segments):
    """
    res_segments / sup_segments: list of tuples (x0, y0, x1, y1)
      x* may be pandas/np/py datetime; y* floats.
    returns: (res_src, sup_src)
    """
    return _mk_src(res_segments), _mk_src(sup_segments)

def attach_cursor_panel(fig, res_src, sup_src, candle_src, below_layout=None):
    """
    Adds a live panel that shows Δ% vs previous RES and previous SUP at mouse cursor.
    - fig: existing Bokeh figure
    - res_src, sup_src: ColumnDataSource from build_sources(...)
    - candle_src: ColumnDataSource containing candlestick data with 'Date', 'High', 'Low', 'Close'
    - below_layout: optional layout (e.g., column/row) to which the panel Div is already added.
                    If None, returns the Div so you can place it yourself.
    """
    info = Div(text="<b>Hover over candlesticks…</b>", height=24, styles={"font-family": "monospace", "font-size": "14px"})
    cb = CustomJS(args=dict(res=res_src, sup=sup_src, candles=candle_src, div=info), code="""
        const x = cb_obj.x;

        // Get the candlestick index and price at cursor position
        const candleIdx = Math.round(x);
        const candleData = candles.data;

        if (candleIdx < 0 || candleIdx >= candleData['Date'].length) {
            div.text = '<b>Hover over candlesticks…</b>';
            return;
        }

        const candleDate = candleData['Date'][candleIdx];
        const candleHigh = candleData['High'][candleIdx];
        const candleLow = candleData['Low'][candleIdx];
        const candleClose = candleData['Close'][candleIdx];

        function yPrevAtDate(src, dateMs) {
            const d = src.data, n = d['x_end'].length;
            let best = -Infinity, yAt = null;
            for (let i = 0; i < n; i++) {
                const xe = d['x_end'][i];
                if (dateMs >= xe && xe > best) {   // 'previous' = line that ENDED before this candle
                    best = xe;
                    yAt = d['m'][i] * dateMs + d['b'][i];
                }
            }
            return yAt;
        }

        function pctDelta(y, yref) {
            if (yref === null || !isFinite(yref) || yref === 0) return '—';
            const p = (y - yref) / yref * 100.0;
            const sign = p >= 0 ? '+' : '';
            return sign + p.toFixed(2) + '%';
        }

        const yRes = yPrevAtDate(res, candleDate);
        const ySup = yPrevAtDate(sup, candleDate);

        // Calculate percentage from close price to previous resistance and support
        const pctToRes = pctDelta(candleClose, yRes);
        const pctToSup = pctDelta(candleClose, ySup);

        div.text = `<b>Close: ${candleClose.toFixed(2)}</b> &nbsp; | &nbsp; <b>Δ vs prev RES:</b> ${pctToRes} &nbsp; | &nbsp; <b>Δ vs prev SUP:</b> ${pctToSup}`;
    """)
    fig.js_on_event("mousemove", cb)
    if below_layout is None:
        return info
    else:
        below_layout.children.push(info)
        return info  # still return reference
