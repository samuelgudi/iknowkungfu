# MCP Integration Guide

The `iknowkungfu-mcp` server exposes the skills registry as Model Context Protocol tools. Any MCP-compatible agent runtime (Claude Code, OpenClaw, Codex, Cursor, Gemini CLI, etc.) can spawn it as a subprocess and call the 8 tools to search, fetch, and install skills mid-task.

> **The differentiator**: most skill-registry products expose a search API. We additionally expose `install_skill` — the agent can pull a skill into its own host's canonical directory and use it immediately, without leaving the agent loop.

---

## Tools at a glance

| Tool | Stage | Purpose |
|---|---|---|
| `search` | 1 | Ranked metadata search with the full query DSL |
| `get_skill` | 2 | Fetch one skill's SKILL.md body + metadata |
| `get_skill_file` | 3 | Fetch one resource file from a skill (`scripts/`, `references/`, `assets/`) |
| `install_skill` | — | Write the skill into the host's canonical directory via the adapter |
| `list_categories` | — | Discovery aid: all categories + counts |
| `list_tags` | — | Discovery aid: tags with optional prefix filter |
| `list_agents` | — | Discovery aid: host agents that have ≥1 compatible skill |
| `update_registry` | — | Pull the latest registry.json, rebuild the FTS5 index |

Stage refers to agentskills.io's progressive-disclosure model (metadata → body → resources).

---

## Installation

```bash
pip install iknowkungfu     # or: uv tool install iknowkungfu
```

This installs two CLI entry points:

* `kfu` — the CLI for humans
* `iknowkungfu-mcp` — the MCP server (spawned by agent runtimes, not invoked directly)

Verify:

```bash
which iknowkungfu-mcp        # POSIX
where iknowkungfu-mcp        # Windows
```

---

## Wiring it up per host

### Claude Code

Recommended: let the CLI write the config for you.

```bash
claude mcp add iknowkungfu iknowkungfu-mcp
```

Or edit `~/.claude.json` (user scope) directly — that file is where Claude Code stores MCP server entries (not `settings.json`, which is for hooks, permissions, and env):

```json
{
  "mcpServers": {
    "iknowkungfu": {
      "command": "iknowkungfu-mcp",
      "args": [],
      "env": {}
    }
  }
}
```

Restart Claude Code (`claude` → `/exit`, re-enter). Then in a session:

```
> Use the iknowkungfu search tool to find a rust serialization skill
```

Claude Code will discover the 8 tools via `tools/list`, call them, and surface the results.

### OpenClaw

```jsonc
// ~/.openclaw/config.json
{
  "mcp_servers": {
    "iknowkungfu": {
      "command": "iknowkungfu-mcp"
    }
  }
}
```

### Codex CLI

```toml
# ~/.codex/config.toml
[[mcp_servers]]
name = "iknowkungfu"
command = "iknowkungfu-mcp"
```

### Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "iknowkungfu": { "command": "iknowkungfu-mcp" }
  }
}
```

### Generic MCP client

```bash
iknowkungfu-mcp
```

Reads JSON-RPC 2.0 requests from stdin (one per line), writes responses to stdout. Use `stderr` for logs.

---

## First-run flow

The MCP server depends on a cached `registry.json`. If none is present, every tool that needs the registry returns a `ToolError` asking you to call `update_registry`.

Recommended first interaction with the server:

```jsonc
// 1. Handshake
→ {"jsonrpc":"2.0","id":1,"method":"initialize"}
← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18", ...}}

// 2. Fetch the registry
→ {"jsonrpc":"2.0","id":2,"method":"tools/call",
   "params":{"name":"update_registry","arguments":{}}}
← {"jsonrpc":"2.0","id":2,"result":{
     "content":[{"type":"text","text":"{\"current_version\":\"...\",...}"}],
     "isError":false}}

// 3. Search
→ {"jsonrpc":"2.0","id":3,"method":"tools/call",
   "params":{"name":"search","arguments":{"query":"rust tag:async"}}}
← {...ranked results...}

// 4. Install one of the results into your host
→ {"jsonrpc":"2.0","id":4,"method":"tools/call",
   "params":{"name":"install_skill","arguments":{
      "id":"samuelgudi/rust-tokio","agent":"claude-code"}}}
← {...install log + marker path...}
```

In Claude Code this is conversational; the agent handles the JSON.

---

## Tool: `search`

The flagship tool. Same query DSL as the CLI — see `docs/query-language.md`.

```jsonc
{
  "name": "search",
  "arguments": {
    "query": "tag:rust agent:claude-code version:>=1.0",
    "limit": 20,
    "offset": 0,
    "include_deprecated": false
  }
}
```

Returns metadata only (Stage 1). Use `get_skill` to read the full SKILL.md body.

---

## Tool: `install_skill`

The unique-to-iknowkungfu wedge. An agent mid-task can pull a skill into its own host's canonical skills directory.

```jsonc
{
  "name": "install_skill",
  "arguments": {
    "id": "samuelgudi/rust-tokio",
    "version": "0.9.0",         // optional; defaults to latest non-yanked
    "agent": "claude-code"      // optional; auto-detected from environment
  }
}
```

The server invokes the matching adapter (one of `claude-code`, `hermes`, `codex`, `opencode`, `pi`, `openclaw`). Each adapter writes to its host's canonical location:

* claude-code → `~/.claude/skills/<id>/`
* hermes → `~/.hermes/skills/<id>/`
* codex → `~/.codex/skills/<id>/`
* opencode → `~/.opencode/skills/<id>/`
* pi → host-defined path
* openclaw → host-defined path

The skill is verified against its content hash from `registry.json`. Yanked versions are hard-refused (no `--allow-yanked` override).

---

## Determinism

The MCP `search` tool inherits the determinism contract from the underlying ranker: identical (registry version, query) → identical results. Agents can therefore cache results by (query, registry_version) safely.

`registry_version` is in every `search` response so an agent can detect when its cache is stale.

---

## Security

* **Read tools** (`search`, `get_skill`, `get_skill_file`, `list_*`) read only from the local cache. No network calls.
* **`update_registry`** fetches `registry.json` over HTTPS from GitHub raw. Rollback-guarded by `generated_at` timestamp comparison — a fetched older registry refuses to overwrite a cached newer one.
* **`install_skill`** writes files to the agent host's canonical skills directory. Marker files (`.iknowkungfu-marker.json`) record install provenance for `verify` and `uninstall`.
* **`get_skill_file`** rejects path-traversal: `file_path` is resolved and required to live under the skill's directory. Tested in `tests/test_mcp_server.py`.

---

## Stdio protocol

Standard MCP stdio:

* Messages are line-delimited JSON-RPC 2.0 objects
* One message per line on stdin → one response line on stdout
* stderr is for server logs only — clients should not parse it as protocol
* UTF-8 throughout (server reconfigures stdio at entry)

JSON-RPC error codes:

| Code | Meaning |
|---|---|
| `-32700` | Parse error (invalid JSON) |
| `-32600` | Invalid request (missing `method`, non-object body) |
| `-32601` | Method not found (unknown method or unknown tool name) |
| `-32602` | Invalid params (e.g. `arguments` is not an object) |
| `-32603` | Internal error (a tool crashed unexpectedly) |

Tool-level errors (bad query syntax, registry missing, skill not found) come back as `result.isError = true` with the error message in `content[0].text` — not as JSON-RPC errors. This matches the MCP convention.

---

## Troubleshooting

**"No registry cached locally. Call `update_registry` first."**
First-run state. Call the `update_registry` tool, then retry.

**`MCP server gave no response.`**
The server crashed during import or initialization. Check stderr. Common causes: not installed (`pip install` first), Python version mismatch (requires 3.10+).

**Search returns 0 results for queries you expect to match.**
Are you using uppercase boolean keywords? `and` lowercase is a literal term, not AND.

**`Query syntax error: OR across FTS5 and SQL fields is not supported.`**
v1 limitation — see `docs/query-language.md` § Limitations. Workaround: split the query.

**Path-traversal error from `get_skill_file`.**
The `file_path` argument escapes the skill's directory. Check that the path is relative and doesn't contain `..`.

---

## See also

- `docs/query-language.md` — full query DSL reference
- `docs/superpowers/specs/2026-05-12-mcp-and-search-design.md` — design rationale, decision tables, alternatives considered
- `tests/test_mcp_server.py` — protocol-level test cases (28 tests)
- `tests/test_mcp_subprocess.py` — subprocess wire-up tests (4 tests)
