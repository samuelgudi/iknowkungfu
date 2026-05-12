"""Spawn the MCP server as a real subprocess and exercise the JSON-RPC handshake.

This catches packaging/entry-point bugs that in-process testing doesn't —
e.g. import-time errors, encoding misconfigurations, broken __main__ wiring.
"""
import json
import os
import subprocess
import sys


def _spawn_mcp(env: dict | None = None) -> subprocess.Popen:
    """Spawn `python -m agent_skills.mcp` as a subprocess.

    Uses sys.executable rather than 'python' so the test always runs against
    the same interpreter pytest is using.
    """
    env_full = os.environ.copy()
    if env:
        env_full.update(env)
    return subprocess.Popen(
        [sys.executable, "-m", "agent_skills.mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env=env_full,
    )


def _send_and_recv(
    proc: subprocess.Popen, message: dict, timeout: float = 5.0
) -> dict:
    """Send one JSON-RPC message and read one response line."""
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError(
            f"MCP server gave no response. stderr={proc.stderr.read()!r}"
        )
    return json.loads(line)


def test_subprocess_initialize_handshake(tmp_path):
    proc = _spawn_mcp()
    try:
        resp = _send_and_recv(
            proc,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert "protocolVersion" in resp["result"]
        assert resp["result"]["serverInfo"]["name"] == "iknowkungfu"
    finally:
        proc.stdin.close()
        proc.wait(timeout=5)


def test_subprocess_tools_list_returns_eight_tools():
    proc = _spawn_mcp()
    try:
        _send_and_recv(
            proc,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        )
        resp = _send_and_recv(
            proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        names = {t["name"] for t in resp["result"]["tools"]}
        assert names == {
            "search",
            "get_skill",
            "get_skill_file",
            "install_skill",
            "list_categories",
            "list_tags",
            "list_agents",
            "update_registry",
        }
    finally:
        proc.stdin.close()
        proc.wait(timeout=5)


def test_subprocess_ping():
    proc = _spawn_mcp()
    try:
        resp = _send_and_recv(
            proc, {"jsonrpc": "2.0", "id": 99, "method": "ping"}
        )
        assert resp["result"] == {}
    finally:
        proc.stdin.close()
        proc.wait(timeout=5)


def test_subprocess_search_without_registry_yields_tool_error(tmp_path, monkeypatch):
    """When no registry is cached, the search tool returns a ToolError telling
    the agent to call update_registry first."""
    # Point HOME at a clean tmpdir so the subprocess sees no cached registry.
    env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    proc = _spawn_mcp(env=env)
    try:
        _send_and_recv(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        resp = _send_and_recv(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "search", "arguments": {"query": "rust"}},
            },
        )
        r = resp["result"]
        assert r["isError"] is True
        assert "update_registry" in r["content"][0]["text"]
    finally:
        proc.stdin.close()
        proc.wait(timeout=5)
