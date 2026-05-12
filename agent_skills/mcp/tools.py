"""MCP tool implementations.

Each tool is a small function that takes a dict of arguments and returns a
dict result. Tools reuse existing verbs / search modules — they're thin
wrappers, not reimplementations.

Schemas are JSON Schema Draft 2020-12.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from agent_skills.cache import cache_dir, db_path, load_registry
from agent_skills.search.index import build_index, is_stale
from agent_skills.search.ranker import CompilerError
from agent_skills.search.ranker import search as run_search


# ─── Shared helpers ────────────────────────────────────────────────────────


class ToolError(Exception):
    """Raised by a tool when execution fails. The message becomes the MCP error text."""


def _ensure_index() -> Path:
    """Build or refresh the FTS5 index. Raises ToolError if no registry cached."""
    registry = load_registry()
    if registry is None:
        raise ToolError(
            "No registry cached locally. Call the `update_registry` tool first "
            "to fetch the latest skills registry."
        )
    db = db_path()
    if is_stale(db, registry.get("generated_at", "")):
        build_index(registry, db)
    return db


def _load_registry_json() -> dict[str, Any]:
    """Load the cached registry.json or raise ToolError."""
    reg = load_registry()
    if reg is None:
        raise ToolError(
            "No registry cached locally. Call `update_registry` first."
        )
    return reg


# ─── Tool: search ───────────────────────────────────────────────────────────

def tool_search(args: dict[str, Any]) -> dict[str, Any]:
    if "query" not in args:
        raise ToolError("Missing required argument: query")
    db = _ensure_index()
    try:
        result = run_search(
            args["query"],
            db_path=db,
            limit=int(args.get("limit", 20)),
            offset=int(args.get("offset", 0)),
            include_deprecated=bool(args.get("include_deprecated", False)),
        )
    except CompilerError as e:
        raise ToolError(f"Query syntax error: {e}") from e
    except ValueError as e:
        raise ToolError(f"Invalid arguments: {e}") from e
    return {
        "total": result.total,
        "offset": result.offset,
        "limit": result.limit,
        "registry_version": result.registry_version,
        "results": list(result.results),
    }


SCHEMA_SEARCH = {
    "name": "search",
    "description": (
        "Search the skills registry. Returns ranked metadata-only results "
        "(Stage 1 of agentskills.io progressive disclosure). The query is a "
        "Lucene-style DSL supporting free-text, phrases (\"...\"), prefixes "
        "(rust*), field filters (tag:rust, agent:claude-code, version:>=1.0), "
        "boolean operators (AND, OR, NOT), and negation (-deprecated). "
        "Determinism contract: identical query against the same registry "
        "version always produces identical results."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Query DSL. Examples: 'rust serialization', "
                    "'tag:rust agent:claude-code', "
                    "'\"binary parsing\" -status:deprecated', "
                    "'name:format* version:>=1.0'."
                ),
            },
            "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 200},
            "offset": {"type": "integer", "default": 0, "minimum": 0},
            "include_deprecated": {"type": "boolean", "default": False},
        },
        "required": ["query"],
    },
}


# ─── Tool: get_skill ───────────────────────────────────────────────────────

def tool_get_skill(args: dict[str, Any]) -> dict[str, Any]:
    if "id" not in args:
        raise ToolError("Missing required argument: id")
    reg = _load_registry_json()
    skill_id = args["id"]
    version = args.get("version")
    for s in reg.get("skills", []):
        if s["id"] != skill_id:
            continue
        if version is not None and s.get("version") != version:
            # Version pinning at metadata level — exact match required.
            # Older-version SKILL.md retrieval is a future feature.
            continue
        # Try to load SKILL.md body from the registry-repo clone.
        body = ""
        repo = cache_dir() / "registry-repo"
        skill_path = repo / s.get("source", {}).get("path", "")
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            try:
                body = skill_md.read_text(encoding="utf-8")
            except OSError:
                pass
        files = []
        if skill_path.exists():
            for f in sorted(skill_path.rglob("*")):
                if f.is_file():
                    files.append(str(f.relative_to(skill_path)).replace("\\", "/"))
        return {"metadata": s, "body": body, "files": files}
    raise ToolError(f"Skill not found: {skill_id}" + (f"@{version}" if version else ""))


SCHEMA_GET_SKILL = {
    "name": "get_skill",
    "description": (
        "Fetch the full SKILL.md body and metadata for a specific skill "
        "(Stage 2 of progressive disclosure). Returns the metadata, the "
        "SKILL.md body text, and a list of available resource file paths."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Skill ID, e.g. 'samuelgudi/rust-serde'."},
            "version": {"type": "string", "description": "Semver. Defaults to latest."},
        },
        "required": ["id"],
    },
}


# ─── Tool: get_skill_file ──────────────────────────────────────────────────

def tool_get_skill_file(args: dict[str, Any]) -> dict[str, Any]:
    if "id" not in args:
        raise ToolError("Missing required argument: id")
    if "file_path" not in args:
        raise ToolError("Missing required argument: file_path")
    reg = _load_registry_json()
    skill_id = args["id"]
    file_path = args["file_path"]
    for s in reg.get("skills", []):
        if s["id"] != skill_id:
            continue
        # Review finding #4: an empty/missing source.path would collapse
        # `base` to the repo root, breaking the "stay inside this skill"
        # invariant. A malformed skill could then be used to read any other
        # skill's files via this tool. Treat empty source.path as a hard error.
        source_path = (s.get("source", {}) or {}).get("path", "").strip()
        if not source_path:
            raise ToolError(
                f"Skill {skill_id!r} has no source.path; cannot serve files."
            )
        repo = cache_dir() / "registry-repo"
        base = (repo / source_path).resolve()
        repo_root = repo.resolve()
        # Defense in depth: even after the source_path check, ensure `base`
        # didn't accidentally resolve to the repo root.
        if base == repo_root:
            raise ToolError(
                f"Skill {skill_id!r} source.path resolved to registry root; refusing."
            )
        # Path-traversal guard: resolve and ensure the file is under `base`.
        target = (base / file_path).resolve()
        try:
            target.relative_to(base)
        except ValueError as e:
            raise ToolError(
                f"file_path {file_path!r} escapes the skill directory"
            ) from e
        if not target.exists() or not target.is_file():
            raise ToolError(f"File not found in skill: {file_path}")
        try:
            content = target.read_text(encoding="utf-8")
            return {"content": content, "encoding": "utf-8", "path": file_path}
        except UnicodeDecodeError:
            import base64
            content_b = target.read_bytes()
            return {
                "content": base64.b64encode(content_b).decode("ascii"),
                "encoding": "base64",
                "path": file_path,
            }
    raise ToolError(f"Skill not found: {skill_id}")


SCHEMA_GET_SKILL_FILE = {
    "name": "get_skill_file",
    "description": (
        "Fetch a specific resource file from a skill's scripts/, references/, "
        "or assets/ directory (Stage 3 of progressive disclosure). Returns "
        "file content; binary files are base64-encoded."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "file_path": {
                "type": "string",
                "description": "Path relative to the skill directory, e.g. 'scripts/helpers.py'.",
            },
            "version": {"type": "string"},
        },
        "required": ["id", "file_path"],
    },
}


# ─── Tool: install_skill ───────────────────────────────────────────────────

def tool_install_skill(args: dict[str, Any]) -> dict[str, Any]:
    if "id" not in args:
        raise ToolError("Missing required argument: id")
    skill_id = args["id"]
    version = args.get("version")
    agent = args.get("agent")  # auto-detect if not given
    spec = f"{skill_id}@{version}" if version else skill_id
    cmd = [sys.executable, "-m", "agent_skills.cli", "install", spec]
    if agent:
        cmd += ["--agent", agent]
    cmd += ["--json"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=120
        )
    except subprocess.TimeoutExpired as e:
        raise ToolError("install_skill timed out after 120s") from e
    except FileNotFoundError as e:
        raise ToolError(
            f"Failed to spawn the install subprocess (sys.executable={sys.executable!r}): {e}"
        ) from e
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise ToolError(
            f"install failed (exit {proc.returncode}): {err or out}"
        )
    # The install verb emits JSON on stdout when --json. Try to parse; fall
    # back to a plain message if it didn't.
    try:
        return {"exit_code": 0, "result": json.loads(out)}
    except json.JSONDecodeError:
        return {"exit_code": 0, "log": out, "stderr": err}


SCHEMA_INSTALL_SKILL = {
    "name": "install_skill",
    "description": (
        "Install a skill into the host agent's canonical skills directory. "
        "Auto-detects the host (Claude Code, OpenClaw, Codex, etc.) and uses "
        "the appropriate adapter to write the skill files. This is the "
        "unique value of this registry vs federated-search alternatives — "
        "an agent mid-task can pull a needed skill into its own toolchain."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "version": {"type": "string"},
            "agent": {
                "type": "string",
                "enum": ["claude-code", "hermes", "codex", "opencode", "pi", "openclaw"],
                "description": "Override the auto-detected host.",
            },
        },
        "required": ["id"],
    },
}


# ─── Tool: list_categories ─────────────────────────────────────────────────

def tool_list_categories(args: dict[str, Any]) -> dict[str, Any]:
    reg = _load_registry_json()
    cats: dict[str, int] = {}
    for s in reg.get("skills", []):
        c = s.get("category", "")
        if c:
            cats[c] = cats.get(c, 0) + 1
    return {"categories": [{"name": k, "count": v} for k, v in sorted(cats.items())]}


SCHEMA_LIST_CATEGORIES = {
    "name": "list_categories",
    "description": "List all categories in the registry with skill counts.",
    "inputSchema": {"type": "object", "properties": {}},
}


# ─── Tool: list_tags ───────────────────────────────────────────────────────

def tool_list_tags(args: dict[str, Any]) -> dict[str, Any]:
    reg = _load_registry_json()
    prefix = (args.get("prefix") or "").lower()
    limit = int(args.get("limit", 100))
    if limit < 1:
        raise ToolError("limit must be ≥ 1")
    counts: dict[str, int] = {}
    for s in reg.get("skills", []):
        for t in s.get("tags") or []:
            if prefix and not t.lower().startswith(prefix):
                continue
            counts[t] = counts.get(t, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return {"tags": [{"name": k, "count": v} for k, v in items]}


SCHEMA_LIST_TAGS = {
    "name": "list_tags",
    "description": (
        "List tags in the registry with skill counts. Useful for building "
        "queries — agents can call this to discover available tag values."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "prefix": {"type": "string", "description": "Optional prefix filter."},
            "limit": {"type": "integer", "default": 100, "minimum": 1},
        },
    },
}


# ─── Tool: list_agents ─────────────────────────────────────────────────────

def tool_list_agents(args: dict[str, Any]) -> dict[str, Any]:
    reg = _load_registry_json()
    counts: dict[str, int] = {}
    for s in reg.get("skills", []):
        for a in s.get("agent_compat") or []:
            counts[a] = counts.get(a, 0) + 1
    return {"agents": [{"name": k, "count": v} for k, v in sorted(counts.items())]}


SCHEMA_LIST_AGENTS = {
    "name": "list_agents",
    "description": (
        "List host agents that have at least one compatible skill, with "
        "counts. Useful for agent:X filter discovery."
    ),
    "inputSchema": {"type": "object", "properties": {}},
}


# ─── Tool: update_registry ─────────────────────────────────────────────────

def tool_update_registry(args: dict[str, Any]) -> dict[str, Any]:
    prev = load_registry()
    prev_version = (prev or {}).get("generated_at", "") if prev else ""
    cmd = [sys.executable, "-m", "agent_skills.cli", "update", "--json"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", timeout=60
        )
    except subprocess.TimeoutExpired as e:
        raise ToolError("update_registry timed out after 60s") from e
    except FileNotFoundError as e:
        raise ToolError(
            f"Failed to spawn the update subprocess (sys.executable={sys.executable!r}): {e}"
        ) from e
    if proc.returncode != 0:
        raise ToolError(
            f"update failed (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()}"
        )
    # After update, rebuild the FTS5 index too.
    new = load_registry()
    new_version = (new or {}).get("generated_at", "") if new else ""
    if new is not None:
        try:
            build_index(new, db_path())
        except (sqlite3.Error, OSError) as e:
            raise ToolError(f"registry fetched but index rebuild failed: {e}") from e
    return {
        "previous_version": prev_version,
        "current_version": new_version,
        "rebuilt_index": new is not None,
    }


SCHEMA_UPDATE_REGISTRY = {
    "name": "update_registry",
    "description": (
        "Pull the latest registry.json, rebuild the FTS5 search index, sync "
        "the local registry-repo clone. Returns previous and current "
        "registry versions for diff inspection."
    ),
    "inputSchema": {"type": "object", "properties": {}},
}


# ─── Registry of tools ─────────────────────────────────────────────────────


TOOLS: list[tuple[dict[str, Any], Callable[[dict[str, Any]], dict[str, Any]]]] = [
    (SCHEMA_SEARCH, tool_search),
    (SCHEMA_GET_SKILL, tool_get_skill),
    (SCHEMA_GET_SKILL_FILE, tool_get_skill_file),
    (SCHEMA_INSTALL_SKILL, tool_install_skill),
    (SCHEMA_LIST_CATEGORIES, tool_list_categories),
    (SCHEMA_LIST_TAGS, tool_list_tags),
    (SCHEMA_LIST_AGENTS, tool_list_agents),
    (SCHEMA_UPDATE_REGISTRY, tool_update_registry),
]


def get_tool_schemas() -> list[dict[str, Any]]:
    return [schema for schema, _ in TOOLS]


def get_tool_handler(name: str) -> Callable[[dict[str, Any]], dict[str, Any]] | None:
    for schema, handler in TOOLS:
        if schema["name"] == name:
            return handler
    return None
