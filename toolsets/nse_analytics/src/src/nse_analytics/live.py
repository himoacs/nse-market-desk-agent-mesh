"""Live sector tilt from the cm-market live board.

``cm_get_live_market_data`` (index ``gainers`` / ``loosers``) returns, per
segment, the top 20 gainers or losers. For the NIFTY segment that covers up to
40 of the 50 constituents: the two tails of the day's distribution. The ~10
constituents missing from both lists are the middle of the pack, so per-sector
averages here describe the *tilt* of the tape, not exact sector returns.
"""

import csv
import io
from statistics import mean
from typing import Dict, List

from .universe import sector_of


def _segment_rows(payload: dict, segment: str) -> List[dict]:
    data = payload.get("data") or {}
    seg = data.get(segment) or {}
    return list(seg.get("data") or [])


def _segment_ts(payload: dict, segment: str) -> str:
    seg = (payload.get("data") or {}).get(segment) or {}
    return seg.get("timestamp") or payload.get("updatedAt") or ""


def live_sector_tilt(universe_rows: List[Dict[str, str]], gainers: dict, losers: dict,
                     segment: str = "NIFTY") -> dict:
    sec_of = sector_of(universe_rows)
    seen: Dict[str, dict] = {}
    for row in _segment_rows(gainers, segment) + _segment_rows(losers, segment):
        sym = row.get("symbol")
        if sym in sec_of and row.get("perChange") is not None:
            seen[sym] = row  # dedupe: a stock can only be on one side, last write wins
    if not seen:
        raise ValueError(f"no {segment} rows found in the live gainers/losers payloads")

    constituents: Dict[str, int] = {}
    for r in universe_rows:
        constituents[r["desk_sector"]] = constituents.get(r["desk_sector"], 0) + 1

    by_sector: Dict[str, List[dict]] = {}
    for sym, row in seen.items():
        by_sector.setdefault(sec_of[sym], []).append(row)

    sectors = []
    for sector, rows in by_sector.items():
        changes = [float(r["perChange"]) for r in rows]
        best = max(rows, key=lambda r: float(r["perChange"]))
        worst = min(rows, key=lambda r: float(r["perChange"]))
        sectors.append({
            "sector": sector,
            "seen": len(rows),
            "constituents": constituents.get(sector, len(rows)),
            "avg_change_pct": round(mean(changes), 2),
            "up": sum(1 for c in changes if c > 0),
            "down": sum(1 for c in changes if c < 0),
            "best": f"{best['symbol']} {float(best['perChange']):+.2f}%",
            "worst": f"{worst['symbol']} {float(worst['perChange']):+.2f}%",
        })
    sectors.sort(key=lambda s: s["avg_change_pct"], reverse=True)

    all_changes = [float(r["perChange"]) for r in seen.values()]
    unseen = [r["symbol"] for r in universe_rows if r["symbol"] not in seen]
    as_of = max(_segment_ts(gainers, segment), _segment_ts(losers, segment))

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["sector", "seen", "constituents", "avg_change_pct", "up", "down", "best", "worst"])
    for s in sectors:
        w.writerow([s["sector"], s["seen"], s["constituents"], s["avg_change_pct"], s["up"], s["down"],
                    s["best"], s["worst"]])

    return {
        "segment": segment,
        "as_of": as_of,
        "coverage": {"seen": len(seen), "universe": len(universe_rows), "unseen": unseen,
                     "note": "Live board lists only the top 20 gainers and top 20 losers; unseen stocks are mid-pack movers."},
        "overall": {"up": sum(1 for c in all_changes if c > 0), "down": sum(1 for c in all_changes if c < 0),
                    "avg_change_pct_seen": round(mean(all_changes), 2)},
        "sectors": sectors,
        "csv": {"live_sector_tilt.csv": buf.getvalue()},
    }
