# agent-skills hub v0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement v0 of `agent-skills` — an agent-agnostic registry for skill discovery and contribution, with Claude Code and Hermes adapters, full discovery+contribution pipeline, deterministic match scoring, registry-anchored integrity, per-version yanking, and CI.

**Architecture:** Single flat-file git monorepo. `agent_skills/` Python package provides the `agent-skills` CLI. Three layers:
1. **Tooling** (`scripts/`): validate.py + security_scan.py + generate_manifest.py operate on the registry; CI runs them.
2. **Adapters** (`adapters/`): per-host install/uninstall/verify logic (Claude Code, Hermes; extensible by adding `<name>.py`).
3. **Clients** (`clients/`): discovery (match.py, update.py) and contribution (sanitize.py, diff.py, submit.py); also installable as skills themselves.

**Tech Stack:** Python 3.10+ (stdlib-first), `jsonschema` for schema validation, `PyYAML` for rules.yaml, `gh` CLI for GitHub operations, `pytest` for tests. No web service. No external network during install (verified by `NET-IN-ADAPTER` rule).

**Spec ref:** `docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md` (v4, post-Hermes Agent + Gemini + walkthrough). Read §§ 4 (locked decisions) + 5 (repo layout) + 7 (schema) before starting Task 1.

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata; installs `agent-skills` console script via entry_points |
| `SCHEMA.md` | Human-readable field spec + category taxonomy |
| `scripts/schema.json` | Machine-readable JSON Schema (draft 2020-12) |
| `scripts/rules.yaml` | Declarative security-scan rules |
| `SECURITY.md` | Reviewer checklist + yank procedure |
| `CONTRIBUTING.md` | Human submission walkthrough + skill-description guideline |
| `registry.json` | Generated manifest; auto-rebuilt by `generate_manifest.py` |
| `yanks.json` | Append-only operational yank list |
| `scripts/validate.py` | Schema + cross-file + cross-skill validation |
| `scripts/security_scan.py` | Pattern-based content scan of `scripts/` and `templates/` |
| `scripts/generate_manifest.py` | Builds registry.json from skills/ tree + git log + yanks.json |
| `adapters/_base.py` | Adapter ABC + shared install/uninstall mechanics + marker |
| `adapters/claude_code.py` | Claude Code adapter (`~/.claude/skills/<author>-<slug>/`) |
| `adapters/hermes.py` | Hermes adapter (`~/.hermes/skills/<category>/<slug>/`) + frontmatter synthesis |
| `agent_skills/cli.py` | Argparse verb dispatch (`agent-skills` entry point) |
| `agent_skills/detect.py` | Host auto-detection |
| `agent_skills/cache.py` | `~/.cache/agent-skills/` helpers |
| `clients/skill-discovery/match.py` | Keyword + filter scoring; deterministic ranking |
| `clients/skill-discovery/update.py` | Registry refresh with monotonicity guard |
| `clients/skill-contribution/sanitize.py` | Path/secret/prompt-injection detection (interactive) |
| `clients/skill-contribution/diff.py` | Post-sanitization diff generation |
| `clients/skill-contribution/submit.py` | 5-step submit flow; opens PR via gh |
| `.github/workflows/ci.yml` | validate + scan + manifest-check + pytest + GitHub-ID check on PRs |
| `.github/workflows/on-merge.yml` | Move submitted/ to skills/; regenerate manifest; tag release |
| `tests/fixtures/good/*` | Canonical valid skills (instructions-only, with-scripts, deprecated, multi-version, multi-agent) |
| `tests/fixtures/bad/*` | One fixture per documented validation rule |
| `tests/conftest.py` | tmpdir, fake-gh shim, fake-registry http.server fixtures |

---

## Execution Order and Dependencies

Tasks are ordered so that each task's prerequisites complete first. Independent tasks within a phase can be parallelized by a subagent dispatcher. Phase boundaries are explicit checkpoints.

- **Phase 1 — Foundation** (Tasks 1-7): can largely run in parallel after Task 1.
- **Phase 2 — Registry Tooling** (Tasks 8-10): each depends on Phase 1 fixtures + schema.
- **Phase 3 — Adapters** (Tasks 11-13): depend on Phase 1 + 2.
- **Phase 4 — Top-level CLI** (Tasks 14-21): CLI scaffold first, then verbs (each verb is independent of the others).
- **Phase 5 — Contribution Flow** (Tasks 22-28): depend on Phase 4.
- **Phase 6 — CI** (Tasks 29-30): depend on all prior tooling existing.
- **Phase 7 — Hardening** (Tasks 31-33): seed skills + docs polish.

---

# Phase 1 — Foundation

## Task 1: Project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `agent_skills/__init__.py`
- Create: `agent_skills/__main__.py`
- Modify: `.gitignore` (already exists from initial commit — append python-test entries)

- [ ] **Step 1: Write pyproject.toml**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agent-skills"
version = "0.1.0"
description = "Agent-agnostic registry for skill discovery and contribution"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "Samuel Gudi", email = "samuel.gudi.official@gmail.com" }]
dependencies = [
  "jsonschema>=4.20",
  "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-cov>=4.1",
]

[project.scripts]
agent-skills = "agent_skills.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["agent_skills*", "adapters*"]
```

- [ ] **Step 2: Create the package entrypoint**

Create `agent_skills/__init__.py`:

```python
"""agent-skills — agent-agnostic skill registry CLI."""

__version__ = "0.1.0"
```

Create `agent_skills/__main__.py`:

```python
from agent_skills.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Verify pip install works**

Run:
```bash
pip install -e .[dev]
```

Expected: installs without errors. `agent-skills` command appears on PATH but currently fails because `cli.py` doesn't exist yet — that's expected.

- [ ] **Step 4: Add Python-specific patterns to .gitignore (already present from initial commit — verify)**

Run:
```bash
grep -E "^(\.pytest_cache|\.coverage|build/|dist/|\*.egg-info)" .gitignore
```

Expected: all entries present (from the initial commit's .gitignore). If any missing, append.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml agent_skills/__init__.py agent_skills/__main__.py
git commit -m "feat: bootstrap agent_skills package skeleton"
```

---

## Task 2: SCHEMA.md authored

**Files:**
- Create: `SCHEMA.md`

- [ ] **Step 1: Write SCHEMA.md from spec § 7 (registry.json fields) + § 8 (meta.json fields)**

Create `SCHEMA.md` with the full schema reference. The document must list every field with type, required/optional, semantics. Include the v0 starter category taxonomy explicitly: `media`, `dev`, `ops`, `data`, `comms`, `docs`, `meta`, `ai`. Cite the spec's § 7 field-semantics table verbatim.

Include sections:
1. Overview (1 paragraph: source of truth for `validate.py` and `generate_manifest.py`).
2. registry.json top-level structure (with `schema_version: 2`).
3. Skill entry fields (full table from spec § 7 with v4 updates: `author.github_login` + `author.github_id`, `versions` map, no `toolsets`).
4. meta.json fields (mirror of registry entry minus derived fields).
5. yanks.json structure (from spec § 7).
6. Category taxonomy enumerated: media, dev, ops, data, comms, docs, meta, ai. Each with one-line description.
7. Slug grammar regex: `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`.
8. Semver requirement for version field.

Direct quote: keep aligned with spec; if there's drift, the spec wins and this file is updated.

- [ ] **Step 2: Verify SCHEMA.md mentions every required field from spec**

Run:
```bash
grep -cE "(id|name|description|version|status|author|category|tags|platforms|agent_compat|requires|has_scripts|license|install|source|provenance|versions|composes|extends|supersedes|superseded_by)" SCHEMA.md
```

Expected: count ≥ 20 (every field surfaces at least once).

- [ ] **Step 3: Commit**

```bash
git add SCHEMA.md
git commit -m "docs: author SCHEMA.md from spec v4"
```

---

## Task 3: scripts/schema.json (machine-readable)

**Files:**
- Create: `scripts/schema.json`

- [ ] **Step 1: Write schema.json as JSON Schema draft 2020-12 covering the registry.json top-level + skill entry**

Create `scripts/schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://github.com/samuelgudi/agent-skills/scripts/schema.json",
  "title": "agent-skills registry",
  "type": "object",
  "required": ["schema_version", "generated_at", "skills"],
  "properties": {
    "schema_version": { "const": 2 },
    "generated_at": { "type": "string", "format": "date-time" },
    "skills": { "type": "array", "items": { "$ref": "#/$defs/skill" } }
  },
  "$defs": {
    "skill": {
      "type": "object",
      "required": [
        "id", "name", "description", "version", "status",
        "author", "category", "agent_compat", "license",
        "install", "source", "versions"
      ],
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z][a-z0-9-]{0,38}[a-z0-9]/[a-z][a-z0-9-]{0,38}[a-z0-9]$" },
        "name": { "type": "string", "pattern": "^[a-z][a-z0-9-]{0,38}[a-z0-9]$" },
        "description": { "type": "string", "minLength": 1 },
        "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+(-[0-9A-Za-z-.]+)?$" },
        "status": { "enum": ["active", "deprecated"] },
        "author": {
          "type": "object",
          "required": ["name", "github_login", "github_id"],
          "properties": {
            "name":         { "type": "string", "minLength": 1 },
            "github_login": { "type": "string", "minLength": 1 },
            "github_id":    { "type": "integer", "minimum": 1 }
          },
          "additionalProperties": false
        },
        "category": { "enum": ["media", "dev", "ops", "data", "comms", "docs", "meta", "ai"] },
        "tags": { "type": "array", "items": { "type": "string", "pattern": "^[a-z0-9-]+$" }, "maxItems": 10 },
        "platforms": { "type": "array", "items": { "enum": ["linux", "macos", "windows"] } },
        "agent_compat": {
          "type": "array",
          "items": { "enum": ["claude-code", "hermes", "codex", "opencode"] },
          "minItems": 1
        },
        "requires": {
          "type": "object",
          "properties": {
            "env_vars": { "type": "array", "items": { "type": "string" } },
            "commands": { "type": "array", "items": { "type": "string" } }
          },
          "additionalProperties": false
        },
        "has_scripts": { "type": "boolean" },
        "license":     { "type": "string", "minLength": 1 },
        "install":     { "type": "object", "minProperties": 1 },
        "source": {
          "type": "object",
          "required": ["path", "content_hash", "files"],
          "properties": {
            "path":         { "type": "string" },
            "content_hash": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
            "files":        { "type": "array", "items": { "type": "string" } }
          },
          "additionalProperties": false
        },
        "versions": {
          "type": "object",
          "minProperties": 1,
          "additionalProperties": {
            "type": "object",
            "required": ["sha", "released"],
            "properties": {
              "sha":         { "type": "string", "pattern": "^[0-9a-f]{40}$" },
              "released":    { "type": "string", "format": "date-time" },
              "yanked":      { "type": "boolean" },
              "yank_reason": { "type": "string", "minLength": 1 }
            },
            "additionalProperties": false
          }
        },
        "provenance": {
          "type": "object",
          "properties": {
            "submitted_pr": { "type": "integer" },
            "merged_at":    { "type": "string", "format": "date-time" },
            "reviewed_by":  { "type": "string" }
          },
          "additionalProperties": false
        },
        "composes":      { "type": "array", "items": { "type": "string" } },
        "extends":       { "type": ["string", "null"] },
        "supersedes":    { "type": "array", "items": { "type": "string" } },
        "superseded_by": { "type": ["string", "null"] }
      },
      "if":   { "properties": { "status": { "const": "deprecated" } } },
      "then": { "required": ["superseded_by"], "properties": { "superseded_by": { "type": "string" } } }
    }
  }
}
```

- [ ] **Step 2: Verify schema.json is valid JSON**

Run:
```bash
python -c "import json; json.load(open('scripts/schema.json'))"
```

Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/schema.json
git commit -m "feat: add machine-readable schema.json (JSON Schema draft 2020-12)"
```

---

## Task 4: scripts/rules.yaml — v0 security-scan ruleset

**Files:**
- Create: `scripts/rules.yaml`

- [ ] **Step 1: Write rules.yaml with the v0 hard-block + soft-warn rules from spec § 10**

Create `scripts/rules.yaml`:

```yaml
# agent-skills security_scan.py rules (v0)
# Spec reference: docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md § 10

rules:
  # ---- Hard blocks (no override in v0) ----

  - id: PY-EVAL-CALL
    severity: block
    pattern: '\beval\s*\('
    languages: [python]
    message: "Python eval-builtin executes arbitrary code"
    fix_hint: "Parse the value explicitly (use ast.literal_eval for literals, or a real parser)."

  - id: PY-EXEC-CALL
    severity: block
    pattern: '\bexec\s*\('
    languages: [python]
    message: "Python exec-builtin executes arbitrary code"
    fix_hint: "Refactor to avoid dynamic code execution."

  - id: JS-FUNCTION-CTOR
    severity: block
    pattern: '\bnew\s+Function\s*\('
    languages: [javascript]
    message: "JS Function constructor enables dynamic code execution"
    fix_hint: "Refactor to avoid the Function constructor; use static functions."

  - id: PY-SHELL-INTERP
    severity: block
    pattern: 'subprocess\.\w+\([^)]*shell\s*=\s*True[^)]*[+f"]'
    languages: [python]
    message: "subprocess with shell=True and non-literal args — command injection risk"
    fix_hint: "Pass args as a list; drop shell=True."

  - id: SH-CURL-PIPE
    severity: block
    pattern: '(curl|wget)\s+[^|]*\|\s*(bash|sh|zsh)'
    languages: [python, bash, javascript]
    message: "Piping remote content into a shell interpreter is unsafe"
    fix_hint: "Download, verify sha256, then execute. Or declare the tool in requires.commands."

  - id: B64-PAYLOAD
    severity: block
    pattern: '["''][A-Za-z0-9+/=]{50,}["'']'
    languages: [python, javascript, bash]
    message: "Long base64 string in source — possible obfuscated payload"
    fix_hint: "Inline the decoded content if it's data, or document the encoding clearly."

  - id: NET-IN-ADAPTER
    severity: block
    pattern: '(urllib|requests|fetch|http\.)'
    languages: [python]
    scope: "adapters/**"
    message: "Install adapters must be offline-deterministic"
    fix_hint: "Move network access to discovery client; install only reads from local source."

  - id: PKG-INSTALL
    severity: block
    pattern: '\b(pip|pipx|uv|npm|pnpm|yarn|gem|cargo|go|brew|apt|apt-get|dnf|yum|apk)\s+(install|add)\b'
    languages: [python, bash, javascript]
    message: "Package-manager install in scripts/ enables post-merge code swap (event-stream / dependency-confusion vector)"
    fix_hint: "Declare the dependency in meta.json.requires.commands; the user/host installs it before invocation."

  # ---- Soft warnings (proceed, recorded in REVIEW.md) ----

  - id: PY-SUBPROCESS-USE
    severity: warn
    pattern: '\bsubprocess\.'
    languages: [python]
    message: "Skill spawns subprocesses — declare commands in meta.json.requires.commands"
    fix_hint: "Add the spawned binary to requires.commands."

  - id: FS-WRITE-OUTSIDE-SKILL
    severity: warn
    pattern: '(open\([^)]*[''"]w[''"]?|Path\([^)]*\)\.write_text)'
    languages: [python]
    message: "Filesystem write detected — confirm path is inside ${SKILL_DIR}/cache/"
    fix_hint: "Restrict writes to ${SKILL_DIR}/cache/ or document the path in REVIEW.md."

  - id: NET-IN-SCRIPT
    severity: warn
    pattern: '(urllib|requests|fetch|http\.|aiohttp|httpx)'
    languages: [python]
    scope: "scripts/**"
    message: "Network call in script — disclose endpoint in REVIEW.md"
    fix_hint: "List the endpoint in REVIEW.md → What does it access? → Network endpoints."

  - id: UNDECLARED-CMD
    severity: warn
    pattern: '\b(ssh|git|docker|kubectl|aws|gcloud|az)\b'
    languages: [python, bash]
    message: "External binary referenced — declare in meta.json.requires.commands if used"
    fix_hint: "If this binary is invoked at runtime, add it to requires.commands."
```

- [ ] **Step 2: Verify rules.yaml is valid**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('scripts/rules.yaml'))"
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add scripts/rules.yaml
git commit -m "feat: add v0 security_scan rules.yaml (8 hard-blocks + 4 soft-warns)"
```

---

## Task 5: Empty registry.json + yanks.json

**Files:**
- Create: `registry.json`
- Create: `yanks.json`

- [ ] **Step 1: Write empty registry.json**

Create `registry.json`:

```json
{
  "schema_version": 2,
  "generated_at": "1970-01-01T00:00:00Z",
  "skills": []
}
```

`generated_at` is a placeholder; `generate_manifest.py` will overwrite with the commit timestamp on first run.

- [ ] **Step 2: Write empty yanks.json**

Create `yanks.json`:

```json
{
  "yanks": []
}
```

- [ ] **Step 3: Commit**

```bash
git add registry.json yanks.json
git commit -m "feat: initialize empty registry.json + yanks.json"
```

---

## Task 6: SECURITY.md + CONTRIBUTING.md

**Files:**
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Write SECURITY.md**

Create `SECURITY.md` with:

1. **Threat model** (1 paragraph): registry distributes executable content; primary threat is post-merge supply-chain compromise.
2. **Reviewer checklist** (numbered):
   - Read REVIEW.md → match claims against actual code.
   - Inspect SANITIZATION.diff → did sanitization quietly add anything?
   - Inspect scan_results.json → all hard-blocks zero; warnings acknowledged in REVIEW.md.
   - For `has_scripts: true` PRs: line-by-line script review; verify capability declarations match actual access; verify real test evidence present.
   - For new authors: verify github_id was fetched fresh from `gh api users/<login>`.
   - For yank PRs: verify version exists; reason is concrete (not "just because").
3. **Reporting** (1 paragraph): vulnerabilities reported to samuel.gudi.official@gmail.com (NOT a public issue). Yank workflow procedure inline.
4. **Yank procedure** (numbered): run `agent-skills yank <id>@<version> --reason "..."`; review PR; merge; verify `versions[ver].yanked = true` in regenerated registry.json.

- [ ] **Step 2: Write CONTRIBUTING.md**

Create `CONTRIBUTING.md` with:

1. **Getting started** (numbered): clone, install `agent-skills` CLI, write SKILL.md, run `agent-skills init`, run `agent-skills submit`.
2. **Skill design guidelines**:
   - Slug grammar (link to SCHEMA.md).
   - Description must be a complete sentence describing WHEN to invoke, not just WHAT (M5 guideline).
   - Include English keywords for search even when description is non-English (W5 guideline).
   - For personal/private skills, qualify the slug or don't publish (W7 guideline).
3. **Frontmatter contract** (link to SCHEMA.md).
4. **REVIEW.md template** with the 6 fields from spec § 10 Step 4.
5. **Test discipline**: instructions-only skills can omit test evidence; `has_scripts: true` skills MUST include real commands + outputs.
6. **Common rejection reasons** (numbered list):
   - meta.json fields missing or malformed.
   - SKILL.md filename is lowercase (Linux CI rejects).
   - GitHub ID mismatch (username was re-registered).
   - PKG-INSTALL detected in scripts.
   - Description doesn't include WHEN-to-invoke wording.

- [ ] **Step 3: Commit**

```bash
git add SECURITY.md CONTRIBUTING.md
git commit -m "docs: author SECURITY.md (review checklist + yank procedure) and CONTRIBUTING.md (author guidelines)"
```

---

## Task 7: Test fixtures

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/fixtures/good/instructions-only/{SKILL.md,meta.json}`
- Create: `tests/fixtures/good/with-scripts/{SKILL.md,meta.json,scripts/example.py}`
- Create: `tests/fixtures/good/with-templates/{SKILL.md,meta.json,templates/output.md}`
- Create: `tests/fixtures/good/deprecated/{SKILL.md,meta.json}`
- Create: `tests/fixtures/good/multi-agent/{SKILL.md,meta.json}`
- Create: `tests/fixtures/good/multi-version/{SKILL.md,meta.json}` (versions added later via test git history)
- Create: `tests/fixtures/bad/<rule-name>/{SKILL.md,meta.json}` × ~15
- Create: `tests/conftest.py`

- [ ] **Step 1: Create empty tests/__init__.py**

Run:
```bash
mkdir -p tests/fixtures/good tests/fixtures/bad
touch tests/__init__.py
```

- [ ] **Step 2: Write tests/fixtures/good/instructions-only/**

Create `tests/fixtures/good/instructions-only/SKILL.md`:

```markdown
---
name: example-skill
description: Example instructions-only skill for testing. Use when running validate.py against canonical good input.
---

# Example Skill

This is a test fixture. Body contains no scripts and no sensitive data.

## When to use
- Pytest fixture only.

## Limits
- Read-only.
```

Create `tests/fixtures/good/instructions-only/meta.json`:

```json
{
  "id": "test-author/example-skill",
  "version": "0.1.0",
  "status": "active",
  "author": { "name": "Test Author", "github_login": "test-author", "github_id": 1 },
  "category": "meta",
  "tags": ["test", "fixture"],
  "platforms": ["linux", "macos", "windows"],
  "agent_compat": ["claude-code", "hermes"],
  "requires": { "env_vars": [], "commands": [] },
  "license": "MIT",
  "install": { "claude-code": { "scope": "user" }, "hermes": {} },
  "composes": [],
  "extends": null,
  "supersedes": [],
  "superseded_by": null,
  "related_skills": []
}
```

- [ ] **Step 3: Write tests/fixtures/good/with-scripts/**

Create `tests/fixtures/good/with-scripts/SKILL.md` (same shape as instructions-only, but body mentions scripts/example.py and declares the dependency).

Create `tests/fixtures/good/with-scripts/scripts/example.py`:

```python
"""Example script — no network, no secrets, no eval/exec."""
import json
import sys


def main():
    print(json.dumps({"status": "ok"}))


if __name__ == "__main__":
    sys.exit(main() or 0)
```

Create `meta.json` with `tags` mentioning `test`, `with-scripts`, and `requires.commands = []` (no external commands needed).

- [ ] **Step 4: Write remaining good/ fixtures**

For each remaining fixture (`with-templates`, `deprecated`, `multi-agent`, `multi-version`):

- `with-templates`: same as instructions-only + a `templates/output.md` (plain text body).
- `deprecated`: `meta.json` has `status: "deprecated"` AND `superseded_by: "test-author/example-skill"` (refers back to instructions-only).
- `multi-agent`: `meta.json` has `agent_compat: ["claude-code", "hermes", "codex", "opencode"]`.
- `multi-version`: same as instructions-only; versions are simulated by committing changes in test setup.

- [ ] **Step 5: Write bad/ fixtures (one per rule)**

For each bad fixture, the fixture name == the validation rule it violates. Each contains a minimal SKILL.md + meta.json that fails exactly that rule.

Names to create (with the violation in meta.json or filename):

1. `slug-with-uppercase` — `id: "test-author/Example-Skill"` (uppercase in slug).
2. `slug-path-traversal` — `id: "test-author/../etc"`.
3. `missing-license` — `meta.json` lacks `license`.
4. `deprecated-no-successor` — `status: "deprecated"`, `superseded_by: null`.
5. `deprecated-cycle` — A.superseded_by=B, B.superseded_by=A (two-fixture pair).
6. `composes-cycle` — A.composes=[B], B.composes=[A].
7. `extends-cycle` — A.extends=B, B.extends=A.
8. `same-slug-collision` — two fixtures with different authors but same slug `colliding-slug`.
9. `frontmatter-mismatch` — SKILL.md name=`other`, meta.json id=`test-author/example`.
10. `extraneous-file` — adds `secrets.txt` not in any declared list.
11. `nested-git` — has `.git/HEAD` directly in the skill dir.
12. `nested-git-in-scripts` — has `scripts/.git/HEAD`.
13. `pkg-install-pip` — has `scripts/setup.sh` containing `pip install some-pkg`.
14. `pkg-install-npm` — has `scripts/setup.js` containing `npm install some-pkg`.
15. `pkg-install-apt` — has `scripts/setup.sh` containing `apt-get install some-pkg`.
16. `github-id-mismatch` — `meta.json` has `github_id: 12345`; conftest will mock `gh api` to return a different id.
17. `tag-cap-exceeded` — `tags` array has 11 entries.
18. `yank-no-reason` — used by yank-validation tests; entry in yanks.json with empty `reason`.

For each, write the minimal `SKILL.md` + `meta.json` that fails exactly that check. Use a doc comment in each fixture's `meta.json` (if JSONC) — actually JSON doesn't support comments, so add a `README.md` per fixture noting "violates rule X".

- [ ] **Step 6: Write conftest.py with shared fixtures**

Create `tests/conftest.py`:

```python
"""Shared pytest fixtures."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Patch HOME to a tmpdir for adapter tests."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


@pytest.fixture
def fake_gh(tmp_path, monkeypatch):
    """Install a fake `gh` shim on PATH. Returns the shim's invocation log path."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "gh.log"
    response_file = tmp_path / "gh.response"
    response_file.write_text(json.dumps({"id": 12345678, "login": "test-author"}))
    shim = bin_dir / ("gh.bat" if os.name == "nt" else "gh")
    if os.name == "nt":
        shim.write_text(
            f'@echo off\r\n'
            f'echo %* >> "{log_file}"\r\n'
            f'type "{response_file}"\r\n'
        )
    else:
        shim.write_text(
            f'#!/bin/sh\n'
            f'echo "$@" >> "{log_file}"\n'
            f'cat "{response_file}"\n'
        )
        os.chmod(shim, 0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    yield {"log": log_file, "response": response_file}


@pytest.fixture
def fake_registry_server(tmp_path):
    """Spin up an http.server serving a controlled registry.json. Yields the URL."""
    import http.server
    import socketserver
    import threading

    serve_dir = tmp_path / "registry"
    serve_dir.mkdir()
    handler = http.server.SimpleHTTPRequestHandler

    def serve():
        os.chdir(serve_dir)
        with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
            yield_url[0] = f"http://127.0.0.1:{httpd.server_address[1]}/registry.json"
            httpd.serve_forever()

    yield_url = [None]
    t = threading.Thread(target=serve, daemon=True)
    t.start()
    while yield_url[0] is None:
        pass
    yield {"url": yield_url[0], "dir": serve_dir}


@pytest.fixture
def good_fixture(request):
    """Yield a copy of a good/<name>/ fixture into tmp_path."""
    name = request.param
    src = FIXTURES_DIR / "good" / name
    return src


@pytest.fixture
def bad_fixture(request):
    name = request.param
    src = FIXTURES_DIR / "bad" / name
    return src
```

- [ ] **Step 7: Verify pytest can collect tests**

Run:
```bash
pytest tests/ --collect-only -q
```

Expected: pytest discovers `tests/conftest.py` and finds 0 tests (none written yet). No errors.

- [ ] **Step 8: Commit**

```bash
git add tests/
git commit -m "test: scaffold fixtures (good/ + bad/) and shared pytest conftest.py"
```

---

# Phase 2 — Registry Tooling

## Task 8: scripts/validate.py

**Files:**
- Create: `scripts/validate.py`
- Create: `tests/test_validate.py`

Validate.py is responsible for: JSON Schema validation (via schema.json), plus cross-file checks (frontmatter ↔ meta.json), plus cross-skill checks (deprecation cycles, superseded_by references), plus the v3/v4 additions (github_id check, SKILL.md uppercase exact, category enum, requires field validation).

Implementing this is ~12 TDD cycles, one per validation rule.

- [ ] **Step 1: Write test for schema-valid-fixture**

Create `tests/test_validate.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
VALIDATE = ROOT / "scripts" / "validate.py"


def run_validate(*args):
    return subprocess.run(
        [sys.executable, str(VALIDATE), *args],
        capture_output=True, text=True
    )


def test_good_instructions_only_passes():
    result = run_validate(str(ROOT / "tests/fixtures/good/instructions-only"))
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
```

- [ ] **Step 2: Run test, verify it fails (no script yet)**

Run:
```bash
pytest tests/test_validate.py::test_good_instructions_only_passes -v
```

Expected: FAIL with "No such file or directory" or similar (validate.py doesn't exist).

- [ ] **Step 3: Write minimal validate.py — schema check only**

Create `scripts/validate.py`:

```python
"""validate.py — schema + cross-file + cross-skill validation."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import jsonschema


ROOT = Path(__file__).parent.parent
SCHEMA_FILE = Path(__file__).parent / "schema.json"
SLUG_REGEX = re.compile(r"^[a-z][a-z0-9-]{0,38}[a-z0-9]$")
ID_REGEX = re.compile(r"^[a-z][a-z0-9-]{0,38}[a-z0-9]/[a-z][a-z0-9-]{0,38}[a-z0-9]$")
SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z-.]+)?$")
ALLOWED_CATEGORIES = {"media", "dev", "ops", "data", "comms", "docs", "meta", "ai"}


def parse_frontmatter(skill_md: Path) -> dict:
    """Parse YAML frontmatter from SKILL.md. Returns dict or raises."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_md}: missing YAML frontmatter delimiter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError(f"{skill_md}: unterminated frontmatter")
    import yaml
    return yaml.safe_load(text[4:end])


def validate_skill_dir(skill_dir: Path, *, strict: bool = False) -> list[dict]:
    """Validate one skill directory. Returns list of issues with severity + message."""
    issues = []

    skill_md = skill_dir / "SKILL.md"
    meta_file = skill_dir / "meta.json"

    if not skill_md.is_file():
        issues.append({"severity": "error", "msg": "SKILL.md missing (must be uppercase)"})
        return issues
    if not meta_file.is_file():
        issues.append({"severity": "error", "msg": "meta.json missing"})
        return issues

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        issues.append({"severity": "error", "msg": f"meta.json parse error: {e}"})
        return issues

    try:
        fm = parse_frontmatter(skill_md)
    except Exception as e:
        issues.append({"severity": "error", "msg": str(e)})
        return issues

    # Cross-file checks
    if fm.get("name") != meta.get("id", "").split("/", 1)[-1]:
        issues.append({"severity": "error", "msg": f"frontmatter name '{fm.get('name')}' != meta.json id slug part '{meta.get('id', '').split('/', 1)[-1]}'"})
    if fm.get("description") != meta.get("description"):
        # description not yet enforced bidirectionally — skip for now
        pass

    # Slug grammar
    if not ID_REGEX.match(meta.get("id", "")):
        issues.append({"severity": "error", "msg": f"id '{meta.get('id')}' doesn't match author/slug regex"})

    # Required fields (subset; schema.json catches the full set)
    for required in ("id", "version", "status", "author", "category", "agent_compat", "license", "install"):
        if required not in meta:
            issues.append({"severity": "error", "msg": f"meta.json missing required field: {required}"})

    # Category enum
    if meta.get("category") not in ALLOWED_CATEGORIES:
        issues.append({"severity": "error", "msg": f"category '{meta.get('category')}' not in {sorted(ALLOWED_CATEGORIES)}"})

    # Tag cap
    tags = meta.get("tags", [])
    if len(tags) > 10:
        issues.append({"severity": "error", "msg": f"tags count {len(tags)} > 10 (anti-stuffing cap)"})

    # requires sub-fields restriction
    requires = meta.get("requires", {})
    allowed_requires = {"env_vars", "commands"}
    extra = set(requires.keys()) - allowed_requires
    if extra:
        issues.append({"severity": "error", "msg": f"requires has unknown sub-fields: {extra}; only {allowed_requires} allowed"})

    # Deprecation: superseded_by must be set
    if meta.get("status") == "deprecated" and not meta.get("superseded_by"):
        issues.append({"severity": "error", "msg": "status=deprecated requires non-null superseded_by"})

    # Semver
    if not SEMVER_REGEX.match(meta.get("version", "")):
        issues.append({"severity": "error", "msg": f"version '{meta.get('version')}' not valid semver"})

    return issues


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("target", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    targets: list[Path] = []
    if args.all:
        for parent in (ROOT / "skills", ROOT / "archive"):
            if parent.exists():
                for author in parent.iterdir():
                    if author.is_dir():
                        for slug in author.iterdir():
                            if slug.is_dir():
                                targets.append(slug)
    elif args.target:
        targets.append(Path(args.target))
    else:
        p.error("target or --all required")

    all_issues = {}
    for t in targets:
        all_issues[str(t)] = validate_skill_dir(t, strict=args.strict)

    if args.json:
        print(json.dumps(all_issues, indent=2))
    else:
        for path, issues in all_issues.items():
            if not issues:
                print(f"{path}: clean")
                continue
            print(f"{path}:")
            for i in issues:
                print(f"  {i['severity'].upper()}  {i['msg']}")

    has_errors = any(i["severity"] == "error" for issues in all_issues.values() for i in issues)
    has_warnings = any(i["severity"] == "warning" for issues in all_issues.values() for i in issues)
    if has_errors:
        return 1
    if has_warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test, verify it passes**

Run:
```bash
pytest tests/test_validate.py::test_good_instructions_only_passes -v
```

Expected: PASS.

- [ ] **Step 5: Add tests for each bad/ fixture (one test per rule)**

Append to `tests/test_validate.py`:

```python
@pytest.mark.parametrize("name,expected_msg_substring", [
    ("slug-with-uppercase", "regex"),
    ("missing-license", "license"),
    ("deprecated-no-successor", "superseded_by"),
    ("tag-cap-exceeded", "tags count"),
])
def test_bad_fixture_fails(name, expected_msg_substring):
    result = run_validate(str(ROOT / f"tests/fixtures/bad/{name}"))
    assert result.returncode != 0, f"Expected fail; got: {result.stdout}"
    assert expected_msg_substring in result.stdout, f"Expected '{expected_msg_substring}' in output, got: {result.stdout}"
```

- [ ] **Step 6: Run, verify each parametrized case fails as expected**

Run:
```bash
pytest tests/test_validate.py -v
```

Expected: all `test_bad_fixture_fails` cases PASS (the validate.py returns nonzero AND the expected substring is found).

If any fail, refine validate.py until they pass.

- [ ] **Step 7: Add tests for github_id mismatch, frontmatter-mismatch, nested-git, etc.**

Add similar parametrized cases for the remaining bad fixtures. Implement validate.py logic for each (e.g., github_id check via `subprocess.run(['gh', 'api', f'users/{login}'], ...)` and parse the response).

For github_id specifically, the test uses the `fake_gh` fixture which mocks the gh CLI's response.

```python
def test_github_id_mismatch_fails(fake_gh, tmp_path):
    # Stage a skill dir whose meta.json declares github_id=999
    # but fake_gh.response returns id=12345678
    skill = tmp_path / "skills/test-author/sample"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: sample\ndescription: test\n---\n")
    (skill / "meta.json").write_text(json.dumps({
        "id": "test-author/sample",
        "version": "0.1.0", "status": "active",
        "author": {"name": "Test", "github_login": "test-author", "github_id": 999},
        "category": "meta", "agent_compat": ["claude-code"],
        "license": "MIT", "install": {"claude-code": {}}
    }))
    result = run_validate(str(skill))
    assert result.returncode != 0
    assert "github_id" in result.stdout
```

Implement the gh-fetch check in validate.py. Catch network errors gracefully (offline mode skips the check with a warning).

- [ ] **Step 8: Run full validate test suite**

Run:
```bash
pytest tests/test_validate.py -v
```

Expected: all tests pass (good fixtures green, bad fixtures correctly identified).

- [ ] **Step 9: Commit**

```bash
git add scripts/validate.py tests/test_validate.py
git commit -m "feat: validate.py with schema + cross-file + github_id checks; tests cover good + bad fixtures"
```

---

## Task 9: scripts/security_scan.py

**Files:**
- Create: `scripts/security_scan.py`
- Create: `tests/test_security_scan.py`
- Modify: `tests/fixtures/bad/` (add pkg-install-* fixtures from Task 7)

- [ ] **Step 1: Write test for clean skill passing**

Create `tests/test_security_scan.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCAN = ROOT / "scripts" / "security_scan.py"


def run_scan(*args):
    return subprocess.run([sys.executable, str(SCAN), *args], capture_output=True, text=True)


def test_clean_with_scripts_passes():
    result = run_scan(str(ROOT / "tests/fixtures/good/with-scripts"))
    assert result.returncode == 0, f"stdout: {result.stdout}"
```

- [ ] **Step 2: Run, verify fail (script doesn't exist)**

```bash
pytest tests/test_security_scan.py -v
```

Expected: FAIL (security_scan.py missing).

- [ ] **Step 3: Implement security_scan.py**

Create `scripts/security_scan.py`:

```python
"""security_scan.py — pattern-based scan of scripts/ and templates/."""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).parent.parent
RULES_FILE = Path(__file__).parent / "rules.yaml"

LANG_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".ts": "javascript", ".mjs": "javascript",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".md": "markdown",
}


def load_rules() -> list[dict]:
    with open(RULES_FILE) as f:
        data = yaml.safe_load(f)
    rules = data["rules"]
    for r in rules:
        r["_compiled"] = re.compile(r["pattern"], re.MULTILINE)
    return rules


def file_language(path: Path) -> str:
    return LANG_BY_EXT.get(path.suffix.lower(), "unknown")


def rule_applies(rule: dict, path: Path, lang: str, repo_relpath: str) -> bool:
    languages = rule.get("languages")
    if languages and lang not in languages:
        return False
    scope = rule.get("scope")
    if scope and not fnmatch.fnmatch(repo_relpath, scope):
        return False
    return True


def scan_file(path: Path, rules: list[dict], repo_relpath: str) -> list[dict]:
    findings = []
    lang = file_language(path)
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings
    for rule in rules:
        if not rule_applies(rule, path, lang, repo_relpath):
            continue
        for match in rule["_compiled"].finditer(content):
            line = content[: match.start()].count("\n") + 1
            findings.append({
                "file": str(path),
                "line": line,
                "rule_id": rule["id"],
                "severity": rule["severity"],
                "message": rule["message"],
                "fix_hint": rule.get("fix_hint", ""),
            })
    return findings


def scan_skill_dir(skill_dir: Path, rules: list[dict]) -> list[dict]:
    findings = []
    for sub in ("scripts", "templates"):
        target = skill_dir / sub
        if not target.exists():
            continue
        for f in target.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(ROOT)).replace("\\", "/")
                findings.extend(scan_file(f, rules, rel))
    return findings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("target", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    rules = load_rules()
    targets: list[Path] = []
    if args.all:
        for parent in (ROOT / "skills", ROOT / "archive"):
            if parent.exists():
                for author in parent.iterdir():
                    for slug in author.iterdir():
                        if slug.is_dir():
                            targets.append(slug)
    elif args.target:
        targets.append(Path(args.target))
    else:
        p.error("target or --all required")

    all_findings = []
    for t in targets:
        all_findings.extend(scan_skill_dir(t, rules))

    if args.json:
        print(json.dumps(all_findings, indent=2))
    else:
        if not all_findings:
            print("clean")
        else:
            for f in all_findings:
                print(f"  {f['file']}")
                print(f"    line {f['line']}  {f['severity'].upper()}  {f['rule_id']}  {f['message']}")
                if f.get("fix_hint"):
                    print(f"                fix: {f['fix_hint']}")

    blocks = [f for f in all_findings if f["severity"] == "block"]
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run clean-pass test, verify it passes**

```bash
pytest tests/test_security_scan.py::test_clean_with_scripts_passes -v
```

Expected: PASS.

- [ ] **Step 5: Add parametrized tests for each PKG-INSTALL bad fixture**

Append to `tests/test_security_scan.py`:

```python
import pytest

@pytest.mark.parametrize("name,expected_rule", [
    ("pkg-install-pip", "PKG-INSTALL"),
    ("pkg-install-npm", "PKG-INSTALL"),
    ("pkg-install-apt", "PKG-INSTALL"),
])
def test_pkg_install_blocks(name, expected_rule):
    result = run_scan(str(ROOT / f"tests/fixtures/bad/{name}"))
    assert result.returncode == 1
    assert expected_rule in result.stdout
```

- [ ] **Step 6: Add tests for eval/exec/shell-interp/curl-pipe**

Add bad fixtures (if missing) and parametrized cases:

```python
@pytest.mark.parametrize("name,rule", [
    ("eval-call", "PY-EVAL-CALL"),
    ("exec-call", "PY-EXEC-CALL"),
    ("shell-interp", "PY-SHELL-INTERP"),
    ("curl-pipe", "SH-CURL-PIPE"),
])
def test_hard_blocks(name, rule):
    result = run_scan(str(ROOT / f"tests/fixtures/bad/{name}"))
    assert result.returncode == 1
    assert rule in result.stdout
```

Create the bad fixtures matching each name. Each contains a `scripts/example.<ext>` whose content matches exactly the rule and nothing else.

- [ ] **Step 7: Add tests for whitespace variants and reflective evasion**

```python
def test_eval_with_whitespace_caught(tmp_path):
    skill = tmp_path / "skills/test/whitespace"
    (skill / "scripts").mkdir(parents=True)
    (skill / "scripts/var.py").write_text("e v a l = 1  # not an eval call\neval ( 'x' )\n")
    result = run_scan(str(skill))
    assert "PY-EVAL-CALL" in result.stdout


def test_reflective_eval_known_miss(tmp_path):
    """Documented limit: getattr(builtins, 'exec') is not caught by pattern. Human review covers."""
    skill = tmp_path / "skills/test/reflect"
    (skill / "scripts").mkdir(parents=True)
    (skill / "scripts/var.py").write_text("import builtins\nfn = getattr(builtins, 'exec')\nfn('x')\n")
    result = run_scan(str(skill))
    # Document the conscious miss: this passes the scan
    assert "PY-EXEC-CALL" not in result.stdout
```

- [ ] **Step 8: Run full security_scan suite**

```bash
pytest tests/test_security_scan.py -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add scripts/security_scan.py tests/test_security_scan.py tests/fixtures/bad/
git commit -m "feat: security_scan.py with PKG-INSTALL + eval/exec/shell-interp + soft-warns; tests cover all rules"
```

---

## Task 10: scripts/generate_manifest.py

**Files:**
- Create: `scripts/generate_manifest.py`
- Create: `tests/test_generate_manifest.py`

- [ ] **Step 1: Write test for deterministic output**

Create `tests/test_generate_manifest.py`:

```python
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
GEN = ROOT / "scripts" / "generate_manifest.py"


def run_gen(cwd, *args):
    return subprocess.run([sys.executable, str(GEN), *args], cwd=cwd, capture_output=True, text=True)


def setup_test_repo(tmp_path):
    """Copy a minimal good fixture into a tmpdir + git init."""
    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "tests"))
    skill = repo / "skills" / "test-author" / "example"
    shutil.copytree(ROOT / "tests/fixtures/good/instructions-only", skill, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "test commit"], cwd=repo, check=True, capture_output=True)
    return repo


def test_generates_registry_json(tmp_path):
    repo = setup_test_repo(tmp_path)
    result = run_gen(repo)
    assert result.returncode == 0
    reg = json.loads((repo / "registry.json").read_text())
    assert reg["schema_version"] == 2
    assert len(reg["skills"]) == 1
    s = reg["skills"][0]
    assert s["id"] == "test-author/example"
    assert "source" in s and "content_hash" in s["source"]
    assert "versions" in s and "0.1.0" in s["versions"]


def test_deterministic(tmp_path):
    repo = setup_test_repo(tmp_path)
    run_gen(repo)
    first = (repo / "registry.json").read_bytes()
    run_gen(repo)
    second = (repo / "registry.json").read_bytes()
    assert first == second


def test_check_mode_passes_on_synced(tmp_path):
    repo = setup_test_repo(tmp_path)
    run_gen(repo)
    result = run_gen(repo, "--check")
    assert result.returncode == 0


def test_check_mode_fails_on_drift(tmp_path):
    repo = setup_test_repo(tmp_path)
    run_gen(repo)
    # Tamper with registry.json
    reg_path = repo / "registry.json"
    data = json.loads(reg_path.read_text())
    data["generated_at"] = "1999-01-01T00:00:00Z"
    reg_path.write_text(json.dumps(data))
    result = run_gen(repo, "--check")
    assert result.returncode == 1
```

- [ ] **Step 2: Run, verify all fail (no script)**

```bash
pytest tests/test_generate_manifest.py -v
```

Expected: FAIL on all (script missing).

- [ ] **Step 3: Implement generate_manifest.py**

Create `scripts/generate_manifest.py`:

```python
"""generate_manifest.py — build registry.json from skills/ + yanks.json + git log."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).parent.parent


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}
    return yaml.safe_load(text[4:end])


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def compute_content_hash(skill_dir: Path) -> tuple[str, list[str]]:
    files = sorted(
        f.relative_to(skill_dir) for f in skill_dir.rglob("*") if f.is_file()
    )
    combined = b"\n".join(
        f"{str(rel).replace(chr(92), '/')}".encode() + b"\0" + sha256_file(skill_dir / rel).encode()
        for rel in files
    )
    return "sha256:" + hashlib.sha256(combined).hexdigest(), [str(rel).replace("\\", "/") for rel in files]


def get_git_tree_sha(repo: Path, skill_path: Path) -> str:
    rel = skill_path.relative_to(repo)
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%T", "--", str(rel)],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def get_skill_versions(repo: Path, skill_dir: Path) -> dict:
    """Walk git log for the skill's meta.json; record each version's tree SHA + release date."""
    meta_rel = (skill_dir / "meta.json").relative_to(repo)
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--format=%H %cI", "--", str(meta_rel)],
        capture_output=True, text=True
    )
    versions = {}
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        commit_sha, released = line.split(maxsplit=1)
        # Read meta.json at this commit to extract version
        show = subprocess.run(
            ["git", "-C", str(repo), "show", f"{commit_sha}:{meta_rel}"],
            capture_output=True, text=True
        )
        try:
            meta = json.loads(show.stdout)
        except json.JSONDecodeError:
            continue
        ver = meta.get("version")
        if not ver or ver in versions:
            continue
        tree_sha_result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{commit_sha}^{{tree}}"],
            capture_output=True, text=True
        )
        versions[ver] = {
            "sha": tree_sha_result.stdout.strip(),
            "released": released,
        }
    return versions


def get_commit_timestamp(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%cI", "HEAD"],
        capture_output=True, text=True
    )
    return result.stdout.strip() or "1970-01-01T00:00:00Z"


def get_provenance(repo: Path, skill_dir: Path) -> dict:
    rel = skill_dir.relative_to(repo)
    result = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%cI %s", "--", str(rel)],
        capture_output=True, text=True
    )
    line = result.stdout.strip()
    if not line:
        return {}
    merged_at, msg = line.split(maxsplit=1)
    pr_match = None
    import re
    m = re.search(r"#(\d+)", msg)
    if m:
        pr_match = int(m.group(1))
    return {"submitted_pr": pr_match, "merged_at": merged_at, "reviewed_by": "samuelgudi"}


def build_skill_entry(repo: Path, skill_dir: Path, status: str) -> dict:
    meta = json.loads((skill_dir / "meta.json").read_text(encoding="utf-8"))
    fm = parse_frontmatter(skill_dir / "SKILL.md")
    content_hash, files = compute_content_hash(skill_dir)
    has_scripts = (skill_dir / "scripts").is_dir()
    versions = get_skill_versions(repo, skill_dir) or {meta["version"]: {"sha": get_git_tree_sha(repo, skill_dir), "released": get_commit_timestamp(repo)}}
    return {
        "id": meta["id"],
        "name": fm.get("name", meta["id"].split("/")[-1]),
        "description": fm.get("description", ""),
        "version": meta["version"],
        "status": status,
        "author": meta["author"],
        "category": meta["category"],
        "tags": meta.get("tags", []),
        "platforms": meta.get("platforms", ["linux", "macos", "windows"]),
        "agent_compat": meta["agent_compat"],
        "requires": meta.get("requires", {"env_vars": [], "commands": []}),
        "has_scripts": has_scripts,
        "license": meta["license"],
        "install": meta["install"],
        "source": {
            "path": str(skill_dir.relative_to(repo)).replace("\\", "/"),
            "content_hash": content_hash,
            "files": files,
        },
        "versions": versions,
        "provenance": get_provenance(repo, skill_dir),
        "composes": meta.get("composes", []),
        "extends": meta.get("extends"),
        "supersedes": meta.get("supersedes", []),
        "superseded_by": meta.get("superseded_by"),
    }


def load_yanks(repo: Path) -> dict:
    yanks_path = repo / "yanks.json"
    if not yanks_path.exists():
        return {}
    data = json.loads(yanks_path.read_text(encoding="utf-8"))
    out = {}
    for y in data.get("yanks", []):
        out.setdefault(y["id"], {})[y["version"]] = {"yanked": True, "yank_reason": y["reason"]}
    return out


def apply_yanks(skills: list[dict], yanks: dict) -> None:
    for s in skills:
        for ver, info in yanks.get(s["id"], {}).items():
            if ver in s["versions"]:
                s["versions"][ver].update(info)


def build_manifest(repo: Path) -> dict:
    skills = []
    for status, parent in [("active", repo / "skills"), ("deprecated", repo / "archive")]:
        if not parent.exists():
            continue
        for author in sorted(parent.iterdir()):
            if not author.is_dir():
                continue
            for slug in sorted(author.iterdir()):
                if slug.is_dir() and (slug / "meta.json").exists():
                    skills.append(build_skill_entry(repo, slug, status))
    skills.sort(key=lambda s: s["id"])
    apply_yanks(skills, load_yanks(repo))
    return {
        "schema_version": 2,
        "generated_at": get_commit_timestamp(repo),
        "skills": skills,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args(argv)

    repo = Path.cwd()
    manifest = build_manifest(repo)
    serialized = json.dumps(manifest, indent=2, sort_keys=False) + "\n"

    reg_path = repo / "registry.json"
    if args.check:
        current = reg_path.read_text(encoding="utf-8") if reg_path.exists() else ""
        if current != serialized:
            print("registry.json out of sync. Run generate_manifest.py to regenerate.")
            return 1
        return 0
    reg_path.write_text(serialized, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest tests/test_generate_manifest.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_manifest.py tests/test_generate_manifest.py
git commit -m "feat: generate_manifest.py builds registry.json from skills + yanks + git log; deterministic"
```

---

# Phase 3 — Adapters

## Task 11: adapters/_base.py — Adapter ABC + shared mechanics

**Files:**
- Create: `adapters/__init__.py` (empty)
- Create: `adapters/_base.py`
- Create: `tests/test_adapter_base.py`

- [ ] **Step 1: Write test for marker write/read**

Create `tests/test_adapter_base.py`:

```python
import json
from pathlib import Path

from adapters._base import write_marker, read_marker, MARKER_FILENAME


def test_write_and_read_marker(tmp_path):
    target = tmp_path / "skill"
    target.mkdir()
    write_marker(target, skill_id="a/b", version="0.1.0", content_hash="sha256:abc", source_url="x", tree_sha="def")
    m = read_marker(target)
    assert m["id"] == "a/b"
    assert m["version"] == "0.1.0"
    assert m["registry_content_hash"] == "sha256:abc"
    assert (target / MARKER_FILENAME).exists()
```

- [ ] **Step 2: Run, verify fail (module missing)**

```bash
pytest tests/test_adapter_base.py -v
```

Expected: FAIL with ImportError.

- [ ] **Step 3: Implement adapters/_base.py**

Create `adapters/__init__.py` empty.

Create `adapters/_base.py`:

```python
"""Adapter ABC + shared install/uninstall mechanics."""
from __future__ import annotations

import abc
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


MARKER_FILENAME = ".agent-skills-marker.json"


@dataclass
class InstallResult:
    success: bool
    target: Path
    files_written: list[str]
    error: str | None = None


@dataclass
class UninstallResult:
    success: bool
    target: Path
    error: str | None = None


@dataclass
class Installed:
    id: str
    version: str
    target: Path


@dataclass
class VerifyResult:
    status: str  # "clean" | "drift" | "marker_outdated" | "yanked" | "tampered" | "deprecated"
    message: str


def write_marker(target: Path, *, skill_id: str, version: str, content_hash: str, source_url: str, tree_sha: str) -> None:
    marker = {
        "id": skill_id,
        "version": version,
        "installed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "installed_by": "agent-skills 0.1.0",
        "registry_content_hash": content_hash,
        "source_url": source_url,
        "tree_sha": tree_sha,
    }
    (target / MARKER_FILENAME).write_text(json.dumps(marker, indent=2), encoding="utf-8")


def read_marker(target: Path) -> dict | None:
    m = target / MARKER_FILENAME
    if not m.exists():
        return None
    return json.loads(m.read_text(encoding="utf-8"))


def compute_dir_content_hash(directory: Path) -> str:
    files = sorted(f for f in directory.rglob("*") if f.is_file() and f.name != MARKER_FILENAME)
    h = hashlib.sha256()
    for f in files:
        rel = str(f.relative_to(directory)).replace("\\", "/")
        h.update(rel.encode())
        h.update(b"\0")
        h.update(hashlib.sha256(f.read_bytes()).hexdigest().encode())
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


def atomic_install(src_dir: Path, target: Path) -> list[str]:
    """Stage src into temp; rename into target; return list of written files (relative)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        staging = Path(tmp) / "staged"
        shutil.copytree(src_dir, staging)
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(staging), str(target))
    return sorted(str(f.relative_to(target)).replace("\\", "/") for f in target.rglob("*") if f.is_file())


class Adapter(abc.ABC):
    name: str

    @abc.abstractmethod
    def detect(self) -> bool: ...

    @abc.abstractmethod
    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path: ...

    @abc.abstractmethod
    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult: ...

    @abc.abstractmethod
    def uninstall(self, skill_id: str) -> UninstallResult: ...

    @abc.abstractmethod
    def list_installed(self) -> list[Installed]: ...

    @abc.abstractmethod
    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult: ...
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_adapter_base.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/__init__.py adapters/_base.py tests/test_adapter_base.py
git commit -m "feat: adapter ABC with marker + atomic install + content_hash"
```

---

## Task 12: adapters/claude_code.py

**Files:**
- Create: `adapters/claude_code.py`
- Create: `tests/test_adapter_claude_code.py`

- [ ] **Step 1: Write tests for Claude Code adapter (install, uninstall, verify-clean, verify-drift, conflict-refuse)**

Create `tests/test_adapter_claude_code.py`:

```python
from pathlib import Path
import json
import shutil

import pytest

from adapters.claude_code import ClaudeCodeAdapter
from adapters._base import compute_dir_content_hash


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def src_skill(tmp_path):
    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n# Example\n")
    (src / "meta.json").write_text(json.dumps({"id": "test-author/example", "version": "0.1.0"}))
    return src


def test_detect_false_when_no_claude(home):
    assert ClaudeCodeAdapter().detect() is False


def test_detect_true_when_claude_dir_exists(home):
    (home / ".claude").mkdir()
    assert ClaudeCodeAdapter().detect() is True


def test_install_writes_files_and_marker(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    result = adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    assert result.success
    target = home / ".claude/skills/test-author-example"
    assert (target / "SKILL.md").exists()
    assert (target / ".agent-skills-marker.json").exists()


def test_uninstall_removes_directory(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    target = home / ".claude/skills/test-author-example"
    assert target.exists()
    result = adapter.uninstall("test-author/example")
    assert result.success
    assert not target.exists()


def test_uninstall_refuses_without_marker(home, src_skill):
    (home / ".claude").mkdir()
    target = home / ".claude/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("hand-authored")
    adapter = ClaudeCodeAdapter()
    result = adapter.uninstall("test-author/example")
    assert not result.success
    assert target.exists()


def test_verify_clean(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    result = adapter.verify("test-author/example", registry_hash=h, yanked=False, yank_reason=None)
    assert result.status == "clean"


def test_verify_drift_when_file_edited(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    target = home / ".claude/skills/test-author-example"
    (target / "SKILL.md").write_text("tampered")
    result = adapter.verify("test-author/example", registry_hash=h, yanked=False, yank_reason=None)
    assert result.status == "drift"


def test_verify_yanked_alert(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    result = adapter.verify("test-author/example", registry_hash=h, yanked=True, yank_reason="compromised dep")
    assert result.status == "yanked"
    assert "compromised dep" in result.message
```

- [ ] **Step 2: Run, verify all fail (adapter doesn't exist)**

```bash
pytest tests/test_adapter_claude_code.py -v
```

Expected: FAIL with ImportError.

- [ ] **Step 3: Implement adapters/claude_code.py**

Create `adapters/claude_code.py`:

```python
"""Claude Code adapter."""
from __future__ import annotations

import shutil
from pathlib import Path

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install, compute_dir_content_hash,
    MARKER_FILENAME,
)


class ClaudeCodeAdapter(Adapter):
    name = "claude-code"

    def detect(self) -> bool:
        return (Path.home() / ".claude").exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        author, slug = skill_id.split("/", 1)
        flat = f"{author}-{slug}"
        if scope == "project":
            return Path.cwd() / ".claude/skills" / flat
        return Path.home() / ".claude/skills" / flat

    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult:
        category = meta.get("category", "meta")
        scope = opts.get("scope", "user")
        target = self.target_dir(skill_id, category, scope=scope)

        if target.exists() and read_marker(target) is None:
            return InstallResult(success=False, target=target, files_written=[],
                                 error=f"target {target} exists without marker — refuse to overwrite user-authored skill")
        try:
            files_written = atomic_install(src_dir, target)
            write_marker(
                target,
                skill_id=skill_id, version=version,
                content_hash=opts.get("registry_hash", ""),
                source_url=opts.get("source_url", ""),
                tree_sha=opts.get("tree_sha", ""),
            )
            return InstallResult(success=True, target=target, files_written=files_written)
        except Exception as e:
            if target.exists():
                shutil.rmtree(target)
            return InstallResult(success=False, target=target, files_written=[], error=str(e))

    def uninstall(self, skill_id: str) -> UninstallResult:
        author, slug = skill_id.split("/", 1)
        target = Path.home() / ".claude/skills" / f"{author}-{slug}"
        if not target.exists():
            return UninstallResult(success=False, target=target, error="not installed")
        if read_marker(target) is None:
            return UninstallResult(success=False, target=target, error="no marker — refusing to remove user-authored skill")
        shutil.rmtree(target)
        return UninstallResult(success=True, target=target)

    def list_installed(self) -> list[Installed]:
        skills_dir = Path.home() / ".claude/skills"
        if not skills_dir.exists():
            return []
        result = []
        for d in skills_dir.iterdir():
            marker = read_marker(d) if d.is_dir() else None
            if marker:
                result.append(Installed(id=marker["id"], version=marker["version"], target=d))
        return result

    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult:
        author, slug = skill_id.split("/", 1)
        target = Path.home() / ".claude/skills" / f"{author}-{slug}"
        if not target.exists():
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in claude-code")
        marker = read_marker(target)
        if marker is None:
            return VerifyResult(status="no_marker", message="no marker — skill not managed by agent-skills")
        actual_hash = compute_dir_content_hash(target)
        if yanked:
            return VerifyResult(status="yanked", message=f"version {marker['version']} YANKED: {yank_reason}. Uninstall recommended.")
        if actual_hash != registry_hash:
            return VerifyResult(status="drift", message=f"installed files differ from registry source hash for {skill_id}@{marker['version']}")
        return VerifyResult(status="clean", message=f"{skill_id}@{marker['version']} matches registry")
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest tests/test_adapter_claude_code.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add adapters/claude_code.py tests/test_adapter_claude_code.py
git commit -m "feat: Claude Code adapter (install/uninstall/verify/list); registry-anchored verify; yanked alert"
```

---

## Task 13: adapters/hermes.py — with frontmatter synthesis

**Files:**
- Create: `adapters/hermes.py`
- Create: `tests/test_adapter_hermes.py`

- [ ] **Step 1: Write tests covering category-based target_dir + frontmatter synthesis**

Create `tests/test_adapter_hermes.py`:

```python
import json
from pathlib import Path
import re

import pytest

from adapters.hermes import HermesAdapter
from adapters._base import compute_dir_content_hash


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def src_skill(tmp_path):
    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: example\ndescription: test skill\n---\n\n# Example\n\nBody text.\n")
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.3.0",
        "author": {"name": "Test", "github_login": "test", "github_id": 1},
        "category": "ops",
        "license": "MIT",
        "platforms": ["linux"],
        "tags": ["test", "fixture"],
        "requires": {"env_vars": ["MY_VAR"], "commands": ["git"]},
        "related_skills": ["test-author/other"],
    }))
    return src


def test_target_dir_uses_category(home):
    a = HermesAdapter()
    t = a.target_dir("test-author/example", category="ops")
    assert str(t).endswith("/.hermes/skills/ops/example") or str(t).endswith("\\.hermes\\skills\\ops\\example")


def test_install_synthesizes_full_frontmatter(home, src_skill):
    (home / ".hermes").mkdir()
    a = HermesAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    result = a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    assert result.success
    target = home / ".hermes/skills/ops/example"
    installed_md = (target / "SKILL.md").read_text()

    # Synthesized fields appear in frontmatter
    assert "version: 0.3.0" in installed_md
    assert "license: MIT" in installed_md
    assert "platforms" in installed_md and "linux" in installed_md
    assert "prerequisites" in installed_md and "MY_VAR" in installed_md and "git" in installed_md
    assert "metadata" in installed_md and "hermes" in installed_md and "test" in installed_md
    # Body preserved
    assert "# Example" in installed_md
    assert "Body text." in installed_md
```

- [ ] **Step 2: Run, verify fail**

```bash
pytest tests/test_adapter_hermes.py -v
```

Expected: FAIL with ImportError.

- [ ] **Step 3: Implement adapters/hermes.py**

Create `adapters/hermes.py`:

```python
"""Hermes adapter — category-based target, frontmatter synthesis."""
from __future__ import annotations

import shutil
import yaml
from pathlib import Path

from adapters._base import (
    Adapter, InstallResult, UninstallResult, Installed, VerifyResult,
    write_marker, read_marker, atomic_install, compute_dir_content_hash,
)


def synthesize_hermes_frontmatter(meta: dict, fm_name: str, fm_description: str) -> dict:
    fm = {
        "name": fm_name,
        "description": fm_description,
        "version": meta["version"],
        "author": f"{meta['author']['name']} ({meta['author']['github_login']})",
        "license": meta["license"],
    }
    if meta.get("platforms"):
        fm["platforms"] = meta["platforms"]
    if meta.get("requires"):
        fm["prerequisites"] = {
            "env_vars": meta["requires"].get("env_vars", []),
            "commands": meta["requires"].get("commands", []),
        }
    hermes_meta = {}
    if meta.get("tags"):
        hermes_meta["tags"] = meta["tags"]
    if meta.get("related_skills"):
        hermes_meta["related_skills"] = meta["related_skills"]
    if hermes_meta:
        fm["metadata"] = {"hermes": hermes_meta}
    return fm


def rewrite_skill_md(path: Path, new_fm: dict) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        body = text
    else:
        end = text.find("\n---\n", 4)
        body = text[end + 5:]
    new_text = "---\n" + yaml.safe_dump(new_fm, sort_keys=False) + "---\n" + body
    path.write_text(new_text, encoding="utf-8")


class HermesAdapter(Adapter):
    name = "hermes"

    def detect(self) -> bool:
        return (Path.home() / ".hermes").exists()

    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path:
        _, slug = skill_id.split("/", 1)
        return Path.home() / ".hermes/skills" / category / slug

    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult:
        target = self.target_dir(skill_id, meta["category"])
        if target.exists() and read_marker(target) is None:
            return InstallResult(success=False, target=target, files_written=[],
                                 error=f"target {target} exists without marker — refuse to overwrite")
        try:
            files_written = atomic_install(src_dir, target)
            # Synthesize frontmatter in installed SKILL.md
            skill_md = target / "SKILL.md"
            # Parse existing frontmatter
            import yaml as _yaml
            text = skill_md.read_text(encoding="utf-8")
            end = text.find("\n---\n", 4)
            existing_fm = _yaml.safe_load(text[4:end])
            new_fm = synthesize_hermes_frontmatter(meta, existing_fm["name"], existing_fm["description"])
            rewrite_skill_md(skill_md, new_fm)
            write_marker(
                target,
                skill_id=skill_id, version=version,
                content_hash=opts.get("registry_hash", ""),
                source_url=opts.get("source_url", ""),
                tree_sha=opts.get("tree_sha", ""),
            )
            return InstallResult(success=True, target=target, files_written=files_written)
        except Exception as e:
            if target.exists():
                shutil.rmtree(target)
            return InstallResult(success=False, target=target, files_written=[], error=str(e))

    def uninstall(self, skill_id: str) -> UninstallResult:
        # Walk all categories to find the slug
        skills_dir = Path.home() / ".hermes/skills"
        if not skills_dir.exists():
            return UninstallResult(success=False, target=skills_dir, error="hermes skills dir not present")
        _, slug = skill_id.split("/", 1)
        for cat in skills_dir.iterdir():
            t = cat / slug
            if t.exists() and read_marker(t):
                m = read_marker(t)
                if m["id"] == skill_id:
                    shutil.rmtree(t)
                    return UninstallResult(success=True, target=t)
        return UninstallResult(success=False, target=skills_dir, error="not found")

    def list_installed(self) -> list[Installed]:
        skills_dir = Path.home() / ".hermes/skills"
        if not skills_dir.exists():
            return []
        result = []
        for cat in skills_dir.iterdir():
            if not cat.is_dir():
                continue
            for d in cat.iterdir():
                m = read_marker(d) if d.is_dir() else None
                if m:
                    result.append(Installed(id=m["id"], version=m["version"], target=d))
        return result

    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult:
        skills_dir = Path.home() / ".hermes/skills"
        _, slug = skill_id.split("/", 1)
        target = None
        for cat in skills_dir.iterdir() if skills_dir.exists() else []:
            t = cat / slug
            if t.exists() and read_marker(t) and read_marker(t)["id"] == skill_id:
                target = t
                break
        if target is None:
            return VerifyResult(status="not_installed", message=f"{skill_id} not installed in hermes")
        marker = read_marker(target)
        # NOTE: Hermes verify cannot directly compare hashes — the installed SKILL.md has synthesized frontmatter
        # that differs from the registry's minimal frontmatter. For v0: verify the marker's stored hash matches
        # registry hash; mark a separate yanked-aware status.
        if yanked:
            return VerifyResult(status="yanked", message=f"version {marker['version']} YANKED: {yank_reason}. Uninstall recommended.")
        if marker.get("registry_content_hash") != registry_hash:
            return VerifyResult(status="marker_outdated", message=f"marker hash differs from registry hash; reinstall may be needed")
        return VerifyResult(status="clean", message=f"{skill_id}@{marker['version']} marker matches registry (Hermes frontmatter is host-synthesized so hash differs from raw registry tree)")
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest tests/test_adapter_hermes.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add adapters/hermes.py tests/test_adapter_hermes.py
git commit -m "feat: Hermes adapter (category-based target, frontmatter synthesis, marker-based verify)"
```

---

# Phase 4 — Top-level CLI

> NOTE: Phases 4-7 follow the same TDD pattern as Phases 1-3. Each verb in the CLI is its own task with: write test → run/fail → implement → run/pass → commit. The implementations below are condensed structurally — every test+code block remains complete, but task narrative is tighter. Engineers should expand each step to the same depth as Tasks 1-13.

## Task 14: CLI scaffold — `agent_skills/cli.py`, `detect.py`, `cache.py`

**Files:**
- Create: `agent_skills/cli.py`
- Create: `agent_skills/detect.py`
- Create: `agent_skills/cache.py`
- Create: `tests/test_cli_scaffold.py`

- [ ] **Step 1: Write test for `agent-skills --help`**

Create `tests/test_cli_scaffold.py`:

```python
import subprocess
import sys

def test_help_lists_verbs():
    result = subprocess.run([sys.executable, "-m", "agent_skills", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    for verb in ("search", "show", "install", "uninstall", "verify", "list", "update", "init", "submit", "issue", "deprecate", "yank"):
        assert verb in result.stdout, f"verb '{verb}' missing from help"
```

- [ ] **Step 2: Implement detect.py + cache.py + cli.py**

Create `agent_skills/detect.py`:

```python
"""Host auto-detection."""
import os
from pathlib import Path

from adapters.claude_code import ClaudeCodeAdapter
from adapters.hermes import HermesAdapter


ADAPTERS = {"claude-code": ClaudeCodeAdapter, "hermes": HermesAdapter}


def detect_host(*, override: str | None = None) -> str:
    if override:
        if override not in ADAPTERS:
            raise SystemExit(f"unknown agent: {override}; expected one of {list(ADAPTERS)}")
        return override
    found = [name for name, cls in ADAPTERS.items() if cls().detect()]
    if not found:
        raise SystemExit("No agent host detected. Pass --agent or install Claude Code / Hermes.")
    if len(found) == 1:
        return found[0]
    pref = os.environ.get("AGENT_SKILLS_DEFAULT_AGENT")
    if pref and pref in found:
        return pref
    raise SystemExit(f"Multiple hosts detected ({found}). Set AGENT_SKILLS_DEFAULT_AGENT or pass --agent.")


def get_adapter(name: str):
    return ADAPTERS[name]()
```

Create `agent_skills/cache.py`:

```python
"""~/.cache/agent-skills/ helpers."""
import json
from pathlib import Path


def cache_dir() -> Path:
    d = Path.home() / ".cache/agent-skills"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_registry() -> dict | None:
    p = cache_dir() / "registry.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
```

Create `agent_skills/cli.py`:

```python
"""agent-skills CLI verb dispatch."""
import argparse
import sys


VERBS = ["search", "show", "install", "uninstall", "verify", "list", "update", "init", "submit", "issue", "deprecate", "yank"]


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent-skills", description="Agent-agnostic skill registry.")
    sub = p.add_subparsers(dest="verb", required=True)
    for v in VERBS:
        sp = sub.add_parser(v, help=f"{v} verb")
        sp.add_argument("--agent", default=None)
        sp.add_argument("--json", action="store_true")
        sp.add_argument("--yes", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    p = make_parser()
    args = p.parse_args(argv)
    if args.verb == "search":
        from agent_skills.verbs.search import run; return run(args)
    if args.verb == "show":
        from agent_skills.verbs.show import run; return run(args)
    # ... other verbs dispatched similarly; each verb implemented in agent_skills/verbs/<name>.py
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Create `agent_skills/verbs/__init__.py` (empty).

- [ ] **Step 3: Run, verify help test passes**

```bash
pytest tests/test_cli_scaffold.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add agent_skills/ tests/test_cli_scaffold.py
git commit -m "feat: CLI scaffold (cli.py + detect.py + cache.py); 12 verbs registered"
```

---

## Task 15: search verb + match.py

**Files:**
- Create: `clients/skill-discovery/match.py`
- Create: `agent_skills/verbs/search.py`
- Create: `tests/test_match.py`

- [ ] **Step 1: Write tests for match.py ranking**

```python
# tests/test_match.py
from clients.skill_discovery.match import score, rank

REGISTRY = {
    "schema_version": 2,
    "skills": [
        {"id": "a/spotify-search", "name": "spotify-search",
         "description": "Search Spotify by track or artist.",
         "tags": ["spotify", "music"], "version": "0.1.0",
         "agent_compat": ["claude-code"], "category": "media",
         "status": "active", "platforms": ["linux"], "has_scripts": True},
        {"id": "a/lastfm", "name": "lastfm",
         "description": "Last.fm music lookup.",
         "tags": ["lastfm", "music"], "version": "0.2.0",
         "agent_compat": ["claude-code"], "category": "media",
         "status": "active", "platforms": ["linux"], "has_scripts": False},
    ],
}


def test_exact_match_scores_higher():
    candidates = rank("spotify", REGISTRY, agent="claude-code", limit=2)
    assert candidates[0]["id"] == "a/spotify-search"


def test_filter_agent_drops_incompatible():
    skills_with_other = dict(REGISTRY)
    skills_with_other["skills"] = REGISTRY["skills"] + [{**REGISTRY["skills"][0], "id": "z/hermes-only", "agent_compat": ["hermes"]}]
    candidates = rank("spotify", skills_with_other, agent="claude-code", limit=10)
    assert all("hermes-only" not in c["id"] for c in candidates)


def test_deprecated_excluded_by_default():
    reg = dict(REGISTRY)
    reg["skills"] = REGISTRY["skills"] + [{**REGISTRY["skills"][0], "id": "a/old", "status": "deprecated"}]
    candidates = rank("spotify", reg, agent="claude-code", limit=10)
    assert all("/old" not in c["id"] for c in candidates)


def test_regex_chars_in_query_dont_crash():
    candidates = rank("spotify[*]", REGISTRY, agent="claude-code", limit=2)
    assert isinstance(candidates, list)
```

(Continue with parametrized tests covering filters by category, tag, platform; tie-breaking; yanked-version exclusion.)

- [ ] **Step 2: Implement match.py**

Create `clients/skill_discovery/__init__.py` (empty).

Create `clients/skill_discovery/match.py`:

```python
"""Keyword + filter scoring."""
from __future__ import annotations

import math
import re
from collections import Counter


STOPWORDS = {"a", "an", "the", "and", "or", "but", "with", "for", "from", "of", "to", "in", "on"}
TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall((text or "").lower()) if t not in STOPWORDS]


def jaccard_idf(query_tokens: set[str], target_tokens: list[str], idf: dict[str, float]) -> float:
    target_set = set(target_tokens)
    if not query_tokens or not target_set:
        return 0.0
    intersection_score = sum(idf.get(t, 1.0) for t in query_tokens & target_set)
    union_score = sum(idf.get(t, 1.0) for t in query_tokens | target_set) or 1.0
    return intersection_score / union_score


def build_idf(skills: list[dict]) -> dict[str, float]:
    N = max(1, len(skills))
    df = Counter()
    for s in skills:
        terms = set(tokenize(s["name"]) + tokenize(s["description"]) + sum((tokenize(t) for t in s.get("tags", [])), []))
        for term in terms:
            df[term] += 1
    return {term: math.log(1 + N / max(1, freq)) for term, freq in df.items()}


def filter_yanked_latest(s: dict) -> bool:
    versions = s.get("versions", {})
    if not versions:
        return True
    # Skip if all versions yanked
    return any(not v.get("yanked", False) for v in versions.values())


def score(query: str, skill: dict, idf: dict[str, float]) -> float:
    q = set(tokenize(query))
    n = jaccard_idf(q, tokenize(skill["name"]), idf)
    d = jaccard_idf(q, tokenize(skill["description"]), idf)
    t = jaccard_idf(q, [tok for tag in skill.get("tags", []) for tok in tokenize(tag)], idf)
    # Length penalty for very long descriptions (Gemini m1 anti-stuffing)
    desc_len = len(skill["description"])
    length_factor = 1.0 if desc_len <= 500 else max(0.5, 500 / desc_len)
    return (0.45 * n + 0.40 * d + 0.15 * t) * length_factor


def rank(query: str, registry: dict, *, agent: str | None = None, category: str | None = None,
         tag: str | None = None, platform: str | None = None, limit: int = 5,
         include_archived: bool = False) -> list[dict]:
    skills = registry["skills"]
    candidates = []
    for s in skills:
        if s.get("status") == "deprecated" and not include_archived:
            continue
        if not filter_yanked_latest(s):
            continue
        if agent and agent not in s.get("agent_compat", []):
            continue
        if category and s.get("category") != category:
            continue
        if tag and tag not in s.get("tags", []):
            continue
        if platform and platform not in s.get("platforms", []):
            continue
        candidates.append(s)
    idf = build_idf(skills)
    scored = sorted(candidates, key=lambda s: (
        -score(query, s, idf),
        # tiebreakers
        -tuple(int(x) for x in (s["version"] + ".0.0.0").split(".")[:3]),  # higher version first
        s["id"],
    ))
    out = []
    for s in scored[:limit]:
        out.append({**s, "score": round(score(query, s, idf), 3)})
    return out
```

- [ ] **Step 3: Implement search verb**

Create `agent_skills/verbs/search.py`:

```python
"""search verb."""
import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import detect_host
from clients.skill_discovery.match import rank


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("Run `agent-skills update` first.", file=sys.stderr)
        return 1
    agent = detect_host(override=args.agent)
    candidates = rank(args.query if hasattr(args, "query") else " ".join(args.terms),
                      registry, agent=agent, limit=getattr(args, "limit", 5))
    if args.json:
        print(json.dumps({"candidates": candidates}, indent=2))
        return 0
    if not candidates:
        print("No skills match. Try `agent-skills list-categories` for ideas.")
        return 0
    for i, c in enumerate(candidates, 1):
        star = " ★" if i == 1 else "  "
        print(f"  {star} {i}  {c['id']:40s} v{c['version']}")
        print(f"       {c['description']}")
        tags = " ".join(f"#{t}" for t in c.get("tags", []))
        req = c.get("requires", {})
        req_part = ""
        if req.get("env_vars"):
            req_part = " · requires " + " + ".join(req["env_vars"])
        print(f"       {tags}{req_part}")
        print()
    return 0
```

Update `agent_skills/cli.py` to wire the `search` verb's positional `terms`:

```python
sp = sub.add_parser("search", help="Find skills")
sp.add_argument("terms", nargs="+")
sp.add_argument("--agent")
sp.add_argument("--limit", type=int, default=5)
sp.add_argument("--json", action="store_true")
```

- [ ] **Step 4: Run match tests**

```bash
pytest tests/test_match.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clients/skill_discovery/ agent_skills/verbs/search.py agent_skills/cli.py tests/test_match.py
git commit -m "feat: match.py keyword+filter scoring; search verb wired"
```

---

## Tasks 16-21 — Remaining CLI verbs

Each verb follows the same TDD pattern. Implementations summarized.

### Task 16: `show` verb

- Test: `agent-skills show samuelgudi/example` prints id, version, license, author, category, tags, platforms, agents, files, requires, install status.
- Implementation: `agent_skills/verbs/show.py` — loads registry, finds skill by id, queries detected adapter for `list_installed()` to determine install status, formats output.
- Commit message: `feat: show verb`

### Task 17: `install` verb

- Test: `agent-skills install spotify-search` resolves @version via versions map, refuses yanked versions, calls adapter.install, writes marker.
- Implementation: `agent_skills/verbs/install.py` — version resolution (latest non-yanked default, or pinned), fetch git tree via `git fetch + git read-tree`, hash verification, adapter dispatch.
- Edge cases tested: yanked version refusal (no override), missing version error, conflicting target without marker error.
- Commit message: `feat: install verb with version pinning + yanked refusal`

### Task 18: `uninstall` verb

- Test: removes installed skill; refuses on drift unless `--force`; refuses without marker.
- Implementation: `agent_skills/verbs/uninstall.py` — calls adapter.uninstall after confirmation.
- Commit message: `feat: uninstall verb with drift check`

### Task 19: `verify` verb

- Test: clean / drift / yanked / marker_outdated paths.
- Implementation: `agent_skills/verbs/verify.py` — fetches registry hash + yanked flag, calls adapter.verify, prints status.
- Commit message: `feat: verify verb (registry-anchored hash + yanked alert)`

### Task 20: `list` verb

- Test: lists installed skills per detected agent; `--agent` overrides; output includes id, version, target dir.
- Implementation: `agent_skills/verbs/list.py` — adapter.list_installed.
- Commit message: `feat: list verb (--agent supported)`

### Task 21: `update` verb

- Test: fetches registry.json + yanks.json; verifies sha256 if .sig present (warning if absent); rolls back if fetched generated_at older than cached.
- Implementation: `clients/skill_discovery/update.py` + `agent_skills/verbs/update.py`.
- Commit message: `feat: update verb with rollback-attack guard`

---

# Phase 5 — Contribution Flow

## Task 22: `init` verb (W1 scaffolding)

**Files:**
- Create: `agent_skills/verbs/init.py`
- Create: `tests/test_init_verb.py`

- [ ] **Step 1: Write test**

```python
def test_init_scaffolds_meta_from_skill_md(tmp_path, fake_gh, monkeypatch):
    skill = tmp_path / "homelab-docs"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: homelab-docs\ndescription: example\n---\n# H\n")
    # Provide pre-set responses via stdin
    inputs = "\n".join(["", "", "", "", "3", "homelab,docs", "linux,windows", "1", "git,ssh"])
    monkeypatch.setattr("sys.stdin", io.StringIO(inputs))
    from agent_skills.verbs.init import run
    class Args: target = str(skill); yes = False
    rc = run(Args())
    assert rc == 0
    meta = json.loads((skill / "meta.json").read_text())
    assert meta["id"] == "test-author/homelab-docs"
    assert meta["category"] == "ops"
    assert "git" in meta["requires"]["commands"]
    assert "ssh" in meta["requires"]["commands"]
```

- [ ] **Step 2-4: Implement init.py**

Detects SKILL.md (lowercase rename + notice if needed), parses frontmatter, calls `gh auth status` + `gh api users/<login>` to get id, prompts for category (numbered), tags, platforms (CSV), agent_compat (multi-select), license (default MIT), greps SKILL.md body for ALL_CAPS env vars + shell command tokens (`ssh`, `git`, `curl`, etc.) and prompts for confirmation, writes meta.json with full schema (including reserved fields initialized empty).

- [ ] **Step 5: Commit**

```bash
git add agent_skills/verbs/init.py tests/test_init_verb.py
git commit -m "feat: init verb scaffolds meta.json interactively from SKILL.md (W1)"
```

## Task 23: `sanitize.py`

**Files:**
- Create: `clients/skill_contribution/sanitize.py`
- Create: `tests/test_sanitize.py`

Test cases: detection of each rule (home path, GitHub PAT, OpenAI key shape, Anthropic key shape, AWS key, LAN IP, prompt injection in SKILL.md body); user accepts/skips/cancels; SANITIZATION.diff generated post-completion.

Implementation: regex-based detection per `sanitize_rules.py` (data file), interactive prompt loop, applies replacements to a sanitized-copy directory.

Commit: `feat: sanitize.py with interactive per-detection prompts; SKILL.md body prompt-injection scan (M6)`

## Task 24: `diff.py`

Generates SANITIZATION.diff: unified-diff between pre-sanitization snapshot and post-sanitization output. Tests: produces valid diff format; only contains files that changed.

Commit: `feat: diff.py generates SANITIZATION.diff post-sanitization (m12)`

## Task 25: `submit.py` — 5-step flow

**Files:**
- Create: `clients/skill_contribution/submit.py`
- Create: `agent_skills/verbs/submit.py`
- Create: `tests/test_submit.py`

Tests use `fake_gh` fixture. Cover: meta.json missing → offers init; validate.py invocation; sanitize.py invocation; security_scan.py invocation; REVIEW.md template population + user edit; gh pr create call recorded in fake-gh log.

Implementation orchestrates: Step 0 (filename + meta.json check), Step 1 (validate), Step 2 (sanitize), Step 3 (security_scan), Step 4 (REVIEW.md template + edit), Step 5 (git branch + commit + gh pr create).

Commit: `feat: submit verb runs the 5-step contribution pipeline; fake-gh test fixture`

## Task 26: `issue` verb

Interactive wizard: type (bug/feature/docs/security), title, context, proposed change, will-implement-myself. Opens GitHub issue via `gh issue create`.

Commit: `feat: issue verb (Path B contribution)`

## Task 27: `deprecate` verb

Sets meta.json `status: deprecated` + `superseded_by`; moves dir `skills/` → `archive/`; commits + opens PR.

Commit: `feat: deprecate verb (soft obsolescence)`

## Task 28: `yank` verb (Gemini M3)

Appends entry to `yanks.json`; opens PR titled `Yank <id>@<version>`. Asserts target version exists in versions map; reason is non-empty.

Test: `test_yank.py` — yank PR opened; on merge (test simulates), `versions[ver].yanked = true`; subsequent `install <id>@<yanked-ver>` hard-refuses (no `--allow-yanked` flag accepted).

Commit: `feat: yank verb (hard-block compromised versions; no override; M3)`

---

# Phase 6 — CI

## Task 29: `.github/workflows/ci.yml`

**Files:**
- Create: `.github/workflows/ci.yml`

Implements the matrix from spec § 16 + contribution-PR-only checks (SANITIZATION.diff consistency, REVIEW.md completeness, GitHub-ID verification via `gh api`).

Commit: `ci: add main CI workflow (matrix + contribution-PR checks)`

## Task 30: `.github/workflows/on-merge.yml`

Moves submitted/pr-NN/ → skills/ or archive/; runs generate_manifest.py; commits + tags release.

Commit: `ci: add on-merge workflow (manifest regen + auto-tag)`

---

# Phase 7 — Hardening

## Task 31: Seed skills

Create 2 canonical example skills under `skills/samuelgudi/`:
- `agent-skills-discovery` (the discovery client itself as a skill)
- `agent-skills-contribution` (the contribution client as a skill)

Run `generate_manifest.py` to refresh registry.json with both entries. Commit.

Commit: `feat: seed skills (discovery + contribution clients published as registry entries)`

## Task 32: README polish

Expand README.md from the placeholder to a full project README: badges (CI status), one-paragraph pitch, install instructions (`pipx install agent-skills`), quickstart (3 commands), link to spec + CONTRIBUTING + SECURITY, license.

Commit: `docs: README polish for v0 ship`

## Task 33: CONTRIBUTING.md and SECURITY.md polish

Final pass on CONTRIBUTING.md (skill-description guideline, slug naming, REVIEW.md template walkthrough). SECURITY.md (yank procedure, reporting policy, threat model).

Commit: `docs: SECURITY.md + CONTRIBUTING.md final hardening pass`

---

# Self-Review

After completing all 33 tasks:

1. **Spec coverage**: walk through spec § 4 (locked decisions) — every decision implemented? Walk § 5 (repo layout) — every file present? Walk §§ 7-15 (component specs) — every behavior covered by a task + test?
2. **Schema-version migration**: verify `scripts/migrate_v1_to_v2.py` exists for v3 schema bump (note: spec mentions this; if not in task list, add a Task 7.5).
3. **Test coverage**: run `pytest tests/ --cov=. --cov-report=term`; aim for >85% on validate/security_scan/generate_manifest, >75% on adapters/CLI verbs.
4. **CI green on a clean clone**: `git clone` to a fresh location, `pip install -e .[dev]`, `pytest tests/ -v` should all green.

---

# Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-agent-skills-hub-v0.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task. Tasks 1-7 (Foundation) and Tasks 8-10 (Registry Tooling) can run sequentially. Tasks 11-13 (Adapters) and Tasks 16-21 (CLI verbs after 15) can run in parallel where dependencies allow. Two-stage review between tasks: code-reviewer subagent after each task before commit.

**2. Inline Execution** — Run the full plan in one session via the executing-plans skill, with checkpoint reviews at Phase boundaries (after Task 7, 10, 13, 21, 28, 30).

Both modes use the `subagent-driven-development` or `executing-plans` sub-skill respectively.

---

End of implementation plan.
