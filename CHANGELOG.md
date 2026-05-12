# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.2] — 2026-05-12

### Changed (BREAKING — pip install name)

- **Project renamed**: `agent-skills` → `I Know Kung Fu`. Decision recorded in [`docs/decisions.md` § ADR-001](docs/decisions.md). Migration is a pip-install-name change only; existing skills, marker files, cache directories, and registry IDs continue to work without modification.
  - PyPI package name: `agent-skills` → `iknowkungfu`. Install with `pip install iknowkungfu` (or `uv tool install iknowkungfu`).
  - Primary CLI command: `kfu`. The legacy `agent-skills` command is retained as a back-compat alias and resolves to the same entry point.
  - MCP server binary: `iknowkungfu-mcp` (already in place from the previous release).
  - Default registry URLs in `clients/skill_discovery/update.py` now point at `github.com/samuelgudi/iknowkungfu` (the repo was renamed on 2026-05-12).
  - Adapter install-marker `installed_by` field now records `iknowkungfu {version}` for new installs.

### Added

- **Deterministic FTS5 search engine** (`agent_skills/search/`): Lucene-style query DSL, SQLite FTS5 index, BM25 ranking with deterministic tie-break. Identical `(query, registry_version)` produces byte-identical result order. Reference: [`docs/query-language.md`](docs/query-language.md). 219 tests in `tests/test_search_*` + 20 determinism canaries in `tests/test_determinism.py`.
- **MCP server** (`iknowkungfu-mcp`): exposes the registry as Model Context Protocol tools so AI agent runtimes (Claude Code, OpenClaw, Codex, Cursor, Gemini CLI) can search and install skills mid-task. Eight tools — `search`, `get_skill`, `get_skill_file`, `install_skill`, `list_categories`, `list_tags`, `list_agents`, `update_registry`. `install_skill` is the differentiator: cross-host install via MCP that no other skill registry currently offers. Reference: [`docs/mcp-integration.md`](docs/mcp-integration.md). 32 tests.
- **CLI search rewrite**: the `kfu search` verb now parses the new query DSL (`tag:`, `agent:`, `version:>=`, boolean ops, phrases, prefixes, grouping). Deprecated `--agent` / `--category` / `--tag` flags are retained for one release with a stderr deprecation warning that translates them to the new DSL.
- **New CLI flags on `search`**: `--include-deprecated`, `--ndjson`, `--limit`, `--offset`.
- **ADR-001** locking the project name and the boundary between external-rename and internal-stability ([`docs/decisions.md`](docs/decisions.md)).

### Fixed

- **Empty-search-result hint** (`agent_skills/verbs/search.py`): previously suggested running `agent-skills list-categories` / `kfu list-categories`, a verb that doesn't exist. Replaced with an inline list of the eight valid categories so the suggestion is actionable.

### Stayed the same (back-compat, by design)

The rename is deliberately scoped to external surfaces. The following are unchanged so that existing installs continue to work without migration:

- Python module on disk: `agent_skills/`
- Cache directory: `~/.cache/agent-skills/`
- Install marker filename: `.agent-skills-marker.json`
- Environment variables: `AGENT_SKILLS_REGISTRY_URL`, `AGENT_SKILLS_REGISTRY_REPO`, `AGENT_SKILLS_SKIP_REPO_SYNC`
- Registry skill IDs (`samuelgudi/agent-skills-contribution`, `samuelgudi/agent-skills-discovery`) — immutable per the registry contract

### Known issues (deferred)

- **MCP `install_skill` / `update_registry` subprocess fragility on Windows**: these two tools shell out to the CLI via `subprocess.run(["agent-skills", ...])`. On Windows MCP clients that launch the server with a stripped `PATH`, the executable may not resolve. The other six MCP tools are unaffected. Refactor to in-process verb dispatch is on the post-launch backlog.
- **Hyphenated tag false positives in search**: `tag:claude-code` correctly matches skills with that literal tag, but also false-positives on skills that declare separate adjacent `claude` and `code` tags. Fix requires a schema bump (`INDEX_SCHEMA_VERSION` 1 → 2) to add a pipe-delimited `tags_filter` column. On the backlog.

### Test suite

- 446 passing, 1 skipped on Windows × Python 3.13. Cross-platform verification (Linux, macOS) runs via the existing `.github/workflows/ci.yml` once a commit is pushed.

---

## [0.1.1] — 2026-05-12 (internal, unreleased)

Dogfood-hardening pass: six new per-host adapters (claude-code, codex, opencode, openclaw, pi, hermes), CRLF-normalized content hashing for cross-platform stability, UTF-8 stream reconfiguration at CLI entry for Windows consoles, expanded CLI verb coverage. The version was tagged for the internal session-5 dogfood checkpoint but never published to a registry. See `docs/handoff/2026-05-12-execution-handoff-session5.md`.

## [0.1.0] — 2026-05-11 (internal, unreleased)

Initial public-shape scaffold: registry schema, CLI surface, validate.py, security_scan.py, manifest generation, claude-code adapter, contribution + discovery skills. See `docs/superpowers/plans/2026-05-11-agent-skills-hub-v0.md` for the initial plan.

[0.1.2]: https://github.com/samuelgudi/iknowkungfu/releases/tag/v0.1.2
[0.1.1]: https://github.com/samuelgudi/iknowkungfu/commits/main
[0.1.0]: https://github.com/samuelgudi/iknowkungfu/commits/main
