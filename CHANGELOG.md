# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.9] — 2026-07-17

Security-hardening release. An internal review of the trust model found five weaknesses — none known-exploited, all closed here. Also the release where the first **external** skill landed: `kriptoburak/hermes-tweet` v0.1.6, the first submission to travel the full cross-fork PR → CI → on-merge promotion path (registry now at 10 skills).

### Security

- **`security_scan.py` now scans skill markdown** (`scripts/security_scan.py`, `scripts/rules.yaml`). SKILL.md — the file loaded verbatim into an agent's context — was previously unscanned; only `scripts/` and `templates/` were. Five new markdown rules: `MD-EXFIL-INSTRUCTION` (credential path + network endpoint on one line, block), `MD-PROMPT-OVERRIDE` (ignore-previous-instructions phrasing, block), `MD-HIDDEN-COMMENT` (HTML comments — invisible in rendered review, block), `MD-INVISIBLE-UNICODE` (zero-width/bidi characters, block), `MD-B64-PAYLOAD` (long base64-like strings, warn). `SH-CURL-PIPE` now also fires in markdown.
- **CI re-validates and re-scans every submission** (`.github/workflows/ci.yml`). The contribution PR gate now runs `validate.py` and a **fresh** `security_scan.py` against the submitted skill tree instead of trusting the submitter-provided `scan_results.json` alone.
- **Promotion is gated** (`.github/workflows/on-merge.yml`). Before any `submitted/` tree is moved into `skills/` and pushed, the workflow enforces the id grammar and runs `validate.py` + `security_scan.py` — a PR gate can be bypassed; promotion cannot.
- **Skill ids are validated before any path is built** (`adapters/_base.py::split_skill_id`). All six adapters derived install/uninstall paths from a raw `skill_id.split("/")` — an id like `author/../../../x` escaped the skills directory. Ids must now match the registry grammar (same regex as `validate.py`), enforced centrally.
- **`kfu uninstall` cross-checks the marker's id** (`adapters/_base.py::checked_uninstall`). Every adapter now refuses to remove a directory whose marker belongs to a different skill than the one named on the command line (previously only the hermes adapter checked).
- **`generate_manifest.py` refuses malformed directory names.** A directory that violates the `<author>/<slug>` grammar can no longer be baked into `registry.json`.

### Fixed

- **`atomic_install` no longer has a delete-then-move window** (`adapters/_base.py`). On reinstall the old tree is moved aside, the new tree moves in, then the old is discarded — an interruption (Ctrl-C, crash, power loss) now leaves either the old or the new install on disk, never neither.
- **`security_scan.py` decodes rules and prints findings as UTF-8 on Windows.** `rules.yaml` was read with the legacy console codepage (cp1252), which crashed on non-ASCII rule text; stdout is likewise reconfigured.

### Changed

- **Meta-skills at 0.2.0** *(retroactive record — shipped in commit `7eae805` after v0.1.8 without a changelog entry)*: `iknowkungfu-discovery` and `iknowkungfu-contribution` expanded from pointer-style docs to runbook depth.

27 new regression tests (494 total): markdown scanner rules, traversal ids, marker mismatch, interrupted-install rollback, malformed-manifest refusal, promotion gating.

---

## [0.1.8] — 2026-05-14

UX-polish release. Seven friction items from the Hermes Agent's v0.1.7 field test — none were blockers, all were day-one papercuts for a new user.

### Fixed

- **`kfu search` accepts leading-dash DSL tokens** (`agent_skills/cli.py`). Queries using the DSL's `-` negation prefix — `kfu search -status:deprecated`, `kfu search -deprecated` — were rejected by argparse as unknown options (exit 2). The search verb now accepts them as query terms; every other verb still rejects unrecognized arguments.
- **`kfu show` without `--agent` reports the real install status** (`agent_skills/verbs/show.py`). On a multi-host setup it printed `Installed: no` even when the skill was installed — it resolved "which host am I?" instead of "where is this skill?". It now checks every detected host and reports where the skill is installed.
- **`kfu verify` without `--agent` no longer errors on multi-host setups** (`agent_skills/verbs/verify.py`). It exited 1 with "Multiple agent hosts detected" instead of verifying. It now verifies wherever the skill is actually installed.

### Changed

- **`kfu update` confirms what happened** (`clients/skill_discovery/update.py`). Previously silent on success; now prints `Updated — N skills (registry version …)` or `Already up to date — …`.
- **`kfu list` consolidates the all-empty case** (`agent_skills/verbs/list.py`). When no detected host has any installed skill, it prints one line instead of a repeated "No skills installed" block per host.
- **A malformed search query exits 1, not 2** (`agent_skills/verbs/search.py`). Exit 2 is reserved for argparse usage errors; a query that fails the DSL compiler is a runtime error.
- **A bare `kfu search` is documented as the catalog view** (`agent_skills/verbs/search.py`, `README.md`). An empty query lists the whole registry — the output now leads with `All N skills in the registry:` so it reads as a feature.

---

## [0.1.7] — 2026-05-14

Polish release ahead of the Hermes Discord soft-launch.

### Changed

- **`kfu install` prints `"I know kung fu."` on a successful install.** An in-product easter egg on the human-readable path; `--json` output is unchanged.
- **README refreshed** — a hero illustration, architecture / pipeline / sequence diagrams (Mermaid), and tightened copy. The hero image uses an absolute URL so it renders on the PyPI project page as well as on GitHub. Note: Mermaid diagrams render on GitHub but not on PyPI, where they appear as plain code blocks.

---

## [0.1.6] — 2026-05-14

Catalog-thickening release ahead of the soft-launch. The registry went from one real general-purpose skill to seven, and the schema gained a non-identity-binding way to credit the original author of a skill that was imported from elsewhere. No third-party skill has actually been imported yet — this release ships the *tooling*, not imported content.

### Added

- **Six first-party general-purpose skills.** Each one teaches something a stranger can use unchanged — Samuel's setup-specific skills were deliberately left out. Registry is now 9 skills (7 real + 2 meta).
  - `samuelgudi/session-handoff` — handing off agent work across a context-window boundary.
  - `samuelgudi/caddy-local-https` — Caddy as a local reverse proxy with auto-HTTPS `.localhost` domains.
  - `samuelgudi/keep-a-changelog` — CHANGELOG discipline; pairs with `semver-bump-decider`.
  - `samuelgudi/deployment-runbook` — writing a deploy runbook a stranger can follow under pressure.
  - `samuelgudi/lessons-learned-log` — durable one-line capture of hard-won lessons.
  - `samuelgudi/adversarial-test-design` — tests that actually catch regressions, not false-green tests.
- **`origin` block in `meta.json`** (ADR-002 — `docs/decisions.md`, Accepted). An optional, display-only credit block — `{author_name, author_url?, repo, ref, imported_at}` — for skills imported from a third-party source. It carries *credit*, not *identity*: the existing `author` field still means curator / maintainer-of-record and still drives Decision #4's immutable-ID binding and the CI verification chain. The presence of an `origin` block is itself the import marker — there is no separate `imported` flag, and there is no `origin.license` (the top-level `license` field carries the source license; a curator can't re-license). Reference: `SCHEMA.md` § 9, with the field spec in § 3.
- **`kfu show` renders imported skills with attribution.** An imported skill shows as *"curated by `<curator>`, originally by `<origin author>`"* plus an Origin section; first-party output is unchanged. `kfu search` is untouched — it does not surface authorship.

### Changed

- **`validate.py` accepts `LICENSE` / `LICENSE.txt` / `NOTICE` in a skill root only when the skill has an `origin` block.** First-party skills still reject those files — they keep their licensing at the repo root. Implementation touched `scripts/schema.json`, `scripts/validate.py`, and `scripts/generate_manifest.py`.

---

## [0.1.5] — 2026-05-13

Pre-announcement polish driven by the Hermes Agent's 0.1.4 field test. The 0.1.4 release passed end-to-end (CLI verbs, all eight MCP tools, frontmatter synthesis, install layout, no rename breakage) — these are the cosmetic items that surfaced during the walkthrough.

### Added

- **`kfu --version`** (`agent_skills/cli.py`): prints `kfu <version>` and exits 0. Hermes Agent field-test finding — previously the only way to confirm an install's version was `kfu --help` or `uv tool list`.

### Changed

- **First-pull unsigned-registry warning suppressed** (`clients/skill_discovery/update.py`): the `Warning: registry.json.sig not found — running unsigned.` line now fires only when a previously-cached sig is missing on a re-pull (a real regression). On a first pull, or when signing has not yet rolled out upstream, `kfu update` stays silent. The previous behaviour made new users mistake the line for an error.

### Field test

The 0.1.4 walkthrough by the Hermes Agent (WSL/Morpheus), 2026-05-13 ~07:12 UTC. Verdict: clean pass, no blockers. Two of three minor items addressed here; the third (no persistent `--default-agent` flag when multiple hosts are detected) is deferred — `IKNOWKUNGFU_DEFAULT_AGENT` env var is the current escape hatch and the multi-host error message is already actionable.

---

## [0.1.4] — 2026-05-12

Cleanup release. The 0.1.2 brand rename kept `agent-skills` everywhere as a "back-compat alias" — but there was nothing to be back-compatible with: the project had never been published before today. This release drops every `agent-skills` literal from the user-facing surface so a fresh reader doesn't have to learn a legacy name on their way in.

### Changed (BREAKING — internal storage paths and env vars)

- **CLI alias `agent-skills` removed** from `[project.scripts]` in `pyproject.toml`. The only CLI entry point is `kfu`. The MCP binary `iknowkungfu-mcp` is unchanged.
- **Cache directory renamed**: `~/.cache/agent-skills/` → `~/.cache/iknowkungfu/`. After upgrading, your next `kfu update` will populate the new path; the old path can be deleted.
- **Install marker renamed**: `.agent-skills-marker.json` → `.iknowkungfu-marker.json`. Skills installed with 0.1.2/0.1.3 won't be recognized as managed installs by 0.1.4 — `kfu verify` on those would report "no marker". The clean path is to `kfu uninstall <id>` against the old install (or just delete the directory) and `kfu install <id>` again under 0.1.4.
- **Environment variables renamed**:
  - `AGENT_SKILLS_REGISTRY_URL` → `IKNOWKUNGFU_REGISTRY_URL`
  - `AGENT_SKILLS_REGISTRY_REPO` → `IKNOWKUNGFU_REGISTRY_REPO`
  - `AGENT_SKILLS_SKIP_REPO_SYNC` → `IKNOWKUNGFU_SKIP_REPO_SYNC`
  - `AGENT_SKILLS_DEFAULT_AGENT` → `IKNOWKUNGFU_DEFAULT_AGENT`
- **Meta-skill registry IDs renamed**:
  - `samuelgudi/agent-skills-contribution` → `samuelgudi/iknowkungfu-contribution`
  - `samuelgudi/agent-skills-discovery` → `samuelgudi/iknowkungfu-discovery`

Both renamed meta-skills reset to version `0.1.0` under their new IDs (a fresh start; their 0.1.1 history under the old IDs is gone with the old IDs).

### Removed

- `yanks.json` cleared — the 0.1.0 yank entries from 0.1.3 referenced the old `samuelgudi/agent-skills-*` IDs, which no longer exist. New IDs start fresh, so there is nothing to yank.

### Migration notes

This release is BREAKING in the literal sense that any 0.1.2 or 0.1.3 install on your machine has cache/marker paths and env var names that 0.1.4 doesn't read. In practice, there are five people in the world who installed those versions (Samuel + Hermes Agent + 3 unknown if any). The migration is: `kfu update` to repopulate the new cache, and reinstall any skills you had installed.

---

## [0.1.3] — 2026-05-12

Patch release surfaced by the first external field test (Hermes Agent on WSL, 36 minutes after 0.1.2 went live). The `install_skill` path was broken end-to-end; everything else worked. Both root causes fixed.

### Fixed

- **Registry-repo shallow clone broke `install_skill`** (`clients/skill_discovery/update.py`): `kfu update` was cloning and fetching the registry repo with `--depth=1`. The install verb then `git archive`s a version-pinned SHA that can predate `origin/main`'s tip, so the tree isn't in the shallow clone and `git archive` returns exit 128. Switched to full-history clone + `git fetch --tags origin main`. Added two regression tests in `tests/test_update.py` that assert no `--depth` flag appears in any git argv produced by `_sync_registry_repo`.
- **Content-hash mismatch on all three skills**: `registry.json`'s `source.content_hash` is recomputed from the working tree on every regeneration, but `versions[<v>].sha` is frozen at the version's *first* commit (where the meta.json `version` field was introduced). Between iknowkungfu's 0.1.2 pre-publication audit and the brand rename, all three meta-skills' working-tree content changed without a version bump, so `source.content_hash` (working-tree-derived) diverged from what `git archive <version_sha>` produces (frozen old content). Worked around for 0.1.3 by bumping every skill 0.1.0 → 0.1.1 (new version pins a new tree SHA matching current content) and yanking 0.1.0 (so explicit `@0.1.0` installs hard-refuse with a clear yank message rather than hit the hash mismatch). Yanked versions can never be installed — there is no override flag (spec Decision #10).
- **`kfu list` exited non-zero when multiple agent hosts were detected** (`agent_skills/verbs/list.py`): the verb shared `detect_host`'s exit-1 "pick one with --agent" raise. `list` is read-only — when multiple hosts are detected, it now sections the output per host instead of forcing the user to pick. JSON shape is back-compat: single-host returns the old `{agent, installed:[...]}`; multi-host returns the new `{agents:[{agent, installed:[...]}, ...]}`.
- **`kfu show` left the user dangling on `Installed: no`** (`agent_skills/verbs/show.py`): now prints the exact `kfu install <id>` command on the next line so the next step is obvious.

### Known design issue (deferred)

The generator's `content_hash` is computed from the working tree rather than from `git archive <version_sha>`'s output. This means: **if anyone ever edits a skill's working-tree content without bumping its `version` field, the content_hash silently drifts and install will refuse the version**. The 0.1.1 version-bump-and-yank pattern is the manual workaround until the generator is rewritten to compute `content_hash` from the version's frozen git content. Documenting in CONTRIBUTING for now; tracked for the next minor.

### Field test

First external dogfood by the Hermes Agent (WSL/Morpheus), 2026-05-12 ~21:18 CEST. Report covered: clean pip install, all CLI verbs working, MCP tool discovery + 5 of 8 tools working, `install_skill` broken (the two root causes above), plus a clear friction journal that drove the 0.1.3 UX nits. Thread: agentmail thread `ca2a8a21-d2dc-4006-ae05-5ddc896bfae3`.

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

- **Deterministic FTS5 search engine** (`agent_skills/search/`): Lucene-style query DSL, SQLite FTS5 index, BM25 ranking with deterministic tie-break. Identical `(query, registry_version)` produces byte-identical result order. Reference: [`docs/query-language.md`](docs/query-language.md). 171 tests in `tests/test_search_*.py` + 20 determinism canaries in `tests/test_determinism.py`.
- **MCP server** (`iknowkungfu-mcp`): exposes the registry as Model Context Protocol tools so AI agent runtimes (Claude Code, OpenClaw, Codex, Cursor, Gemini CLI) can search and install skills mid-task. Eight tools — `search`, `get_skill`, `get_skill_file`, `install_skill`, `list_categories`, `list_tags`, `list_agents`, `update_registry`. `install_skill` is the differentiator: cross-host install via MCP that no other skill registry currently offers. Reference: [`docs/mcp-integration.md`](docs/mcp-integration.md). 32 tests.
- **CLI search rewrite**: the `kfu search` verb now parses the new query DSL (`tag:`, `agent:`, `version:>=`, boolean ops, phrases, prefixes, grouping). Deprecated `--agent` / `--category` / `--tag` flags are retained for one release with a stderr deprecation warning that translates them to the new DSL.
- **New CLI flags on `search`**: `--include-deprecated`, `--ndjson`, `--limit`, `--offset`.
- **ADR-001** locking the project name and the boundary between external-rename and internal-stability ([`docs/decisions.md`](docs/decisions.md)).

### Fixed

- **Empty-search-result hint** (`agent_skills/verbs/search.py`): previously suggested running `agent-skills list-categories` / `kfu list-categories`, a verb that doesn't exist. Replaced with an inline list of the eight valid categories so the suggestion is actionable.
- **MCP `install_skill` / `update_registry` PATH fragility** (`agent_skills/mcp/tools.py`): both tools previously shelled out via `subprocess.run(["agent-skills", ...])`, which broke on Windows MCP clients that launch the server with a stripped `PATH`. Now invoked as `[sys.executable, "-m", "agent_skills.cli", ...]` so the same Python interpreter the server is running under is used unconditionally, with no PATH lookup required.

### Stayed the same (back-compat, by design)

The rename is deliberately scoped to external surfaces. The following are unchanged so that existing installs continue to work without migration:

- Python module on disk: `agent_skills/`
- Cache directory: `~/.cache/agent-skills/`
- Install marker filename: `.agent-skills-marker.json`
- Environment variables: `AGENT_SKILLS_REGISTRY_URL`, `AGENT_SKILLS_REGISTRY_REPO`, `AGENT_SKILLS_SKIP_REPO_SYNC`
- Registry skill IDs (`samuelgudi/agent-skills-contribution`, `samuelgudi/agent-skills-discovery`) — immutable per the registry contract

### Known issues (deferred)

- **Hyphenated tag false positives in search**: `tag:claude-code` correctly matches skills with that literal tag, but also false-positives on skills that declare separate adjacent `claude` and `code` tags. Fix requires a schema bump (`INDEX_SCHEMA_VERSION` 1 → 2) to add a pipe-delimited `tags_filter` column. On the backlog.

### Test suite

- 446 passing, 1 skipped on Windows × Python 3.13. Cross-platform verification (Linux, macOS) runs via the existing `.github/workflows/ci.yml` once a commit is pushed.

---

## [0.1.1] — 2026-05-12 (internal, unreleased)

Dogfood-hardening pass: six new per-host adapters (claude-code, codex, opencode, openclaw, pi, hermes), CRLF-normalized content hashing for cross-platform stability, UTF-8 stream reconfiguration at CLI entry for Windows consoles, expanded CLI verb coverage. The version was tagged for the internal session-5 dogfood checkpoint but never published to a registry. See `docs/handoff/2026-05-12-execution-handoff-session5.md`.

## [0.1.0] — 2026-05-11 (internal, unreleased)

Initial public-shape scaffold: registry schema, CLI surface, validate.py, security_scan.py, manifest generation, claude-code adapter, contribution + discovery skills. See `docs/superpowers/plans/2026-05-11-agent-skills-hub-v0.md` for the initial plan.

[0.1.8]: https://github.com/samuelgudi/iknowkungfu/releases/tag/v0.1.8
[0.1.7]: https://github.com/samuelgudi/iknowkungfu/releases/tag/v0.1.7
[0.1.6]: https://github.com/samuelgudi/iknowkungfu/releases/tag/v0.1.6
[0.1.5]: https://github.com/samuelgudi/iknowkungfu/releases/tag/v0.1.5
[0.1.4]: https://github.com/samuelgudi/iknowkungfu/releases/tag/v0.1.4
[0.1.2]: https://github.com/samuelgudi/iknowkungfu/releases/tag/v0.1.2
[0.1.1]: https://github.com/samuelgudi/iknowkungfu/commits/main
[0.1.0]: https://github.com/samuelgudi/iknowkungfu/commits/main
