# Query Language Reference

The query language for `iknowkungfu search` (and the MCP `search` tool) is a Lucene-style DSL: free text, phrases, field filters, boolean operators, prefixes, and version comparisons — all parsed deterministically and executed against a local SQLite FTS5 index.

> **Determinism contract**: identical (query, registry version) always returns identical results in identical order. The index is rebuilt deterministically from `registry.json`. Tested with recorded fixtures in `tests/test_determinism.py`.

---

## Quick reference

```
# Free text — matches across name, description, tags, body
rust serialization

# Phrase — must match as an exact phrase
"binary data parsing"

# Prefix — token starts with
rust*

# Field filter — exact value
tag:rust
agent:claude-code
license:MIT
category:dev
status:active
author:samuelgudi

# Prefix on a field
name:format*

# Version constraints
version:1.2.0       # exact
version:>=1.0       # gte
version:<2.0        # lt
version:>0.5        # gt

# Boolean ops (operators are UPPERCASE)
rust AND serde
rust OR go
NOT deprecated

# Negation via `-`
-deprecated
-status:deprecated

# Grouping
(tag:rust OR tag:go) agent:claude-code

# Multi-value targeting
requires:env_var:OPENAI_API_KEY
platform:linux
```

---

## Default behavior

* **Whitespace between terms is implicit `AND`.** `rust async` ≡ `rust AND async`.
* **Precedence**: `NOT` > `AND` > `OR`. Use parens to override.
* **Case sensitivity**: keywords (`AND`, `OR`, `NOT`) are case-sensitive uppercase. Lowercased they're treated as terms (`a and b` is three terms AND'd together).
* **Diacritics** are folded in indexed columns (`café` matches `cafe`). FTS5 tokenizer is `unicode61 remove_diacritics 2`.
* **Empty query** lists every skill (deprecated excluded by default).

---

## Field reference

| Field | Type | Notes |
|---|---|---|
| `name` | indexed text | Skill display name. Tokenized. |
| `description` | indexed text | Skill description. Tokenized. |
| `tag` (alias `tags`) | indexed text | Tag tokens. Tokenized. |
| `body` | indexed text | Full SKILL.md body (when present in index). |
| `id` | exact | `<author>/<slug>` primary key. |
| `category` | exact | One of: `dev`, `media`, `ops`, `data`, `comms`, `docs`, `meta`, `ai`. |
| `agent` | pipe-multi | Repeatable per skill. `agent:claude-code` matches if `claude-code` is in the skill's `agent_compat`. |
| `license` | exact | SPDX identifier. |
| `author` | exact | GitHub login. (Numeric `github_id` resolution is via a separate field — TBD.) |
| `version` | range | Semver. Supports `=`, `>=`, `<=`, `>`, `<`. Post-filtered in Python for safety. |
| `status` | exact | `active` or `deprecated`. |
| `requires` | pipe-multi | `requires:env_var:OPENAI_API_KEY`, `requires:command:ffmpeg`. |
| `platform` | pipe-multi | `linux`, `macos`, `windows`. |

**Comparison operators** (`>=`, `<=`, `>`, `<`) are valid on `version` only. Other fields require exact-match or prefix.

---

## Worked examples

### Find a skill by topic

```
rust serialization
```

Searches all indexed columns for both terms. Top BM25 score wins.

### Restrict to a specific agent + tag

```
tag:rust agent:claude-code
```

Returns rust-tagged skills compatible with Claude Code.

### Phrase + exclusion

```
"binary data parsing" -status:deprecated
```

Looks for the exact phrase, excludes deprecated skills (also excluded by default unless `--include-deprecated`).

### Either-of-N tags, scoped by agent

```
(tag:rust OR tag:go) agent:claude-code
```

Rust *or* Go skills that work with Claude Code.

### Author + license

```
author:samuelgudi license:MIT
```

### Version constraint

```
name:format* version:>=1.0
```

All skills whose name starts with `format` and version ≥ 1.0.

### Skills that require no env vars

```
NOT requires:env_var:*
```

The `*` is a prefix wildcard inside the field value; any skill that declares any `env_var:*` is excluded.

### Find what's available for a host

```
agent:openclaw category:dev
```

---

## Operators reference

| Operator | Example | Notes |
|---|---|---|
| (whitespace) | `rust async` | Implicit AND |
| `AND` | `rust AND async` | Explicit AND. Same as whitespace. |
| `OR` | `tag:rust OR tag:go` | Lower precedence than AND. |
| `NOT` | `NOT deprecated` | Unary, prefix. |
| `-` | `-deprecated` | Shorthand for `NOT deprecated`. |
| `"..."` | `"exact phrase"` | Phrase match. Tokens must appear in order. |
| `term*` | `rust*` | Prefix match. |
| `(...)` | `(a OR b) AND c` | Grouping. |
| `field:value` | `tag:rust` | Field-targeted filter. |
| `field:>=N` | `version:>=1.0` | Comparison operators on `version`. |
| `field:value*` | `name:format*` | Prefix on a field. |

---

## Limitations (v1)

These are documented constraints; PRs welcome.

1. **OR across FTS5/SQL boundaries is rejected.** `tag:rust OR license:MIT` raises a `CompilerError` because the tag is in FTS5-indexed land while license is SQL-filtered. Workaround: split the query, or contact maintainers for UNION support.
2. **Pre-release semver components** (`-rc.1`, `-beta`) are stripped before comparison. `1.0.0-rc.1` sorts as `1.0.0`.
3. **No semantic / embedding-based ranking.** BM25 only. A semantic-ranker plug-in is plausible v2 work.
4. **Single colon as field separator.** A value containing a colon (e.g. `env_var:OPENAI_API_KEY`) works because only the first colon is the separator. Multi-colon values stay literal.
5. **Bare wildcard `*`** is treated as a regular term, not a match-everything operator. To match-everything, use an empty query.

---

## Error reference

| Error message | Meaning | Fix |
|---|---|---|
| `Unclosed quote at position N` | Phrase started with `"` but didn't end. | Add the closing `"`. |
| `Expected RPAREN at position N` | `(` opened but never closed. | Balance parens. |
| `Empty field name` | `:value` with no field before the colon. | Add a field name. |
| `Empty value` | `field:` with no value. | Add a value. |
| `Unknown field: 'X'` | `X` isn't a recognized field. | Check the Field Reference table. |
| `OR across FTS5 and SQL fields is not supported` | OR mixed indexed and unindexed branches. | Split the query, or use AND instead. |
| `Comparison operators are not supported on indexed field X` | Used `>=`, `<=`, etc. on a tokenized field. | Use exact match or prefix; comparisons only work on `version`. |

---

## Programmatic access

```python
from agent_skills.search.ranker import search

result = search(
    "tag:rust agent:claude-code",
    db_path="/path/to/registry.db",
    limit=20,
    offset=0,
    include_deprecated=False,
)

result.total           # total matching rows in the registry
result.registry_version  # the registry's generated_at timestamp
result.results         # tuple of result dicts
```

To build the index from a `registry.json`:

```python
from agent_skills.search.index import build_index, is_stale

if is_stale(db_path, registry["generated_at"]):
    build_index(registry, db_path)
```

---

## See also

- `docs/mcp-integration.md` — exposing this search via MCP tools to AI agents
- `docs/superpowers/specs/2026-05-12-mcp-and-search-design.md` — design rationale and decisions
- `tests/test_search_query.py` — parser test fixtures (64 cases)
- `tests/test_search_ranker.py` — runner test fixtures (43 cases)
- `tests/test_determinism.py` — determinism contract canaries
