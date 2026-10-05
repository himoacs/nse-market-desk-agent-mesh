# Plotly templates

Replace every `<...>` placeholder. Arrays must have matching lengths. Keep the
shared `layout` keys (size, fonts, margins, footer) exactly as shown.

## Shared layout block

Merge these keys into every template's `layout`:

```json
{
  "width": 1200, "height": 700,
  "paper_bgcolor": "#ffffff", "plot_bgcolor": "#ffffff",
  "font": {"family": "Inter, Arial, sans-serif", "size": 14, "color": "#222222"},
  "margin": {"l": 90, "r": 40, "t": 100, "b": 110},
  "annotations": [
    {"text": "Source: NSE MCP · as of <AS_OF> · informational/educational use only",
     "xref": "paper", "yref": "paper", "x": 0, "y": -0.16, "xanchor": "left",
     "showarrow": false, "font": {"size": 11, "color": "#777777"}}
  ]
}
```

Title format (put the window/as-of in the subtitle):

```json
"title": {"text": "<TITLE><br><sup><SUBTITLE></sup>", "x": 0.02, "xanchor": "left"}
```

## rotation_quadrant

x = 3M RS, y = 1M RS (both in percentage points vs the NIFTY 50 equal-weight).
Colour each point by quadrant: Leading `#1a9850`, Weakening `#fdae61`,
Improving `#2c7fb8`, Lagging `#d73027`.

```json
{
  "data": [{
    "type": "scatter", "mode": "markers+text",
    "x": [<RS_3M...>], "y": [<RS_1M...>], "text": [<SECTOR...>],
    "textposition": "top center",
    "marker": {"size": 16, "color": [<QUADRANT_COLOUR...>], "line": {"width": 1, "color": "#333333"}},
    "hovertemplate": "%{text}<br>3M RS %{x:.2f} pp<br>1M RS %{y:.2f} pp<extra></extra>"
  }],
  "layout": {
    "title": {"text": "NIFTY 50 sector rotation<br><sup>Relative strength vs NIFTY 50 equal-weight · 1M <W1> · 3M <W3></sup>", "x": 0.02, "xanchor": "left"},
    "xaxis": {"title": {"text": "3-month relative strength (pp)"}, "zeroline": true, "zerolinewidth": 2, "zerolinecolor": "#999999", "gridcolor": "#eeeeee"},
    "yaxis": {"title": {"text": "1-month relative strength (pp)"}, "zeroline": true, "zerolinewidth": 2, "zerolinecolor": "#999999", "gridcolor": "#eeeeee"},
    "showlegend": false,
    "annotations": [
      {"text": "LEADING", "xref": "paper", "yref": "paper", "x": 0.98, "y": 0.98, "showarrow": false, "xanchor": "right", "font": {"color": "#1a9850", "size": 13}},
      {"text": "WEAKENING", "xref": "paper", "yref": "paper", "x": 0.98, "y": 0.02, "showarrow": false, "xanchor": "right", "font": {"color": "#fdae61", "size": 13}},
      {"text": "IMPROVING", "xref": "paper", "yref": "paper", "x": 0.02, "y": 0.98, "showarrow": false, "xanchor": "left", "font": {"color": "#2c7fb8", "size": 13}},
      {"text": "LAGGING", "xref": "paper", "yref": "paper", "x": 0.02, "y": 0.02, "showarrow": false, "xanchor": "left", "font": {"color": "#d73027", "size": 13}},
      {"text": "Source: NSE MCP · as of <AS_OF> · informational/educational use only", "xref": "paper", "yref": "paper", "x": 0, "y": -0.16, "xanchor": "left", "showarrow": false, "font": {"size": 11, "color": "#777777"}}
    ]
  }
}
```

Keep the axes symmetric around zero (set `range` to +/- the largest absolute
value plus 10%) so the quadrants are the same size.

## sector_returns_bar

```json
{
  "data": [
    {"type": "bar", "name": "1 month", "x": [<SECTOR...>], "y": [<RET_1M...>], "marker": {"color": "#2c7fb8"}, "texttemplate": "%{y:.1f}%", "textposition": "outside"},
    {"type": "bar", "name": "3 months", "x": [<SECTOR...>], "y": [<RET_3M...>], "marker": {"color": "#4d4d4d"}, "texttemplate": "%{y:.1f}%", "textposition": "outside"}
  ],
  "layout": {
    "barmode": "group",
    "title": {"text": "NIFTY 50 sector returns, equal-weighted<br><sup>1M <W1> · 3M <W3> · benchmark 1M <B1>% / 3M <B3>%</sup>", "x": 0.02, "xanchor": "left"},
    "yaxis": {"title": {"text": "Return (%)"}, "ticksuffix": "%", "zeroline": true, "zerolinecolor": "#999999", "gridcolor": "#eeeeee"},
    "legend": {"orientation": "h", "x": 0.6, "y": 1.08}
  }
}
```

Order sectors by 3M relative strength (the analyst CSV is already sorted).

## breadth_trend

```json
{
  "data": [
    {"type": "bar", "name": "Advances", "x": [<DATE...>], "y": [<ADVANCES...>], "marker": {"color": "#1a9850"}},
    {"type": "bar", "name": "Declines", "x": [<DATE...>], "y": [<DECLINES...>], "marker": {"color": "#d73027"}},
    {"type": "scatter", "mode": "lines+markers+text", "name": "A/D ratio", "x": [<DATE...>], "y": [<AD_RATIO...>], "yaxis": "y2",
     "text": [<AD_RATIO_TEXT...>], "textposition": "top center", "line": {"color": "#222222", "width": 3}}
  ],
  "layout": {
    "barmode": "group",
    "title": {"text": "NSE market breadth<br><sup><FIRST_DATE> to <LAST_DATE> · all NSE cash-market stocks</sup>", "x": 0.02, "xanchor": "left"},
    "xaxis": {"type": "category"},
    "yaxis": {"title": {"text": "Stocks"}, "gridcolor": "#eeeeee"},
    "yaxis2": {"title": {"text": "A/D ratio"}, "overlaying": "y", "side": "right", "rangemode": "tozero", "showgrid": false},
    "shapes": [{"type": "line", "xref": "paper", "x0": 0, "x1": 1, "yref": "y2", "y0": 1, "y1": 1, "line": {"dash": "dot", "color": "#999999"}}],
    "legend": {"orientation": "h", "x": 0.55, "y": 1.08}
  }
}
```

## top_movers_bar

Horizontal bars, gainers and losers together, sorted best (top) to worst (bottom).
Plotly draws the first y value at the bottom, so pass rows worst-first.

```json
{
  "data": [{
    "type": "bar", "orientation": "h",
    "x": [<PCT_CHANGE...>], "y": [<SYMBOL...>],
    "marker": {"color": [<GREEN_OR_RED_PER_ROW...>]},
    "texttemplate": "%{x:+.2f}%", "textposition": "outside"
  }],
  "layout": {
    "title": {"text": "<SCOPE> top gainers and losers<br><sup><AS_OF_TEXT></sup>", "x": 0.02, "xanchor": "left"},
    "xaxis": {"title": {"text": "Change (%)"}, "ticksuffix": "%", "zeroline": true, "zerolinecolor": "#999999", "gridcolor": "#eeeeee"},
    "yaxis": {"automargin": true},
    "showlegend": false
  }
}
```

## stock_compare

From a compare_stocks response: `stocks[].symbol`, `return_pct`, `max_drawdown`.
Drawdown is shown as a negative bar so both series read as "good up, bad down".

```json
{
  "data": [
    {"type": "bar", "name": "Return", "x": [<SYMBOL...>], "y": [<RETURN_PCT...>], "marker": {"color": [<GREEN_OR_RED_PER_ROW...>]}, "texttemplate": "%{y:+.2f}%", "textposition": "outside"},
    {"type": "bar", "name": "Max drawdown", "x": [<SYMBOL...>], "y": [<MINUS_MAX_DRAWDOWN...>], "marker": {"color": "#bdbdbd"}, "texttemplate": "%{y:.2f}%", "textposition": "outside"}
  ],
  "layout": {
    "barmode": "group",
    "title": {"text": "<SYMBOLS> over <N> months<br><sup><FROM_DATE> to <TO_DATE> · close-to-close, unadjusted</sup>", "x": 0.02, "xanchor": "left"},
    "yaxis": {"title": {"text": "%"}, "ticksuffix": "%", "zeroline": true, "zerolinecolor": "#999999", "gridcolor": "#eeeeee"},
    "legend": {"orientation": "h", "x": 0.6, "y": 1.08}
  }
}
```

## live_sector_tilt

```json
{
  "data": [{
    "type": "bar", "orientation": "h",
    "x": [<AVG_CHANGE...>], "y": [<SECTOR_WITH_COUNT e.g. "IT (4/4)"...>],
    "marker": {"color": [<GREEN_OR_RED_PER_ROW...>]},
    "texttemplate": "%{x:+.2f}%", "textposition": "outside"
  }],
  "layout": {
    "title": {"text": "NIFTY 50 live sector tilt<br><sup>As of <CRAWL_TIME> IST · <SEEN>/50 stocks on the live gainers/losers board</sup>", "x": 0.02, "xanchor": "left"},
    "xaxis": {"title": {"text": "Average live change (%)"}, "ticksuffix": "%", "zeroline": true, "zerolinecolor": "#999999", "gridcolor": "#eeeeee"},
    "yaxis": {"automargin": true},
    "showlegend": false
  }
}
```

Pass sectors worst-first so the strongest sector is drawn at the top.
