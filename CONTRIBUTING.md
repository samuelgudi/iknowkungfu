# CONTRIBUTING.md

## Getting started

1. **Clone the repo** (or fork it if you don't have write access):
   ```
   git clone https://github.com/samuelgudi/agent-skills
   ```
2. **Install the CLI**:
   ```
   pip install agent-skills
   ```
   or, with uv:
   ```
   uv tool install agent-skills
   ```
3. **Write your skill.** Create a directory with `SKILL.md` as the main body (see **SKILL.md filename** below). Add any scripts in `scripts/` and templates in `templates/`.
4. **Run `agent-skills init <local-dir>`** to scaffold `meta.json` interactively. The tool detects your GitHub login via `gh auth`, fetches your numeric GitHub ID via `gh api`, and prompts for category, tags, platforms, agent compatibility, and license. You can also hand-write `meta.json` following [SCHEMA.md](SCHEMA.md). (Decision #17)
5. **Run `agent-skills submit <local-dir>`** to validate, sanitize, scan, and open a PR. The submit flow will offer `init` inline if `meta.json` is missing.

---

## Skill design guidelines

### Slug grammar

A slug is the `<slug>` part of your skill's `<author>/<slug>` ID. See [SCHEMA.md § Slug grammar](SCHEMA.md) for the canonical regex and constraints. Slugs are immutable after first registration.

### Description: WHEN, not just WHAT

The `description` field (and the matching SKILL.md frontmatter `description`) must be a **complete sentence** that tells an agent **when to invoke the skill**, not merely what it does.

Good: _"Use this skill when you need to search Spotify for tracks or playlists and return structured results."_

Poor: _"Searches Spotify."_

This matters because agents use the description to decide whether to invoke a skill. A WHAT-only description produces invocation mismatches. (M5 guideline)

### English keywords for search

The match algorithm is keyword-based. If your description or name is in a language other than English, include English keywords in the `tags` array so the skill is discoverable from English queries. (W5 guideline)

### Personal and private skills

If a skill is tightly scoped to your personal setup (specific paths, personal API keys, private services), qualify the slug (`yourlogin/my-personal-X`) or do not publish it. A skill that only works for one person and breaks for everyone else degrades the registry's signal-to-noise ratio. (W7 guideline)

### Category taxonomy

`category` must be one of: `media`, `dev`, `ops`, `data`, `comms`, `docs`, `meta`, `ai`. To propose a new category, open a PR to [SCHEMA.md](SCHEMA.md) with a rationale. (Decision #15)

---

## Frontmatter contract

See [SCHEMA.md](SCHEMA.md) for the full `meta.json` and SKILL.md frontmatter specification, including all required and optional fields, their types, and validation rules.

Key points:
- `name` and `description` in `meta.json` must match SKILL.md frontmatter exactly.
- `author.github_id` must be the **numeric** GitHub user ID (not the login string). The CLI fetches this automatically via `gh api users/<login>`.
- `license` must be a valid SPDX identifier.
- `requires.commands` (not `requires.toolsets` — that field was removed) lists external binaries the skill depends on. **Do not install them from within scripts** — declare them here and let the user install them beforehand.

---

## SKILL.md filename casing

The canonical filename is **`SKILL.md`** — uppercase, case-exact. (Decision #16)

- `agent-skills submit` normalises a lowercase `skill.md` to `SKILL.md` at submit time with a notice.
- However, **Linux CI rejects a PR that adds `skill.md` directly** (Linux is case-sensitive; the case-exact check runs in CI and fails even if you submitted from Windows). Commit `SKILL.md`, not `skill.md`.

---

## REVIEW.md template

Before submitting, create a `REVIEW.md` in your skill directory. The `agent-skills submit` command generates a pre-filled template from this layout (copied verbatim from `clients/skill_contribution/templates/review.md`):

```markdown
# REVIEW.md — {skill_id}@{version}

## What does it do?
{description}

## What does it access?

- Network endpoints: <list endpoints OR write "none">
- Filesystem paths: <list paths OR write "${SKILL_DIR}/cache/ only">
- Environment variables: {env_vars}
- Processes spawned: {commands}

## Worst case if compromised?
<describe what an attacker could do if scripts/ were replaced with malicious code>

## Why is this useful?
<one paragraph; gap-check: what existing skill does this overlap with?>

## Test evidence
{test_evidence_section}

## What changed?
<for updates only; leave blank for first-version>
```

The six fields are:
1. **What does it do?** — 1-2 sentences describing the skill's function.
2. **What does it access?** — Every network endpoint, filesystem path, env var, and process spawned. Mandatory for `has_scripts: true` skills.
3. **Worst case if compromised?** — Concrete attacker impact if `scripts/` were replaced with malicious code.
4. **Why is this useful?** — One paragraph including a gap-check against existing skills.
5. **Test evidence** — Actual commands run and actual outputs. For `has_scripts: true` skills, real test evidence is mandatory.
6. **What changed?** — Required for skill updates only; leave blank for first-version submissions.

Reviewers will cross-check your claims against the actual code.

---

## Sanitization

`agent-skills submit` automatically runs `sanitize.py` against your skill directory before opening a PR. The sanitizer detects and replaces the following:

- **Home directory paths** — POSIX (`/home/<user>/`) and Windows (`C:\Users\<user>\`) absolute paths containing your username.
- **GitHub Personal Access Tokens** — patterns matching `ghp_...`.
- **OpenAI API keys** — patterns matching `sk-...` or `sk-proj-...`.
- **Anthropic API keys** — patterns matching `sk-ant-...`.
- **AWS access key IDs** — patterns matching `AKIA...`.
- **LAN/private IP addresses** — RFC 1918 ranges (192.168.x.x, 10.x.x.x, 172.16–31.x.x).
- **Prompt-injection trigger phrases** in `SKILL.md` body only — phrases such as "ignore all previous instructions", "your new instructions are", and "disregard the above".

The submit flow produces `SANITIZATION.diff` — a unified diff of every replacement made. Reviewers inspect this diff to confirm that sanitization only removed sensitive content and did not introduce any additions. Sanitization runs automatically through `submit`; there is no standalone `sanitize` verb in v0.

---

## Test discipline

- **Instructions-only skills** (no `scripts/` directory, `has_scripts: false`): test evidence is recommended but not required. Describe how you verified the instructions work.
- **`has_scripts: true` skills**: real test evidence is **mandatory**. Paste the actual commands you ran and their actual outputs in the REVIEW.md "Test evidence" section. A description of what would happen, or a statement that the agent ran it, is not sufficient.

---

## Common rejection reasons

1. **`meta.json` fields missing or malformed.** Run `agent-skills validate <local-dir>` before submitting. Hard-fail fields include `author.github_id`, `license` (must be SPDX), and `category` (must be one of the eight allowed values).
2. **`SKILL.md` filename is lowercase.** Linux CI rejects `skill.md` even if `agent-skills submit` normalised it locally. Always commit the file as `SKILL.md`.
3. **GitHub ID mismatch.** The `author.github_id` in `meta.json` does not match the ID fetched from `gh api users/<github_login>`. This happens when a GitHub username is re-registered to a different person. Use the CLI (`agent-skills init` or `agent-skills submit`) — it fetches the ID automatically.
4. **`PKG-INSTALL` detected in scripts.** Scripts must not call `pip install`, `npm install`, `apt install`, or any other package-manager install command at runtime. Declare runtime dependencies in `meta.json.requires.commands` and instruct users to install them beforehand. There is no override.
5. **Description doesn't include WHEN-to-invoke wording.** The description must tell agents under what circumstances to invoke the skill, not just summarise its function. Revise to start with "Use this skill when..." or equivalent.
6. **Hard-block findings in `scan_results.json`.** Any finding with `severity: block` from `security_scan.py` causes an automatic CI failure. The PR cannot be merged until the offending code is removed or rewritten. Hard blocks include `PKG-INSTALL`, `EXEC-ARBITRARY`, `OBFUSCATED-CODE`, and others defined in `rules.yaml`.
7. **`SANITIZATION.diff` missing or shows additions.** The diff must be present (generated by `submit`) and must contain only removals or neutral path normalisations. Any addition to `scripts/` in the diff is an automatic blocker.

---

## Verbs reference

The following CLI verbs are relevant to contributors. Consumer-side verbs (`search`, `install`, `uninstall`, `verify`, `list`, `update`, `show`) are documented in [README.md](README.md).

| Verb | What it does | Example |
|---|---|---|
| `init` | Scaffold `meta.json` interactively from SKILL.md frontmatter | `agent-skills init ~/.claude/skills/my-skill/` |
| `submit` | Validate, sanitize, scan, and open a contribution PR | `agent-skills submit ~/.claude/skills/my-skill/` |
| `issue` | Open a bug report or feature request for an existing skill | `agent-skills issue samuelgudi/spotify-search` |
| `deprecate` | Mark a skill as deprecated in favor of a newer skill | `agent-skills deprecate samuelgudi/old-skill --in-favor-of samuelgudi/new-skill` |
| `yank` | Hard-mark a specific version as compromised and open a yank PR | `agent-skills yank samuelgudi/my-skill@0.1.0 --reason "Credential leak in scripts/fetch.py"` |
