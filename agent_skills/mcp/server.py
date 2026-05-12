"""MCP JSON-RPC 2.0 server core.

Pure protocol layer. Reads/writes JSON-RPC messages over text streams.
Dispatches to handlers defined in `tools.py`. No stdin/stdout coupling so
the same logic is testable in-process.
"""
from __future__ import annotations

import json
import sys
import traceback
from typing import IO, Any

from agent_skills.mcp import PROTOCOL_VERSION, SERVER_NAME, SERVER_VERSION
from agent_skills.mcp.tools import ToolError, get_tool_handler, get_tool_schemas


# JSON-RPC 2.0 error codes (https://www.jsonrpc.org/specification#error_object)
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _ok(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def handle_request(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Process one parsed JSON-RPC message. Returns the response dict, or
    None for notifications (no response expected)."""
    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    # JSON-RPC notification: no `id` field, no response.
    is_notification = "id" not in msg

    if method is None:
        if is_notification:
            return None
        return _err(req_id, INVALID_REQUEST, "Missing 'method' field")

    if method == "initialize":
        return _ok(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            },
        )

    if method == "initialized" or method == "notifications/initialized":
        return None  # Client-side notification, no response.

    if method == "ping":
        return _ok(req_id, {})

    if method == "tools/list":
        return _ok(req_id, {"tools": get_tool_schemas()})

    if method == "tools/call":
        if is_notification:
            return None
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return _err(req_id, INVALID_PARAMS, "tools/call requires string 'name'")
        if not isinstance(arguments, dict):
            return _err(req_id, INVALID_PARAMS, "tools/call 'arguments' must be an object")
        handler = get_tool_handler(name)
        if handler is None:
            return _err(req_id, METHOD_NOT_FOUND, f"Unknown tool: {name}")
        try:
            result = handler(arguments)
            return _ok(
                req_id,
                {
                    "content": [
                        {"type": "text", "text": json.dumps(result, default=str)}
                    ],
                    "isError": False,
                },
            )
        except ToolError as e:
            return _ok(
                req_id,
                {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            )
        except Exception as e:  # pragma: no cover — surfaced via test if it happens
            tb = traceback.format_exc()
            return _err(
                req_id, INTERNAL_ERROR, f"Tool {name} crashed: {e}", data=tb
            )

    if is_notification:
        return None
    return _err(req_id, METHOD_NOT_FOUND, f"Unknown method: {method}")


def serve(stdin: IO[str] = sys.stdin, stdout: IO[str] = sys.stdout) -> None:
    """Run the stdio loop. One JSON message per line. Reads until EOF."""
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            response = _err(None, PARSE_ERROR, f"Invalid JSON: {e}")
        else:
            if not isinstance(msg, dict):
                response = _err(None, INVALID_REQUEST, "Request must be an object")
            else:
                response = handle_request(msg)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()
