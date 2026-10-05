# Pre-market note template

Purpose: a 2-minute read before the open on what the previous session and the
last 1-3 months say about breadth, sector leadership and momentum.

## Gather (one turn, in parallel)

**Ask the Analyst (nse_market_analyst):**
> "For the pre-market note: run the sector rotation and momentum analysis
> (1M vs 3M) and the breadth trend for the last ~5 sessions. Return your summary
> and the CSV artifact names (sector_rotation.csv, momentum_ranking.csv,
> breadth_trend.csv)."

**Ask Market Data (nse_market_data):**
> "For the latest end-of-day session (date 'today'): get_top_movers direction
> gain n=15, get_top_movers direction loss n=15, and get_top_by_volume sortBy
> value n=10, in parallel. Return the artifact filename for each call."

Movers lists include bonds and debt series. Use only equity symbols: drop any
symbol that starts with a digit (e.g. `1275DCC28`) or contains a hyphen suffix
such as `-RE` (rights entitlements), then keep the top 5 each way.

**Then ask the Chart Studio (nse_chart_studio)**, passing sector_rotation.csv,
breadth_trend.csv and the two top-movers artifacts:
> "Make three charts: (1) rotation_quadrant from sector_rotation.csv,
> (2) breadth_trend from breadth_trend.csv, (3) top_movers_bar combining the
> gainers and losers artifacts, equity symbols only (skip symbols starting with
> a digit or ending in -RE), top 5 each way. As-of date <session date>."

## Sections

1. **Headline**: one sentence (e.g. "Breadth collapsed to 0.33 as Auto led a broad sell-off; IT keeps 3-month leadership").
2. **Yesterday in numbers**: session date; advances / declines / unchanged; A/D ratio and regime; direction vs prior sessions. Chart: breadth trend.
3. **Sector rotation**: benchmark 1M / 3M; table of sectors with 1M RS, 3M RS, quadrant (Leading first); 2-3 bullets on what moved between quadrants. Chart: rotation quadrant.
4. **Momentum leaders and laggards**: top 5 and bottom 5 by 3M return with 1M return; mention "accelerating" names in one line.
5. **Biggest movers yesterday**: top gainers and losers (symbol, % change) and the most active by value. Chart: top movers. Note any loser down more than 20%: possibly a corporate action (prices are unadjusted).
6. **Data notes**: windows, coverage (x/50 stocks), any flagged stocks or failed data pieces.
7. **Disclaimer** (verbatim): "Source: NSE MCP (end-of-day bhavcopy data). For informational and educational purposes only; not investment advice. Prices are unadjusted for corporate actions. Sector groupings are the desk's own mapping of NSE industry classifications."
