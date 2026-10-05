"""Shared test helpers: import path setup and fixture loading."""

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
# The SAM Desktop bundle ships the tool SDK; use it so tools.py can be tested too.
SDK = Path("/Applications/Solace Agent Mesh.app/Contents/Resources/sandbox/sam-tool-sdk")

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if SDK.is_dir() and str(SDK) not in sys.path:
    sys.path.append(str(SDK))


def fixture_raw(name: str) -> str:
    """The fixture exactly as captured: a JSON-RPC envelope around an MCP CallToolResult."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture_text(name: str) -> str:
    """Just the NSE payload text (what MCP puts in content[0].text)."""
    return json.loads(fixture_raw(name))["result"]["content"][0]["text"]


def fixture_payload(name: str) -> dict:
    return json.loads(fixture_text(name))


def compare_payloads(months: int):
    return [fixture_payload(f"compare_{months}m_batch{i}.json") for i in range(1, 6)]


BREADTH_FILES = [
    "breadth_today.json",
    "breadth_2026-09-30.json",
    "breadth_2026-09-29.json",
    "breadth_2026-09-28.json",
    "breadth_2026-09-25.json",
    "breadth_2026-10-02.json",  # holiday: NSE returns the previous session (2026-10-01)
]
