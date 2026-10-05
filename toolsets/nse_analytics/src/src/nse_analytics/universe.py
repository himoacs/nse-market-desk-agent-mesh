"""NIFTY 50 constituents mapped to desk sectors.

NSE's MCP servers carry no sector or industry data, so the desk ships its
own mapping in ``data/nifty50_sectors.csv``. It is built from the official
constituent list (https://niftyindices.com/IndexConstituent/ind_nifty50list.csv),
keeping NSE's ``Industry`` column as ``nse_industry`` and grouping it into
broader ``desk_sector`` buckets so each sector has enough stocks to average:

- Financial Services is split into Banks and Financials ex-Banks.
- Oil, Gas & Consumable Fuels + Power -> Energy & Power.
- Consumer Durables + Consumer Services -> Consumer.
- Construction, Construction Materials, Capital Goods, Services -> Infra & Industrials.

Refresh the CSV (and CONSTITUENTS_AS_OF) after each semi-annual index rebalance.
"""

import csv
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

CONSTITUENTS_AS_OF = "2026-10-05"
COMPARE_BATCH_SIZE = 10  # compare_stocks accepts at most 10 symbols per call

_CSV_PATH = Path(__file__).parent / "data" / "nifty50_sectors.csv"


def load_universe() -> List[Dict[str, str]]:
    """Return the constituent rows (symbol, company, desk_sector, nse_industry) in file order."""
    with _CSV_PATH.open(newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def sector_of(rows: List[Dict[str, str]]) -> Dict[str, str]:
    return {r["symbol"]: r["desk_sector"] for r in rows}


def sectors(rows: List[Dict[str, str]]) -> "OrderedDict[str, List[str]]":
    grouped: "OrderedDict[str, List[str]]" = OrderedDict()
    for r in rows:
        grouped.setdefault(r["desk_sector"], []).append(r["symbol"])
    return grouped


def compare_batches(rows: List[Dict[str, str]], size: int = COMPARE_BATCH_SIZE) -> List[List[str]]:
    symbols = [r["symbol"] for r in rows]
    return [symbols[i : i + size] for i in range(0, len(symbols), size)]
