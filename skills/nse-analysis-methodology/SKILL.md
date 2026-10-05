---
name: nse-analysis-methodology
description: >-
  Procedures and metric definitions for the NSE desk analyst: NIFTY 50 sector
  rotation (1M vs 3M relative strength quadrants), momentum ranking, market
  breadth trend, live sector tilt, and how to request the underlying data from
  the NSE Market Data agent. Load before any market analysis.
tags: [nse, analysis, sector-rotation, breadth, momentum]
---

# NSE desk analysis methodology

All numbers come from the **NSE Market Data** agent (it alone talks to NSE)
and are computed by the `nse_analytics` tools. Never compute returns, averages
or ratios in your head; never invent a number. Exact definitions and thresholds
are in `references/metrics.md`; read it when you need to explain a metric.

## Requesting data from Market Data

- Send ONE delegation per analysis that lists every call needed, and ask it to
  make the calls in parallel and return the exact artifact filename for each call.
- The artifacts it returns are raw NSE responses; pass those filenames straight
  into the `nse_analytics` tools. Do not open or retype their contents.
- If some calls failed after retries, run the analysis on what came back and
  state the coverage gap.

## Procedure A: sector rotation and momentum (end-of-day)

Use for "which sectors are leading/lagging", "sector rotation", "momentum leaders".

1. Call `get_nifty50_universe` to get the 5 `compare_batches` (max 10 symbols each).
2. Ask Market Data: "Run compare_stocks for each of these 5 batches with months=1
   and again with months=3 (10 calls, in parallel). Return the artifact filename
   for every call, labelled by batch and months." Paste the batches verbatim.
3. Call `sector_rotation(compare_1m=[the five months=1 files], compare_3m=[the five months=3 files])`.
4. Report: the quadrant table (sector, 1M RS, 3M RS, quadrant), the benchmark
   returns, the top/bottom momentum stocks, and any flagged stocks.

## Procedure B: breadth trend (end-of-day)

Use for "market breadth", "advance/decline", "how broad is the move".

1. Ask Market Data for `get_market_breadth` for date `today` plus each of the
   previous 6 weekdays (yyyy-MM-dd), in parallel. Holidays resolve to the
   previous session and are de-duplicated by the tool.
2. Call `breadth_trend(breadth=[all the files])`.
3. Report latest A/D ratio and regime, direction vs prior sessions, and the per-day table.

## Procedure C: live sector tilt (market hours, 09:15-15:30 IST)

Use for "which sectors are moving today/right now", and for the EOD wrap.

1. Ask Market Data for `cm_get_live_market_data` with index `gainers` AND with
   index `loosers` (NSE's spelling), in parallel.
2. Call `live_sector_tilt(gainers=<gainers file>, losers=<loosers file>)`.
3. Report sector averages with the coverage note (the live board only lists the
   top 20 gainers and top 20 losers of the NIFTY 50) and the crawl time.

## Corporate-action check (only when needed)

NSE end-of-day prices are unadjusted. `sector_rotation` already flags stocks
with implausible moves and excludes them from averages. If a flagged stock, or
a top loser down more than 20% in a day, matters to the answer, ask Market Data
for `get_corporate_actions` for just those symbols and say whether an ex-date
explains the move.

## Output format

- One-line headline with the key finding.
- One compact table (the tool output already has the columns you need).
- 3-5 bullets of interpretation, using the quadrant and regime meanings in
  `references/metrics.md`. Describe; do not give buy/sell advice.
- State the data window or as-of time (from the tool output).
- List the CSV artifact filenames the tool produced, so the Chart Studio or the
  Briefing Writer can use them.
