# agent-skills hub — design spec (v0)

| Field | Value |
|---|---|
| Status | spec phase — pre-implementation |
| Date | 2026-05-11 |
| Owner | Samuel Gudi (@samuelgudi) |
| Reviewer | Claude Code (Morpheus instance) |
| Repo | `samuelgudi/agent-skills` (private until v0 functional) |
| License | MIT |

---

## 1. Overview

`agent-skills` is an agent-agnostic registry for skill discovery and contribution. Any agent — Claude Code, Hermes, or others added later — can:

- Query the registry to find a skill that matches a task it doesn't have built-in for.
- Install that skill into the host agent's expected skill location.
- Propose new skills back to the registry through a sanitization + review pipeline.

The registry is a single flat-file git repository. There is no service to run, no auth flow at read time, no telemetry. Anyone can `git clone` the whole thing and mirror it.

The system is explicitly **agent-agnostic**. v0 ships adapters for Claude Code and Hermes. Adding Codex, OpenCode, or any future agent is a self-contained PR adding `adapters/<name>.py` plus an enum entry in `SCHEMA.md`.

## 2. Goals (v0)

- **Discovery**: programmatic + interactive search for skills by name, description, tag, category, agent compatibility, platform.
- **Contribution**: a 5-step pipeline (validate → sanitize → security-scan → self-review → submit) culminating in a GitHub PR.
- **Cross-agent**: both Claude Code and Hermes supported from v0; per-agent install adapters in the same repo.
- **Human-reviewed**: every merge passes through Samuel until v1. No auto-merge in v0.
- **Mirror-able**: flat-file git repo, no external dependencies for read access.
- **Forward-compatible schema**: room for hierarchical skills (`composes`, `extends`, `supersedes`), telemetry, learned curation — without breaking changes when those land.

## 3. Non-goals (v0)

- **Learned curation policies.** SkillOS-style trainable curators are deferred. v0 review is fully human.
- **Plugins.** Skills (instructions + optional deterministic scripts) only. Plugins (arbitrary Python entry points) are a separate trust tier; v1+ at the earliest.
- **Telemetry / usage signals.** No data sent from `match.py` or install adapters. Schema reserves an optional `usage_signals` block for future use; nothing emits it.
- **Hard-block override.** Security-scan hard blocks (Python code-evaluation builtins, shell calls with interpolated arguments, etc.) have no `--allow` escape hatch in v0. First legitimate case will inform the override design later.
- **Multi-author skills.** `author` is a single object. Co-authored skills can be filed under one owner with credit in `README.md`.
- **Semantic / vector search.** Match algorithm is deterministic keyword + filter scoring. Embeddings come later, behind the same `match.py` CLI surface, as a backend swap.

## 4. Locked decisions

| # | Question | Decision |
|---|---|---|
| 1 | MILO's role in v0 | Consumer only — registry is agent-agnostic from day one (CC + Hermes adapters ship together) |
| 2 | v0 scope | Full pipeline (discovery client + contribution client + validation + security scan + adapters) |
| 3 | Match-rank algorithm | Deterministic keyword scoring + filter flags (category / tag / agent / platform). No LLM, no embeddings in v0 |
| 4 | Skill identity | `<author>/<slug>` (e.g., `samuelgudi/spotify-search`) |
| 5 | Trust tier model | Single tier with uniform strict review. No `skills-executable/` split. |
| 6 | Repo shape | Monorepo (`samuelgudi/agent-skills`) — registry data, scripts, clients, adapters in one tree |
| 7 | Sanitization granularity | Confirm each detected change individually (one-by-one apply/skip prompts). `--yes` flag auto-accepts for scripts. |
| 8 | Hard-block override | None in v0. First legit need triggers a designed override mechanism with explicit per-pattern allow + REVIEW.md justification. |
| 9 | Deprecation model | `status: "deprecated"` + mandatory non-null `superseded_by` + filesystem move from `skills/` → `archive/` |
| 10 | Versioning | Semver per skill in `meta.json`. Updates via `submit` (auto-detects existing `<author>/<slug>` and bumps version). |
| 11 | Path B contribution verb | `agent-skills issue <skill-id>` (single verb, GitHub-aligned) |
| 12 | REVIEW.md fields | 5 fields: what does it do / what does it access / worst case / why useful (with gap-check) / test evidence |

## 5. Repo layout

```
agent-skills/                          (samuelgudi/agent-skills, MIT)
├── README.md
├── LICENSE
├── SCHEMA.md                          # registry.json + meta.json field spec
├── SECURITY.md                        # review checklist + reporting policy
├── CONTRIBUTING.md                    # human submission walkthrough
├── registry.json                      # canonical manifest (generated)
│
├── skills/                            # approved skills (status: active)
│   └── <author>/
│       └── <slug>/
│           ├── SKILL.md
│           ├── meta.json
│           ├── scripts/               # optional
│           ├── templates/             # optional
│           └── README.md              # optional (human-facing)
│
├── archive/                           # deprecated skills (status: deprecated)
│   └── <author>/<slug>/               # same shape as skills/
│
├── submitted/                         # open contribution PRs
│   └── pr-<NNN>/
│       ├── <author>/<slug>/           # sanitized skill files
│       ├── REVIEW.md                  # agent self-review (claim)
│       ├── SANITIZATION.diff          # original → sanitized (evidence)
│       └── scan_results.json          # security scan output
│
├── rejected/                          # closed-without-merge PRs, with reason
│
├── scripts/                           # registry tooling
│   ├── validate.py
│   ├── security_scan.py
│   ├── generate_manifest.py
│   ├── schema.json                    # machine-readable schema (synced with SCHEMA.md)
│   └── rules.yaml                     # declarative security-scan rules
│
├── clients/
│   ├── skill-discovery/
│   │   ├── SKILL.md
│   │   ├── match.py
│   │   └── update.py
│   └── skill-contribution/
│       ├── SKILL.md
│       ├── sanitize.py
│       ├── diff.py
│       ├── submit.py
│       └── templates/
│           ├── review.md
│           ├── pr-body.md
│           └── issue.md
│
├── adapters/                          # per-agent install logic
│   ├── claude_code.py
│   ├── hermes.py
│   └── _base.py                       # Adapter ABC, shared install/uninstall mechanics
│
├── agent_skills/                      # top-level CLI package
│   ├── __init__.py
│   ├── __main__.py                    # entry: `python -m agent_skills` or `agent-skills`
│   ├── cli.py                         # verb dispatch
│   ├── detect.py                      # host auto-detection
│   └── cache.py                       # ~/.cache/agent-skills/ helpers
│
├── tests/
│   ├── fixtures/
│   │   ├── good/                      # canonical valid skills
│   │   └── bad/                       # one fixture per documented validation rule
│   ├── conftest.py                    # tmpdir, fake-gh, fake-registry-server fixtures
│   └── test_*.py
│
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-11-agent-skills-hub-design.md   # this document
│
├── .github/
│   └── workflows/
│       ├── ci.yml                     # validate + scan + manifest-check + pytest
│       └── on-merge.yml               # generate_manifest.py + move submitted/ → skills/
│
├── pyproject.toml                     # packaging (pipx install agent-skills)
└── .gitignore
```

**Key shape decisions:**

- Skills nested as `skills/<author>/<slug>/` — natural filesystem reflection of the `<author>/<slug>` ID.
- `submitted/`, `rejected/`, and `archive/` are sibling top-level dirs to `skills/` — clear lifecycle states.
- `clients/` and `adapters/` are themselves the install artifacts: when an agent installs `skill-discovery`, the adapter copies that directory into the agent's skill location.
- `agent_skills/` is the installable Python package providing the `agent-skills` CLI entry point.

## 6. Skill identity and namespacing

- **Primary key**: `<author>/<slug>`, e.g., `samuelgudi/spotify-search`.
- **Slug grammar**: lowercase ASCII, dash-separated, ≤40 chars, no leading or trailing dashes, no `--`. Regex `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`.
- **Author**: lowercase ASCII GitHub-handle-shaped; the contributor's GitHub login.
- **Bare slug shorthand**: CLI accepts `agent-skills install spotify-search` and resolves to `samuelgudi/spotify-search` when unambiguous. When two authors publish the same slug, CLI prompts: "Multiple: `samuelgudi/spotify-search`, `someoneelse/spotify-search` — which?"
- **Installed directory name**: `<author>-<slug>` (flattened single segment). Most agents don't support nested skill directories.
- **`name:` in SKILL.md frontmatter**: bare slug only, no author prefix — installed skills remain portable across hosts.

## 7. `registry.json` schema

### Top-level structure

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-11T14:00:00Z",
  "skills": [ /* array of skill entries */ ]
}
```

`schema_version` increments on breaking schema changes. `generated_at` is the commit timestamp (not wall clock) for reproducibility.

### Skill entry

```json
{
  "id": "samuelgudi/spotify-search",
  "name": "spotify-search",
  "description": "Search Spotify by track, artist, or album using the Web API. Use when the user asks to find, look up, or check songs/albums/artists on Spotify.",
  "version": "0.1.0",
  "status": "active",
  "author": { "name": "Samuel Gudi", "github": "samuelgudi" },
  "category": "media",
  "tags": ["spotify", "music", "search", "api"],
  "platforms": ["linux", "macos", "windows"],
  "agent_compat": ["claude-code", "hermes"],
  "requires": {
    "env_vars": ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"],
    "commands": [],
    "toolsets": []
  },
  "has_scripts": true,
  "license": "MIT",
  "install": {
    "claude-code": { "scope": "user", "target_dir": "~/.claude/skills/samuelgudi-spotify-search/" },
    "hermes":      { "target_dir": "~/.hermes/skills/samuelgudi-spotify-search/" }
  },
  "source": {
    "path": "skills/samuelgudi/spotify-search",
    "content_hash": "sha256:abc123…",
    "files": ["SKILL.md", "scripts/search.py", "templates/result-format.md", "meta.json"]
  },
  "provenance": {
    "submitted_pr": 42,
    "merged_at": "2026-05-09T12:00:00Z",
    "reviewed_by": "samuelgudi"
  },
  "composes":   [],
  "extends":    null,
  "supersedes": [],
  "superseded_by": null
}
```

### Field semantics

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `<author>/<slug>`. Immutable. Primary key. |
| `name` | string | yes | Bare slug. Mirrors SKILL.md frontmatter `name`. |
| `description` | string | yes | **The trigger string** — what `match.py` scores against and what Claude Code's reflexive selection reads. Should describe WHEN to invoke, not just WHAT. |
| `version` | string | yes | Semver. Bumped on every merged change. |
| `status` | enum | yes | `"active"` \| `"deprecated"`. |
| `author` | object | yes | `{name, github}`. Single author in v0. |
| `category` | string | yes | One value from the fixed taxonomy in SCHEMA.md (extensible by PR). |
| `tags` | string[] | optional | Free-form, lowercase. Used by `--tag` filter; contributes to match score. |
| `platforms` | string[] | optional | Default `["linux", "macos", "windows"]`. |
| `agent_compat` | string[] | yes | Subset of `{claude-code, hermes, codex, opencode}`. v0 ships first two adapters. |
| `requires` | object | optional | Declared deps: env vars, external commands, toolsets. Surfaced to user before install. |
| `has_scripts` | bool | derived | True if `scripts/` exists. |
| `license` | string | yes | SPDX identifier. |
| `install` | object | yes | Per-agent install metadata. One block per supported agent. |
| `source` | object | derived | `{path, content_hash, files}`. Computed by `generate_manifest.py`. |
| `provenance` | object | derived | `{submitted_pr, merged_at, reviewed_by}`. Set on merge. |
| `composes` | string[] | optional | IDs of skills this skill calls/wraps. v0 doesn't act on this; reserved. |
| `extends` | string\|null | optional | ID of skill this one refines. Reserved. |
| `supersedes` | string[] | optional | IDs of skills this one replaces. Reserved. |
| `superseded_by` | string\|null | required if `status == "deprecated"` | ID of replacement skill. Validation enforces non-null + cross-reference. |

### Authoring convention

`generate_manifest.py` is the source of truth. Humans never hand-edit `registry.json`. They edit `meta.json` + `SKILL.md` in the skill directory; the script regenerates the manifest. CI runs `generate_manifest.py --check` and fails the PR if checked-in `registry.json` is out of sync.

## 8. Skill anatomy on disk

```
skills/samuelgudi/spotify-search/
├── SKILL.md                # frontmatter + agent-facing body
├── meta.json               # registry-facing machine metadata
├── scripts/                # optional, deterministic logic
│   └── search.py
├── templates/              # optional, reusable text/prompts
│   └── result-format.md
└── README.md               # optional, human-facing (not loaded by agents)
```

### `SKILL.md`

```markdown
---
name: spotify-search
description: Search Spotify by track, artist, or album using the Web API. Use when the user asks to find, look up, or check songs/albums/artists on Spotify.
---

# Spotify Search

## When to use
- User asks to find a song, album, or artist on Spotify
- User wants metadata for a known track
- DO NOT use for playlist management — see samuelgudi/spotify-playlist

## How to use
1. Confirm SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are set in env
2. Call `scripts/search.py <query> --type track|album|artist`
3. Format results using templates/result-format.md

## Limits
- Read-only — does not modify user data on Spotify
- Returns top 20 results per query
```

**Frontmatter contract:**

- `name` (required): bare slug. No author prefix in frontmatter.
- `description` (required): same string as `registry.json`. **Single source of truth at build time** — `generate_manifest.py` reads from SKILL.md and writes to registry.json; mismatch fails CI.
- Optional Claude-Code-specific keys (`model`, `allowed-tools`) are passed through untouched. Other agents ignore unknown keys.

### `meta.json`

Holds the registry-facing metadata except fields derivable from SKILL.md (`name`, `description`) or filesystem (`has_scripts`, `source.*`, `provenance.*`):

```json
{
  "id": "samuelgudi/spotify-search",
  "version": "0.1.0",
  "status": "active",
  "author": { "name": "Samuel Gudi", "github": "samuelgudi" },
  "category": "media",
  "tags": ["spotify", "music", "search", "api"],
  "platforms": ["linux", "macos", "windows"],
  "agent_compat": ["claude-code", "hermes"],
  "requires": {
    "env_vars": ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"],
    "commands": [],
    "toolsets": []
  },
  "license": "MIT",
  "install": {
    "claude-code": { "scope": "user" },
    "hermes":      {}
  },
  "composes":   [],
  "extends":    null,
  "supersedes": []
}
```

`superseded_by` is added (required) when `status` flips to `"deprecated"`.

### `scripts/`

- Pure Python, Bash, or Node. Language declared in SKILL.md body.
- No network calls at install time. Only at invoke time, only as documented.
- `security_scan.py` walks every file here.
- Path references inside scripts are relative to the skill directory; `${SKILL_DIR}` is substituted at install time by the adapter.

### `templates/`

- Plain text or markdown. Loaded by `scripts/` or referenced by SKILL.md body.
- No executable content. `.py`/`.sh`/`.js` files here trigger a validation warning.

### `README.md`

Optional. Human-facing (GitHub browsing). Not consumed by agents. Useful for screenshots, demos, longer rationale.

## 9. Top-level CLI + discovery client

### One binary: `agent-skills`

| Verb | Purpose | Pattern |
|---|---|---|
| `search <query>` | Find skills (primary entry) | `agent-skills search spotify song` |
| `show <id>` | Detail on one skill, including install status | `agent-skills show samuelgudi/spotify-search` |
| `install <id>` | Install for current host agent (auto-detected) | `agent-skills install spotify-search` |
| `uninstall <id>` | Remove from current host | `agent-skills uninstall spotify-search` |
| `verify <id>` | Check installed skill against marker + registry | `agent-skills verify spotify-search` |
| `list` | Show installed skills (current host) | `agent-skills list` |
| `update` | Force registry-cache refresh | `agent-skills update` |
| `submit <local-dir>` | Propose a new skill or new version | `agent-skills submit ./my-skill/` |
| `issue <id>` | Open improvement issue against an existing skill | `agent-skills issue samuelgudi/spotify-search` |
| `deprecate <id> --in-favor-of <new-id>` | Propose deprecation PR | — |

### Flags

- `--agent <name>` — override host auto-detection (defaults to detected `~/.claude/` or `~/.hermes/`)
- `--category <c>` / `--tag <t>` / `--platform <p>` — filter
- `--limit <N>` — search result count (default 5)
- `--json` — machine-readable output (agents)
- `--yes` — skip confirmation prompts (scripts)
- `--scope=user|project` — Claude Code install scope (defaults to `user`)
- `--include-archived` — include deprecated skills in search/show output

### Search UI (TTY)

```
$ agent-skills search spotify
Searching 47 skills (cache 2h old, refreshing)…

  ★ 1  samuelgudi/spotify-search                v0.1.0
       Search Spotify by track, artist, or album using the Web API.
       #spotify #music #search · requires SPOTIFY_CLIENT_ID + _SECRET

    2  samuelgudi/lastfm-lookup                 v0.2.1
       Look up tracks and artists on Last.fm.
       #lastfm #music #search

    3  somecontrib/spotify-playlist             v0.4.0
       Create and manage Spotify playlists.
       #spotify #music #write · requires SPOTIFY_OAUTH_TOKEN

Install which? [1-3, s=show details, q=quit]: _
```

- No exposed score numbers — `★` marks top match.
- Tags as `#hashtag` pills.
- Required env vars/commands surfaced inline.
- Numbered interactive selection by default; `--non-interactive` for scripts.

### Search JSON (agents)

```json
{
  "query": "spotify song",
  "filters": { "agent": "claude-code" },
  "candidates": [
    {
      "id": "samuelgudi/spotify-search",
      "score": 0.87,
      "version": "0.1.0",
      "description": "…",
      "tags": [ "spotify", "music", "search", "api" ],
      "has_scripts": true,
      "requires": { "env_vars": ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"], "commands": [], "toolsets": [] },
      "install_command": "agent-skills install samuelgudi/spotify-search"
    }
  ]
}
```

Schema versioned by `schema_version` in the registry it was generated from.

### Install UI (TTY)

```
$ agent-skills install spotify-search

samuelgudi/spotify-search  v0.1.0  (MIT, by samuelgudi)

  Search Spotify by track, artist, or album using the Web API.

  Files to install:
    SKILL.md                     1.2 KB
    scripts/search.py            3.4 KB
    templates/result-format.md   0.8 KB
    meta.json                    0.6 KB

  Target:  ~/.claude/skills/samuelgudi-spotify-search/

  Requires (set before invoking):
    SPOTIFY_CLIENT_ID            not set
    SPOTIFY_CLIENT_SECRET        not set

Proceed? [y/N]: y

  Fetching from github.com/samuelgudi/agent-skills@v0.1.0…
  Verifying content_hash sha256:abc123…  ok
  Writing:
    + ~/.claude/skills/samuelgudi-spotify-search/SKILL.md
    + ~/.claude/skills/samuelgudi-spotify-search/scripts/search.py
    + ~/.claude/skills/samuelgudi-spotify-search/templates/result-format.md
    + ~/.claude/skills/samuelgudi-spotify-search/meta.json
    + ~/.claude/skills/samuelgudi-spotify-search/.agent-skills-marker.json

Installed. Available in claude-code as `spotify-search`.
Uninstall: agent-skills uninstall spotify-search
```

### Match-scoring algorithm

Deterministic, no LLM:

```
score = 0.45 * name_token_match
      + 0.40 * description_token_match
      + 0.15 * tag_token_match
```

Each component:

1. Tokenize query: lowercase, strip punctuation, drop English stopwords.
2. Tokenize target field same way.
3. Compute Jaccard overlap, weighted by IDF (cached per registry-refresh).
4. Apply length normalization so verbose descriptions don't dominate.

**Filters apply before scoring.** `--agent claude-code` removes incompatible entries entirely before ranking, so the top-N is always relevant.

Ties broken by: (1) higher version, (2) more recent `merged_at`, (3) lexical `id` order. Deterministic.

### Discovery cache

- `~/.cache/agent-skills/registry.json` — cached manifest
- `~/.cache/agent-skills/registry.json.sig` — detached signature (optional in v0; loud warning when unsigned)
- `~/.cache/agent-skills/idf.json` — precomputed IDF table (regenerated on each `update`)
- `~/.cache/agent-skills/installed.json` — list of `id@version` strings the user has installed (per-adapter)

### `update.py`

- Fetches `registry.json` from `https://raw.githubusercontent.com/samuelgudi/agent-skills/main/registry.json` (configurable via `AGENT_SKILLS_REGISTRY_URL`).
- Verifies sha256 against `registry.json.sig` (when signing is enabled).
- Atomic write to cache; previous version preserved as `.prev` for rollback.
- Refuses to overwrite if the fetched `generated_at` is older than the cached one (rollback-attack guard).

### `clients/skill-discovery/SKILL.md`

```markdown
---
name: skill-discovery
description: Query the agent-skills registry for a skill that matches the current task. Use ONLY when explicitly asked to search for a skill ("search skills for X", "find a skill that does X"). Do not invoke reflexively for every task.
---
```

**Trigger model is explicit-only in v0.** Reflexive invocation on every task is deferred until false-positive rate has been measured.

## 10. Contribution pipeline

`agent-skills submit <local-dir>` walks five blocking steps. Failure at any step halts the flow.

### Step 1 — Validate structure (`validate.py`)

- Required files present (`SKILL.md`, `meta.json`).
- Frontmatter parses; `name` and `description` match `meta.json`/derived ID.
- `id` is well-formed; slug grammar matches.
- All required `meta.json` fields present.
- License is a valid SPDX identifier.
- `category` in fixed taxonomy.

Hard fail on missing required fields. No `--force`.

### Step 2 — Sanitize paths and secrets (`sanitize.py`)

Detection rules (deterministic, no LLM):

| Rule | Pattern (description) | Replacement |
|---|---|---|
| Absolute home path | `/home/<user>/`, `/Users/<user>/`, `C:\Users\<user>\` | `${HOME}/` |
| Skill-local absolute path | submission's own dir as absolute | `${SKILL_DIR}/` |
| GitHub PAT | `ghp_*`, `github_pat_*` | `${GITHUB_TOKEN}` |
| OpenAI key shape | `sk-` + alphanumeric ≥20 chars | `${OPENAI_API_KEY}` |
| Anthropic key shape | `sk-ant-` + alphanumeric/dashes ≥40 chars | `${ANTHROPIC_API_KEY}` |
| AWS access key | `AKIA` + 16 uppercase alphanumeric | `${AWS_ACCESS_KEY_ID}` |
| Long hex (≥40 chars) | possible token | flag for review |
| Env-var-shaped assignment | `*_TOKEN=...`, `*_KEY=...`, `*_SECRET=...`, `*_PASSWORD=...` with non-`${...}` value | flag for review |
| LAN IPs | 192.168/, 10./, 172.16-31./ | flag for review (may be intentional) |
| Email addresses | RFC 5322 simple match | flag for review (may be intentional) |

**Mode**: propose changes, never auto-apply. Each detection is interactive `[apply / skip / cancel]`. `--yes` bulk-accepts. `--no` bulk-skips. Cancel aborts.

### Step 3 — Security scan (`security_scan.py`)

Pattern-based scan of files in `scripts/` and `templates/`. Rules in `scripts/rules.yaml` (declarative, no code change to add rules).

**Hard blocks** (no override in v0). Each rule detects a different attack pattern; the full regexes live in `rules.yaml` and are deliberately not quoted verbatim in this spec to keep this document free of executable-looking literals:

| Rule ID | Detects | Language | Notes |
|---|---|---|---|
| `PY-EVAL-CALL` | Python identifier `eval` followed by `(` (with optional whitespace) | python | the Python eval-builtin executes arbitrary code |
| `PY-EXEC-CALL` | Python identifier `exec` followed by `(` (with optional whitespace) | python | the Python exec-builtin executes arbitrary code |
| `JS-FUNCTION-CTOR` | JS `Function` constructor invocation | javascript | dynamic code-evaluation in JS |
| `PY-SHELL-INTERP` | `subprocess` call with `shell=True` and a non-literal argument (concatenation or f-string) | python | command-injection risk |
| `SH-CURL-PIPE` | `curl` or `wget` piped into a shell interpreter | all | piping remote content to a shell is unsafe |
| `B64-PAYLOAD` | quoted base64 string ≥50 chars | all | possible obfuscated payload |
| `NET-IN-ADAPTER` | networking primitives (`urllib`, `requests`, `fetch`, `http.`) inside `adapters/` | python | install must be offline-deterministic |

**Soft warnings** (proceed, recorded in REVIEW.md):

| Rule ID | Detects | Notes |
|---|---|---|
| `PY-SUBPROCESS-USE` | any `subprocess.` reference | declare commands in `meta.json.requires.commands` |
| `FS-WRITE-OUTSIDE-SKILL` | filesystem writes outside `${SKILL_DIR}/cache/` | recorded in REVIEW.md |
| `UNDECLARED-CMD` | external binary used but not declared in `requires.commands` | |

**Output format:**

```
scripts/search.py
  line 42  BLOCK  PY-SHELL-INTERP  subprocess with shell=True and non-literal args
                  fix: pass args as a list, drop shell=True
  line 67  WARN   PY-SUBPROCESS-USE  declare in meta.json.requires.commands

templates/result-format.md
  clean

1 block, 1 warning. Cannot proceed.
```

CI re-runs `security_scan.py` on every push (defense in depth).

### Step 4 — Self-review (REVIEW.md)

Auto-generated by the agent submitter (or filled manually if human), with five fields:

```markdown
# REVIEW.md

## What does this skill do?
(1-2 sentences)

## What does it access?
- Network endpoints:
- Filesystem paths written:
- Env vars read:
- Processes spawned:

## Worst case if it misbehaves?
(concrete; not hand-wavy)

## Why is this useful?
- What task it solves:
- What existing skill DOES NOT already solve it (gap-check):

## Test evidence
- Commands run manually before submitting:
- Outputs:
- (or "agent-only execution — see SANITIZATION.diff for full code path")
```

**This is a claim, not evidence.** UI surfaces it alongside SANITIZATION.diff and `scan_results.json` at PR review time. The reviewer (Samuel in v0) compares REVIEW.md against the code; never auto-trusts.

### Step 5 — Open PR (`submit.py`)

- Repo: `samuelgudi/agent-skills`
- Branch: `submit/<slug>-<YYYY-MM-DD>-<3-char-hex>`
- Path in PR: `submitted/pr-<NNN>/<author>/<slug>/` (the sanitized skill files) + `submitted/pr-<NNN>/REVIEW.md` + `submitted/pr-<NNN>/SANITIZATION.diff` + `submitted/pr-<NNN>/scan_results.json`
- PR body template (from `clients/skill-contribution/templates/pr-body.md`) summarizes: skill ID, version, license, install matrix, scan results, REVIEW.md highlights, link to SANITIZATION.diff.
- Pre-flight: `gh` auth check, no conflicting branch, slot in `submitted/pr-NNN/` reserved by the PR number (known after `gh pr create`).

### Path B — `agent-skills issue <skill-id>`

Lower-friction contribution for non-implementers:

```
$ agent-skills issue samuelgudi/spotify-search

Open improvement issue for samuelgudi/spotify-search v0.1.0.

  Type? [bug / feature / docs / security]: feature
  Title: _ Add ISRC code to track search results
  Context (what task were you trying to do?):
  _ Looking up ISRC for cross-platform deduplication
  Proposed change:
  _ Include `isrc` field in result JSON when available
  Will you implement this yourself? [y/N]: n

Open issue at samuelgudi/agent-skills? [y/N]: y
Issue opened: https://github.com/samuelgudi/agent-skills/issues/57
```

Template: `clients/skill-contribution/templates/issue.md`.

### Update flow (new version of existing skill)

`agent-skills submit <local-dir>` detects whether `<author>/<slug>` already exists in the registry.

- **Not present** → first-submission flow above.
- **Already exists** → "Detected existing skill `samuelgudi/spotify-search` v0.1.0. This submission proposes v0.2.0 (heuristic: minor — 1 new env var, no removed fields). Override with `--version-bump patch|minor|major`."

The PR replaces the existing `skills/<author>/<slug>/` directory contents (no parallel version directories — git history is the version log).

Pinning to a past version: `agent-skills install <id>@<version>` fetches files from the corresponding git ref.

### Deprecation flow

`agent-skills deprecate <id> --in-favor-of <new-id>` opens a deprecation PR that:

1. Sets `status: "deprecated"` and `superseded_by: <new-id>` in `meta.json`.
2. Moves `skills/<author>/<slug>/` → `archive/<author>/<slug>/`.
3. Updates `registry.json` via `generate_manifest.py`.

`validate.py` enforces: `status == "deprecated"` requires non-null `superseded_by` referencing an existing active skill. No orphan deprecations.

`match.py` excludes deprecated skills by default; `--include-archived` surfaces them with `[DEPRECATED → <new-id>]` badge.

### CI re-runs every check

`.github/workflows/ci.yml` runs on every push to a PR:

1. `validate.py --all --strict`
2. `security_scan.py --all`
3. `generate_manifest.py --check`
4. `pytest tests/ -v`
5. (contribution PRs only) verify `SANITIZATION.diff` matches actual file diff between pre-sanitization snapshot and submitted files; verify REVIEW.md present and non-empty.

Merge blocked until all pass.

### On-merge workflow

`.github/workflows/on-merge.yml` runs after merge to `main`:

1. Move `submitted/pr-<NNN>/<author>/<slug>/` → `skills/<author>/<slug>/` (or `archive/` for deprecation PRs).
2. Run `generate_manifest.py` to recompute `source.content_hash`, set `provenance`.
3. Commit `[automerge] Add <id>@<version>` (or `[automerge] Deprecate <id>`).
4. Tag release if a new minor/major version was published.

## 11. `scripts/validate.py` details

**Inputs:**

```bash
validate.py <skill-dir>             # validate one skill directory
validate.py --all                   # walk skills/ and archive/, validate every entry
validate.py --strict                # treat warnings as errors (CI mode)
validate.py --json                  # machine output
```

**Schema source of truth:**

- Human-readable: `SCHEMA.md`
- Machine-readable: `scripts/schema.json` (JSON Schema draft 2020-12)
- `tests/test_schema_sync.py` asserts that every documented rule in SCHEMA.md has a corresponding constraint in `schema.json`, and that every "bad fixture" in `tests/fixtures/bad/` is caught by exactly the rule it's named for.

**Validation checks (beyond schema):**

- `id` matches directory path (`skills/<author>/<slug>/` → `<author>/<slug>`).
- Frontmatter `name` and `description` match `meta.json` (cross-file consistency).
- If `status == "deprecated"`, `superseded_by` references an existing active skill (cross-skill).
- No nested git repos (`.git/` inside skill dirs).
- No extraneous files beyond what's declared in `source.files` (prevents stowaways).
- Deprecation chain has no cycles (A → B → A blocked).

**Exit codes:** `0` clean · `1` errors · `2` warnings only (in non-strict mode).

## 12. `scripts/security_scan.py` details

Patterns declared in `scripts/rules.yaml` (see § 10 table for the v0 rule set). The full regular expressions are kept in the YAML — this spec describes rules by what they detect rather than quoting executable-looking literals.

**Rule shape (rules.yaml entry, schematic):**

- `id`: stable identifier (e.g., `PY-EVAL-CALL`)
- `severity`: `block` or `warn`
- `pattern`: regex string
- `languages`: list of language tags filtered by file extension
- `scope`: optional glob narrowing which files this rule applies to (default: all)
- `message`: human-readable description shown in scan output
- `fix_hint`: actionable remediation advice

**Engine:** per-file regex match with multiline flag enabled. File language inferred from extension.

**Output format:** see § 10 example. `--json` emits a structured list of findings with line/column.

**Exit codes:** `0` clean or warnings only · `1` at least one block.

No suppression mechanism in v0.

## 13. `scripts/generate_manifest.py` details

**Inputs:**

```bash
generate_manifest.py                # rebuild registry.json
generate_manifest.py --check        # exit 1 if registry.json doesn't match the regenerated output
```

**Algorithm:**

1. Walk `skills/` and `archive/` for every `meta.json` + `SKILL.md` pair.
2. For each skill:
   - Load `meta.json`.
   - Read `name` and `description` from SKILL.md frontmatter.
   - Build `source.path` (relative).
   - Build `source.files` (sorted list of all files in the skill dir).
   - Compute `source.content_hash`: sha256 over a deterministic concatenation of `<relpath>\0<sha256(file_contents)>` for each file, joined by newline. Deterministic.
   - Detect `has_scripts` from filesystem.
   - Read `provenance` from git: last merge commit affecting this dir → `merged_at`, PR number from commit message convention (`[automerge] Add <id>@<ver> (#NN)`).
3. Sort skills by `id` (lexical).
4. Set top-level `generated_at` to the current commit timestamp (via `git log -1 --format=%cI HEAD`), NOT wall clock — reproducible builds.
5. Write `registry.json`.

`--check` mode regenerates in a tmpdir, byte-compares with the checked-in `registry.json`. Any difference → exit 1 with diff output.

## 14. Per-agent adapters

### Common adapter contract (`adapters/_base.py`)

```python
class Adapter(ABC):
    name: str

    @abstractmethod
    def detect(self) -> bool: ...                              # is this host present?

    @abstractmethod
    def target_dir(self, skill_id: str, *, scope: str = "user") -> Path: ...

    @abstractmethod
    def install(self, src_dir: Path, skill_id: str, version: str, opts: dict) -> InstallResult: ...

    @abstractmethod
    def uninstall(self, skill_id: str) -> UninstallResult: ...

    @abstractmethod
    def list_installed(self) -> list[Installed]: ...

    @abstractmethod
    def verify(self, skill_id: str) -> VerifyResult: ...
```

### Shared install mechanics

1. Stage: copy source files to a temp dir.
2. Verify: recompute content_hash, compare to `registry.json`. Mismatch → abort.
3. Write marker `.agent-skills-marker.json` into the staged dir:

```json
{
  "id": "samuelgudi/spotify-search",
  "version": "0.1.0",
  "installed_at": "2026-05-11T15:00:00Z",
  "installed_by": "agent-skills v0.1.0",
  "content_hash": "sha256:abc…",
  "source_url": "github.com/samuelgudi/agent-skills@v0.1.0"
}
```

4. Atomic move: temp dir → final target (POSIX rename; Windows fallback: write-then-replace).
5. Rollback on mid-install failure: delete temp, leave existing target untouched.

### `adapters/claude_code.py`

- **Detect**: `~/.claude/` exists.
- **Target dir** (user scope): `~/.claude/skills/<author>-<slug>/`
- **Target dir** (project scope, `--scope=project`): `<cwd>/.claude/skills/<author>-<slug>/`
- **Frontmatter pass-through**: `name`, `description` (required); `model`, `allowed-tools` (optional, copied verbatim); other keys preserved.
- **No special hook**: Claude Code re-scans skills on next session start.

### `adapters/hermes.py`

- **Detect**: `~/.hermes/` exists.
- **Target dir**: `~/.hermes/skills/<author>-<slug>/`
- **Runtime**: Hermes hot-reloads on filesystem changes.
- **`plugin.py` emission**: when `meta.json.install.hermes.emit_plugin == true`, a Hermes-specific stub is written that wires `@hermes.on(...)` decorators to the skill's script entry points. Default off — most skills are instruction-only.

### Conflict handling (all adapters)

- Target exists with marker, same version → reinstall prompt.
- Target exists with marker, different version → upgrade prompt (default Yes).
- Target exists, **no marker** → hard refuse: cannot overwrite a user-authored skill. Rename or remove manually first.

### Drift detection (`agent-skills verify <id>`)

Recomputes content_hash of installed files; compares to marker; compares marker to registry. Outcomes:

- Clean: files match marker, marker matches registry.
- Local drift: files != marker. User edited. Warn; offer reinstall.
- Marker outdated: marker matches files but newer version in registry. Suggest upgrade.
- Tampered marker: marker hash != registry's published hash for that version. Loud warning; refuse to trust until re-installed.

### Auto-detection logic

```python
def detect_host() -> str:
    found = [a.name for a in registered_adapters if a.detect()]
    if not found:
        die("No agent host detected. Install Claude Code or Hermes, or pass --agent.")
    if len(found) == 1:
        return found[0]
    if pref := environ.get("AGENT_SKILLS_DEFAULT_AGENT"):
        if pref in found:
            return pref
    return prompt("Multiple hosts detected. Which?", found)
```

`--agent <name>` always wins.

## 15. Testing strategy

### Layout

```
tests/
├── fixtures/
│   ├── good/                          # canonical valid skills
│   │   ├── instructions-only/
│   │   ├── with-scripts/
│   │   ├── with-templates/
│   │   ├── deprecated/
│   │   └── multi-agent/
│   └── bad/                           # named for the rule each violates
│       ├── slug-with-uppercase/
│       ├── slug-path-traversal/
│       ├── missing-license/
│       ├── deprecated-no-successor/
│       ├── deprecated-cycle/
│       ├── frontmatter-mismatch/
│       ├── extraneous-file/
│       └── nested-git/
├── test_validate.py
├── test_security_scan.py
├── test_generate_manifest.py
├── test_match.py
├── test_update.py                     # uses fake http.server fixture
├── test_sanitize.py
├── test_submit.py                     # uses fake-gh shim
├── test_adapter_claude_code.py
├── test_adapter_hermes.py
├── test_cli.py
├── test_schema_sync.py
└── conftest.py
```

### Principles

- **No mocks for the system under test.** tmpdir for filesystem; fake HTTP server fixture for network; fake-gh shell script on PATH for `gh` invocations. Real subprocess calls against real (controlled) binaries.
- **Adversarial inputs by default.** For every rule documented in SCHEMA.md or rules.yaml, a fixture exists that violates it; the test asserts both that detection fires AND that the message text matches.
- **False positives matter as much as detection.** A 40-char git SHA looks like a token. A `/tmp/...` path looks like a leaked path but isn't. Tests document both the catch and the conscious miss.
- **Determinism is tested.** `generate_manifest.py` running twice on the same fixtures produces byte-identical output. `match.py` with same query and same registry produces the same ranking.

### Adversarial test cases (sample)

- Code-eval builtins (`eval`, `exec`) with whitespace variations between the identifier and the opening paren — caught by `PY-EVAL-CALL` / `PY-EXEC-CALL`.
- Alias evasion: aliasing the builtin to another name before calling — caught by a separate alias-detection rule.
- Reflective dispatch: looking up the builtin via `getattr` on the builtins module — known limit, documented test as "consciously missed; security model relies on human review for cleverness."
- Use of the legacy `os` module's system-call function instead of `subprocess` — caught.
- A `subprocess` invocation passing `sh -c <variable>` with a non-literal argument — caught (rule matches `sh -c` + non-literal).
- 50-char base64 string that's a real hash → false positive flagged; sanitize prompts user to skip.

### CI matrix

```yaml
os:     [ubuntu-latest, macos-latest, windows-latest]
python: ['3.10', '3.11', '3.12']
```

### What's NOT tested (consciously)

- Real GitHub API. Fake-gh shim only.
- Real registry hosting. fake HTTP server fixture only.
- Cross-OS path edge cases beyond CI matrix.
- Performance / scale. v0 assumes <500 skills. Perf tests added when that becomes wrong.

## 16. CI workflows

### `.github/workflows/ci.yml` (on every push to PR)

```yaml
jobs:
  ci:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '${{ matrix.python }}' }
      - run: pip install -e .[dev]
      - run: python scripts/validate.py --all --strict
      - run: python scripts/security_scan.py --all
      - run: python scripts/generate_manifest.py --check
      - run: pytest tests/ -v
```

Contribution-PR-only job adds:

- Verify `SANITIZATION.diff` matches actual file diff between submitter's pre-sanitization snapshot and submitted files.
- Verify REVIEW.md present, non-empty, all 5 fields filled.
- Post a comment summarizing scan results + REVIEW.md highlights + permalinks.

### `.github/workflows/on-merge.yml` (on merge to `main`)

- Move `submitted/pr-<NNN>/` contents to `skills/` or `archive/`.
- Run `generate_manifest.py` to recompute hashes and update `registry.json`.
- Commit and tag release (if version bump warrants).

## 17. Out of scope for v0

- Learned curation policies (SkillOS-style trainable curator).
- Plugin support (arbitrary Python entry points).
- Telemetry / usage signal collection.
- Multi-author skills.
- Semantic / vector search.
- Hard-block override flag.
- Auto-merge for low-risk PRs.
- Skill mirroring across federated registries.
- Per-agent skill marketplaces.

## 18. Forward compatibility notes

### SkillOS paper (arxiv 2605.06614)

Architectural moves the paper validates that are already in v0:

- Decoupled executor (discovery-client side) / curator-input (contribution-client side).
- Markdown as the skill encoding.
- Cross-agent generalization (`agent_compat` field).

Architectural moves the paper recommends that v0 reserves but does not act on:

- `composes` / `extends` / `supersedes` fields admit hierarchical / meta-skills. v0 carries them in schema; `match.py` and adapters ignore.
- Optional future `usage_signals` block on each skill entry. Not collected in v0; reserved.

A learned curator could be added in v1+ as a separate `clients/skill-curator/` component without breaking the registry schema. The contribution pipeline already separates submitter (writer) from reviewer (curator) — a learned curator slots into the reviewer role without disrupting submission UX.

### Schema-version bumps reserved for

- Removing fields (never adding — additions are backward-compatible).
- Changing field semantics.
- Introducing required fields.

## 19. Open decisions deferred to v0.x

- **Reflexive skill-discovery invocation** — SKILL.md trigger condition relaxed from "explicit invoke only" to something more reflexive, once false-positive rate is measured.
- **Override mechanism for hard security blocks** — designed on first legitimate use case.
- **Signing infrastructure** — `registry.json.sig` and key distribution. v0 ships unsigned with loud warning; signing turned on when a key is in place.
- **`pipx` / PyPI publication of `agent-skills` CLI** — v0 installable from git; PyPI publication is a v0.1 concern.
- **Plugin trust tier (v1+)** — when plugin support is added, design the second trust tier with its own folder (`plugins/`), stricter review, and capability declarations.

## 20. Build sequence (preview for the implementation plan)

This spec produces an implementation plan (separate document). High-level milestones:

1. Skeleton repo: SCHEMA.md, SECURITY.md, CONTRIBUTING.md, schema.json, rules.yaml, empty registry.json.
2. `validate.py` + fixtures + tests — schema layer first.
3. `security_scan.py` + rules.yaml + fixtures + tests.
4. `generate_manifest.py` + tests (depends on validate).
5. Adapter base + `claude_code.py` + tests.
6. Adapter `hermes.py` + tests.
7. Top-level `agent-skills` CLI: detect, search (without update), show, list, verify.
8. `update.py` + cache + tests.
9. `sanitize.py` + `diff.py` + tests.
10. `submit.py` + fake-gh fixture + tests.
11. `issue` verb + tests.
12. CI workflows.
13. Seed skills (2–3 instruction-only skills as canonical examples).
14. README + CONTRIBUTING + SECURITY hardening pass.

Detailed sequence with task-level breakdown lands in the writing-plans output.
