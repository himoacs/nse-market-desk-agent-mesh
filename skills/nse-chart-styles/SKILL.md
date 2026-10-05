---
name: nse-chart-styles
description: >-
  House style and ready-to-fill Plotly templates for the NSE market desk:
  sector rotation quadrant, sector returns bars, breadth trend, top movers,
  stock comparison and live sector tilt. Load before making any chart.
tags: [nse, charts, plotly, style]
---

# NSE desk chart styles

Every chart is rendered with `create_chart_from_plotly_config`:

- `config_content`: the Plotly figure as a JSON string (`{"data": [...], "layout": {...}}`)
- `config_format`: `json`
- `output_filename`: a specific name ending in `.png`, e.g. `sector_rotation_quadrant_2026-10-01.png`
- `output_format`: `png`

## Workflow

1. Identify the chart type from the request and the data you were given
   (see the table below). One chart per request unless asked for more.
2. Read the data artifact with `load_artifact` (CSV from the analyst, or a raw
   NSE JSON response from the market data agent). Use only its numbers.
3. Copy the matching template from `references/plotly-templates.md`, fill in the
   arrays, title, subtitle and the footer's as-of date, then render.
4. Reply with the image filename and a one-line caption that states the data
   window or as-of time. Do not interpret the market beyond the caption.

| Request / data | Template |
|---|---|
| sector_rotation.csv, "rotation", "quadrant", "leading/lagging sectors" | `rotation_quadrant` (default for rotation) |
| sector_rotation.csv, "sector returns", "1M vs 3M" | `sector_returns_bar` |
| breadth_trend.csv, "breadth", "advance/decline" | `breadth_trend` |
| top movers (get_top_movers / nse_get_market_movers JSON), "gainers/losers" | `top_movers_bar` |
| compare_stocks JSON, "compare X, Y, Z" | `stock_compare` |
| live_sector_tilt.csv, "sectors today/right now" | `live_sector_tilt` |

## House style (non-negotiable)

- Up / positive: `#1a9850`. Down / negative: `#d73027`. Neutral / benchmark: `#4d4d4d`.
  Accent for a second series: `#2c7fb8`.
- Canvas 1200 x 700, white background, font family "Inter, Arial, sans-serif", size 14.
- Title: what the chart shows. Subtitle (second line of the title, smaller): window or as-of time.
- Percentages to 2 decimals with a `%` suffix; zero lines visible.
- Footer annotation on every chart: `Source: NSE MCP · as of <date or time> · informational/educational use only`.
- Sort bars so the story reads top to bottom (best first) unless time-ordered.
- No 3D, no pie charts, no dual axes except the breadth trend's A/D ratio line.
- Keep the config compact: at most ~60 points per series (downsample daily data
  to weekly). Long configs get truncated and the render fails.
