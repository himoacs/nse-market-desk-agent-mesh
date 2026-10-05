"""SAM tool entry points for the NSE market desk analyst.

Each function is wrapped with ``tool_cli`` and exposed as a console script in
pyproject.toml; manifest.yaml points each tool at its script. Artifact
parameters receive the raw NSE MCP responses that the Market Data agent saved;
``parsing.extract_payload`` copes with whichever envelope they were saved in.

Annotations must stay real objects (no ``from __future__ import annotations``):
the SDK detects ``List[Artifact]`` parameters with ``typing.get_origin``.
Every tool also takes a ``ctx: SandboxToolContextFacade`` parameter: without
an annotated Artifact or context parameter the SDK falls back to "legacy
injection" and passes the context as a positional argument.
"""

from typing import List

from sam_tool_sdk import Artifact, DataDisposition, DataObject, SandboxToolContextFacade, ToolResult, tool_cli

from . import live, rotation, universe
from .parsing import extract_payload


def _payloads(artifacts: List[Artifact], label: str) -> List[dict]:
    out = []
    for art in artifacts or []:
        try:
            out.append(extract_payload(art.content))
        except ValueError as exc:
            raise ValueError(f"{label}: could not read {art.filename}: {exc}") from exc
    return out


def _csv_objects(csvs: dict, description: str) -> List[DataObject]:
    return [
        DataObject(name=name, content=text, mime_type="text/csv",
                   disposition=DataDisposition.ARTIFACT, description=description)
        for name, text in csvs.items()
    ]


def _without_csv(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "csv"}


async def get_nifty50_universe(ctx: SandboxToolContextFacade = None) -> ToolResult:
    """List the NIFTY 50 constituents by desk sector, plus ready-made symbol batches for compare_stocks.

    NSE's MCP servers have no sector data; this is the desk's mapping built from
    the official niftyindices.com constituent list. Use compare_batches to request
    compare_stocks from the Market Data agent (each batch has at most 10 symbols).
    """
    rows = universe.load_universe()
    return ToolResult.ok(
        message=f"NIFTY 50 universe as of {universe.CONSTITUENTS_AS_OF}: {len(rows)} stocks in "
                f"{len(universe.sectors(rows))} desk sectors, {len(universe.compare_batches(rows))} compare batches.",
        data={
            "as_of": universe.CONSTITUENTS_AS_OF,
            "sectors": universe.sectors(rows),
            "compare_batches": universe.compare_batches(rows),
        },
    )


async def sector_rotation(compare_1m: List[Artifact], compare_3m: List[Artifact],
                          ctx: SandboxToolContextFacade = None) -> ToolResult:
    """Sector rotation and momentum ranking for the NIFTY 50 from compare_stocks results.

    Computes equal-weighted 1-month and 3-month sector returns, relative strength
    versus the NIFTY 50 equal-weight benchmark, and a Leading / Weakening /
    Improving / Lagging quadrant per sector. Flags likely corporate-action
    distortions (unadjusted prices). Saves sector_rotation.csv and momentum_ranking.csv.

    Args:
        compare_1m: artifact filenames holding compare_stocks responses with months=1, one per symbol batch
        compare_3m: artifact filenames holding compare_stocks responses with months=3, one per symbol batch
    """
    if ctx is not None:
        ctx.send_status(f"Computing sector rotation from {len(compare_1m or [])}+{len(compare_3m or [])} compare_stocks files")
    try:
        result = rotation.sector_rotation(
            universe.load_universe(),
            _payloads(compare_1m, "compare_1m"),
            _payloads(compare_3m, "compare_3m"),
        )
    except ValueError as exc:
        return ToolResult.error(str(exc), code="BAD_INPUT")
    q = result["quadrants"]
    return ToolResult.ok(
        message=(f"Sector rotation over {result['coverage']['included']}/{result['coverage']['universe']} stocks. "
                 f"Leading: {', '.join(q['Leading']) or 'none'}. Lagging: {', '.join(q['Lagging']) or 'none'}."),
        data=_without_csv(result),
        data_objects=_csv_objects(result["csv"], "NSE market desk sector rotation output"),
    )


async def breadth_trend(breadth: List[Artifact], ctx: SandboxToolContextFacade = None) -> ToolResult:
    """Advance/decline breadth trend from several get_market_breadth results.

    Dedupes by trading date (holidays and 'today' resolve to the previous
    session), sorts oldest to newest, labels each session's regime
    (A/D >= 1.5 broad strength, <= 0.67 broad weakness, else mixed) and
    whether breadth is improving or deteriorating. Saves breadth_trend.csv.

    Args:
        breadth: artifact filenames holding get_market_breadth responses, one per date
    """
    if ctx is not None:
        ctx.send_status(f"Computing breadth trend from {len(breadth or [])} sessions")
    try:
        result = rotation.breadth_trend(_payloads(breadth, "breadth"))
    except ValueError as exc:
        return ToolResult.error(str(exc), code="BAD_INPUT")
    latest = result["latest"]
    return ToolResult.ok(
        message=(f"Breadth over {result['sessions']} sessions: latest {latest['date']} A/D {latest['ad_ratio']} "
                 f"({latest['regime']}), {result['direction']}."),
        data=_without_csv(result),
        data_objects=_csv_objects(result["csv"], "NSE market desk breadth trend"),
    )


async def live_sector_tilt(gainers: Artifact, losers: Artifact,
                           ctx: SandboxToolContextFacade = None) -> ToolResult:
    """Live intraday sector tilt for the NIFTY 50 from the cm-market live board.

    Maps the NIFTY segment of cm_get_live_market_data (index 'gainers' and
    'loosers') to desk sectors and averages each sector's live % change.
    The live board only lists the top 20 gainers and top 20 losers, so the
    result reports coverage. Saves live_sector_tilt.csv.

    Args:
        gainers: artifact filename holding the cm_get_live_market_data response for index=gainers
        losers: artifact filename holding the cm_get_live_market_data response for index=loosers
    """
    if ctx is not None:
        ctx.send_status("Mapping the live NIFTY 50 board to sectors")
    try:
        result = live.live_sector_tilt(
            universe.load_universe(),
            extract_payload(gainers.content),
            extract_payload(losers.content),
        )
    except ValueError as exc:
        return ToolResult.error(str(exc), code="BAD_INPUT")
    top, bottom = result["sectors"][0], result["sectors"][-1]
    return ToolResult.ok(
        message=(f"Live tilt as of {result['as_of']} ({result['coverage']['seen']}/50 seen): strongest "
                 f"{top['sector']} {top['avg_change_pct']:+.2f}%, weakest {bottom['sector']} {bottom['avg_change_pct']:+.2f}%."),
        data=_without_csv(result),
        data_objects=_csv_objects(result["csv"], "NSE market desk live sector tilt"),
    )


cli_universe = tool_cli(get_nifty50_universe)
cli_sector_rotation = tool_cli(sector_rotation)
cli_breadth_trend = tool_cli(breadth_trend)
cli_live_sector_tilt = tool_cli(live_sector_tilt)
