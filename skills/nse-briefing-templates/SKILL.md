---
name: nse-briefing-templates
description: >-
  How the NSE desk Briefing Writer produces the pre-market note and the
  end-of-day (EOD) wrap: which desk agents to ask for what (in parallel),
  the section templates, the house writing style, and how to publish the note
  as chat markdown plus a PDF with embedded charts. Load before writing a note.
tags: [nse, briefing, pre-market, eod, pdf]
---

# NSE desk briefings

Two products, each with a fixed template in `references/`:

| Product | When | Data | Template |
|---|---|---|---|
| Pre-market note | before 09:15 IST, about the previous session | end-of-day (bhavcopy) | `references/pre-market-note.md` |
| EOD wrap | after 15:30 IST, about today's session | live board (final crawl) | `references/eod-wrap.md` |

If the request does not say which, pick by time of day (IST): before 12:00 means
the pre-market note, otherwise the EOD wrap. "Tomorrow's note" means the
pre-market note.

## Step 1: gather (delegate everything, in parallel, in ONE turn)

Each template lists exactly what to ask the Analyst, the Market Data agent and
the Chart Studio. Send the Analyst and Market Data requests in the same turn.
When the Analyst's CSVs come back, send ONE Chart Studio request asking for all
the template's charts, passing the CSV and JSON artifacts it needs.

If a piece fails, write the note without it and say "data unavailable" in that
section; never fill gaps from memory.

## Step 2: write

- Lead with a one-sentence headline stating the single most important fact.
- Numbers first, adjectives second. Use the exact figures from the agents'
  replies and CSVs; give % to 2 decimals and A/D ratios to 2 decimals.
- Short sections, short bullets. The whole note fits on two printed pages.
- Describe what happened and what the data shows. No buy/sell calls, no targets,
  no forecasts.
- Always state the data date (end-of-day) or crawl time (live).
- Data notes are about the data only (dates, coverage, flags, unavailable
  pieces). Never mention your own process: retries, which agent did what,
  whether charts were visually checked.
- End with the disclaimer from the template, verbatim.

## Step 3: publish (write the note once)

1. Write the full note as ONE markdown artifact named `<product>_<date>.md`
   (e.g. `pre_market_note_2026-10-06.md`, `eod_wrap_2026-10-05.md`):
   - first line `# <Title>` (e.g. `# Pre-market note: Tuesday 6 October 2026`),
     then the headline as a bold paragraph, then the template sections as `##` headings;
   - place each chart where it belongs as `![<caption>](<chart filename>.png)`.
2. Call `render_note_html` with `note` = that markdown artifact, `charts` = every
   chart PNG the note references, `product` = "Pre-market note" or "EOD wrap".
   It returns `<product>_<date>.html` with the charts embedded. If it reports
   missing charts, pass them and call it again.
3. Call `html_to_pdf` with `input_document` = that HTML artifact,
   `output_filename` = `<product>_<date>.pdf`, `page_size` = `a4`.
4. Reply in chat with a SHORT version (do not repeat the whole note):
   - the title and the bold headline;
   - 4-6 bullets with the key numbers (one per section);
   - each chart shown with `«artifact_return:<chart filename>»`;
   - the PDF with `«artifact_return:<pdf filename>»` and the markdown note with
     `«artifact_return:<md filename>»`.
5. If `html_to_pdf` fails, return the HTML artifact instead and say so in one line.
