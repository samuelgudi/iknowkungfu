# Phase 1 Rename + Polish + Commit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Convert the uncommitted session-7 working tree into a clean, push-ready `main` by (a) splitting current changes into 6 logical commits, (b) applying Phase 1 brand rename per ADR-001, (c) verifying wheel build + 446-test suite, leaving the repo in `pip install -e .` and `kfu --help`-ready state.

**Architecture:** Two passes. **Pass A** commits the existing session-7 work in 6 thematic chunks without touching content (B1-B3 search, B4 CLI wiring, B5 MCP, B6 determinism, B7 docs, ADR+handoff). **Pass B** is a surgical rename across ~15 files: external CLI/package name only, internal `agent_skills/` module + cache dir + marker filename + env vars stay (ADR-001 § Decision item 5; handoff item 7). Reviewer subagent gates the final Phase 1 commit.

**Tech Stack:** Python 3.13, pytest, setuptools (`python -m build` for wheel verify), git. No new deps.

---

## Constraints from memory

- **ADR-001 § Decision (locked)**: PyPI=`iknowkungfu`, CLI alias=**`kfu`**, module on disk=stays `agent_skills/`. Handoff text "add iknowkungfu CLI script alias" is imprecise — ADR wins (it's locked).
- **feedback-tests-must-bite.md**: any new tests must hit real failure paths.
- **feedback-systematic-approach.md**: Analysis (done) → Plan (this doc) → Validation (build+test) → Intervention (rename) → Test.
- **feedback-parallel-agent-cap.md**: max 2 subagents running `install`/`test` concurrently. Only one reviewer subagent runs here — no install/test overlap.
- **feedback-document-then-batch.md**: on walkthroughs/audits, surface all findings first; batch after discovery. The current handoff IS that surfaced batch — proceed to batched fix.
- **feedback-always-push.md**: this plan stops AT push, per Samuel's instruction. Push will require explicit user confirmation.
- **No worktree**: existing uncommitted work is on `main`; HEAD `15ad517`. Worktree migration would lose state. Continue on `main`.

---

## Out of scope (deferred per handoff)

- Backlog #5 (subprocess fragility refactor) — defer to post-push session.
- Backlog #6 (hyphenated-tag schema bump) — defer to post-push session.
- Rename of `skills/samuelgudi/agent-skills-{contribution,discovery}/` registry entries — defer (registry IDs are immutable; renaming requires new skill IDs + yank).
- `registry.json` regeneration — depends on above; defer.
- Domain registrations — Samuel deferred from session 7.
- Public visibility flip + PyPI upload — gated on Samuel's explicit ok (push step).

---

## File Structure — what each file gets

### Pass A: split existing untracked/modified into 6 commits

| Commit | Files | Source phase |
|---|---|---|
| 1 — feat(search): deterministic search engine | `agent_skills/search/__init__.py`, `search/query.py`, `search/index.py`, `search/ranker.py`; `tests/test_search_query.py`, `test_search_index.py`, `test_search_ranker.py`; mod `agent_skills/cache.py` | B1-B3 |
| 2 — feat(cli,search): wire CLI to new search engine | mod `agent_skills/cli.py`, mod `agent_skills/verbs/search.py`; `tests/test_search_verb.py` | B4 |
| 3 — feat(mcp): MCP server with 8 tools | `agent_skills/mcp/__init__.py`, `mcp/__main__.py`, `mcp/server.py`, `mcp/tools.py`; mod `pyproject.toml` (`iknowkungfu-mcp` entry only); `tests/test_mcp_server.py`, `test_mcp_subprocess.py` | B5 |
| 4 — test(search): determinism contract tests | `tests/test_determinism.py` | B6 |
| 5 — docs: query language, MCP integration, README MCP section | mod `README.md`; `docs/query-language.md`, `docs/mcp-integration.md`; `docs/superpowers/specs/2026-05-12-mcp-and-search-design.md` | B7 |
| 6 — docs: ADR-001 rename + naming decision + session-7 handoff | `docs/decisions.md`, `docs/handoff/2026-05-12-naming-decision.md`, `docs/handoff/2026-05-12-execution-handoff-session7.md` | review+rename docs |

### Pass B: Phase 1 rename — files to edit (commit 7)

| File | What changes |
|---|---|
| `pyproject.toml` | `name = "iknowkungfu"`; `version = "0.1.2"`; ADD `kfu = "agent_skills.cli:main"` script entry (KEEP existing `agent-skills` entry as back-compat alias); KEEP `iknowkungfu-mcp` |
| `agent_skills/__init__.py` | Docstring → `"""I Know Kung Fu — agent-agnostic skill registry CLI (formerly agent-skills)."""`; `__version__ = "0.1.2"` |
| `agent_skills/cli.py` | Module docstring; `prog="kfu"` |
| `agent_skills/cache.py` | Module docstring only (`~/.cache/agent-skills/` path stays) |
| `agent_skills/detect.py` | Line 42: hint text `agent-skills <verb>` → `kfu <verb>` |
| `agent_skills/verbs/install.py` | All 4 user-facing strings: `agent-skills update`/`search`/`install` → `kfu update`/`search`/`install` |
| `agent_skills/verbs/show.py` | Line 30: `agent-skills update` → `kfu update` |
| `agent_skills/verbs/verify.py` | Line 17: `agent-skills update` → `kfu update` |
| `agent_skills/verbs/search.py` | Lines 65, 96, 123: example queries + hints |
| `agent_skills/verbs/yank.py` | Line 131: `agent-skills update` → `kfu update` |
| `agent_skills/verbs/init.py` | Line 165 error text + line 330 next-step hint |
| `clients/skill_discovery/update.py` | `DEFAULT_REGISTRY_URL`, `DEFAULT_REGISTRY_REPO` → `samuelgudi/iknowkungfu`; User-Agent → `iknowkungfu/0.1.2` |
| `clients/skill_contribution/submit.py` | Line 109: `agent-skills init` → `kfu init` |
| `adapters/_base.py` | Line 65: `installed_by` → `iknowkungfu {ver}` (NB: `.agent-skills-marker.json` filename STAYS) |
| `adapters/claude_code.py`, `codex.py`, `opencode.py`, `openclaw.py`, `pi.py` | `verify` no-marker message: `agent-skills` → `iknowkungfu` (5 files, one line each) |
| `adapters/codex.py` | Line 4 docstring comment: `agent-skills cares about` → `iknowkungfu cares about` |
| `README.md` | Hero `# agent-skills` → `# I Know Kung Fu`; tagline; badges URL; install commands (`pip install iknowkungfu`); CLI examples; project layout snippet's `agent-skills/` → `iknowkungfu/`; clone URL |
| `CONTRIBUTING.md` | Install commands; all CLI examples `agent-skills <verb>` → `kfu <verb>` |
| `SECURITY.md` | Yank procedure CLI examples; threat-model intro sentence |
| `SCHEMA.md` | Title `agent-skills Schema Reference` → `iknowkungfu Schema Reference`; inline CLI example `agent-skills init` → `kfu init`; meta-category description rewording |
| `scripts/validate.py` | Line 392 argparse description |
| `scripts/schema.json` | `$id` URL → `samuelgudi/iknowkungfu`; `title` → `iknowkungfu registry` |
| `scripts/rules.yaml` | Header comments (lines 1-2) |

**Explicitly NOT touched in Pass B** (per ADR-001 + handoff item 7):
- `agent_skills/` module on disk
- `~/.cache/agent-skills/` cache path (3 callsites in cache.py/update.py)
- `.agent-skills-marker.json` filename (`adapters/_base.py:14` `MARKER_FILENAME`)
- `AGENT_SKILLS_*` env vars in `update.py`
- `skills/samuelgudi/agent-skills-{contribution,discovery}/` directories + meta.json IDs
- `registry.json` (auto-generated; defer regen)
- All `docs/handoff/*`, `docs/dogfood/*`, `docs/superpowers/plans/*` historical records
- All `tests/test_*.py` (no test references "agent-skills" outside cache path / marker filename — confirmed via grep)

---

## Subagent organization

- **All Pass A commits**: me, direct. Sequencing matters (git history) and the work is short-throughput; subagent overhead > savings.
- **Pass B rename**: me, direct. Mechanical surface, ~20 files, easier with `execute()` batched edits than dispatching.
- **Code review of Pass B diff**: dispatch `feature-dev:code-reviewer` (Opus). Runs in parallel with my wheel-build + smoke-test. Reviewer gates the Pass B commit. This is the one valuable subagent slot — extra eyes on the final cosmetic-but-public rename before commit.
- **Wheel-build smoke test**: me, after Pass B edits. `python -m build` + `pip install dist/*.whl` in a throwaway venv + `kfu --help`. Single shell sequence.

Max concurrent subagents = 1 (the reviewer), well under the cap of 2/3.

---

## Tasks

### Task 1: Verify baseline state matches handoff

**Files:** none (read-only).

- [ ] **Step 1: Run full test suite and capture count**

```powershell
Set-Location X:\Repos\agent-skills
python -m pytest tests/ -q --tb=no 2>&1 | Select-String -Pattern "passed|failed|error" | Select-Object -Last 3
```

Expected: `446 passed, 1 skipped`. If different, STOP and investigate before proceeding.

- [ ] **Step 2: Verify HEAD and remote**

```powershell
git log --oneline -1
git remote get-url origin
```

Expected: `15ad517 docs: session-6 plan handoff with strategic reframe`, origin = `https://github.com/samuelgudi/iknowkungfu.git`.

- [ ] **Step 3: Verify working-tree shape**

```powershell
git status --short | Measure-Object -Line
```

Expected: 20 lines (5 modified + 15 untracked, per handoff).

---

### Task 2: Commit 1 — feat(search): deterministic search engine (B1-B3)

**Files:** Add `agent_skills/search/{__init__,query,index,ranker}.py`, `tests/test_search_{query,index,ranker}.py`; Modify `agent_skills/cache.py`.

- [ ] **Step 1: Stage**

```powershell
git add agent_skills/search/ tests/test_search_query.py tests/test_search_index.py tests/test_search_ranker.py agent_skills/cache.py
```

- [ ] **Step 2: Verify stage doesn't leak Pass-B-targeted files**

```powershell
git diff --cached --stat
```

Expected: 8 files (4 src + 3 test + cache.py). NO `cli.py`, no `verbs/search.py`, no `mcp/`, no `pyproject.toml`, no `README.md`.

- [ ] **Step 3: Commit**

```powershell
git commit -m @'
feat(search): deterministic FTS5 search engine

Query DSL parser, FTS5 index builder, AST compiler + ranker.
BM25 ranked with deterministic tie-break. Identical (query, registry
version) produces identical result order — locked by determinism tests
in a later commit.

Adds db_path() helper to agent_skills/cache.py.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

- [ ] **Step 4: Verify tests still pass after commit**

```powershell
python -m pytest tests/test_search_query.py tests/test_search_index.py tests/test_search_ranker.py -q
```

Expected: 149 passed (64+35+50).

---

### Task 3: Commit 2 — feat(cli,search): wire CLI to new search engine (B4)

**Files:** Modify `agent_skills/cli.py`, `agent_skills/verbs/search.py`; Add `tests/test_search_verb.py`.

- [ ] **Step 1: Stage**

```powershell
git add agent_skills/cli.py agent_skills/verbs/search.py tests/test_search_verb.py
```

- [ ] **Step 2: Commit**

```powershell
git commit -m @'
feat(cli,search): wire CLI search verb to new ranker

Rewrites the search subparser to accept the query DSL as raw positional
args. Deprecated --agent/--category/--tag flags retained one release;
translated to DSL prefixes with a stderr warning. New flags: --include-deprecated,
--ndjson, --limit, --offset.

verbs/search.py now calls into the new ranker pipeline (parse → compile → execute)
and emits structured output for --json/--ndjson.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

- [ ] **Step 3: Verify**

```powershell
python -m pytest tests/test_search_verb.py -q
```

Expected: 18 passed.

---

### Task 4: Commit 3 — feat(mcp): MCP server with 8 tools (B5)

**Files:** Add `agent_skills/mcp/{__init__,__main__,server,tools}.py`, `tests/test_mcp_server.py`, `tests/test_mcp_subprocess.py`; Modify `pyproject.toml` (B5 layer only).

- [ ] **Step 1: Stage exactly the B5 layer of pyproject.toml**

The current `pyproject.toml` modification adds the `iknowkungfu-mcp = "agent_skills.mcp.__main__:main"` entry to `[project.scripts]`. Stage it as part of this commit. The Pass-B rename (Task 8) will further modify `pyproject.toml` (name + version + `kfu` alias), so this commit MUST stop at the MCP entry only.

```powershell
git add agent_skills/mcp/ tests/test_mcp_server.py tests/test_mcp_subprocess.py pyproject.toml
git diff --cached pyproject.toml
```

Expected diff: ONE added line — `iknowkungfu-mcp = "agent_skills.mcp.__main__:main"`. If more lines changed, unstage pyproject.toml and `git restore --staged pyproject.toml`; this means another phase already touched it (it shouldn't have).

- [ ] **Step 2: Commit**

```powershell
git commit -m @'
feat(mcp): add MCP server with 8 tools

Tools: search, get_skill, get_skill_file, install_skill, list_categories,
list_tags, list_agents, update_registry. install_skill is the differentiator —
cross-host install via MCP that no other skill registry offers.

Server entry point: iknowkungfu-mcp = agent_skills.mcp.__main__:main.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

- [ ] **Step 3: Verify**

```powershell
python -m pytest tests/test_mcp_server.py tests/test_mcp_subprocess.py -q
```

Expected: 32 passed.

---

### Task 5: Commit 4 — test(search): determinism contract tests (B6)

**Files:** Add `tests/test_determinism.py`.

- [ ] **Step 1: Stage + commit**

```powershell
git add tests/test_determinism.py
git commit -m @'
test(search): determinism contract regression tests

24 tests asserting identical (query, registry version) input produces
byte-identical result order. Includes tie-break stability across runs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

- [ ] **Step 2: Verify**

```powershell
python -m pytest tests/test_determinism.py -q
```

Expected: 24 passed.

---

### Task 6: Commit 5 — docs: query language + MCP integration + README MCP section (B7)

**Files:** Add `docs/query-language.md`, `docs/mcp-integration.md`, `docs/superpowers/specs/2026-05-12-mcp-and-search-design.md`; Modify `README.md` (B7 layer — MCP section only).

- [ ] **Step 1: Stage**

```powershell
git add docs/query-language.md docs/mcp-integration.md docs/superpowers/specs/2026-05-12-mcp-and-search-design.md README.md
```

- [ ] **Step 2: Verify README diff is only the MCP section addition**

```powershell
git diff --cached README.md | Select-String -Pattern "^[\+\-]" | Select-Object -First 50
```

Expected: only insertions (no deletions in B7 layer; rename comes in Pass B). README still says `# agent-skills` after this commit. If you see deletions of the hero/title, abort and re-stage.

- [ ] **Step 3: Commit**

```powershell
git commit -m @'
docs(search,mcp): query language reference + MCP integration guide

- docs/query-language.md — DSL syntax, field reference, worked examples
- docs/mcp-integration.md — per-host wiring for Claude Code, OpenClaw, Codex, Cursor
- docs/superpowers/specs/2026-05-12-mcp-and-search-design.md — design spec
- README — new MCP section linking to both guides

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

---

### Task 7: Commit 6 — docs: ADR-001 + naming methodology + session-7 handoff

**Files:** Add `docs/decisions.md`, `docs/handoff/2026-05-12-naming-decision.md`, `docs/handoff/2026-05-12-execution-handoff-session7.md`.

- [ ] **Step 1: Stage + commit**

```powershell
git add docs/decisions.md docs/handoff/2026-05-12-naming-decision.md docs/handoff/2026-05-12-execution-handoff-session7.md
git commit -m @'
docs: ADR-001 rename to I Know Kung Fu + session-7 execution handoff

- docs/decisions.md — ADR-001 locks brand=I Know Kung Fu, pkg=iknowkungfu,
  CLI=kfu. Module on disk stays agent_skills/.
- docs/handoff/2026-05-12-naming-decision.md — 40-candidate evaluation
  record across 4 expert frameworks (Watkins, Placek, Igor, competitive).
- docs/handoff/2026-05-12-execution-handoff-session7.md — full state for
  session 8.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

- [ ] **Step 2: Verify working tree is now clean**

```powershell
git status --short
```

Expected: empty output. If anything remains, STOP and investigate before Pass B.

- [ ] **Step 3: Run full suite to confirm no regression from Pass A**

```powershell
python -m pytest tests/ -q --tb=no 2>&1 | Select-String "passed" | Select-Object -Last 1
```

Expected: `446 passed, 1 skipped`.

---

### Task 8: Apply Phase 1 rename edits (Pass B)

**Files:** see table at top — ~22 files.

This is one logical change but spans many files. Use `execute()` with `fs.read` + string replace + `fs.write` patterns, or `Edit` for each. Either tool is fine; the file list and exact substitutions are fully specified below.

**Substitution table — apply EXACTLY these**:

**`pyproject.toml`** — three changes:
- Line 6: `name = "agent-skills"` → `name = "iknowkungfu"`
- Line 7: `version = "0.1.1"` → `version = "0.1.2"`
- Inside `[project.scripts]`, ADD a new line `kfu = "agent_skills.cli:main"` directly below the existing `agent-skills = "agent_skills.cli:main"` line. KEEP `agent-skills` and `iknowkungfu-mcp` lines unchanged.

**`agent_skills/__init__.py`** — full rewrite (4 lines):

```python
"""I Know Kung Fu — agent-agnostic skill registry CLI (formerly agent-skills)."""

__version__ = "0.1.2"
```

**`agent_skills/cli.py`** — two edits:
- Line 1 docstring `"""agent-skills CLI verb dispatch."""` → `"""I Know Kung Fu CLI verb dispatch."""`
- Line 36 `prog="agent-skills"` → `prog="kfu"`

**`agent_skills/cache.py`** — one edit:
- Line 1 docstring `"""~/.cache/agent-skills/ helpers."""` → keep as-is (path is unchanged per ADR-001).
- No other changes — cache path stays `.cache/agent-skills` for back-compat.

**`agent_skills/detect.py`** — line 42:
- `f"  agent-skills <verb> --agent {found[0]}\n"` → `f"  kfu <verb> --agent {found[0]}\n"`

**`agent_skills/verbs/install.py`** — four edits (lines 67, 73, 99, 107):
- `agent-skills update` → `kfu update` (lines 67, 107)
- `agent-skills search` → `kfu search` (line 73)
- `agent-skills install` → `kfu install` (line 99)

**`agent_skills/verbs/show.py`** — line 30:
- `agent-skills update` → `kfu update`

**`agent_skills/verbs/verify.py`** — line 17:
- `agent-skills update` → `kfu update`

**`agent_skills/verbs/search.py`** — three edits (lines 65, 96, 123):
- Line 65: `agent-skills search 'tag:rust agent:claude-code'` → `kfu search 'tag:rust agent:claude-code'`
- Line 96: `agent-skills list-categories` → `kfu list-categories`
- Line 123: `agent-skills update` → `kfu update`

**`agent_skills/verbs/yank.py`** — line 131:
- `` `agent-skills update` `` → `` `kfu update` ``

**`agent_skills/verbs/init.py`** — two edits:
- Line 165: `"An \`agent-skills\` skill needs a \`SKILL.md\` with frontmatter."` → `"A SKILL.md with frontmatter is required."` (drop brand-name reference; the message is about the SKILL.md contract, not the tool)
- Line 330: `f"\nNext:\n  agent-skills submit {target}"` → `f"\nNext:\n  kfu submit {target}"`

**`clients/skill_discovery/update.py`** — three edits:
- Line 35: `DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/samuelgudi/agent-skills/main/registry.json"` → `DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/samuelgudi/iknowkungfu/main/registry.json"`
- Line 36: `DEFAULT_REGISTRY_REPO = "https://github.com/samuelgudi/agent-skills.git"` → `DEFAULT_REGISTRY_REPO = "https://github.com/samuelgudi/iknowkungfu.git"`
- Line 46: `User-Agent`: `"agent-skills/0.1.0"` → `"iknowkungfu/0.1.2"`
- Line 40 `Path.home() / ".cache/agent-skills"` STAYS UNCHANGED (back-compat).

**`clients/skill_contribution/submit.py`** — line 109:
- `meta.json missing — run \`agent-skills init <target>\` first.` → `meta.json missing — run \`kfu init <target>\` first.`

**`adapters/_base.py`** — line 65:
- `"installed_by": f"agent-skills {_agent_skills_version}"` → `"installed_by": f"iknowkungfu {_agent_skills_version}"`
- Line 14 `MARKER_FILENAME = ".agent-skills-marker.json"` STAYS (back-compat).

**`adapters/claude_code.py`, `adapters/opencode.py`, `adapters/openclaw.py`, `adapters/pi.py`** — same edit each:
- `"no marker — skill not managed by agent-skills"` → `"no marker — skill not managed by iknowkungfu"`

**`adapters/codex.py`** — two edits:
- Line 4 docstring comment: `agent-skills cares about` → `iknowkungfu cares about`
- Line 125: `"no marker — skill not managed by agent-skills"` → `"no marker — skill not managed by iknowkungfu"`

**`README.md`** — full rewrite of:
- Title `# agent-skills` → `# I Know Kung Fu`
- New tagline line after title: `> The skills your agents need. Instantly.` (or `> For your agents.`)
- Then a one-line subtitle: `Agent-agnostic registry for skill discovery and contribution. Formerly known as agent-skills.`
- All three badge URLs `samuelgudi/agent-skills` → `samuelgudi/iknowkungfu`
- Install commands: `pip install agent-skills` → `pip install iknowkungfu`; `uv tool install agent-skills` → `uv tool install iknowkungfu`
- Clone URL `git clone https://github.com/samuelgudi/agent-skills` → `git clone https://github.com/samuelgudi/iknowkungfu`
- "PyPI publication is deferred to v1" paragraph: DELETE (PyPI namespace is claimed and v0.1.2 is going up next session). Replace with: `Until v0.1.2 lands on PyPI, install from source:` then keep the git-clone snippet.
- Quickstart commands: `agent-skills <verb>` → `kfu <verb>` (5 lines)
- Contributor commands: `agent-skills init/submit` → `kfu init/submit`
- Project layout snippet: replace `agent-skills/` directory label with `iknowkungfu/`
- Query language section: `agent-skills search` → `kfu search`

**`CONTRIBUTING.md`** — all 16 `agent-skills` occurrences:
- Clone URL: `samuelgudi/agent-skills` → `samuelgudi/iknowkungfu`
- Install commands: `pip install agent-skills` / `uv tool install agent-skills` → `iknowkungfu`
- CLI verb examples: `agent-skills init/submit/validate/yank` → `kfu init/submit/validate/yank` (all examples in the body + verbs reference table)
- Section heading "agent-skills submit normalises..." → "`kfu submit` normalises..." (line 84)
- "PR adds skill.md directly" sentence: `agent-skills submit` → `kfu submit`

**`SECURITY.md`** — 4 occurrences:
- "agent-skills install hard-refuses" → "`kfu install` hard-refuses" (line 10 + line 56)
- "agent-skills registry distributes" → "I Know Kung Fu registry distributes" (line 17)
- "agent-skills yank" → "kfu yank" (line 51)

**`SCHEMA.md`** — 5 occurrences:
- Title `# agent-skills Schema Reference` → `# iknowkungfu Schema Reference`
- "Fetched by agent-skills init" → "Fetched by `kfu init`" (line 75)
- "fetched by agent-skills init" → "fetched by `kfu init`" (line 242)
- "the agent-skills system itself" → "the iknowkungfu system itself" (line 318)
- (line 3 cross-link spec path stays — it's a historical filename)

**`scripts/validate.py`** — line 392:
- `description="Validate agent-skills skill directories."` → `description="Validate iknowkungfu skill directories."`

**`scripts/schema.json`** — two edits:
- Line 3 `"$id": "https://github.com/samuelgudi/agent-skills/scripts/schema.json"` → `"$id": "https://github.com/samuelgudi/iknowkungfu/scripts/schema.json"`
- Line 4 `"title": "agent-skills registry"` → `"title": "iknowkungfu registry"`

**`scripts/rules.yaml`** — two header comments:
- Line 1: `# agent-skills security_scan.py rules (v0)` → `# iknowkungfu security_scan.py rules (v0)`
- Line 2: cross-link spec path stays (historical filename)

- [ ] **Step 1: Apply all substitutions above**

Use `execute()` with `fs.read` + `.replace(...)` + `fs.write` for batch, or `Edit` tool per file. Both are acceptable.

- [ ] **Step 2: Verify no STAYING-AS-IS string was accidentally rewritten**

```powershell
git diff -- agent_skills/cache.py clients/skill_discovery/update.py adapters/_base.py | Select-String "\.cache/agent-skills|\.agent-skills-marker\.json|AGENT_SKILLS_"
```

Expected: empty output (no diff hits on these reserved strings). If any line appears, revert that specific change.

- [ ] **Step 3: Verify full diff scope**

```powershell
git diff --stat
```

Expected: ~22 files changed. NO `tests/`, NO `skills/`, NO `registry.json`, NO `docs/handoff/`, NO `docs/dogfood/`.

---

### Task 9: Validate Pass B — run full test suite

**Files:** none.

- [ ] **Step 1: Run full suite**

```powershell
python -m pytest tests/ -q --tb=short 2>&1 | Select-String -Pattern "passed|FAILED|ERROR" | Select-Object -Last 5
```

Expected: `446 passed, 1 skipped`. If failures appear, the rename broke an assertion on user-facing text — fix the specific test (or revert the offending message change) and re-run.

- [ ] **Step 2: Run CLI smoke**

```powershell
python -m agent_skills.cli --help
```

Expected: help output, prog line shows `kfu` (not `agent-skills`).

---

### Task 10: Dispatch reviewer subagent in parallel with wheel build

Dispatch `feature-dev:code-reviewer` (Opus) with the full Pass B diff as input. Reviewer brief:

> Pass B rename of project `agent-skills` to `I Know Kung Fu` (PyPI: `iknowkungfu`, CLI: `kfu`). External brand only — internal `agent_skills/` module + `~/.cache/agent-skills/` + `.agent-skills-marker.json` + `AGENT_SKILLS_*` env vars STAY per ADR-001. The diff is `git diff main -- <Pass B file list>` (still uncommitted). Find: (a) any user-facing string that still says `agent-skills` and should be `kfu` / `iknowkungfu`, (b) any reserved string (cache path, marker filename, env var) that was wrongly changed, (c) any test that will break on prog rename (`prog="kfu"`) — specifically tests that assert CLI error message format, (d) consistency: are `kfu` (CLI command), `iknowkungfu` (package), `I Know Kung Fu` (brand) used in the right contexts.

- [ ] **Step 1: Dispatch reviewer (background)**

Use Agent tool, subagent_type=`feature-dev:code-reviewer`, model=Opus, run_in_background=true.

- [ ] **Step 2: Build wheel while reviewer runs**

```powershell
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
python -m build 2>&1 | Select-String -Pattern "Successfully built|error"
```

Expected: `Successfully built iknowkungfu-0.1.2.tar.gz and iknowkungfu-0.1.2-py3-none-any.whl`.

- [ ] **Step 3: Smoke-install wheel in throwaway venv**

```powershell
python -m venv .smoke-venv
.\.smoke-venv\Scripts\python.exe -m pip install --quiet dist\iknowkungfu-0.1.2-py3-none-any.whl
.\.smoke-venv\Scripts\python.exe -c "import agent_skills; print(agent_skills.__version__)"
.\.smoke-venv\Scripts\kfu.exe --help 2>&1 | Select-Object -First 5
.\.smoke-venv\Scripts\agent-skills.exe --help 2>&1 | Select-Object -First 5
.\.smoke-venv\Scripts\iknowkungfu-mcp.exe --help 2>&1 | Select-Object -First 5
Remove-Item -Recurse -Force .smoke-venv
```

Expected: version prints `0.1.2`; `kfu` and `agent-skills` both emit help with prog `kfu`; `iknowkungfu-mcp` resolves.

- [ ] **Step 4: Collect reviewer report**

Read the reviewer's output. Filter for "high" and "critical" confidence findings.

- [ ] **Step 5: Address findings**

For each critical/high finding: apply the suggested fix. For medium/low: log to `docs/handoff/2026-05-12-execution-handoff-session7.md` § Known-issues backlog instead of fixing inline (handoff item 6 stays out-of-scope here).

- [ ] **Step 6: Re-run test suite if any fixes were applied**

```powershell
python -m pytest tests/ -q --tb=no 2>&1 | Select-String "passed" | Select-Object -Last 1
```

Expected: `446 passed, 1 skipped`.

---

### Task 11: Commit 7 — chore(brand): Phase 1 rename

**Files:** all Pass B files staged together.

- [ ] **Step 1: Stage**

```powershell
git add -A
git status --short
```

Expected: ~22 modified files. NO untracked. NO tests changed.

- [ ] **Step 2: Commit**

```powershell
git commit -m @'
chore(brand)!: rename to I Know Kung Fu, bump to 0.1.2

External rename per ADR-001:

- PyPI package: agent-skills → iknowkungfu
- CLI primary: agent-skills → kfu (agent-skills retained as back-compat alias)
- Brand (README, docs): agent-skills → I Know Kung Fu
- Repo URLs in default registry config → samuelgudi/iknowkungfu

Stays unchanged (per ADR-001 § Decision 5 + 7):

- Python module on disk: agent_skills/
- Cache directory: ~/.cache/agent-skills/
- Marker filename: .agent-skills-marker.json
- Env vars: AGENT_SKILLS_*
- Registry skill IDs under skills/samuelgudi/agent-skills-*

Version: 0.1.1 → 0.1.2.

BREAKING: pip-install name changes to iknowkungfu. The agent-skills CLI
command continues to work as a back-compat alias and resolves to the
same entry point.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

- [ ] **Step 3: Final clean-tree check**

```powershell
git status --short
git log --oneline -8
```

Expected: empty status, 7 new commits on top of `15ad517`.

---

### Task 12: Final verification + DAEMON notify

**Files:** none.

- [ ] **Step 1: Final full-suite test**

```powershell
python -m pytest tests/ -q --tb=no 2>&1 | Select-String "passed" | Select-Object -Last 1
```

Expected: `446 passed, 1 skipped`.

- [ ] **Step 2: Build final wheel**

```powershell
Remove-Item -Recurse -Force dist, build, *.egg-info -ErrorAction SilentlyContinue
python -m build 2>&1 | Select-String "Successfully built"
Get-ChildItem dist
```

Expected: `iknowkungfu-0.1.2.tar.gz` and `iknowkungfu-0.1.2-py3-none-any.whl` present.

- [ ] **Step 3: DAEMON notify**

Send DAEMON notification:

> Phase 1 rename + Pass A polish complete on `samuelgudi/iknowkungfu` `main`.
> 7 commits ahead of `15ad517`. 446 tests passing. Wheel built (`iknowkungfu-0.1.2`).
> Ready for push + `twine upload` whenever you give the green light.
> Reviewer findings: <summary, or "none above medium">.

- [ ] **Step 4: Stop. Do NOT push.**

Per Samuel's instruction: stop at push. Wait for explicit user confirmation.

---

## Self-review checklist

After plan complete, before execution:

1. **Spec coverage**: every item in handoff § "Phase 1 — Codebase rename" has a task? Yes — items 1-10 mapped to Task 8 substitution table; items kept-as-is (cache, marker, env, module) explicitly excluded.
2. **No placeholders**: every code/command shown verbatim? Yes — substitutions are full string forms, commit messages are HEREDOC literals.
3. **Type consistency**: `kfu` (CLI), `iknowkungfu` (pkg/MCP cmd), `I Know Kung Fu` (brand) used consistently across the substitution table? Yes — checked.
4. **Test plan**: tests run after Task 6 (Pass A clean), Task 9 (Pass B applied), Task 12 (final). 3 checkpoints, sufficient.
5. **Stop conditions**: Task 12 step 4 explicit "Do NOT push". Handoff stop-conditions honored (no name re-litigation, no MCP redesign).
