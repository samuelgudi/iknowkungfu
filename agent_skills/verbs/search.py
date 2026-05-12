"""search verb — query the registry via the deterministic FTS5 search engine.

Wires the CLI to agent_skills.search.ranker. Auto-builds / refreshes the FTS5
index from the cached registry.json on each invocation so the user never has
to think about index maintenance.

Backwards compatibility: the legacy `--agent`, `--category`, `--tag` flags
still work for one release cycle; they're translated to DSL prefixes with a
deprecation warning on stderr.
"""
import json
import sys
from pathlib import Path

from agent_skills.cache import db_path, load_registry
from agent_skills.search.index import build_index, is_stale
from agent_skills.search.ranker import CompilerError, SearchResult
from agent_skills.search.ranker import search as run_search


_DEPRECATED_FLAGS = ("agent", "category", "tag")


def _ensure_index() -> Path | None:
    """Build or refresh the FTS5 index from the cached registry.json. Returns
    the db path, or None if no registry is cached yet."""
    registry = load_registry()
    if registry is None:
        return None
    db = db_path()
    if is_stale(db, registry.get("generated_at", "")):
        build_index(registry, db)
    return db


def _build_query_from_args(args) -> str:
    """Compose a DSL query string from positional terms + deprecated flags.

    Deprecated flag → DSL prefix:
      --agent A   →  agent:A
      --category C → category:C
      --tag T     →  tag:T

    Emits a stderr warning when any deprecated flag is used.
    """
    parts: list[str] = []
    deprecated_used: list[str] = []

    for flag in _DEPRECATED_FLAGS:
        value = getattr(args, flag, None)
        if value:
            parts.append(f"{flag}:{value}")
            deprecated_used.append(f"--{flag}")

    # Positional terms become the free-text portion of the query.
    terms = getattr(args, "terms", None) or []
    if isinstance(terms, str):
        terms = [terms]
    parts.extend(terms)

    if deprecated_used:
        flags = ", ".join(deprecated_used)
        print(
            f"Warning: {flags} are deprecated. Use the query DSL instead "
            f"(e.g. `kfu search 'tag:rust agent:claude-code'`). "
            f"These flags will be removed in v0.2.0.",
            file=sys.stderr,
        )

    return " ".join(parts)


def _emit_json(result: SearchResult) -> None:
    print(
        json.dumps(
            {
                "total": result.total,
                "offset": result.offset,
                "limit": result.limit,
                "registry_version": result.registry_version,
                "results": list(result.results),
            },
            indent=2,
        )
    )


def _emit_ndjson(result: SearchResult) -> None:
    for item in result.results:
        print(json.dumps(item))


def _emit_pretty(result: SearchResult) -> None:
    if not result.results:
        print(
            "No skills match. Try a broader query, or filter by `category:` "
            "(one of: dev, media, ops, data, comms, docs, meta, ai)."
        )
        return
    for i, item in enumerate(result.results, 1):
        star = " ★" if i == 1 else "  "
        print(f"  {star} {i}  {item['id']:40s} v{item['version']}")
        print(f"       {item['description']}")
        tags = " ".join(f"#{t}" for t in item.get("tags", []))
        env_vars = [
            r.split(":", 1)[1]
            for r in item.get("requires", [])
            if r.startswith("env_var:")
        ]
        req_part = " · requires " + " + ".join(env_vars) if env_vars else ""
        print(f"       {tags}{req_part}")
        print()
    if result.total > len(result.results):
        rest = result.total - (result.offset + len(result.results))
        if rest > 0:
            print(
                f"  … {rest} more match. Use --limit/--offset to page."
            )


def run(args) -> int:
    db = _ensure_index()
    if db is None:
        print("Run `kfu update` first.", file=sys.stderr)
        return 1

    query = _build_query_from_args(args)

    try:
        result = run_search(
            query,
            db_path=db,
            limit=max(1, int(getattr(args, "limit", 5))),
            offset=max(0, int(getattr(args, "offset", 0))),
            include_deprecated=bool(getattr(args, "include_deprecated", False)),
        )
    except CompilerError as e:
        print(f"Query error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"Invalid query: {e}", file=sys.stderr)
        return 2

    if getattr(args, "json", False):
        _emit_json(result)
    elif getattr(args, "ndjson", False):
        _emit_ndjson(result)
    else:
        _emit_pretty(result)
    return 0
