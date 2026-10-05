"""End-of-day analytics: sector rotation, momentum ranking and breadth trend.

All functions are pure: they take already-parsed NSE payloads (see
``parsing.extract_payload``) and return plain dicts / CSV text, so they can be
unit-tested without SAM.

Definitions (mirrored in the nse-analysis-methodology skill):

- Sector return: equal-weighted mean of constituent ``return_pct`` from
  ``compare_stocks`` over the lookback (1 month and 3 months).
- Benchmark: equal-weighted mean over all included NIFTY 50 constituents.
- Relative strength (RS): sector return minus benchmark, per lookback.
- Quadrant: RS3>0 & RS1>0 Leading; RS3>0 & RS1<=0 Weakening;
  RS3<=0 & RS1>0 Improving; RS3<=0 & RS1<=0 Lagging.
- Acceleration: 1M return minus the 3M return's average monthly pace (r3 / 3).
- Possible corporate action: NSE bhavcopy prices are unadjusted, so a bonus or
  split inside the window shows up as a huge fake move. Stocks with
  |1M| > 35% or |3M| > 45% are flagged and left out of all averages.
"""

import csv
import io
from statistics import mean
from typing import Dict, Iterable, List, Optional

OUTLIER_1M_PCT = 35.0
OUTLIER_3M_PCT = 45.0

# Breadth regimes on the advance/decline ratio.
BROAD_STRENGTH_AD = 1.5
BROAD_WEAKNESS_AD = 0.67


def _r(x: Optional[float], nd: int = 2) -> Optional[float]:
    return None if x is None else round(x, nd)


def _quadrant(rs3: float, rs1: float) -> str:
    if rs3 > 0:
        return "Leading" if rs1 > 0 else "Weakening"
    return "Improving" if rs1 > 0 else "Lagging"


def _collect_compare(payloads: Iterable[dict]) -> Dict[str, object]:
    stocks: Dict[str, dict] = {}
    from_dates: List[str] = []
    to_dates: List[str] = []
    for p in payloads:
        if p.get("from_date"):
            from_dates.append(p["from_date"])
        if p.get("to_date"):
            to_dates.append(p["to_date"])
        for s in p.get("stocks") or []:
            sym = s.get("symbol")
            if sym and s.get("return_pct") is not None:
                stocks[sym] = s
    return {
        "stocks": stocks,
        "from_date": min(from_dates) if from_dates else None,
        "to_date": max(to_dates) if to_dates else None,
    }


def _to_csv(header: List[str], rows: List[List[object]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def sector_rotation(
    universe_rows: List[Dict[str, str]],
    compare_1m: Iterable[dict],
    compare_3m: Iterable[dict],
    top_n: int = 5,
) -> dict:
    """Compute sector RS / quadrants and a stock momentum ranking."""
    one = _collect_compare(compare_1m)
    three = _collect_compare(compare_3m)
    s1: Dict[str, dict] = one["stocks"]  # type: ignore[assignment]
    s3: Dict[str, dict] = three["stocks"]  # type: ignore[assignment]

    stocks = []
    missing = []
    outliers = []
    for row in universe_rows:
        sym = row["symbol"]
        if sym not in s1 or sym not in s3:
            missing.append(sym)
            continue
        r1 = float(s1[sym]["return_pct"])
        r3 = float(s3[sym]["return_pct"])
        rec = {
            "symbol": sym,
            "company": row.get("company", ""),
            "sector": row["desk_sector"],
            "ret_1m": r1,
            "ret_3m": r3,
            "max_dd_3m": s3[sym].get("max_drawdown"),
            "accel": r1 - r3 / 3.0,
            "flag": "",
        }
        if abs(r1) > OUTLIER_1M_PCT or abs(r3) > OUTLIER_3M_PCT:
            rec["flag"] = "possible corporate action (unadjusted prices)"
            outliers.append(rec)
        stocks.append(rec)

    included = [s for s in stocks if not s["flag"]]
    if not included:
        raise ValueError("no constituents with both 1M and 3M returns; check the compare_stocks artifacts")

    bench_1m = mean(s["ret_1m"] for s in included)
    bench_3m = mean(s["ret_3m"] for s in included)

    by_sector: Dict[str, List[dict]] = {}
    constituents: Dict[str, int] = {}
    for row in universe_rows:
        constituents[row["desk_sector"]] = constituents.get(row["desk_sector"], 0) + 1
    for s in included:
        by_sector.setdefault(s["sector"], []).append(s)

    sectors = []
    for sector, members in by_sector.items():
        r1 = mean(m["ret_1m"] for m in members)
        r3 = mean(m["ret_3m"] for m in members)
        rs1, rs3 = r1 - bench_1m, r3 - bench_3m
        sectors.append(
            {
                "sector": sector,
                "constituents": constituents.get(sector, len(members)),
                "included": len(members),
                "ret_1m": _r(r1),
                "ret_3m": _r(r3),
                "rs_1m": _r(rs1),
                "rs_3m": _r(rs3),
                "quadrant": _quadrant(rs3, rs1),
                "up_1m": sum(1 for m in members if m["ret_1m"] > 0),
                "best_1m": max(members, key=lambda m: m["ret_1m"])["symbol"],
                "worst_1m": min(members, key=lambda m: m["ret_1m"])["symbol"],
            }
        )
    sectors.sort(key=lambda x: (x["rs_3m"], x["rs_1m"]), reverse=True)

    ranked = sorted(included, key=lambda s: s["ret_3m"], reverse=True)
    for i, s in enumerate(ranked, 1):
        s["rank_3m"] = i

    def _brief(s: dict) -> dict:
        return {
            "symbol": s["symbol"],
            "sector": s["sector"],
            "ret_1m": _r(s["ret_1m"]),
            "ret_3m": _r(s["ret_3m"]),
            "max_dd_3m": _r(s["max_dd_3m"]),
        }

    quadrants: Dict[str, List[str]] = {"Leading": [], "Weakening": [], "Improving": [], "Lagging": []}
    for sec in sectors:
        quadrants[sec["quadrant"]].append(sec["sector"])

    sector_csv = _to_csv(
        ["sector", "constituents", "included", "ret_1m_pct", "ret_3m_pct", "rs_1m_pct", "rs_3m_pct",
         "quadrant", "up_1m", "best_1m", "worst_1m"],
        [[s["sector"], s["constituents"], s["included"], s["ret_1m"], s["ret_3m"], s["rs_1m"], s["rs_3m"],
          s["quadrant"], s["up_1m"], s["best_1m"], s["worst_1m"]] for s in sectors],
    )
    momentum_csv = _to_csv(
        ["rank_3m", "symbol", "company", "sector", "ret_1m_pct", "ret_3m_pct", "max_dd_3m_pct", "accel_pct", "flag"],
        [[s.get("rank_3m", ""), s["symbol"], s["company"], s["sector"], _r(s["ret_1m"]), _r(s["ret_3m"]),
          _r(s["max_dd_3m"]), _r(s["accel"]), s["flag"]]
         for s in ranked + outliers],
    )

    return {
        "window_1m": {"from": one["from_date"], "to": one["to_date"]},
        "window_3m": {"from": three["from_date"], "to": three["to_date"]},
        "benchmark": {"name": "NIFTY 50 equal-weight", "ret_1m": _r(bench_1m), "ret_3m": _r(bench_3m)},
        "coverage": {"universe": len(universe_rows), "included": len(included),
                     "missing": missing, "flagged": [o["symbol"] for o in outliers]},
        "sectors": sectors,
        "quadrants": quadrants,
        "top_momentum": [_brief(s) for s in ranked[:top_n]],
        "bottom_momentum": [_brief(s) for s in ranked[-top_n:][::-1]],
        "accelerating": [_brief(s) for s in sorted(included, key=lambda s: s["accel"], reverse=True)[:top_n]],
        "flagged": [{"symbol": o["symbol"], "ret_1m": _r(o["ret_1m"]), "ret_3m": _r(o["ret_3m"]), "flag": o["flag"]}
                    for o in outliers],
        "csv": {"sector_rotation.csv": sector_csv, "momentum_ranking.csv": momentum_csv},
    }


def _regime(ad: float) -> str:
    if ad >= BROAD_STRENGTH_AD:
        return "broad strength"
    if ad <= BROAD_WEAKNESS_AD:
        return "broad weakness"
    return "mixed"


def breadth_trend(payloads: Iterable[dict]) -> dict:
    """Dedupe/sort get_market_breadth payloads by trading date and describe the trend."""
    by_date: Dict[str, dict] = {}
    for p in payloads:
        if p.get("date") and p.get("advances") is not None:
            by_date[p["date"]] = p
    if not by_date:
        raise ValueError("no usable get_market_breadth payloads")

    days = []
    for d in sorted(by_date):
        p = by_date[d]
        adv, dec = int(p["advances"]), int(p["declines"])
        unch = int(p.get("unchanged") or 0)
        total = int(p.get("total_stocks") or adv + dec + unch)
        ad = float(p["ad_ratio"]) if p.get("ad_ratio") is not None else (adv / dec if dec else float("inf"))
        days.append({
            "date": d, "advances": adv, "declines": dec, "unchanged": unch, "total": total,
            "ad_ratio": round(ad, 2), "pct_advancing": round(100.0 * adv / total, 1) if total else None,
            "regime": _regime(ad),
        })

    latest = days[-1]
    prior = days[:-1]
    if prior:
        prior_avg = mean(d["ad_ratio"] for d in prior)
        if latest["ad_ratio"] > prior_avg * 1.1:
            direction = "improving"
        elif latest["ad_ratio"] < prior_avg * 0.9:
            direction = "deteriorating"
        else:
            direction = "steady"
    else:
        prior_avg, direction = None, "n/a (single session)"

    breadth_csv = _to_csv(
        ["date", "advances", "declines", "unchanged", "total", "ad_ratio", "pct_advancing", "regime"],
        [[d["date"], d["advances"], d["declines"], d["unchanged"], d["total"], d["ad_ratio"],
          d["pct_advancing"], d["regime"]] for d in days],
    )
    return {
        "sessions": len(days),
        "latest": latest,
        "prior_avg_ad_ratio": _r(prior_avg),
        "direction": direction,
        "sessions_with_more_decliners": sum(1 for d in days if d["ad_ratio"] < 1),
        "days": days,
        "csv": {"breadth_trend.csv": breadth_csv},
    }
