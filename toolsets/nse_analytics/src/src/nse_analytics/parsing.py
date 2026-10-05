"""Extract the JSON payload from a saved NSE MCP tool response.

Depending on how an MCP response reached the analyst (an auto-saved MCP
artifact, a file the Market Data agent wrote, a copy-pasted tool result),
the bytes can be any of:

- the bare JSON payload the NSE server put in ``content[0].text``
- an MCP ``CallToolResult`` (``{"content": [{"type": "text", "text": "..."}]}``)
- a full JSON-RPC envelope (``{"jsonrpc": "2.0", "result": {...}}``)
- a bare list of MCP content items
- Server-Sent-Events framing (``event: message`` / ``data: {...}``)

``extract_payload`` peels those layers off until it reaches the NSE object.
"""

import json
from typing import Any, Union

_MAX_UNWRAP_DEPTH = 8


def _loads_lenient(text: str) -> Any:
    text = text.strip()
    if not text:
        raise ValueError("empty content")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # SSE framing: take the first data: line that parses.
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
    # Last resort: the outermost {...} span (e.g. JSON with a prose preamble).
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("no JSON object found")


def _unwrap_content_items(items: list) -> Any:
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            try:
                return _loads_lenient(item["text"])
            except ValueError:
                continue
    raise ValueError("no parseable text item in MCP content list")


def extract_payload(raw: Union[str, bytes, dict, list]) -> dict:
    """Return the innermost NSE JSON object from ``raw``.

    Raises ValueError if no JSON object can be found, or if the MCP result
    is flagged ``isError``.
    """
    value: Any = raw
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        value = _loads_lenient(value)

    for _ in range(_MAX_UNWRAP_DEPTH):
        if isinstance(value, list):
            value = _unwrap_content_items(value)
            continue
        if not isinstance(value, dict):
            break
        if "result" in value and ("jsonrpc" in value or "id" in value):
            value = value["result"]
            continue
        if "error" in value and "jsonrpc" in value:
            raise ValueError(f"MCP error: {value['error']}")
        if value.get("isError") is True:
            raise ValueError(f"MCP tool returned isError: {json.dumps(value)[:300]}")
        if isinstance(value.get("structuredContent"), dict):
            value = value["structuredContent"]
            continue
        if isinstance(value.get("content"), list):
            value = _unwrap_content_items(value["content"])
            continue
        break

    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object, got {type(value).__name__}")
    if set(value.keys()) == {"error"}:
        raise ValueError(f"NSE tool error: {value['error']}")
    return value
