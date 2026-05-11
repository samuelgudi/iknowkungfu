# agent-skills hub — design spec (v3, post-MILO + post-Gemini review)

| Field | Value |
|---|---|
| Status | spec phase v3 — pre-implementation (MILO + Gemini reviews folded in) |
| Date | 2026-05-11 |
| Owner | Samuel Gudi (@samuelgudi) |
| Reviewer | Claude Code (Morpheus) + MILO (Hermes agent) + Gemini 3 Pro |
| Repo | `samuelgudi/agent-skills` (private until v0 functional) |
| License | MIT |

> **Changelog**: § 21 documents v1→v2 (MILO findings). § 22 documents v2→v3 (Gemini findings).

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
- **Cross-agent**: both Claude Code and Hermes supported from v0; per-agent install adapters in the same repo, each handling that host's filesystem conventions and frontmatter expectations.
- **Human-reviewed**: every merge passes through Samuel until v1. No auto-merge in v0.
- **Mirror-able**: flat-file git repo, no external dependencies for read access.
- **Version pinning works**: `<id>@<version>` resolves in constant time via a precomputed `versions` map; reproducible installs of any prior published version.
- **Compromise response**: distinct yank semantics for compromised versions (hard-refuse, no override) vs deprecation (soft-hide, supersession).
- **Identity stability**: skill ownership is bound to GitHub's immutable numeric user ID, not the mutable username string.
- **Forward-compatible schema**: room for hierarchical skills (`composes`, `extends`, `supersedes`), telemetry, learned curation — without breaking changes when those land.

## 3. Non-goals (v0)

- **Learned curation policies.** SkillOS-style trainable curators are deferred. v0 review is fully human.
- **Plugins.** Skills (instructions + optional deterministic scripts) only. Hermes plugins (Python entry points in `~/.hermes/plugins/`) are a separate trust tier; v1+ at the earliest.
- **Telemetry / usage signals.** No data sent from `match.py` or install adapters. Schema reserves an optional `usage_signals` block for future use; nothing emits it.
- **Hard-block override.** Security-scan hard blocks have no `--allow` escape hatch in v0. First legitimate case will inform the override design later.
- **Multi-author skills.** `author` is a single object. Co-authored skills can be filed under one owner with credit in `README.md`.
- **Semantic / vector search.** Match algorithm is deterministic keyword + filter scoring. Known limitation documented in § 9 and § 17; embeddings come later behind the same `match.py` CLI surface as a backend swap.
- **Anti-spam ranking** (keyword stuffing penalties beyond a tag cap). Pure-spam-fighting isn't urgent at v0 scale with curated PR review (Gemini m1, deferred).
- **Verified publisher signals.** No `verified: true` flag at v0; meaningful only post-v1 with multi-org contributors (Gemini m2, deferred).

## 4. Locked decisions

| # | Question | Decision |
|---|---|---|
| 1 | MILO's role in v0 | Consumer only — registry is agent-agnostic from day one (CC + Hermes adapters ship together) |
| 2 | v0 scope | Full pipeline (discovery client + contribution client + validation + security scan + adapters) |
| 3 | Match-rank algorithm | Deterministic keyword scoring + filter flags (category / tag / agent / platform). No LLM, no embeddings in v0. Limitation acknowledged: degrades past ~30 skills; mitigated by contributor-guideline coaching (CONTRIBUTING.md) and a tag-count cap. |
| 4 | Skill identity | `<author>/<slug>` — where `<author>` is the GitHub login at registration time, **bound to the immutable GitHub user ID** (Gemini M2). |
| 5 | Trust tier model | Single pipeline; stricter requirements for scripts-bearing skills. `has_scripts: true` triggers (a) line-by-line script review, (b) explicit capability declaration in REVIEW.md, (c) mandatory test evidence — no "agent-only execution" exemption. |
| 6 | Repo shape | Monorepo (`samuelgudi/agent-skills`) — registry data, scripts, clients, adapters in one tree |
| 7 | Sanitization granularity | Confirm each detected change individually (one-by-one apply/skip prompts). `--yes` flag auto-accepts for scripts. |
| 8 | Hard-block override | None in v0. First legit need triggers a designed override mechanism with explicit per-pattern allow + REVIEW.md justification. |
| 9 | Deprecation model | `status: "deprecated"` + mandatory non-null `superseded_by` — **obsolescence semantics** (soft-hide, install requires `--allow-deprecated`). Distinct from yanking (Gemini M3). |
| 10 | Yanking model (v3) | **Per-version `yanked: true` + `yank_reason` in `versions` map** — **compromise semantics** (hard-refuse install, no override). Yanks are recorded in `yanks.json` at the registry root; `generate_manifest.py` merges them into `registry.json.skills[].versions`. |
| 11 | Versioning | Semver per skill in `meta.json`. **`registry.json` carries a per-skill `versions: {<ver>: {sha, released, yanked?, yank_reason?}}` map** for constant-time pinning resolution (Gemini M1). Updates via `submit` (auto-detects existing `<author>/<slug>` and bumps version). |
| 12 | Path B contribution verb | `agent-skills issue <skill-id>` (single verb, GitHub-aligned) |
| 13 | REVIEW.md fields | 6 fields: what does it do / what does it access / worst case / why useful (with gap-check) / test evidence / what changed (skill updates only). For `has_scripts: true`, capabilities listed explicitly. |
| 14 | External-code policy (v3) | **Hard-block any unpinned package-manager install in `scripts/`**: `pip install`, `npm install`, `gem install`, `cargo install`, `apt(-get) install`, `brew install`, `go install`, `pnpm install`, `yarn add`, `pipx install`, `uv install`, etc. Skill runtime dependencies must be declared in `meta.json.requires.commands` and installed by the user/host beforehand (Gemini B1). |

## 5. Repo layout

```
agent-skills/                          (samuelgudi/agent-skills, MIT)
├── README.md
├── LICENSE
├── SCHEMA.md                          # registry.json + meta.json field spec + category taxonomy
├── SECURITY.md                        # review checklist + reporting policy + yank procedure
├── CONTRIBUTING.md                    # human submission walkthrough + skill-description guideline
├── registry.json                      # canonical manifest (generated)
├── yanks.json                         # operational yank list (hand-edited / via `agent-skills yank` PR)
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
│       ├── SANITIZATION.diff          # original → sanitized (evidence, regenerated post-sanitization)
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
│   ├── __main__.py
│   ├── cli.py                         # verb dispatch
│   ├── detect.py                      # host auto-detection
│   └── cache.py
│
├── tests/
│   ├── fixtures/
│   │   ├── good/
│   │   └── bad/
│   ├── conftest.py
│   └── test_*.py
│
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-11-agent-skills-hub-design.md   # this document
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── on-merge.yml
│
├── pyproject.toml
└── .gitignore
```

**Key shape decisions:**

- **Registry storage** uses `<author>/<slug>` namespacing throughout. Adapters translate to per-host install layouts (§ 14).
- **`yanks.json` is sibling to `registry.json`** but distinct: yanks are operational decisions (sometimes urgent), `registry.json` is fully regenerated from `skills/` + `yanks.json` by `generate_manifest.py`.
- `submitted/`, `rejected/`, and `archive/` are sibling top-level dirs to `skills/` — clear lifecycle states.
- `clients/` and `adapters/` are themselves install artifacts.
- `agent_skills/` is the installable Python package providing the `agent-skills` CLI entry point.

## 6. Skill identity and namespacing

- **Primary key**: `<author>/<slug>`, e.g., `samuelgudi/spotify-search`.
- **Slug grammar**: lowercase ASCII, dash-separated, ≤40 chars, no leading or trailing dashes, no `--`. Regex `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`.
- **Author**: the contributor's GitHub login at registration time. **Backed by `author.github_id` — the immutable GitHub numeric user ID — which is the actual identity anchor.** The login is human-readable; the ID is the cryptographic-grade key (Gemini M2).
- **Bare slug shorthand**: CLI accepts `agent-skills install spotify-search` and resolves to `samuelgudi/spotify-search` when unambiguous. When two authors publish the same slug, CLI prompts; CI surfaces same-slug warnings on the PR.
- **`name:` in SKILL.md frontmatter (registry copy)**: bare slug only, no author prefix.
- **Installed directory name (per-adapter convention)**:
  - Claude Code: `~/.claude/skills/<author>-<slug>/`
  - Hermes: `~/.hermes/skills/<category>/<slug>/`
- **Cross-adapter portability**: SKILL.md in the registry stays minimal (name + description). The adapter for the target host synthesizes the full frontmatter block at install time (§ 14).

### GitHub-ID binding (v3, Gemini M2)

GitHub allows re-registration of previously-deleted usernames after a holding period. If `samuelgudi` deletes the account, an attacker could later register the same login and inherit ownership of every `samuelgudi/*` skill — `validate.py` matching strings would happily accept the PR.

**Mitigation**: at the first PR for a new author, CI fetches `gh api users/<login>` and records the numeric `id` into `meta.json.author.github_id`. On every subsequent PR from that author, CI re-fetches the current id and asserts it matches the recorded one. Mismatch → PR is automatically blocked with a notice (`Author "<login>" has been re-registered; original owner had id=N, current id=M. Ownership transfer requires a separate verified PR.`)

The numeric id is stable across login renames (GitHub keeps the id when a user renames). It is replaced only on account deletion, which is the exact threat we're defending against.

## 7. `registry.json` schema

### Top-level structure

```json
{
  "schema_version": 2,
  "generated_at": "2026-05-11T14:00:00Z",
  "skills": [ /* array of skill entries */ ]
}
```

> **v3 change**: `schema_version` bumped to 2 (the prior v0/v1/v2 spec was `schema_version: 1`). Breaking schema changes: `author.github_id` becomes required; `versions` becomes required; `yanked` flag moves from skill level to per-version inside `versions`.

`generated_at` is the commit timestamp (not wall clock) for reproducibility.

### Skill entry

```json
{
  "id": "samuelgudi/spotify-search",
  "name": "spotify-search",
  "description": "Search Spotify by track, artist, or album using the Web API. Use when the user asks to find, look up, or check songs/albums/artists on Spotify.",
  "version": "0.2.0",
  "status": "active",
  "author": {
    "name": "Samuel Gudi",
    "github_login": "samuelgudi",
    "github_id": 12345678
  },
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
    "claude-code": { "scope": "user" },
    "hermes":      {}
  },
  "source": {
    "path": "skills/samuelgudi/spotify-search",
    "content_hash": "sha256:abc123…",
    "files": ["SKILL.md", "scripts/search.py", "templates/result-format.md", "meta.json"]
  },
  "versions": {
    "0.1.0": {
      "sha": "abc111000…",
      "released": "2026-05-09T12:00:00Z"
    },
    "0.1.1": {
      "sha": "abc222000…",
      "released": "2026-05-10T08:00:00Z",
      "yanked": true,
      "yank_reason": "Compromised upstream dependency in scripts/search.py; users must upgrade to 0.2.0+."
    },
    "0.2.0": {
      "sha": "abc333000…",
      "released": "2026-05-11T15:00:00Z"
    }
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

> **v3 changes**:
> - `author.github` → `author.github_login` + new required `author.github_id` (Gemini M2).
> - New required `versions` map: per-version `{sha, released, yanked?, yank_reason?}` (Gemini M1 + M3).
> - `source.content_hash` is the hash of the **current latest version**. Each entry in `versions` carries its own `sha` for git tree lookup; hashes of prior versions can be recomputed from those trees on demand.

### Field semantics

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | `<author>/<slug>`. Immutable. Primary key. |
| `name` | string | yes | Bare slug. Mirrors SKILL.md frontmatter `name`. |
| `description` | string | yes | **The trigger string** — what `match.py` scores against. Authors should include synonyms (M5). |
| `version` | string | yes | Semver. The current/latest version. |
| `status` | enum | yes | `"active"` \| `"deprecated"`. Obsolescence semantics. |
| `author` | object | yes | `{name, github_login, github_id}`. `github_id` is GitHub's immutable numeric user ID (M2). |
| `category` | string | yes | One value from fixed taxonomy in SCHEMA.md. Drives Hermes install path. |
| `tags` | string[] | optional | Free-form, lowercase. **Capped at 10 entries** in validate.py to mitigate keyword stuffing (Gemini m1 partial fold). |
| `platforms` | string[] | optional | Default `["linux", "macos", "windows"]`. Hermes adapter translates to frontmatter `platforms:` (M2). |
| `agent_compat` | string[] | yes | Subset of `{claude-code, hermes, codex, opencode}`. |
| `requires` | object | optional | Declared deps. Hermes adapter translates to frontmatter `prerequisites:` (M1). |
| `has_scripts` | bool | derived | True if `scripts/` exists. Triggers stricter review (Decision #5). |
| `license` | string | yes | SPDX identifier. |
| `install` | object | yes | Per-agent install metadata (sparse — host-specific options only). |
| `source` | object | derived | `{path, content_hash, files}`. Reflects the current version. |
| **`versions`** | **object** | **yes** | **Map `{ <semver>: { sha, released, yanked?, yank_reason? } }`. Built by `generate_manifest.py` from git history; populated/updated by `yanks.json` for the yanked flag. Enables O(1) version pinning (M1).** |
| `provenance` | object | derived | `{submitted_pr, merged_at, reviewed_by}`. Set on merge. |
| `composes` | string[] | optional | Reserved for hierarchical skills. |
| `extends` | string\|null | optional | Reserved. |
| `supersedes` | string[] | optional | Reserved. |
| `superseded_by` | string\|null | required if `status == "deprecated"` | ID of replacement skill (active). |

### `yanks.json` shape

```json
{
  "yanks": [
    {
      "id": "samuelgudi/spotify-search",
      "version": "0.1.1",
      "yanked_at": "2026-05-12T09:00:00Z",
      "yanked_by": "samuelgudi",
      "reason": "Compromised upstream dependency in scripts/search.py; users must upgrade to 0.2.0+."
    }
  ]
}
```

`generate_manifest.py` reads `yanks.json` on every regeneration and applies `yanked: true` + `yank_reason` to the matching `versions[ver]` entries. Yanks are append-only — once a version is yanked, it stays yanked. Removing an entry from `yanks.json` is allowed only via a separate explicit PR with documented reason (e.g., false-positive recall).

## 8. Skill anatomy on disk

```
skills/samuelgudi/spotify-search/
├── SKILL.md                # minimal frontmatter + agent-facing body
├── meta.json               # registry-facing machine metadata
├── scripts/                # optional, deterministic logic
│   └── search.py
├── templates/              # optional, reusable text/prompts
│   └── result-format.md
└── README.md               # optional, human-facing
```

### `SKILL.md` (registry copy)

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

**Frontmatter contract (registry copy):**

- `name` (required): bare slug.
- `description` (required): same string as `registry.json`. Mismatch fails CI.

The full Hermes-compatible frontmatter is **synthesized by the Hermes adapter at install time** (§ 14).

### `meta.json`

```json
{
  "id": "samuelgudi/spotify-search",
  "version": "0.2.0",
  "status": "active",
  "author": {
    "name": "Samuel Gudi",
    "github_login": "samuelgudi",
    "github_id": 12345678
  },
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
  "composes":      [],
  "extends":       null,
  "supersedes":    [],
  "superseded_by": null,
  "related_skills": []
}
```

`author.github_id` is recorded at first-PR time by CI fetching `gh api users/<login>`. Contributors do not need to look it up manually — the `agent-skills submit` flow handles it.

`versions` is NOT in `meta.json` — it's a derived field in `registry.json` only, computed from git history by `generate_manifest.py`.

### `scripts/`

- Pure Python, Bash, or Node. Language declared in SKILL.md body.
- **No package-manager installs at runtime** (Gemini B1, Decision #14). Runtime deps go in `meta.json.requires.commands` and must be installed by the user/host before invocation.
- No network calls at install time. Only at invoke time, only as documented.
- `security_scan.py` walks every file here.
- `${SKILL_DIR}` substituted at invoke time, not install time.

### `templates/`

- Plain text or markdown. No executable content.

### `README.md`

Optional. Human-facing. Not consumed by agents.

## 9. Top-level CLI + discovery client

### One binary: `agent-skills`

| Verb | Purpose | Pattern |
|---|---|---|
| `search <query>` | Find skills | `agent-skills search spotify song` |
| `show <id>` | Detail on one skill | `agent-skills show samuelgudi/spotify-search` |
| `install <id>[@version]` | Install for current host (latest non-yanked by default) | `agent-skills install spotify-search@0.1.0` |
| `uninstall <id>` | Remove from current host | `agent-skills uninstall spotify-search` |
| `verify <id>` | Check installed skill against registry hash | `agent-skills verify spotify-search` |
| `list` | Show installed skills (current host; `--agent` overrides) | `agent-skills list` |
| `update` | Force registry-cache refresh | `agent-skills update` |
| `submit <local-dir>` | Propose a new skill or new version | `agent-skills submit ./my-skill/` |
| `issue <id>` | Open improvement issue | `agent-skills issue samuelgudi/spotify-search` |
| `deprecate <id> --in-favor-of <new-id>` | Propose deprecation PR (soft) | — |
| **`yank <id>@<version> --reason "..."`** | **Propose yank PR (hard, no install)** | `agent-skills yank samuelgudi/spotify-search@0.1.1 --reason "..."` |

### Flags

- `--agent <name>` — override host auto-detection (defaults to detected). Supported by all verbs including `list`.
- `--category <c>` / `--tag <t>` / `--platform <p>` — filter
- `--limit <N>` — search result count (default 5)
- `--json` — machine-readable output
- `--yes` — skip confirmation prompts (consistent across all interactive verbs)
- `--scope=user|project` — Claude Code install scope
- `--include-archived` — include deprecated skills in search/show output
- **`--allow-deprecated`** — required to install a deprecated version (soft).
- **`--allow-yanked` does NOT exist.** Yanked versions cannot be installed at any flag (Gemini M3).

### Version pinning resolution (v3, Gemini M1)

`agent-skills install <id>@<version>` workflow:

1. Look up `registry.json.skills[id].versions[version]`.
2. If absent → "Version 0.1.0 not found. Available: 0.1.1 (yanked), 0.2.0."
3. If `yanked: true` → "Version 0.1.1 was yanked on 2026-05-12: <reason>. Use --version <safe-version> to pin a non-yanked release." Hard refuse, exit non-zero.
4. Otherwise read `versions[version].sha`, do a shallow `git fetch` + `git read-tree` at that SHA to materialize the skill files at the correct historical state.

No git-log walk. No history scan. O(1) lookup + O(version files) fetch.

`agent-skills install <id>` without `@<version>` installs the latest non-yanked version (typically `registry.json.skills[id].version`).

### Search UI (TTY)

```
$ agent-skills search spotify
Searching 47 skills (cache 2h old, refreshing)…

  ★ 1  samuelgudi/spotify-search                v0.2.0
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

### Search JSON (agents)

```json
{
  "query": "spotify song",
  "filters": { "agent": "claude-code" },
  "candidates": [
    {
      "id": "samuelgudi/spotify-search",
      "score": 0.87,
      "version": "0.2.0",
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

samuelgudi/spotify-search  v0.2.0  (MIT, by samuelgudi)

  Search Spotify by track, artist, or album using the Web API.

  Files to install:
    SKILL.md                     1.2 KB
    scripts/search.py            3.4 KB
    templates/result-format.md   0.8 KB
    meta.json                    0.6 KB

  Target:  ~/.claude/skills/samuelgudi-spotify-search/   (claude-code)
       or  ~/.hermes/skills/media/spotify-search/        (hermes)

  Requires (set before invoking):
    SPOTIFY_CLIENT_ID            not set
    SPOTIFY_CLIENT_SECRET        not set

Proceed? [y/N]: y

  Fetching git tree abc333000… from origin…
  Verifying content_hash sha256:abc123…  ok
  Writing:
    + <target>/SKILL.md
    + <target>/scripts/search.py
    + <target>/templates/result-format.md
    + <target>/meta.json
    + <target>/.agent-skills-marker.json

Installed v0.2.0. On Hermes: run /reload-skills or start a new session.
Uninstall: agent-skills uninstall spotify-search
```

### Install on a yanked version

```
$ agent-skills install spotify-search@0.1.1

samuelgudi/spotify-search v0.1.1 was YANKED on 2026-05-12 by samuelgudi.
Reason: Compromised upstream dependency in scripts/search.py; users must upgrade to 0.2.0+.

Yanked versions cannot be installed. No override flag exists.
Available non-yanked: 0.1.0, 0.2.0.

Try: agent-skills install samuelgudi/spotify-search@0.2.0
```

### Uninstall UI

```
$ agent-skills uninstall spotify-search

samuelgudi/spotify-search  v0.2.0  (installed in claude-code)

  Target:  ~/.claude/skills/samuelgudi-spotify-search/

  Files to remove:
    SKILL.md
    scripts/search.py
    templates/result-format.md
    meta.json
    .agent-skills-marker.json

  Drift check: ok (files match registry source.content_hash)

Proceed? [y/N]: y
  Removed ~/.claude/skills/samuelgudi-spotify-search/
Done.
```

### Yank UI

```
$ agent-skills yank samuelgudi/spotify-search@0.1.1 --reason "Compromised upstream dependency"

Yanking a published version is irreversible (only a separate explicit PR can unyank).

  Skill:    samuelgudi/spotify-search
  Version:  0.1.1 (released 2026-05-10)
  Reason:   Compromised upstream dependency

This will:
  1. Append to yanks.json
  2. Open a PR titled "Yank samuelgudi/spotify-search@0.1.1"
  3. Once merged, all clients refusing to install this version on next cache update

Proceed? [y/N]: y
PR opened: https://github.com/samuelgudi/agent-skills/pull/89
```

After merge, `agent-skills update` propagates the yanked flag; subsequent `install <id>@0.1.1` attempts hard-refuse. `agent-skills verify <id>` on an already-installed yanked version surfaces a red warning and recommends `uninstall`.

### Match-scoring algorithm

```
score = 0.45 * name_token_match
      + 0.40 * description_token_match
      + 0.15 * tag_token_match
```

Each component: Jaccard overlap weighted by IDF, with length normalization. Filters apply before scoring. Ties broken by (1) higher version, (2) more recent merge timestamp, (3) lexical id order.

**Anti-stuffing (partial fold of Gemini m1)**:
- Tags capped at 10 entries (enforced in `validate.py`).
- Descriptions with > 500 chars get a length penalty in the score (full-score cap stays).

### Discovery cache

- `~/.cache/agent-skills/registry.json`
- `~/.cache/agent-skills/registry.json.sig` (optional in v0; loud warning when unsigned)
- `~/.cache/agent-skills/idf.json`
- `~/.cache/agent-skills/installed.json`

### `update.py`

Fetches `registry.json` + `yanks.json` from the configured remote. Verifies sha256 against `registry.json.sig` when signing is enabled. Atomic write. Refuses overwrite if fetched `generated_at` is older than cached (rollback-attack guard).

### `clients/skill-discovery/SKILL.md`

```markdown
---
name: skill-discovery
description: Query the agent-skills registry for a skill that matches the current task. Use ONLY when explicitly asked to search for a skill. Do not invoke reflexively for every task.
---
```

## 10. Contribution pipeline

`agent-skills submit <local-dir>` walks five blocking steps. Failure at any step halts the flow.

### Step 1 — Validate structure (`validate.py`)

- Required files present (`SKILL.md`, `meta.json`).
- Frontmatter parses; `name` and `description` match `meta.json`.
- `id` well-formed; slug grammar matches.
- All required `meta.json` fields present, including `author.github_login` and `author.github_id`.
- License is a valid SPDX identifier.
- `category` in fixed taxonomy.
- `tags` count ≤ 10.
- **First-PR for a new author**: CI fetches `gh api users/<github_login>` and records the `id`. The PR must declare `author.github_id` matching the fetched id (the `agent-skills submit` CLI does this automatically).
- **Subsequent PR for existing author**: CI re-fetches the current id for `<github_login>`. Asserts it matches the previously-recorded `github_id`. Mismatch → block with notice (M2).
- Same-slug collision check across authors (m8 from v2).
- No nested git repos.
- No extraneous files.
- Cycle detection across `composes` / `extends` / `supersedes` / `superseded_by`.

Hard fail on missing required fields. No `--force`.

### Step 2 — Sanitize paths and secrets (`sanitize.py`)

Same rules as v2 (see § 10 v2 table; preserved as-is). Includes SKILL.md body scan for prompt-injection patterns (warning, surfaced in REVIEW.md).

`SANITIZATION.diff` generated **after** sanitization completes (m12).

### Step 3 — Security scan (`security_scan.py`)

Scans `scripts/` and `templates/`. Does NOT scan SKILL.md body (sanitize.py's domain).

**Hard blocks** (no override in v0). Rules in `scripts/rules.yaml`:

| Rule ID | Detects | Language | Notes |
|---|---|---|---|
| `PY-EVAL-CALL` | Python `eval` identifier followed by `(` | python | code execution |
| `PY-EXEC-CALL` | Python `exec` identifier followed by `(` | python | code execution |
| `JS-FUNCTION-CTOR` | JS `Function` constructor invocation | javascript | dynamic eval |
| `PY-SHELL-INTERP` | `subprocess` with `shell=True` + non-literal args | python | command-injection |
| `SH-CURL-PIPE` | `curl` or `wget` piped into a shell interpreter | all | remote-to-shell |
| `B64-PAYLOAD` | quoted base64 string ≥50 chars | all | obfuscated payload |
| `NET-IN-ADAPTER` | network primitives inside `adapters/` | python | install must be offline |
| **`PKG-INSTALL` (v3)** | **package-manager install commands**: `pip install`, `npm install`, `gem install`, `cargo install`, `apt install`, `apt-get install`, `brew install`, `go install`, `pnpm install`, `yarn add`, `pipx install`, `uv install`, `dnf install`, `yum install`, `apk add`, etc. | **all** | **external code at runtime breaks the registry's security gate; declare deps in `meta.json.requires.commands` and require the user/host to install them beforehand (Gemini B1)** |

> **v3 change (Gemini B1)**: The `PKG-INSTALL` rule closes the event-stream / dependency-confusion vector. A script-bearing skill cannot pull external code at runtime that an attacker could swap post-merge. If a skill genuinely needs an external tool, it declares it in `meta.json.requires.commands` and the user installs it manually before invoking the skill. This is the same discipline as Homebrew formula audits requiring SHA-pinning for external fetches.

> **Why not `--hash`-pinned package installs?** Hash-pinning support is uneven across package managers (pip has it, npm only via lockfiles, gem has no equivalent). Detecting "is this install hash-pinned?" via static regex is brittle. The clean rule — **declare deps, don't install** — is detectable and enforceable.

**Soft warnings** (proceed, recorded in REVIEW.md):

| Rule ID | Detects | Notes |
|---|---|---|
| `PY-SUBPROCESS-USE` | any `subprocess.` reference | declare commands in `meta.json.requires.commands` |
| `FS-WRITE-OUTSIDE-SKILL` | filesystem writes outside `${SKILL_DIR}/cache/` | recorded in REVIEW.md |
| `UNDECLARED-CMD` | external binary used but not declared in `requires.commands` | |
| `NET-IN-SCRIPT` (v3) | network primitives in `scripts/` (runtime calls) | acceptable for skills like Spotify search; recorded in REVIEW.md with explicit endpoint disclosure |

> **v3 addition**: `NET-IN-SCRIPT` is a soft warning, not a block — many legitimate skills make API calls (the Spotify search example). The discipline is: surface every endpoint in REVIEW.md's "What does it access? → Network endpoints" field. Reviewer cross-checks claimed endpoints against actual script calls.

**Output format:**

```
scripts/search.py
  line 42  BLOCK  PY-SHELL-INTERP  subprocess with shell=True and non-literal args
  line 67  WARN   PY-SUBPROCESS-USE  declare in meta.json.requires.commands
  line 91  WARN   NET-IN-SCRIPT  network call to api.spotify.com (declare in REVIEW.md)

templates/result-format.md
  clean

1 block, 2 warnings. Cannot proceed.
```

### Step 4 — Self-review (REVIEW.md)

Six fields (five for first-version submissions):

```markdown
# REVIEW.md

## What does this skill do?
(1-2 sentences)

## What does it access?
- Network endpoints: (every endpoint reachable from scripts/, even via libraries)
- Filesystem paths written:
- Env vars read:
- Processes spawned:
- (If has_scripts: true, EVERY capability above is mandatory.)

## Worst case if it misbehaves?
(concrete; not hand-wavy)

## Why is this useful?
- What task it solves:
- What existing skill DOES NOT already solve it (gap-check):

## Test evidence
- Commands run manually before submitting:
- Outputs:
- (For has_scripts: true skills, REAL test evidence is MANDATORY.)

## What changed from previous version (skill updates only)
- Breaking changes:
- New capabilities:
- Removed capabilities:
```

### Step 5 — Open PR (`submit.py`)

Same as v2 with one addition: PR body now includes the GitHub-ID verification result ("First-PR for new author; recorded github_id=12345678" or "Subsequent PR; github_id matches recorded").

### Path B — `agent-skills issue <skill-id>`

Same as v2.

### Update flow (new version of existing skill)

Same as v2. The `submit` flow auto-fetches the author's current `github_id` and asserts match against `meta.json.author.github_id` before opening the PR.

### Deprecation flow (obsolescence — soft)

`agent-skills deprecate <id> --in-favor-of <new-id>` sets `status: "deprecated"` + `superseded_by`. Moves files `skills/<author>/<slug>/` → `archive/<author>/<slug>/`.

Behavior:
- `match.py` excludes by default; `--include-archived` surfaces with `[DEPRECATED → <new-id>]`.
- `agent-skills install <deprecated-id>` refuses by default; `--allow-deprecated` overrides.
- `agent-skills verify <id>` on an installed deprecated skill emits migration hint.

### Yank flow (compromise — hard, v3)

`agent-skills yank <id>@<version> --reason "..."` appends an entry to `yanks.json` and opens a PR.

Behavior:
- `match.py`: yanked versions never returned; latest non-yanked version surfaces for the skill.
- `agent-skills install <id>@<version>` for yanked version: hard refuse, **no override flag**.
- `agent-skills install <id>` (no version pin): yanked latest version skipped; CLI installs the latest non-yanked one. If ALL versions are yanked, hard refuse with a strong recommendation to use `--include-archived` only if user wants to manually inspect (not install) the source.
- `agent-skills verify <id>` on an installed yanked version: loud red warning, recommends `uninstall`.

### CI re-runs every check

`.github/workflows/ci.yml`:
1. `validate.py --all --strict` (includes github_id check)
2. `security_scan.py --all`
3. `generate_manifest.py --check`
4. `pytest tests/ -v`
5. (contribution PRs only) `SANITIZATION.diff` consistency + REVIEW.md presence + capability/test-evidence requirements for has_scripts PRs.

For yank PRs specifically: CI verifies that the yanked version exists in `versions` and that `yank_reason` is non-empty.

### On-merge workflow

`.github/workflows/on-merge.yml`:
1. Move `submitted/pr-<NNN>/<author>/<slug>/` → `skills/<author>/<slug>/` (or `archive/` for deprecation; no move for yank PRs).
2. Run `generate_manifest.py` → recompute `source.content_hash`, build `versions` map from git log, merge yanks.json into versions, set `provenance`.
3. Commit `[automerge] Add <id>@<version>` / `[automerge] Deprecate <id>` / `[automerge] Yank <id>@<version>`.
4. Tag release if a new minor/major version was published.

## 11. `scripts/validate.py` details

**Inputs:**

```bash
validate.py <skill-dir>             # validate one skill
validate.py --all                   # walk skills/ and archive/
validate.py --strict                # treat warnings as errors (CI mode)
validate.py --json
```

**Schema source of truth**: `SCHEMA.md` + `scripts/schema.json`. Test asserts they stay in sync.

**Validation checks (v3, additions in bold):**

- `id` matches directory path.
- Frontmatter `name` and `description` match `meta.json`.
- **`author.github_id` matches the current GitHub API result for `author.github_login`** (Gemini M2). CI fetches via `gh api users/<login>` once per PR.
- If `status == "deprecated"`, `superseded_by` references an existing active skill.
- Same-slug collision across authors (warning surfaced in PR comment).
- No nested git repos (recursive into scripts/, templates/).
- No extraneous files.
- Cycle detection across `composes` / `extends` / `supersedes` / `superseded_by`.
- **`tags` count ≤ 10** (Gemini m1 partial fold).
- License is a valid SPDX identifier.
- **For yank PRs**: target version exists in `versions`; `yank_reason` is non-empty (Gemini M3).

**Exit codes:** `0` clean · `1` errors · `2` warnings only.

## 12. `scripts/security_scan.py` details

Patterns declared in `scripts/rules.yaml`. See § 10 table for the v0 rule set including the v3 addition `PKG-INSTALL` (hard-block) and `NET-IN-SCRIPT` (soft-warn).

**Scope:**
- **In scope**: every file under `scripts/` and `templates/`.
- **Out of scope**: `SKILL.md` body (sanitize.py's domain).

**Rule shape:**

- `id`: stable identifier
- `severity`: `block` or `warn`
- `pattern`: regex string (or list of regexes for rules with many command names like `PKG-INSTALL`)
- `languages`: list of language tags
- `scope`: optional glob
- `message`: human-readable description
- `fix_hint`: actionable remediation

For `PKG-INSTALL` specifically, the rule expands to a regex alternation over the documented package-manager invocations. Adding new package managers is a PR against `rules.yaml`.

## 13. `scripts/generate_manifest.py` details

**Inputs:**

```bash
generate_manifest.py                # rebuild registry.json
generate_manifest.py --check        # exit 1 if registry.json doesn't match regenerated output
```

**Algorithm:**

1. Walk `skills/` and `archive/`. For each skill:
   - Load `meta.json`.
   - Read `name` and `description` from SKILL.md frontmatter.
   - Build `source.path`, `source.files`, `source.content_hash` (sha256 over deterministic concatenation of `<relpath>\0<sha256(file_contents)>` per file, joined by newline). Covers entire directory.
   - **Build `versions` map by walking `git log --diff-filter=AM --format=%H -- <skill-dir>/meta.json` and, for each commit, extracting the `version` field from `meta.json` at that commit** (Gemini M1). For each unique semver seen:
     - `sha`: the git tree SHA of the skill-dir at that commit.
     - `released`: committer date of that commit (ISO 8601).
   - `has_scripts` derived from filesystem.
   - `provenance` from git: last merge commit affecting the dir.
2. **Load `yanks.json`. For each yank entry, set `registry.json.skills[id].versions[version].yanked = true` and `yank_reason = ...`** (Gemini M3).
3. Sort skills by `id`.
4. `generated_at` = current commit timestamp (not wall clock).
5. Write `registry.json`.

`--check` mode regenerates in tmpdir; byte-compares; exit 1 with diff on mismatch.

## 14. Per-agent adapters

### Common adapter contract

```python
class Adapter(ABC):
    name: str

    @abstractmethod
    def detect(self) -> bool: ...

    @abstractmethod
    def target_dir(self, skill_id: str, category: str, *, scope: str = "user") -> Path: ...

    @abstractmethod
    def install(self, src_dir: Path, skill_id: str, version: str, meta: dict, opts: dict) -> InstallResult: ...

    @abstractmethod
    def uninstall(self, skill_id: str) -> UninstallResult: ...

    @abstractmethod
    def list_installed(self) -> list[Installed]: ...

    @abstractmethod
    def verify(self, skill_id: str, registry_hash: str, yanked: bool, yank_reason: str | None) -> VerifyResult: ...
```

> **v3 change**: `verify()` receives `yanked` and `yank_reason` from the registry. If the installed version is yanked, the result includes a `red_alert: true` flag and the reason; UI surfaces this prominently regardless of hash-match result.

### Shared install mechanics

1. **Resolve version**: if `@<version>` provided, look up `versions[version]` in `registry.json`. If yanked → hard refuse. If absent → error.
2. Stage: fetch git tree at `versions[version].sha`, materialize files to temp dir.
3. Verify: recompute content_hash from the materialized files, compare against the registry's published hash for that version (recompute from the same tree if needed; the marker is informational only).
4. **For Hermes only**: synthesize the host frontmatter.
5. Write marker `.agent-skills-marker.json`:

```json
{
  "id": "samuelgudi/spotify-search",
  "version": "0.2.0",
  "installed_at": "2026-05-11T15:00:00Z",
  "installed_by": "agent-skills v0.1.0",
  "registry_content_hash": "sha256:abc…",
  "source_url": "github.com/samuelgudi/agent-skills@abc333000",
  "tree_sha": "abc333000…"
}
```

6. Atomic move temp → final target. Rollback on mid-install failure.

### `adapters/claude_code.py`

- Detect: `~/.claude/` exists.
- Target dir (user): `~/.claude/skills/<author>-<slug>/`. Project (`--scope=project`): `<cwd>/.claude/skills/<author>-<slug>/`.
- Frontmatter pass-through (`name`, `description`, optionally `model`, `allowed-tools`).
- Activation: Claude Code re-scans skills at next session start.

### `adapters/hermes.py`

- Detect: `~/.hermes/` exists.
- Target dir: `~/.hermes/skills/<category>/<slug>/`. Category from `meta.json.category`.
- Frontmatter synthesis from `meta.json`:

```yaml
---
name: <slug>
description: <from registry SKILL.md>
version: <meta.json.version>
author: <meta.json.author.name> (<meta.json.author.github_login>)
license: <meta.json.license>
platforms: <meta.json.platforms>
prerequisites:
  env_vars: <meta.json.requires.env_vars>
  commands: <meta.json.requires.commands>
metadata:
  hermes:
    tags: <meta.json.tags>
    related_skills: <meta.json.related_skills>
---
```

- No `plugin.py` emission.
- Activation: user runs `/reload-skills` or starts new Hermes session.

### Conflict handling

- Target exists with marker, same version → reinstall prompt.
- Target exists with marker, different version → upgrade prompt.
- Target exists, **no marker** → hard refuse.

### Drift detection (`agent-skills verify <id>`)

1. Recompute content_hash of installed files.
2. Fetch the current registry's `source.content_hash` for `<id>` (or recompute from `versions[installed_ver].sha` if installed_ver != latest).
3. Compare installed-file hash to registry hash (NOT to marker).
4. Check `versions[installed_ver].yanked`: if true, raise red alert with `yank_reason` regardless of hash.

Outcomes:
- Clean.
- Local drift.
- Marker outdated (newer non-yanked version exists).
- **YANKED installed version** (v3 alert): "Installed version 0.1.1 was yanked: <reason>. Recommend `agent-skills uninstall` and install a non-yanked version."
- Deprecated installed skill (m5).
- Tampered files (marker hash doesn't help — registry hash is the trust anchor).

### Auto-detection logic

Unchanged from v2.

## 15. Testing strategy

### Layout

```
tests/
├── fixtures/
│   ├── good/
│   │   ├── instructions-only/
│   │   ├── with-scripts/
│   │   ├── with-templates/
│   │   ├── deprecated/
│   │   ├── multi-agent/
│   │   └── multi-version/             # v3: skill with versions 0.1.0, 0.2.0
│   └── bad/
│       ├── slug-with-uppercase/
│       ├── slug-path-traversal/
│       ├── missing-license/
│       ├── deprecated-no-successor/
│       ├── deprecated-cycle/
│       ├── composes-cycle/
│       ├── extends-cycle/
│       ├── same-slug-collision/
│       ├── frontmatter-mismatch/
│       ├── extraneous-file/
│       ├── nested-git/
│       ├── nested-git-in-scripts/
│       ├── pkg-install-pip/           # v3 (Gemini B1)
│       ├── pkg-install-npm/           # v3
│       ├── pkg-install-apt/           # v3
│       ├── github-id-mismatch/        # v3 (Gemini M2)
│       ├── tag-cap-exceeded/          # v3 (Gemini m1)
│       └── yank-no-reason/            # v3 (Gemini M3)
├── test_validate.py
├── test_security_scan.py              # v3: covers PKG-INSTALL across all package managers
├── test_generate_manifest.py          # v3: covers versions map construction + yanks.json merge
├── test_match.py
├── test_update.py
├── test_sanitize.py
├── test_submit.py                     # v3: covers github_id record + verify-on-subsequent-PR
├── test_yank.py                       # v3: covers yank PR creation, version refuse, no override
├── test_adapter_claude_code.py
├── test_adapter_hermes.py
├── test_uninstall.py
├── test_verify_drift.py
├── test_verify_yanked.py              # v3: verify on yanked installed version raises red alert
├── test_cli.py
├── test_schema_sync.py
└── conftest.py
```

### Principles

Same as v2: no mocks for the system under test; adversarial inputs; false positives matter; determinism tested; marker-forgery defense tested.

**New in v3**:
- **PKG-INSTALL detection across package managers**: every package manager named in § 10 has its own bad fixture asserting the rule fires.
- **GitHub ID re-registration attack simulation**: a test fixture stages a `meta.json` with `github_login: "samuelgudi", github_id: 12345678` and a fake `gh api users/samuelgudi` response returning `id: 99999999` (simulating username re-registration); `validate.py --strict` must fail.
- **Yank end-to-end**: `agent-skills yank` opens PR; on merge, `versions[ver].yanked = true`; subsequent `install <id>@<ver>` hard-refuses with no override flag accepted.
- **Version pinning resolution**: a multi-version fixture; `install @0.1.0` materializes the v0.1.0 tree (NOT the latest); content_hash matches what registry.json records for that version.

### Adversarial test cases (sample, v3 additions)

- A skill with `scripts/install_deps.sh` calling `apt-get install python3-attacker-mirror` — caught by `PKG-INSTALL`.
- A skill that pip-installs in a Python script via subprocess — also caught by `PKG-INSTALL` (regex covers the command pattern, not just shell-form).
- A meta.json declaring `author.github_login: "samuelgudi"` but `author.github_id` not matching the current GitHub API result — caught by `validate.py`.
- An installed yanked skill: `agent-skills verify` returns red-alert with yank_reason; `agent-skills install @<yanked_ver>` refuses regardless of any flag.

### CI matrix

Unchanged from v2.

## 16. CI workflows

### `.github/workflows/ci.yml`

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
- `SANITIZATION.diff` consistency check.
- REVIEW.md presence + 6-field completeness for updates / 5 for first-version.
- For `has_scripts: true`: capability enumeration check + real test evidence check.
- **GitHub-ID verification** (v3): fetch `gh api users/<author.github_login>`, assert match against `meta.json.author.github_id`. Block on mismatch with a clear message.
- Yank PR validation: target version exists in versions; reason non-empty.

### `.github/workflows/on-merge.yml`

- Move `submitted/pr-<NNN>/` → `skills/` / `archive/` / (no move for yank PRs).
- Run `generate_manifest.py` (builds versions map, merges yanks.json).
- Commit + tag release if version warrants.

## 17. Out of scope for v0

- Learned curation policies (SkillOS-style trainable curator).
- Plugin support (Hermes plugins = Python entry points in `~/.hermes/plugins/`; separate trust tier).
- Telemetry / usage signal collection.
- Multi-author skills.
- Semantic / vector search. Pure keyword scoring degrades past ~30 skills; mitigated by CONTRIBUTING.md authoring guideline + tag cap.
- Hard-block override flag.
- Auto-merge for low-risk PRs.
- Skill mirroring across federated registries.
- Per-agent skill marketplaces.
- Embeddings backend for `match.py` (v0.x — same CLI surface, swapped internals).
- `agent-skills supersede <old-id> --with <forked-skill>` fork-and-improve workflow (deferred, MILO m10).
- **Anti-spam ranking heuristics beyond the tag cap** (Gemini m1 partial fold). Description-length penalty exists; deeper spam-fighting (bayesian filtering, contributor reputation scoring) is post-v1.
- **Verified-publisher signals** (`verified: true` flag for trusted contributors). Only meaningful at multi-org scale (Gemini m2).

## 18. Forward compatibility notes

### SkillOS paper (arxiv 2605.06614)

Already covered in v2; no change in v3.

### Schema-version bumps reserved for

- Removing fields.
- Changing field semantics.
- Introducing required fields.

> **v3 bump**: schema_version goes 1 → 2 because `author.github_id` and `versions` are new required fields. v3 ships with a one-time migration helper in `scripts/migrate_v1_to_v2.py` that fetches GitHub IDs for existing skills and rebuilds the versions map from git history.

## 19. Open decisions deferred to v0.x

- Reflexive skill-discovery invocation (false-positive rate measurement).
- Override mechanism for hard security blocks (on first legit use case).
- Signing infrastructure (`registry.json.sig` + key distribution).
- pipx / PyPI publication of `agent-skills` CLI.
- Plugin trust tier (v1+).
- Semantic / vector search backend.
- `agent-skills supersede` workflow (MILO m10).
- **Anti-spam ranking heuristics** beyond tag cap (Gemini m1).
- **Verified-publisher signals** (Gemini m2).
- **Unyank workflow**: removing an entry from yanks.json requires an explicit PR with documented justification. Procedure (who approves, what evidence) needs design.
- **Ownership transfer between GitHub accounts**: when a contributor legitimately wants to hand over `<author>/*` to a new GitHub account. Currently github_id mismatch hard-blocks; needs an explicit "ownership transfer" PR shape.

## 20. Build sequence (preview for the implementation plan)

1. Skeleton repo: SCHEMA.md, SECURITY.md, CONTRIBUTING.md, schema.json (v2), rules.yaml (incl. PKG-INSTALL), empty registry.json, empty yanks.json.
2. `validate.py` + fixtures + tests — schema layer + github_id check + tag cap + cycle detection.
3. `security_scan.py` + rules.yaml + PKG-INSTALL coverage + fixtures + tests.
4. `generate_manifest.py` + versions-map construction from git log + yanks.json merge + tests.
5. Adapter base + `claude_code.py` + tests.
6. Adapter `hermes.py` + tests.
7. Top-level `agent-skills` CLI: detect, search, show, list (--agent), verify (yanked-aware), uninstall.
8. **Version pinning resolution** (`install <id>@<ver>` via versions map) + tests.
9. `update.py` + cache + tests.
10. `sanitize.py` + `diff.py` + tests.
11. `submit.py` + fake-gh fixture + GitHub-ID fetch path + tests.
12. **`yank.py`** + tests (full end-to-end: yank PR → merge → versions[ver].yanked=true → install refusal).
13. `issue` verb + tests.
14. CI workflows.
15. Seed skills (2–3 instruction-only).
16. README + CONTRIBUTING (with skill-description guideline) + SECURITY (with yank procedure) hardening pass.

## 21. Changelog — v1 → v2 (MILO findings)

(Preserved verbatim from v2.)

### BLOCKER

| MILO ID | Section(s) | Change |
|---|---|---|
| B1 | § 6, § 9, § 14 | Hermes install target_dir changed to `~/.hermes/skills/<category>/<slug>/`. |
| B2 | § 9, § 14 | Removed "hot-reload" claim; documented `/reload-skills` or new session. |
| B3 | § 8, § 14 | Registry SKILL.md keeps minimal frontmatter; Hermes adapter synthesizes full block at install. |
| B4 | § 7, § 14 | Removed `plugin.py` emission and `emit_plugin` flag. |

### MAJOR

| MILO ID | Section(s) | Change |
|---|---|---|
| M1 | § 14 | Hermes adapter translates `requires.env_vars/commands` → `prerequisites.*`. |
| M2 | § 14 | Hermes adapter translates `platforms` → frontmatter `platforms:`. |
| M3 | § 14, § 11 | `verify()` compares against registry hash, not local marker. |
| M4 | § 4 (#5), § 10 | Single-tier reversed: scripts-bearing skills get stricter REVIEW.md + mandatory test evidence. |
| M5 | § 9, § 17 | Match-keyword limitation documented; CONTRIBUTING.md authoring guideline. |
| M6 | § 10, § 12 | `sanitize.py` scans SKILL.md body for prompt-injection patterns. |
| M7 | § 9 | Uninstall section added (was missing). |

### MINOR

12 of 14 folded; 2 deferred (m2 retained, m10 deferred to v0.x).

## 22. Changelog — v2 → v3 (Gemini findings)

### BLOCKER

| Gemini ID | Section(s) | Change |
|---|---|---|
| B1 | § 4 (#14), § 8 (scripts), § 10, § 12, § 15 | **New `PKG-INSTALL` hard-block rule.** Covers `pip install`, `npm install`, `gem install`, `cargo install`, `apt(-get) install`, `brew install`, `go install`, `pnpm install`, `yarn add`, `pipx install`, `uv install`, `dnf install`, `yum install`, `apk add`. Runtime dependencies must be declared in `meta.json.requires.commands` and installed by user/host beforehand. Closes the event-stream / dependency-confusion vector. Companion soft-warn `NET-IN-SCRIPT` added so legitimate API-calling skills are surfaced in REVIEW.md without being blocked. |

### MAJOR

| Gemini ID | Section(s) | Change |
|---|---|---|
| M1 | § 4 (#11), § 7 (versions field), § 9 (install pinning UI), § 13 (generate_manifest algorithm), § 14 (install resolution), § 15 (tests) | **New required `versions: {<semver>: {sha, released, yanked?, yank_reason?}}` map in `registry.json`.** Built by `generate_manifest.py` walking git log per skill. Enables O(1) `agent-skills install <id>@<version>` resolution; no history scan, supports shallow checkout via git tree SHA. |
| M2 | § 4 (#4), § 6 (identity), § 7 (author.github_id), § 8 (meta.json), § 11 (validate.py CI check), § 15 (test fixture), § 22 (schema_version bump) | **GitHub username recycling defense.** `author` now contains both `github_login` (display) and `github_id` (immutable numeric, the actual identity anchor). CI fetches `gh api users/<login>` on every PR and asserts the current id matches the recorded `github_id`. Mismatch → hard-block. Prevents namespace hijacking via account deletion + re-registration. |
| M3 | § 4 (#10), § 7 (versions[ver].yanked), § 9 (yank verb + install refusal UI), § 10 (yank flow), § 13 (yanks.json merge), § 14 (verify yanked-aware), § 15 (test_yank + test_verify_yanked) | **Distinct yank semantics for compromised versions.** Separate from `status: "deprecated"` (obsolescence, soft). `yanked: true` on per-version entries triggers hard-refuse install with **no override flag**. `agent-skills yank <id>@<version> --reason "..."` opens a yank PR; `yanks.json` at the registry root records the operational decisions; `generate_manifest.py` merges them into `registry.json.skills[].versions`. Verify on installed yanked skill raises red alert. |

### MINOR

| Gemini ID | Section(s) | Change |
|---|---|---|
| m1 | § 4 (#3), § 7 (tags ≤ 10), § 9 (description length penalty), § 11 (validate) | **Partial fold**: tag count cap of 10 enforced; description length > 500 chars penalized in match score. Deeper anti-spam heuristics deferred (§ 19). |

### Deferred to v0.x

| Gemini ID | Disposition |
|---|---|
| m2 (verified publisher) | Deferred to v0.x (§ 19). Only meaningful at multi-org scale; single-reviewer Samuel v0 doesn't need the signal. |

### What Gemini confirmed was right (no change)

- Flat-file git registry avoids the complexity and attack surface of a running API service.
- Per-agent adapters correctly acknowledge that execution environments are not cleanly standardizable.
- Deferring `registry.json.sig` with a loud warning matches early-npm / early-PyPI pragmatism — honest tradeoff, not negligence.
- Using GitHub PRs for the contribution pipeline leverages existing identity + review tooling (mirrors Homebrew taps).

---

End of spec v3.
