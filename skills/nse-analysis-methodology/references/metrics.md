# Metric definitions and thresholds

These match the `nse_analytics` toolset code exactly (toolsets/nse_analytics).

## Universe and sectors

- Universe: the 50 NIFTY 50 constituents from the official niftyindices.com list.
- NSE's MCP servers carry no sector data. The desk groups NSE's `Industry`
  classification into 11 desk sectors: Banks, Financials ex-Banks, IT, Auto,
  Pharma & Healthcare, FMCG, Metals & Mining, Energy & Power (oil, gas, coal,
  power), Consumer (durables + consumer services), Infra & Industrials
  (construction, cement, capital goods, ports, airlines) and Telecom (one stock).

## Sector rotation (end-of-day, from compare_stocks)

| Metric | Definition |
|---|---|
| Stock return (1M, 3M) | `return_pct` from compare_stocks with months=1 / months=3 (close to close, unadjusted) |
| Benchmark | Equal-weighted mean return of all included constituents ("NIFTY 50 equal-weight"); this is not the cap-weighted index level |
| Sector return | Equal-weighted mean return of the sector's included constituents |
| Relative strength (RS) | Sector return minus benchmark return, in percentage points, per lookback |
| Acceleration | 1M return minus (3M return / 3): is the latest month faster than the 3-month average pace? |
| Flagged stock | abs(1M) > 35% or abs(3M) > 45%: likely a split/bonus distortion from unadjusted prices; excluded from all averages |

### Quadrants (relative-rotation style)

| Quadrant | Rule | How to describe it |
|---|---|---|
| Leading | RS 3M > 0 and RS 1M > 0 | Outperforming on both horizons; leadership intact |
| Weakening | RS 3M > 0 and RS 1M <= 0 | Was leading, has lost relative momentum this month |
| Improving | RS 3M <= 0 and RS 1M > 0 | Was lagging, has turned up relative to the market this month |
| Lagging | RS 3M <= 0 and RS 1M <= 0 | Underperforming on both horizons |

Typical rotation path: Improving -> Leading -> Weakening -> Lagging. Relative
strength is relative: in a falling market a "Leading" sector may still be down
in absolute terms; say so when the benchmark is negative.

## Breadth (from get_market_breadth)

| Metric | Definition |
|---|---|
| A/D ratio | advances / declines across all NSE cash-market stocks that traded |
| Regime | A/D >= 1.5 broad strength; A/D <= 0.67 broad weakness; otherwise mixed |
| Direction | latest A/D vs the average of the prior sessions: > +10% improving, < -10% deteriorating, else steady |

## Live sector tilt (from cm_get_live_market_data)

- Rows: the NIFTY segment of the live gainers board and losers board (top 20 each).
- Sector tilt: mean live `perChange` of the sector's constituents that appear on either board.
- Coverage: usually ~40 of 50 constituents; the unseen ones are mid-pack movers,
  so averages overstate the extremes. Always report coverage and crawl time.
