# MCP server + deterministic search — design spec

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Status | **Draft for review** — decisions in § 7 need Samuel's confirmation before implementation |
| Project | I Know Kung Fu (`iknowkungfu`) |
| Prior work | Session 5 / Session 6 plan, ADR-001 |
| Implements | Session-6 Phase 3 ("Dynamic discovery MCP server" — the new feature) |
| Phase | B (Phase A — namespace claim — is complete) |

This spec captures the MCP server design + the search-engine UX that agents need to query the skills registry deterministically. Read this before writing code.

---

## 1. Context

### 1.1 What already exists

The repo ships these CLI verbs (`agent_skills/verbs/`): `init`, `install`, `list`, `search`, `show`, `submit`, `update`, `uninstall`, `verify`, `yank`, `issue`, `deprecate`. Six host adapters: claude-code, hermes, codex, opencode, pi, openclaw.

Existing search (`agent_skills/verbs/search.py` → `clients/skill_discovery/match.py`):

- **Backend**: in-memory Jaccard + IDF scoring over a cached `registry.json`.
- **Filters**: agent, category, tag, platform, archived. All as kwargs, not in the query string.
- **Cache**: `~/.cache/agent-skills/registry.json` with rollback-guard on `generated_at` timestamp; sibling shallow `registry-repo` clone for `install`.
- **Yanks**: separate `~/.cache/agent-skills/yanks.json`.

This works for a CLI human typing a 2-3 word query against ~10–100 skills. It does **not** scale to a search-engine-grade UX where an agent constructs a structured query with field filters, boolean operators, and phrase matching.

### 1.2 What's missing

1. **No MCP server.** Agents running in Claude Code / OpenClaw / etc. can't query the registry as a tool — they have to shell out to the CLI, which is a fragile UX inside an agent loop.
2. **Search is filter-poor.** Filters are dict-kwargs, not part of the query language. Agents can't express "rust skills compatible with claude-code that don't require env vars" in a single string.
3. **Not search-engine-grade.** No phrase queries (`"foo bar"`), no boolean ops, no field-prefixed filters (`tag:rust`), no version-range queries, no prefix queries (`rust*`).
4. **Determinism is implicit.** Same query *probably* returns same results today because the ranking is pure-function, but there's no contract or test guaranteeing it.

### 1.3 What competitors do differently

- **Skyll** (skyll.app): runtime MCP search, federated source aggregation, hosted REST API, no versioning, no signing. Mental model: *search engine for skill repos.*
- **agent-skills-hub, agensi.io, etc.**: hosted marketplace, GraphQL/REST API, server-side ranking.
- **Kiln-AI/Kiln**: includes "Skills" as a feature inside a broader build/eval platform. No first-class registry.

**Our wedge**: local-first deterministic search backed by SQLite FTS5, plus the unique `install_skill` MCP tool that writes the skill to the host's canonical directory via the adapter system. No competitor has both.

---

## 2. Goals

1. Agents can query the skills registry **like a search engine** — phrase queries, boolean operators, field filters, prefix matching, version constraints.
2. Search is **deterministic** — same query against same registry version → identical result order. Reproducibility is a first-class property.
3. **Local-first** — search runs against a SQLite database on the agent's machine. No hosted dependency. Works offline once the registry has been pulled.
4. The same query language works in the **MCP server** (machine-facing) and the **CLI** (human-facing).
5. `install_skill` is exposed via MCP so an agent mid-task can pull a needed skill into its host's canonical skills directory.
6. Existing verbs (install, submit, yank, etc.) are reusable from the MCP layer — no code duplication.

## 3. Non-goals

1. **Semantic / embedding-based search** in v1. Adds non-determinism, model-version drift, and weight. Plausible as an optional v2 secondary signal.
2. **Hosted SaaS** (`mcp.iknowkungfu.app`). Stdio-local first. HTTP-SSE later only if there's demand.
3. **Real-time index updates**. Index refreshes on explicit `update_registry()` or via background process — not push-based.
4. **GraphQL / REST API surface**. The MCP tool surface IS our API. Anyone needing GraphQL can build a server on top.
5. **Authentication for reads**. Read access is open. Auth is host-adapter-mediated for write actions (install), not server-mediated.
6. **Custom ranking algorithms**. FTS5 BM25 is the default and only ranker in v1. Custom ranking is a v3+ concern if at all.

---

## 4. Architecture overview

```
┌────────────────────────────────────────────────────────────────┐
│                      Agent runtime                             │
│  (Claude Code / OpenClaw / Codex / Cursor / hermes / pi)       │
└───────────┬────────────────────────────────────────────────────┘
            │ MCP (stdio)
            ▼
┌────────────────────────────────────────────────────────────────┐
│              iknowkungfu.mcp (new sub-package)                 │
│  Tools: search, get_skill, get_skill_file, install_skill,      │
│         list_categories, list_tags, list_agents,               │
│         update_registry                                        │
└─────────────┬──────────────────────────────────────────────────┘
              │ reuses
              ▼
┌────────────────────────────────────────────────────────────────┐
│         Existing layers (unchanged, reused as libraries)       │
│  ┌────────────────────┐  ┌────────────────────────────────┐    │
│  │ agent_skills.verbs │  │ clients.skill_discovery        │    │
│  │ install/submit/etc │  │ match.rank() — fallback        │    │
│  └────────────────────┘  │ update.refresh() — kept        │    │
│                          └────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ NEW: clients.skill_search                                │  │
│  │   index.py    — builds SQLite FTS5 from registry.json    │  │
│  │   query.py    — parses query DSL → FTS5 SQL              │  │
│  │   ranker.py   — runs query, returns ranked results       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────┬──────────────────────────────────────────────────┘
              │
              ▼
┌────────────────────────────────────────────────────────────────┐
│            ~/.cache/iknowkungfu/                               │
│   registry.json       — source of truth (canonical metadata)   │
│   registry.json.sig   — optional signature                     │
│   registry.db         — derived FTS5 index (regenerable)       │
│   registry.db.version — generated_at of the registry.json the  │
│                         .db was built from (for staleness)     │
│   yanks.json          — yank/deprecation overlay               │
│   registry-repo/      — shallow git clone for install verb     │
└────────────────────────────────────────────────────────────────┘
```

Key principles:

- **`registry.json` stays the canonical source.** `registry.db` is a derived view, regenerable from `registry.json` deterministically. If users delete `registry.db`, it gets rebuilt on next search.
- **`update_registry` is a single command** that pulls new `registry.json`, rebuilds `registry.db`, and syncs the `registry-repo` clone. Atomic.
- **MCP server is thin.** It's a tool-surface wrapper over existing functions, plus the new search layer.

---

## 5. MCP tool surface

Eight tools. Each below has name, signature, JSON schema, and behavior.

### 5.1 `search` — Stage 1 (metadata-only ranked results)

```json
{
  "name": "search",
  "description": "Search the skills registry. Returns ranked metadata-only results. Supports query DSL with field filters, boolean ops, phrase queries, and version constraints.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Query string in the DSL. Examples: 'rust serialization', 'tag:rust agent:claude-code', '\"exact phrase\" -deprecated', 'name:format* tag:rust version:>=1.0'."
      },
      "limit": { "type": "integer", "default": 20, "minimum": 1, "maximum": 200 },
      "offset": { "type": "integer", "default": 0, "minimum": 0 },
      "include_deprecated": { "type": "boolean", "default": false }
      // TODO v2: "include_yanked" once yanks.json overlay is integrated.
      // Removed from v1 ranker signature on 2026-05-12 (review finding #2 —
      // dead-code shim that promised behavior the engine doesn't deliver yet).
    },
    "required": ["query"]
  }
}
```

Returns:
```json
{
  "total": 47,
  "offset": 0,
  "limit": 20,
  "registry_version": "2026-05-10T14:23:00Z",
  "results": [
    {
      "id": "samuelgudi/rust-serde-helpers",
      "version": "1.2.0",
      "name": "Rust Serde Helpers",
      "description": "...",
      "tags": ["rust", "serialization"],
      "agent_compat": ["claude-code", "openclaw"],
      "category": "language-specific",
      "license": "MIT",
      "score": 14.27,
      "yanked": false,
      "deprecated": false
    },
    ...
  ]
}
```

### 5.2 `get_skill` — Stage 2 (full SKILL.md body)

```json
{
  "name": "get_skill",
  "description": "Fetch the full SKILL.md body and metadata for a specific skill at a specific version.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "id": { "type": "string", "description": "Skill ID, e.g. 'samuelgudi/rust-serde-helpers'." },
      "version": { "type": "string", "description": "Semver. Defaults to latest non-yanked." }
    },
    "required": ["id"]
  }
}
```

Returns: full SKILL.md (frontmatter + body) + list of available resource files (`scripts/`, `references/`, `assets/`).

### 5.3 `get_skill_file` — Stage 3 (individual resource files)

```json
{
  "name": "get_skill_file",
  "description": "Fetch a specific resource file from a skill's scripts/, references/, or assets/ directory.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "id": { "type": "string" },
      "file_path": { "type": "string", "description": "Path relative to the skill directory, e.g. 'scripts/helpers.py'." },
      "version": { "type": "string" }
    },
    "required": ["id", "file_path"]
  }
}
```

Returns: file content (text or base64-encoded for binaries) + content-type.

### 5.4 `install_skill` — the differentiation wedge

```json
{
  "name": "install_skill",
  "description": "Install a skill into the host agent's canonical skills directory. Uses the appropriate adapter for the detected (or specified) host.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "id": { "type": "string" },
      "version": { "type": "string" },
      "agent": {
        "type": "string",
        "description": "Override the auto-detected host. One of: claude-code, hermes, codex, opencode, pi, openclaw.",
        "enum": ["claude-code", "hermes", "codex", "opencode", "pi", "openclaw"]
      }
    },
    "required": ["id"]
  }
}
```

Returns: `{ "installed_at": "...", "marker_path": "...", "host": "claude-code", "install_log": [...] }`.

**This is the wedge no competitor offers.** An agent mid-task in Claude Code can call `install_skill("samuelgudi/some-skill", agent="claude-code")` and the skill becomes available in `~/.claude/skills/` immediately.

### 5.5 Discovery helpers

```json
{ "name": "list_categories", "inputSchema": { "type": "object", "properties": {} } }
{ "name": "list_tags",       "inputSchema": { "type": "object", "properties": {"prefix": {"type": "string"}, "limit": {"type": "integer", "default": 100}} } }
{ "name": "list_agents",     "inputSchema": { "type": "object", "properties": {} } }
```

These return the cardinality and values an agent can use to build queries. E.g. `list_tags(prefix="rust")` → `["rust", "rust-async", "rust-macros", ...]`.

### 5.6 `update_registry`

```json
{
  "name": "update_registry",
  "description": "Pull the latest registry.json, rebuild the FTS5 index, sync the git clone. Returns the registry_version after refresh.",
  "inputSchema": { "type": "object", "properties": {} }
}
```

Returns: `{ "previous_version": "...", "current_version": "...", "skills_added": 3, "skills_yanked": 1, "skills_deprecated": 0 }`.

---

## 6. Query language spec

Lucene-style DSL. Same parser in MCP `search` tool and CLI `iknowkungfu search` command.

### 6.1 Grammar

```
query        := term (whitespace term)*
term         := free_text | phrase | field_filter | boolean_op | prefix | negation
free_text    := word           # matches in name/description/body
phrase       := "..."          # exact phrase match
field_filter := field:value    # e.g. tag:rust
boolean_op   := AND | OR | NOT # uppercase; default between terms is AND
prefix       := word*          # prefix match, e.g. rust*
negation     := -term          # exclude matches
```

### 6.2 Supported fields

| Field | Type | Example | Notes |
|---|---|---|---|
| `name` | text | `name:format*` | Skill display name |
| `id` | text | `id:samuelgudi/*` | Full skill id, supports prefix |
| `tag` | exact | `tag:rust` | Repeatable; multiple = OR within field |
| `category` | exact | `category:devops` | |
| `agent` | exact | `agent:claude-code` | Repeatable; multiple = OR |
| `license` | exact | `license:MIT` | |
| `author` | exact | `author:samuelgudi` | Numeric GitHub ID match, not handle |
| `version` | range | `version:>=1.0`, `version:1.2.0`, `version:<2.0` | Semver |
| `status` | exact | `status:active`, `status:deprecated` | |
| `requires` | exact | `requires:env_var:OPENAI_API_KEY` | Detects skills that require named env vars |

### 6.3 Worked examples

```
# Find rust serialization skills compatible with claude-code
rust serialization tag:rust agent:claude-code

# Exact phrase, exclude deprecated
"binary data parsing" -status:deprecated

# Prefix match on name, version constraint
name:format* version:>=1.0

# Multi-tag OR + agent filter
(tag:rust OR tag:go) agent:claude-code

# Skills that DON'T require env vars
NOT requires:env_var:*

# By author + license
author:samuelgudi license:MIT
```

### 6.4 Determinism contract

Given:
- a fixed `registry_version` (the `generated_at` timestamp on `registry.json`)
- a fixed query string

The result list is **byte-identical** across runs, machines, and Python versions. This is enforced by:

1. FTS5 BM25 scoring is deterministic (no randomness).
2. Tie-breaking is total-ordered: `(-score, -semver_tuple, id ASC)`.
3. The FTS5 tokenizer is `unicode61 remove_diacritics=2` (fixed configuration).
4. No floating-point dependence on hardware (BM25 uses double-precision identically on any IEEE 754 platform).

A test will assert this: build a fixed `registry.json`, run a fixed query, assert the result hash matches a recorded fixture.

---

## 7. Decisions table

The six load-bearing decisions, each with my recommended call + rationale + alternatives. **Samuel: please review and override where you disagree.**

| # | Decision | Recommend | Why | Alternatives |
|---|---|---|---|---|
| D1 | Search backend | **SQLite FTS5** | Stdlib (sqlite3), deterministic BM25, supports phrase/prefix/field queries natively, ~1ms queries at 10K skills, single-file index, zero new deps | (a) Keep in-memory Jaccard+IDF — too weak for search-engine UX. (b) Whoosh — pure-Python FTS but external dep, slower. (c) Tantivy via PyO3 — Rust-fast but new dep + binary |
| D2 | Transport | **stdio first; HTTP-SSE optional later** | Claude Code spawns MCP servers locally — stdio is the canonical transport. HTTP-SSE adds hosting cost without immediate user benefit. | All-HTTP-SSE: requires hosting + auth + rate limits = months of yak-shaving. Hybrid: yes for v2. |
| D3 | Auth model | **None for read; install gated by adapter, not server** | Read is open (this is a public registry). `install_skill` writes to the user's *own* filesystem via their host's adapter — the adapter already has the permissions, not the MCP server. | Token-based auth for reads: unnecessary friction for the dominant case (open OSS registry). Per-host policy: overengineering for v1. |
| D4 | Server location | **Sub-package `iknowkungfu.mcp` in same repo** | Reuses all existing verbs as libraries. One install (`pip install iknowkungfu`) gives both CLI and MCP. Easier release management. | Separate repo: harder release coordination, code duplication. Both: deferred decision until there's a reason. |
| D5 | Tool surface | **8 tools** (search, get_skill, get_skill_file, install_skill, list_categories, list_tags, list_agents, update_registry) | Maps cleanly to agentskills.io's progressive-disclosure stages 1-3, plus the install wedge, plus discovery helpers, plus refresh. Each tool has one clear job. | Fewer tools (collapse list_* into search): less discoverable for agents. More tools (separate get_metadata vs get_body): overkill. |
| D6 | Skill data source | **registry.json (canonical) → FTS5 db (derived)**. For skill files: GitHub raw via repo clone. | Single source of truth, deterministic derivation, no hosted dependency, signature-verifiable. | Pre-built shipped `.db`: distribution headache, harder to verify integrity. GitHub raw for everything: fragile if a repo moves. |

---

## 8. CLI changes

The existing `agent-skills search` becomes `iknowkungfu search` (post-rename) and gains:

- Full query DSL: `iknowkungfu search 'rust agent:claude-code tag:async'`
- Pretty terminal output (current behavior) + `--json` (current behavior) + new `--ndjson` for streaming
- New flags: `--limit`, `--offset`, `--include-deprecated`, `--include-yanked`
- Backwards compat: bare-word queries (`iknowkungfu search foo bar`) still work — parser treats them as multi-word free-text AND

Other CLI verbs gain corresponding query-DSL support where useful (e.g. `iknowkungfu list 'tag:rust'` instead of `--tag rust`).

The existing `--tag`, `--category`, `--agent` flags are preserved (deprecated, with notice) for one release cycle, then removed.

---

## 9. Implementation order

Each phase is one PR-worth of work. Sequence matters; later phases depend on earlier.

### B1 — Query DSL parser (no integration yet)

- Create `agent_skills/search/query.py` with a hand-written recursive-descent parser
- Parses DSL → AST → FTS5 SQL fragment
- Stand-alone unit tests; no other code touched
- ~300 LOC including tests

### B2 — FTS5 index builder

- Create `agent_skills/search/index.py` with `build_index(registry: dict, db_path: Path)` and `is_stale(db_path, registry_version) -> bool`
- Schema: virtual table with `id`, `name`, `description`, `tags`, `body`, `category`, `agent_compat`, `license`, `author`, `version`, `status`, `requires`
- Tokenizer config fixed for determinism
- Rebuild is atomic (write to `.tmp.db`, fsync, rename)
- ~200 LOC + tests with fixture registries

### B3 — Search runner

- Create `agent_skills/search/ranker.py` exposing `search(query: str, *, db_path, limit, offset, include_deprecated, include_yanked) -> SearchResult`
- Combines parser + FTS5 + post-filtering for fields FTS5 doesn't handle (version range, requires)
- ~150 LOC + tests

### B4 — CLI integration

- Replace internal call in `agent_skills/verbs/search.py` from `match.rank()` to `search.ranker.search()`
- Keep old flags for one cycle with deprecation warning
- Add `--json`, `--ndjson`, `--limit`, `--offset`, `--include-*`
- Backfill tests for the deprecated-flag adapter
- ~100 LOC

### B5 — MCP server scaffold

- New sub-package `agent_skills/mcp/`:
  - `__main__.py` — stdio MCP server entry point
  - `tools/search.py`, `tools/get_skill.py`, `tools/install_skill.py`, etc. — one module per tool
  - `schemas/` — JSON schemas alongside
- Each tool is a thin function calling existing verbs/search
- Add `[project.scripts]` entry: `iknowkungfu-mcp = "agent_skills.mcp.__main__:main"`
- ~500 LOC + tests using `mcp` library's test harness

### B6 — End-to-end test + dogfood

- Run a real MCP session via Claude Code: search → get_skill → install_skill
- Verify the skill ends up at `~/.claude/skills/<skill>/SKILL.md`
- Verify determinism: same query → same result hash across 10 runs

### B7 — Documentation

- README section: "Using the MCP server"
- `docs/mcp-integration.md` for Claude Code / Cursor / OpenClaw setup
- `docs/query-language.md` with worked examples

---

## 10. Open questions for Samuel

These are decisions where I have a leaning but want to confirm before committing:

1. **Registry distribution**: keep current GitHub raw URL for `registry.json`, or move to a CDN (`registry.iknowkungfu.io/v1/registry.json`)? GitHub raw works; CDN gives more control + analytics. *My lean: GitHub raw for now, CDN when traffic justifies.*

2. **Index distribution**: build `registry.db` on the client (cheap, ~1s for 1K skills) or ship a pre-built one alongside `registry.json`? *My lean: build on client. Smaller download, signature-verifiable via the source `registry.json`.*

3. **MCP CLI name**: when registered as an MCP server in Claude Code, what command name? Options: `iknowkungfu`, `iknowkungfu-mcp`, `kfu-mcp`. *My lean: `iknowkungfu-mcp` — explicit + matches the convention of `<brand>-mcp`.*

4. **install_skill error semantics**: if a skill needs env vars that aren't set, install fails or warns? *My lean: warn + install anyway. The agent calling `install_skill` knows what it's doing; failing-closed creates UX friction.*

5. **Semantic search as v2**: should the spec leave a hook for embedding-based ranking as a future secondary signal? *My lean: yes — add a `ranker` parameter to `search()` even if only BM25 is supported in v1.*

---

## 11. Cross-references

- ADR-001 — `docs/decisions.md` (the rename to I Know Kung Fu)
- Session 6 plan — `docs/handoff/2026-05-12-execution-handoff-session6.md` § Phase 3
- Existing search code — `agent_skills/verbs/search.py`, `clients/skill_discovery/match.py`, `clients/skill_discovery/update.py`
- agentskills.io spec — progressive disclosure (Stages 1-3)
- Skyll comparison — `docs/handoff/2026-05-12-execution-handoff-session6.md` § "skyll — the competitor"

---

## 12. What this spec does NOT cover

- README rewrite (Phase 1 of session-6 plan)
- v0.1.2 release mechanics (Phase 2)
- Adapter expansion to Gemini CLI, Cursor, Copilot, etc. (Phase 4)
- Outreach / launch (Phase 5)

Those are separate concerns. This spec is strictly about the MCP server + deterministic search engine.

End of spec.
