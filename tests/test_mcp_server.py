"""Tests for the MCP server (agent_skills.mcp).

Covers: JSON-RPC protocol shape, initialize handshake, tools/list, tools/call
for each of the 8 tools, error handling, notification handling, stdio loop.
"""
import io
import json
import sqlite3
from pathlib import Path

import pytest

from agent_skills.mcp import PROTOCOL_VERSION, SERVER_NAME
from agent_skills.mcp.server import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    handle_request,
    serve,
)
from agent_skills.mcp.tools import (
    ToolError,
    get_tool_schemas,
    tool_list_agents,
    tool_list_categories,
    tool_list_tags,
    tool_search,
)


# ─── Fixture: cached registry (reuses verb test pattern) ───────────────────


def _registry():
    return {
        "schema_version": 2,
        "generated_at": "2026-05-12T08:51:19Z",
        "skills": [
            {
                "id": "samuelgudi/rust-helpers",
                "name": "rust-helpers",
                "description": "Rust helpers for systems programming",
                "version": "1.0.0",
                "status": "active",
                "category": "dev",
                "tags": ["rust", "systems"],
                "platforms": ["linux", "macos", "windows"],
                "agent_compat": ["claude-code", "openclaw"],
                "requires": {"env_vars": [], "commands": []},
                "license": "MIT",
                "author": {"name": "S", "github_login": "samuelgudi", "github_id": 1},
                "body": "",
                "source": {"path": "skills/samuelgudi/rust-helpers", "content_hash": "", "files": []},
            },
            {
                "id": "samuelgudi/python-helpers",
                "name": "python-helpers",
                "description": "Python helpers",
                "version": "0.5.0",
                "status": "active",
                "category": "dev",
                "tags": ["python"],
                "platforms": ["linux"],
                "agent_compat": ["claude-code"],
                "requires": {"env_vars": [], "commands": []},
                "license": "Apache-2.0",
                "author": {"name": "S", "github_login": "samuelgudi", "github_id": 1},
                "body": "",
                "source": {"path": "skills/samuelgudi/python-helpers", "content_hash": "", "files": []},
            },
        ],
    }


@pytest.fixture
def cached(fake_home):
    cache = fake_home / ".cache" / "agent-skills"
    cache.mkdir(parents=True)
    (cache / "registry.json").write_text(json.dumps(_registry()), encoding="utf-8")
    return cache


# ─── JSON-RPC protocol handshake ───────────────────────────────────────────


def test_initialize_returns_protocol_and_server_info():
    msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    resp = handle_request(msg)
    assert resp is not None
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    r = resp["result"]
    assert r["protocolVersion"] == PROTOCOL_VERSION
    assert r["serverInfo"]["name"] == SERVER_NAME
    assert "tools" in r["capabilities"]


def test_ping_returns_empty_result():
    resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert resp == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_initialized_notification_returns_none():
    # Notification has no id; no response should be sent.
    resp = handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert resp is None


def test_missing_method_field_is_invalid_request():
    resp = handle_request({"jsonrpc": "2.0", "id": 3})
    assert resp["error"]["code"] == INVALID_REQUEST


def test_unknown_method():
    resp = handle_request({"jsonrpc": "2.0", "id": 4, "method": "nope"})
    assert resp["error"]["code"] == METHOD_NOT_FOUND


def test_unknown_notification_no_response():
    resp = handle_request({"jsonrpc": "2.0", "method": "nope"})
    assert resp is None


# ─── tools/list ────────────────────────────────────────────────────────────


def test_tools_list_returns_8_tools():
    resp = handle_request({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
    tools = resp["result"]["tools"]
    names = {t["name"] for t in tools}
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


def test_each_tool_has_required_schema_fields():
    for t in get_tool_schemas():
        assert "name" in t
        assert "description" in t
        assert "inputSchema" in t
        s = t["inputSchema"]
        assert s["type"] == "object"
        assert "properties" in s


# ─── tools/call: search ────────────────────────────────────────────────────


def test_tools_call_search_returns_content(cached):
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "rust"}},
        }
    )
    r = resp["result"]
    assert r["isError"] is False
    content = json.loads(r["content"][0]["text"])
    assert content["total"] == 1
    assert content["results"][0]["id"] == "samuelgudi/rust-helpers"


def test_tools_call_search_invalid_query_returns_tool_error(cached):
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "badfield:x"}},
        }
    )
    r = resp["result"]
    assert r["isError"] is True
    assert "unknown field" in r["content"][0]["text"].lower()


def test_tools_call_search_missing_query(cached):
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": "search", "arguments": {}},
        }
    )
    assert resp["result"]["isError"] is True


def test_tools_call_unknown_tool():
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        }
    )
    assert resp["error"]["code"] == METHOD_NOT_FOUND


def test_tools_call_invalid_params():
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {"name": "search", "arguments": "not_an_object"},
        }
    )
    assert resp["error"]["code"] == INVALID_PARAMS


# ─── tools/call: get_skill ─────────────────────────────────────────────────


def test_tools_call_get_skill_returns_metadata(cached):
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "get_skill",
                "arguments": {"id": "samuelgudi/rust-helpers"},
            },
        }
    )
    r = resp["result"]
    assert r["isError"] is False
    payload = json.loads(r["content"][0]["text"])
    assert payload["metadata"]["id"] == "samuelgudi/rust-helpers"
    assert "body" in payload
    assert "files" in payload


def test_tools_call_get_skill_not_found(cached):
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {"name": "get_skill", "arguments": {"id": "nope/missing"}},
        }
    )
    assert resp["result"]["isError"] is True


# ─── tools/call: list_* ────────────────────────────────────────────────────


def test_tools_call_list_categories(cached):
    r = tool_list_categories({})
    names = [c["name"] for c in r["categories"]]
    assert names == ["dev"]
    assert r["categories"][0]["count"] == 2


def test_tools_call_list_tags(cached):
    r = tool_list_tags({})
    names = [t["name"] for t in r["tags"]]
    assert set(names) == {"rust", "systems", "python"}


def test_tools_call_list_tags_prefix(cached):
    r = tool_list_tags({"prefix": "ru"})
    names = [t["name"] for t in r["tags"]]
    assert names == ["rust"]


def test_tools_call_list_agents(cached):
    r = tool_list_agents({})
    names = {a["name"] for a in r["agents"]}
    assert names == {"claude-code", "openclaw"}


# ─── tools/call: get_skill_file path-traversal guard ───────────────────────


def test_get_skill_file_path_traversal_rejected(cached, tmp_path):
    # Even if the file existed, '../' must be rejected.
    repo = cached / "registry-repo"
    (repo / "skills/samuelgudi/rust-helpers").mkdir(parents=True)
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {
                "name": "get_skill_file",
                "arguments": {
                    "id": "samuelgudi/rust-helpers",
                    "file_path": "../../../etc/passwd",
                },
            },
        }
    )
    assert resp["result"]["isError"] is True
    assert "escapes" in resp["result"]["content"][0]["text"]


def test_get_skill_file_rejects_skill_with_empty_source_path(fake_home):
    """Review finding #4: a skill whose source.path is empty would let
    get_skill_file read arbitrary files from the registry-repo root,
    breaking the 'stay inside this skill' invariant. Must hard-error."""
    cache = fake_home / ".cache" / "agent-skills"
    cache.mkdir(parents=True)
    reg = {
        "schema_version": 2,
        "generated_at": "2026-05-12T00:00:00Z",
        "skills": [
            {
                "id": "malformed/skill",
                "name": "malformed",
                "description": "",
                "version": "0.1.0",
                "status": "active",
                "category": "dev",
                "tags": [],
                "platforms": ["linux"],
                "agent_compat": ["claude-code"],
                "requires": {"env_vars": [], "commands": []},
                "license": "MIT",
                "author": {"name": "X", "github_login": "x", "github_id": 1},
                "body": "",
                "source": {"path": "", "content_hash": "", "files": []},
            }
        ],
    }
    import json as _json
    (cache / "registry.json").write_text(_json.dumps(reg), encoding="utf-8")
    (cache / "registry-repo").mkdir()
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 32,
            "method": "tools/call",
            "params": {
                "name": "get_skill_file",
                "arguments": {
                    "id": "malformed/skill",
                    "file_path": "any/file.md",
                },
            },
        }
    )
    assert resp["result"]["isError"] is True
    text = resp["result"]["content"][0]["text"]
    assert "source.path" in text or "registry root" in text


def test_get_skill_file_reads_actual_file(cached):
    repo = cached / "registry-repo"
    skill_dir = repo / "skills/samuelgudi/rust-helpers"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Hello", encoding="utf-8")
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 31,
            "method": "tools/call",
            "params": {
                "name": "get_skill_file",
                "arguments": {
                    "id": "samuelgudi/rust-helpers",
                    "file_path": "SKILL.md",
                },
            },
        }
    )
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["content"] == "# Hello"
    assert payload["encoding"] == "utf-8"


# ─── No-registry behavior ──────────────────────────────────────────────────


def test_search_without_registry_returns_tool_error(fake_home):
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 40,
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "rust"}},
        }
    )
    assert resp["result"]["isError"] is True
    assert "update_registry" in resp["result"]["content"][0]["text"]


# ─── stdio loop ────────────────────────────────────────────────────────────


def test_serve_handles_initialize_then_list_tools(cached):
    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    stdout = io.StringIO()
    serve(stdin=stdin, stdout=stdout)
    lines = [l for l in stdout.getvalue().splitlines() if l.strip()]
    assert len(lines) == 2
    r1 = json.loads(lines[0])
    r2 = json.loads(lines[1])
    assert r1["id"] == 1 and "protocolVersion" in r1["result"]
    assert r2["id"] == 2 and len(r2["result"]["tools"]) == 8


def test_serve_skips_empty_lines():
    stdin = io.StringIO("\n\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n\n")
    stdout = io.StringIO()
    serve(stdin=stdin, stdout=stdout)
    lines = [l for l in stdout.getvalue().splitlines() if l.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["id"] == 1


def test_serve_invalid_json_responds_with_parse_error():
    stdin = io.StringIO("{not valid json\n")
    stdout = io.StringIO()
    serve(stdin=stdin, stdout=stdout)
    resp = json.loads(stdout.getvalue().strip())
    assert resp["error"]["code"] == PARSE_ERROR


def test_serve_non_dict_message_invalid_request():
    stdin = io.StringIO("[1, 2, 3]\n")
    stdout = io.StringIO()
    serve(stdin=stdin, stdout=stdout)
    resp = json.loads(stdout.getvalue().strip())
    assert resp["error"]["code"] == INVALID_REQUEST


def test_serve_does_not_respond_to_notifications():
    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
    )
    stdout = io.StringIO()
    serve(stdin=stdin, stdout=stdout)
    # No response to a notification.
    assert stdout.getvalue() == ""
