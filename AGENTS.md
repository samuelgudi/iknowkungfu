# AGENTS.md

You are an AI agent encountering this repo. This file is your map. The `README.md` is human-first; this one is agent-first.

## What this repo is

**I Know Kung Fu** is a skill library for AI agents that compounds with use. One reviewed, content-hash-verified registry of Agent Skills. Agents pull skills mid-task and contribute improvements back, so the catalog sharpens — not just grows.

## The three roles you can play

1. **Use skills.** Search the registry for one that matches the current task; install it into the host you're running on; let your host load it for the rest of the session.
2. **Contribute skills.** Write new skills, propose improvements to existing ones, deprecate stale ones, yank compromised versions.
3. **Help a human do either.** Most of the friction lives in the contributor path — fork-first, `gh` CLI auth, one-skill-per-PR.

## Fastest path to being useful

Two paths. Pick whichever fits your runtime.

**Path A — MCP server (preferred when you're an agent runtime).** Register `iknowkungfu-mcp` with your host and use eight in-loop tools — `search`, `get_skill`, `get_skill_file`, `install_skill`, `list_categories`, `list_tags`, `list_agents`, `update_registry`. No shelling out. Wiring per host: [docs/mcp-integration.md](docs/mcp-integration.md).

**Path B — Install the two meta-skills.** If MCP isn't available, install both meta-skills and use the `kfu` CLI from there:

```
kfu install samuelgudi/iknowkungfu-discovery
kfu install samuelgudi/iknowkungfu-contribution
```

The first walks you through search → inspect → install. The second walks you through submit → improve → deprecate → yank.

## Where to look in this repo

| If you want to… | Read |
|---|---|
| Search or install a skill | `skills/samuelgudi/iknowkungfu-discovery/SKILL.md` |
| Submit, improve, deprecate, or yank a skill | `skills/samuelgudi/iknowkungfu-contribution/SKILL.md` |
| Schema reference (`meta.json`, `SKILL.md` frontmatter) | `SCHEMA.md` |
| Wire the MCP server into a specific host | `docs/mcp-integration.md` |
| Full contributor submission pipeline | `CONTRIBUTING.md` |
| Query DSL reference | `docs/query-language.md` |
| Architectural decisions | `docs/decisions.md` (ADR-001 = rename, ADR-002 = origin/credit model) |
| Latest release notes | `CHANGELOG.md` |
| Security policy & reviewer checklist | `SECURITY.md` |

Always treat code as the ground truth and reconcile docs to it if they disagree.

## Hard constraints — do not violate

These will bounce a contribution at CI or refuse an install, with no override:

- **One skill per PR.** The `contribution-pr-check` job rejects PRs touching more than one `submitted/<author>/<slug>/` directory. Split your submission; do not bundle.
- **`SKILL.md` filename is case-exact.** Linux CI rejects lowercase `skill.md` even if `kfu submit` normalised it locally on a case-insensitive filesystem.
- **No package-manager installs inside `scripts/`.** `pip install`, `npm install`, `apt install`, and friends are hard-blocked by `security_scan` (`PKG-INSTALL`). Declare runtime dependencies in `meta.json.requires.commands` and let the user install them beforehand.
- **No fabricated test evidence in `REVIEW.md`.** For `has_scripts: true` skills, paste **actual** command output. "Would print X" is not test evidence. Reviewers cross-check.
- **Yanked versions are unreachable.** `kfu install` hard-refuses them. No flag exists to override.
- **Author identity is immutable.** `author.github_id` is the numeric GitHub ID, fetched automatically by `kfu init` via `gh api users/<login>`. Re-publishing under a different identity is the wrong move; if you import a skill from elsewhere, use the `origin` block (ADR-002) instead.

## The compounding bet

This project assumes agents don't only consume the library — they sharpen it. If a skill you used had a bug, a missing edge case, or unclear instructions, don't just work around it. Propose an improvement via `kfu submit` (a new version) or `kfu issue` (the lighter-touch path). Every accepted improvement is a sharper skill the next agent inherits. That's the loop the registry is built around — and it only works if you participate.

## Limits, honestly

- **Trust model today**: content-hash verification, hard-refused yanks, and CI validation + security scanning of every submission. Cryptographic signing and lockfiles are specced (see the design spec in `docs/superpowers/specs/`) but not yet implemented.
- **Registry size**: early. Seven real general-purpose skills plus two meta-skills as of v0.1.8. The catalog grows from contributions like the one you might make next.
- **Adapters**: six host runtimes implemented — claude-code, hermes, codex, opencode, openclaw, pi. Others — Gemini CLI, Cursor native, GitHub Copilot, OpenHands, Goose — are spec-listed but not yet built.
- **You will be the first agent to do some things here.** The submission pipeline has been exercised by the maintainer and dogfooded against a local registry, but the full external-fork → cross-fork PR → `on-merge.yml` promotion path is not yet battle-tested at scale. If something breaks for you, that's the next CHANGELOG entry — open `kfu issue` against the relevant skill, or a normal GitHub issue against the repo.
