# NSE Market Desk on Solace Agent Mesh

A five-agent "market desk" for the Indian equity market, built on
[Solace Agent Mesh](https://docs.solace.com/Agentic-AI/agent-mesh.htm) (SAM) and the official
[NSE MCP server](https://www.nseindia.com/nse-mcp). Each agent is one YAML file. The agents find
each other through agent cards on SAM's event broker and delegate work over A2A; there is no
integration code between them. Everything is set up with the `sam` CLI, with no clicking in the UI.

```
You ─► nse_desk_head (orchestrator)
         ├─► nse_market_data ──► NSE MCP (nse_bhavcopy + nse_cm_market connectors)
         ├─► nse_market_analyst ──► nse_market_data      (+ nse_analytics Python toolset)
         ├─► nse_chart_studio                              (built-in Plotly chart tool)
         └─► nse_briefing_writer ──► analyst, market data, chart studio  (+ nse_publishing, html_to_pdf)
```

| Agent | Job | Tools |
|---|---|---|
| `nse_desk_head` | Front door: routes questions, posts a plan and live progress, gives short numbers-first answers | peers only |
| `nse_market_data` | The only agent that talks to NSE; fetches data and saves raw responses as artifacts | 2 NSE MCP connectors (21 tools) |
| `nse_market_analyst` | Sector rotation (1M vs 3M quadrants), momentum, breadth trend, live sector tilt | `nse_analytics` toolset + `nse-analysis-methodology` skill |
| `nse_chart_studio` | PNG charts in a fixed house style | `create_chart_from_plotly_config` + `nse-chart-styles` skill |
| `nse_briefing_writer` | Pre-market note and end-of-day (EOD) wrap, in chat and as a PDF | `nse_publishing` toolset + `html_to_pdf` + `nse-briefing-templates` skill |

## What you need

| Requirement | Notes |
|---|---|
| **SAM Desktop** app | Download from the Solace product portal: **https://products.solace.com/prods/Agent_Mesh** (login required). No portal access? Contact your Solace account team or [solace.com/support](https://solace.com/support). Installers: macOS `.dmg`, Windows `.msi`, Linux `.tar.gz`. |
| **`sam` CLI** | From the same portal page. Put the binary on your `PATH` (e.g. `~/.local/bin/sam`), `chmod +x` it, and check `sam --version`. On macOS you may need `xattr -d com.apple.quarantine ~/.local/bin/sam` the first time. |
| **An LLM API key** | Any OpenAI-compatible endpoint (e.g. a LiteLLM gateway) or a provider SAM supports. Use a strong tool-calling model (Claude Sonnet class or equivalent). **You configure this yourself in `.env`; see step 2.** |
| **Python 3.10+ with `pip`** | `sam config apply` builds the two Python toolsets locally. |
| **git** and network access to `mcp.nseindia.in` | The NSE MCP servers need no account or key. |

Tested with SAM Desktop 2.325.2 and `sam` CLI 2.275.10 on macOS. The helper script that
switches SAM instances (`scripts/sam-desktop.sh`) is macOS-only; everything else is the
`sam` CLI plus Python and works on any OS.

## Quick start

### 1. Install SAM and clone the repo

Install SAM Desktop and the `sam` CLI from the portal (see above), then:

```bash
git clone https://github.com/himoacs/nse-market-desk-agent-mesh.git
cd nse-market-desk-agent-mesh
```

### 2. Configure your LLM

```bash
cp .env.example .env
```

Edit `.env`. It is gitignored; never commit it.

| Variable | Meaning | Example |
|---|---|---|
| `LLM_PROVIDER` | SAM model provider. `custom` = any OpenAI-compatible endpoint (tested). Other SAM providers: `openai`, `anthropic`, `azure_openai`, `bedrock`, `google_ai_studio`, `vertex_ai`, `ollama`. | `custom` |
| `LLM_MODEL_NAME` | Model id as your endpoint names it. With `custom`, prefix it with the API format the endpoint speaks: `anthropic/<model>` or `openai/<model>`. | `anthropic/claude-sonnet-5-5` |
| `LLM_API_BASE` | Base URL of your endpoint, **without** a trailing `/v1` | `https://litellm.mycompany.com` |
| `LLM_API_KEY` | Your key | `sk-...` |

These values feed `models/nse_sonnet.yaml` (used by the desk agents) and SAM's own
`general` / `planning` models (`models/general.yaml`, `models/planning.yaml`). Declaring the
latter in config means a fresh SAM instance needs no onboarding screen.

Only the LiteLLM / OpenAI-compatible (`custom`) path has been tested end to end. If you use
another provider, check that `sam config plan` resolves your variables and that the first
test prompt (step 5) gets an answer.

### 3. Start a dedicated SAM instance

SAM keeps all state (agents, connectors, models, chats, files, logs) in a *home* directory.
Running the desk in its own home keeps it separate from anything else you have built in SAM.

**macOS:**

```bash
scripts/sam-desktop.sh nse        # quits SAM if running, relaunches it with SAM_HOME=~/sam-homes/nse-desk
```

The script also turns off SAM's Activity Monitor feature for this instance
(`SAM_FEATURE_ACTIVITY_MONITOR=false`), so the mesh shows only the desk and SAM's Builder.

**Windows / Linux:** start SAM Desktop with the environment variable
`SAM_HOME=<some empty folder>` (and optionally `SAM_FEATURE_ACTIVITY_MONITOR=false`), then
run step 4 with `--use-running-instance`. Or, on a fresh SAM install you don't mind
dedicating to the desk, start SAM normally and pass `--use-running-instance`.

### 4. Apply the desk with the SAM CLI

```bash
scripts/bootstrap.py --remove-builtins
# Windows/Linux or a non-dedicated instance:  scripts/bootstrap.py --use-running-instance --remove-builtins
```

`bootstrap.py` does everything through the `sam` CLI:

1. Runs `sam config apply --target desktop` for every resource in `manifest.yaml`: 3 models,
   2 NSE connectors, 2 Python toolsets (built locally), 3 skills and the 5 agents.
2. Creates or updates the **"NSE Market Desk"** chat project (default agent `nse_desk_head`)
   from `instance/project.json` via `sam api`. `sam config` has no resource kind for projects.
3. Creates or updates two **scheduled tasks** from `instance/scheduled-tasks.json` via `sam api`:
   a pre-market note at 08:30 IST and an EOD wrap at 16:00 IST on weekdays.
4. With `--remove-builtins`: deletes SAM's built-in Orchestrator and Activity Monitor agents.
   The Builder is kept. Leave the flag off to keep them; the Desk Head is the default chat
   agent either way.

It is safe to re-run. By default it refuses to run unless the running SAM was launched with
`~/sam-homes/nse-desk`, so it can't configure the wrong instance by accident.

### 5. Try it

Open SAM Desktop (`http://127.0.0.1:8800`), go to **Projects → NSE Market Desk** (or just start
a new chat; the Desk Head is the default agent) and use the welcome-screen buttons, or type:

| Prompt | What happens | Typical time |
|---|---|---|
| What was NSE market breadth on the latest trading day? | Market Data, one NSE call | ~10s-1m |
| How's the market right now? | Live movers + live sector tilt | ~1m15s |
| Compare HDFC Bank, ICICI Bank and Kotak Mahindra Bank over 6 months, with a chart. | Market Data → Chart Studio | ~1m20s |
| Which NIFTY 50 sectors are leading over 1 month vs 3 months? Show the rotation chart. | Analyst → Market Data (10 parallel NSE calls) → Python analytics → chart | ~2m10s |
| Write tomorrow's pre-market note. | All five agents → 2-page PDF with 3 charts | ~6m30s |
| Write today's EOD wrap. | Live sector tilt + leaders/laggards → PDF | ~3m |

More to try: "Live quote for Reliance", "Top 5 BANK NIFTY gainers and losers right now",
"Where is Infosys relative to its 52-week range?", "Any dividends or splits for Reliance in the
last year?", "How has market breadth trended over the last week?".

While a prompt runs, the chat shows the Desk Head's one-line plan and live status lines
from whichever agent is working. Open the **Activity** panel with **Detail Mode** on to see
the agents hand off to each other.

Live prompts ("right now", "today") are best during market hours, 09:15-15:30 IST. End-of-day
data is the latest session NSE has published (usually the previous trading day until the
evening).

## How it works

- **Data travels as files.** Market Data saves every raw NSE response as an artifact. The
  Analyst's Python tools read those files and write CSVs. Chart Studio turns CSVs into PNGs.
  The Briefing Writer writes the note once as markdown; `render_note_html` turns it into
  styled HTML with the PNGs embedded, and `html_to_pdf` makes the PDF.
- **Deterministic maths.** Returns, relative strength, quadrants and breadth regimes are
  computed by the `nse_analytics` Python toolset, unit-tested on real NSE responses. The LLM
  decides what to fetch and how to explain it, never the arithmetic.
- **No sector data in NSE MCP.** `toolsets/nse_analytics/src/src/nse_analytics/data/nifty50_sectors.csv`
  maps the official NIFTY 50 list (niftyindices.com, as of 2026-10-05) to 11 desk sectors.
  Refresh it after each index rebalance.
- **Static NSE tool list.** The connectors carry NSE's tool definitions as a static manifest,
  so deploys and restarts never wait on NSE's servers, which often time out. The generator
  script also rewrites NSE's "call get_corporate_actions first" instructions; followed
  literally, they add one extra NSE call per stock. The Analyst flags unadjusted-price
  distortions instead.
- **Resilience.** NSE's MCP servers intermittently hang or return 504. The Market Data agent
  retries each failed call up to 3 times and runs independent calls in parallel.

## Repo layout

| Path | What it is |
|---|---|
| `manifest.yaml` | Every declarative resource (`sam config plan/apply`) |
| `models/` | `nse_sonnet` for the desk + the instance's `general` / `planning`, all from `.env` |
| `connectors/` | The two NSE MCP servers, with a static tool manifest (generated) |
| `agents/` | The five agents |
| `skills/` | Methodology, chart styles and briefing templates (loaded on demand) |
| `toolsets/nse_analytics/` | Python analytics + unit tests on recorded NSE responses |
| `toolsets/nse_publishing/` | Markdown note to print-ready HTML with charts inlined |
| `instance/` | The chat project and scheduled tasks (applied by `bootstrap.py` via `sam api`) |
| `scripts/bootstrap.py` | Configure a SAM instance end to end with the `sam` CLI |
| `scripts/sam-desktop.sh` | macOS: switch SAM Desktop between the NSE instance and your default one |
| `scripts/refresh_nse_connectors.py` | Regenerates `connectors/*.yaml` from NSE's `tools/list` |

## Working with the instance

```bash
scripts/sam-desktop.sh status     # which SAM instance is running
scripts/sam-desktop.sh default    # back to your usual SAM instance
scripts/sam-desktop.sh nse        # back to the desk
```

Opening SAM from the Dock or Start menu launches your *default* instance, not the desk.
Use `scripts/sam-desktop.sh nse` (or your own `SAM_HOME` launch) to get the desk.

For other `sam` commands, point the CLI at the desk's home first:

```bash
export SAM_HOME=~/sam-homes/nse-desk
sam config plan --target desktop -v          # read the diff before any apply
sam task send "Live quote for RELIANCE" -a nse_market_data
```

- After you edit any YAML, re-run `scripts/bootstrap.py` (or `sam config apply --target desktop`).
- `apply` never deletes anything unless you pass `--prune`; you shouldn't need it.
- `plan` should show `0 delete` everywhere. A few agents always show `update`: a known
  read-back quirk for `skillRefs` and pass-through `additionalConfigurations` keys. It is harmless.
- Optional, for AI-assisted editing of the config: `sam ai-assistance skill install` writes
  SAM's authoring skills into `.claude/skills/` (gitignored).

### Tests

```bash
sam toolset validate nse_analytics && sam toolset validate nse_publishing
(cd toolsets/nse_analytics/src && python3 -m unittest discover -s tests)
(cd toolsets/nse_publishing/src && python3 -m unittest discover -s tests)
```

The publishing tests use the `markdown` package from the bundle that `sam toolset validate`
builds, so run validate first.

### Refresh the NSE connectors

```bash
python3 scripts/refresh_nse_connectors.py            # live fetch from NSE (retries built in)
python3 scripts/refresh_nse_connectors.py --offline  # rebuild from scripts/nse_tools/
scripts/bootstrap.py
```

## Demo script (~10 minutes; nothing is built live)

| # | Prompt (welcome buttons) | What it shows |
|---|---|---|
| 1 | How's the market right now? | Desk Head → Market Data + Analyst, live NSE MCP |
| 2 | Compare HDFC Bank, ICICI Bank and Kotak Mahindra Bank over 6 months, with a chart. | Artifact hand-off from Market Data to Chart Studio |
| 3 | Which NIFTY 50 sectors are leading over 1 month vs 3 months? Show the rotation chart. | Peer-to-peer delegation, parallel NSE calls, Python tool, chart |
| 4 | Write tomorrow's pre-market note. | The deepest chain, ending in a PDF |
| 5 | Open **Schedules** and show the last EOD wrap run | Autonomous, scheduled agents |

Prompt 4 takes ~6 minutes: start it, then talk through the Activity panel while it runs,
or open the PDF from your rehearsal session. Close by opening `agents/nse_desk_head.yaml`:
it names its peers in an allow list and nothing else. No endpoints, no wiring.

**Before the demo:**
- `scripts/sam-desktop.sh status` shows the NSE instance; `plan` shows no unexpected drift.
- Rehearse the full script about an hour before and keep that chat session open as a backup
  (NSE's servers can add a minute on a slow day).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `bootstrap.py` refuses to run | The running SAM isn't the NSE instance: `scripts/sam-desktop.sh nse`, or pass `--use-running-instance` |
| `sam config plan` complains about an unresolved variable | `.env` is missing one of the `LLM_*` variables (run from the repo root) |
| Agents answer "LLM error" / 401 | Wrong `LLM_API_BASE`, `LLM_API_KEY` or `LLM_MODEL_NAME`; fix `.env` and re-run `bootstrap.py` |
| Market Data says NSE tools aren't connected | Look for `invalid mcp tool config` in the log; regenerate connectors with the refresh script |
| Toolset build fails during apply | Needs `python3` 3.10+ with `pip` on `PATH`; try `sam toolset validate nse_analytics` for details |
| PDF shows broken chart images | The Briefing Writer must use `render_note_html` (it inlines the PNGs); `html_to_pdf` doesn't resolve SAM embeds |
| A tool fails with `takes 0 positional arguments` | Every `nse_analytics` / `nse_publishing` tool needs a `ctx: SandboxToolContextFacade` parameter |
| SAM's Orchestrator / Activity Monitor reappear | They are re-seeded in a brand-new home, and the Activity Monitor at every start unless its feature is off; re-run `bootstrap.py --remove-builtins` |
| Logs | `<SAM_HOME>/diagnostics/logs/desktop.log` (`~/sam-homes/nse-desk/...` for the desk) |

## Data and terms

- Data comes from NSE's MCP servers. NSE states it is for informational and educational
  purposes only: not for real-time trading, commercial deployment or training AI models.
  Every note the desk writes carries a disclaimer, and nothing here is investment advice.
- End-of-day prices are not adjusted for splits or bonuses; the Analyst flags implausible moves.
- The test fixtures under `toolsets/*/src/tests/fixtures/` are small recorded NSE responses,
  kept only to make the analytics tests reproducible.
