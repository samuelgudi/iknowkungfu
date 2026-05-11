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

Before submitting, create a `REVIEW.md` in your skill directory with the following six fields (the sixth field is required only for skill updates, not first-version submissions):

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

This template mirrors [SCHEMA.md § REVIEW.md](SCHEMA.md) and the spec § 10 Step 4. Reviewers will cross-check your claims against the actual code.

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
