# EOD wrap template

Purpose: a quick recap of today's session from NSE's live board, written after
the close (15:30 IST). End-of-day (bhavcopy) data for today is not published
until later, so this wrap uses the final live crawl.

## Gather (one turn, in parallel)

**Ask the Analyst (nse_market_analyst):**
> "For the EOD wrap: run the live sector tilt for today. Return your summary and
> the live_sector_tilt.csv artifact name."

**Ask Market Data (nse_market_data):**
> "Live data, in parallel: cm_get_data_status; nse_get_market_movers with
> indexName NIFTY limit 5; with indexName BANKNIFTY limit 5; and with
> indexName "" (all securities) limit 10. Return the artifact filename for each
> call and the crawl time."

**Then ask the Chart Studio (nse_chart_studio)**, passing live_sector_tilt.csv
and the NIFTY movers artifact:
> "Make two charts: (1) live_sector_tilt from live_sector_tilt.csv, (2)
> top_movers_bar for the NIFTY 50 gainers and losers. As of <crawl time> IST."

## Sections

1. **Headline**: one sentence on the day (e.g. "Energy and Telecom led a narrow NIFTY 50 session; Pharma lagged across the board").
2. **Session summary**: crawl time; NIFTY 50 up vs down count on the live board; average move of the stocks seen.
3. **Sector tilt today**: sector table (avg % change, up/down, best/worst) with the coverage note. Chart: live sector tilt.
4. **NIFTY 50 and BANK NIFTY leaders and laggards**: top 5 each way with % change. Chart: top movers.
5. **Broad-market movers**: the top gainers/losers across all NSE securities, one line each; flag anything that looks like a circuit-limit or corporate-action move.
6. **Data notes**: crawl time, live board coverage, anything unavailable.
7. **Disclaimer** (verbatim): "Source: NSE MCP (live cash-market snapshot, 1-5 minutes delayed; final end-of-day figures may differ). For informational and educational purposes only; not investment advice. Sector groupings are the desk's own mapping of NSE industry classifications."
