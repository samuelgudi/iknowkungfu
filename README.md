# agent-skills

Agent-agnostic registry for skill discovery and contribution.

[![CI](https://github.com/samuelgudi/agent-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/samuelgudi/agent-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

---

agent-skills is a content-hash-anchored skill registry that lets any compatible agent discover, install, and verify skills without coupling to a specific host's ecosystem. Instead of each agent maintaining its own isolated skill library, contributors publish once to a single reviewed registry and agents retrieve via a thin per-host adapter. Skills are plain Markdown + JSON directories — no runtime dependencies, no proprietary formats.

---

## Install

```
pip install agent-skills    # or: uv tool install agent-skills
```

PyPI publication is deferred to v1. For now, install from source:

```
git clone https://github.com/samuelgudi/agent-skills
pip install -e agent-skills/
```

---

## Quickstart

```bash
agent-skills update                          # refresh registry cache
agent-skills search <query>                  # find skills
agent-skills install <author>/<skill>        # install for detected host
agent-skills list                            # show installed skills
agent-skills verify <author>/<skill>         # check installed skill against registry
```

---

## For contributors

```bash
agent-skills init <local-dir>     # scaffold meta.json interactively
agent-skills submit <local-dir>   # validate, sanitize, scan, open PR
```

Full contribution guidelines, frontmatter contract, and review template are in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## How it works

- Skills live as `<author>/<slug>/` directories with `SKILL.md` (the instructions body) and `meta.json` (machine metadata). The generated `registry.json` is the content-hash-anchored manifest that clients query.
- Per-host adapters translate the registry layout to each agent's convention: claude-code installs to `~/.claude/skills/<author>-<slug>/`; hermes installs to `~/.hermes/skills/<category>/<slug>/`. Adapters are thin — all logic lives in the registry client.
- `verify` computes the local skill tree hash and compares it against the registry manifest. Yanked versions are hard-refused at install time with no override.

---

## MCP server — for AI agents

`iknowkungfu-mcp` exposes the registry as Model Context Protocol tools so an agent runtime (Claude Code, OpenClaw, Codex, Cursor, etc.) can search and install skills mid-task without leaving the agent loop.

Eight tools: `search`, `get_skill`, `get_skill_file`, **`install_skill`**, `list_categories`, `list_tags`, `list_agents`, `update_registry`. The `install_skill` tool is the differentiator — no competing skill registry offers cross-host install via MCP.

Add to Claude Code's `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "iknowkungfu": { "command": "iknowkungfu-mcp" }
  }
}
```

Then in a session:

```
> Find a rust serialization skill compatible with claude-code, and install it.
```

The agent will call `search`, inspect candidates with `get_skill`, then `install_skill` to write the chosen skill into `~/.claude/skills/`.

### Query language

The search tool (and the CLI's `agent-skills search`) accepts a Lucene-style DSL:

```
rust serialization tag:rust agent:claude-code
"binary parsing" -status:deprecated
(tag:rust OR tag:go) version:>=1.0
NOT requires:env_var:*
```

Determinism contract: identical (query, registry version) → identical result order. BM25 ranked, deterministically tie-broken, SQLite FTS5 backed.

Full reference: [docs/query-language.md](docs/query-language.md). MCP integration per-host: [docs/mcp-integration.md](docs/mcp-integration.md).

---

## Project layout

```
agent-skills/
├── registry.json            # generated manifest (never hand-edit)
├── yanks.json               # append-only yank log
├── skills/                  # approved skills (<author>/<slug>/)
├── archive/                 # deprecated skills with superseded_by pointers
├── submitted/               # open contribution PRs
├── scripts/                 # registry tooling (validate, security_scan, generate_manifest)
├── adapters/                # per-host install logic (claude-code, hermes)
├── clients/                 # discovery + contribution clients
└── agent_skills/            # CLI package
```

---

## Documentation

- [Design spec (v0)](docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md) — canonical requirements and decisions
- [MCP + search design spec](docs/superpowers/specs/2026-05-12-mcp-and-search-design.md) — MCP server architecture, query DSL, determinism contract
- [Query language reference](docs/query-language.md) — DSL syntax, field reference, worked examples
- [MCP integration guide](docs/mcp-integration.md) — per-host wiring (Claude Code, OpenClaw, Codex, Cursor)
- [Decisions log](docs/decisions.md) — ADRs (incl. the rename to *I Know Kung Fu*)
- [CONTRIBUTING.md](CONTRIBUTING.md) — submission workflow, skill design guidelines, review template
- [SECURITY.md](SECURITY.md) — security policy and vulnerability reporting
- [SCHEMA.md](SCHEMA.md) — field-level reference for `registry.json`, `meta.json`, `yanks.json`

---

## License

[MIT](LICENSE)

---

## Acknowledgments

The design spec is at v4, incorporating review rounds from MILO, Gemini, and a real-skill walkthrough that hardened the submission pipeline, yank semantics, and frontmatter contract.
