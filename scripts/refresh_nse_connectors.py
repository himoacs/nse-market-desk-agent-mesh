#!/usr/bin/env python3
"""Regenerate connectors/nse_*.yaml with a static tool manifest from NSE's MCP servers.

Why a static manifest: with ``values.manifest`` set, SAM registers the tools
without live discovery and connects to the server lazily on the first call.
NSE's servers are flaky (many requests hang or 504), and without a manifest
every deploy and every desktop restart has to reach NSE just to list tools.

The script also rewrites NSE's per-tool "call get_corporate_actions before
presenting results" instructions: followed literally, a 50-stock sector scan
would trigger 50 extra calls. The analyst flags unadjusted-price distortions
instead (see toolsets/nse_analytics), and the market data agent calls
get_corporate_actions only when asked.

Usage:
    python3 scripts/refresh_nse_connectors.py            # fetch tools/list live (with retries)
    python3 scripts/refresh_nse_connectors.py --offline  # rebuild from scripts/nse_tools/*.json
"""

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "scripts" / "nse_tools"

CONNECTORS = {
    "nse_bhavcopy": {
        "url": "https://mcp.nseindia.in/bhavcopy/cm/mcp",
        "tools": None,  # all
        "description": (
            "NSE official MCP server, end-of-day (bhavcopy) data for NSE cash-market equities over the "
            "last ~5 years: daily OHLCV history, breadth (advances/declines), top movers and volume, "
            "compare_stocks returns and drawdown, bulk quotes, 52-week high/low, moving averages, volume "
            "analysis, corporate actions and symbol search. Latest data is the previous trading day."
        ),
    },
    "nse_cm_market": {
        "url": "https://mcp.nseindia.in/cmmkt/mcp",
        # SME, call auction, bond and the duplicate raw gainers/losers tools are left out.
        "tools": [
            "nse_get_market_movers", "nse_get_gainers", "nse_get_losers", "cm_get_live_market_data",
            "cm_get_stock_quote", "cm_get_equity_stocks", "cm_get_data_status", "cm_get_allstocks_status",
        ],
        "description": (
            "NSE official MCP server, live snapshot of the current cash-market session (1-5 minutes behind "
            "real time): top gainers/losers across all stocks and NIFTY / BANKNIFTY / NIFTY NEXT 50, the live "
            "gainers/losers board by segment, single-stock live quotes, and data-freshness status."
        ),
    },
}

UNADJUSTED_NOTE = (
    "Note: prices are raw NSE bhavcopy data with no split/bonus adjustment. Do not call "
    "get_corporate_actions automatically; the desk analyst flags likely distortions, and "
    "get_corporate_actions is called only when corporate actions are requested."
)
CA_TOOL_NOTE = (
    "Use when corporate actions are requested, or to confirm whether a specific large price move "
    "is a split/bonus ex-date. The adjustmentFactor field tells you how to interpret pre-event "
    "prices: 1:1 bonus -> 0.5, 10->2 split -> 0.2."
)


def _post(url, payload, session_id=None, timeout=20):
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.headers.get("Mcp-Session-Id"), resp.read().decode()


def _parse(body):
    for line in body.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return json.loads(body)


def _retry(fn, attempts=6):
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - NSE times out or 504s intermittently
            if i == attempts - 1:
                raise
            print(f"  retry {i + 1} after: {exc}")
            time.sleep(1 + i)


def fetch_tools(url):
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "nse-desk-manifest", "version": "1.0"}}}
    sid, _ = _retry(lambda: _post(url, init))
    _retry(lambda: _post(url, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid))
    _, body = _retry(lambda: _post(url, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sid))
    return _parse(body)["result"]["tools"]


def rewrite_description(name, desc):
    # Replace NSE's "IMPORTANT - UNADJUSTED PRICES ..." paragraph (up to the disclaimer).
    desc = re.sub(r"IMPORTANT\s+\S+\s+UNADJUSTED PRICES.*?(?=\n\s*Disclaimer:|\Z)",
                  UNADJUSTED_NOTE + "\n\n", desc, flags=re.S)
    if name == "get_corporate_actions":
        desc = re.sub(r"ALWAYS call this before.*?(?=\n\s*Returns:)", CA_TOOL_NOTE + "\n\n", desc, flags=re.S)
    return re.sub(r"\n{3,}", "\n\n", desc).strip()


def to_yaml(name, spec, tools):
    manifest = [{"name": t["name"], "description": rewrite_description(t["name"], t.get("description", "")),
                 "inputSchema": t.get("inputSchema", {"type": "object"})} for t in tools]
    # A structured list, not a JSON/YAML string: the runtime rejects a string
    # manifest ("'manifest' must be a list of tool entries"). JSON is valid
    # YAML, so each entry is emitted as a flow mapping.
    indented = "\n".join("      - " + json.dumps(entry, ensure_ascii=False) for entry in manifest)
    return (
        "# Generated by scripts/refresh_nse_connectors.py; edit the script, not this file.\n"
        "kind: connector\n"
        f"name: {name}\n"
        "description: >-\n"
        f"  {spec['description']}\n"
        "spec:\n"
        "  type: mcp\n"
        "  subtype: remote\n"
        "  values:\n"
        f"    server_url: \"{spec['url']}\"\n"
        "    connection_type: \"streamable-http\"\n"
        "    auth_type: \"none\"\n"
        "    manifest:\n"
        f"{indented}\n"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="use the saved snapshots instead of calling NSE")
    args = ap.parse_args()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec in CONNECTORS.items():
        snap = SNAPSHOT_DIR / f"{name}.tools.json"
        if args.offline:
            tools = json.loads(snap.read_text(encoding="utf-8"))
        else:
            print(f"{name}: fetching tools/list from {spec['url']}")
            tools = fetch_tools(spec["url"])
            snap.write_text(json.dumps(tools, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if spec["tools"]:
            by_name = {t["name"]: t for t in tools}
            missing = [n for n in spec["tools"] if n not in by_name]
            if missing:
                raise SystemExit(f"{name}: NSE no longer lists {missing}; update CONNECTORS")
            tools = [by_name[n] for n in spec["tools"]]
        out = ROOT / "connectors" / f"{name}.yaml"
        out.write_text(to_yaml(name, spec, tools), encoding="utf-8")
        print(f"{name}: wrote {out.relative_to(ROOT)} with {len(tools)} tools")


if __name__ == "__main__":
    main()
