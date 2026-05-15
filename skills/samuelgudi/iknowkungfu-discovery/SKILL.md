---
name: iknowkungfu-discovery
description: Search the I Know Kung Fu registry for a skill that matches the current task, inspect candidates, and install the right one for the host you are running on. Use when the user asks to find, search for, or install a skill — do not invoke reflexively for every task.
---

# I Know Kung Fu — discovery

Use this skill when the user has explicitly asked you to find, inspect, or install a skill from the I Know Kung Fu registry.

## When to use

- The user says: "is there a skill for X?", "find a skill that does Y", "search the registry for Z", "install the X skill".
- Before reaching for a third-party tool that may already be packaged as a reviewed skill.

## When NOT to use

- Reflexively, for every task. The user must have asked. Reflexive invocation pollutes session context.

## Two paths: MCP (preferred) and CLI

**MCP** — if `iknowkungfu-mcp` is registered with your host (Claude Code, Hermes, Codex, Cursor, etc.), you have eight tools without shelling out: `search`, `get_skill`, `get_skill_file`, `install_skill`, `list_categories`, `list_tags`, `list_agents`, `update_registry`. Stay in-loop and use these. `install_skill` writes the skill into the host's canonical skills directory directly.

**CLI** — if MCP is not wired, fall back to the `kfu` command:

```
kfu update                          # refresh registry cache (~/.cache/iknowkungfu/)
kfu search <query>                  # rank candidates
kfu show <author>/<slug>            # inspect one candidate
kfu install <author>/<slug>         # install for the detected host
```

## Query DSL

Both `kfu search` and the MCP `search` tool accept a Lucene-style DSL — lean on it, plain keywords degrade fast as the registry grows:

```
postgres migration                  # plain keywords
tag:rust agent:claude-code          # filter by tag and host
"binary parsing" -status:deprecated # exclude deprecated
(tag:rust OR tag:go) version:>=1.0  # version constraints
NOT requires:env_var:*              # only skills without env-var requirements
```

Determinism contract: identical `(query, registry version)` always produces identical result order. Tie-broken deterministically.

## The flow

1. **Refresh** if the cache might be stale: `kfu update` (or the MCP `update_registry` tool).
2. **Search**, filtered to the host: `kfu search "<terms>" --agent claude-code`. Skim the top three to five candidates.
3. **Inspect** the strongest match: `kfu show <id>` — confirm the description's WHEN clause matches the user's task, the `requires.commands` are available locally, and `status` is not `deprecated`.
4. **Install**: `kfu install <id>` (CLI) or `install_skill(id, agent)` (MCP). Claude Code picks up the new skill in the current session automatically; other hosts may need a reload.
5. **Multi-host environments**: if more than one host is detected, pass `--agent <host>` explicitly, or set `IKNOWKUNGFU_DEFAULT_AGENT` once.

## Limits

- BM25 ranking via SQLite FTS5; past ~30 candidates, ranking quality degrades — mitigate with `tag:` / `category:` / `agent:` filters.
- Yanked versions are hard-refused at install time. No `--allow-yanked` flag exists.
- Deprecated skills install only with `--allow-deprecated`; prefer the `superseded_by` skill the deprecation points at.
