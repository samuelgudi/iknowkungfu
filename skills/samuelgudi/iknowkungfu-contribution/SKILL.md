---
name: iknowkungfu-contribution
description: Submit a new skill, propose an improvement, deprecate, or yank a skill in the I Know Kung Fu registry. Use when the user wants to publish, update, or report on a skill.
---

# I Know Kung Fu — contribution

Use this skill when the user wants to contribute to the I Know Kung Fu registry — submit a new skill, update an existing one, propose an improvement, deprecate, or yank a compromised version.

## When to use

- The user says: "I want to publish this skill", "submit my skill", "open a PR to the registry", "improve this skill", "deprecate X", "yank X".

## Prerequisites — verify before running anything

Cryptic subprocess errors downstream almost always trace back to one of these being missing. Check them first:

1. **`gh` CLI installed and authenticated.** `kfu init` calls `gh api`; `kfu submit` calls `gh pr create`. Verify with `gh auth status`. If not authenticated: `gh auth login`.
2. **`git` configured** with `user.name` and `user.email`.
3. **A fork of `samuelgudi/iknowkungfu`** on the user's GitHub account, cloned locally — *not* the upstream. The user does not have write access to upstream; `kfu submit` pushes to your fork's `origin` and opens a cross-fork PR. If the user has cloned upstream by mistake, either re-clone the fork or run `gh repo fork --remote --clone` to add the fork and retarget `origin`.

Do not let `kfu submit` fail through one of these — diagnose and fix first.

## Submission flow

```
kfu init <local-dir>     # scaffold meta.json from SKILL.md frontmatter
kfu submit <local-dir>   # validate → sanitize → scan → REVIEW.md → push → gh pr create
```

`kfu submit` produces three required artifacts in the PR: a filled `REVIEW.md`, a `SANITIZATION.diff`, and a clean `scan_results.json`. CI rejects the PR if any are missing or fail.

## REVIEW.md — six required sections

1. **What does it do?** — one or two sentences.
2. **What does it access?** — every network endpoint, filesystem path, env var, and process spawned. Mandatory for `has_scripts: true`.
3. **Worst case if compromised?** — concrete attacker impact if `scripts/` were replaced with malicious code.
4. **Why is this useful?** — one paragraph, including a gap-check against existing skills.
5. **Test evidence** — **real** command output (not "would print X"). Mandatory for `has_scripts: true`.
6. **What changed?** — required for updates only; leave blank on first-version submissions.

## One skill per PR

CI's `contribution-pr-check` job rejects any PR touching more than one `submitted/<author>/<slug>/` directory. If the user has several skills to contribute, run `kfu submit` once per skill — each gets its own branch and its own PR. Do not bundle.

## When CI bounces the PR

Read the failing job's log and map the failure to the fix:

- **`validate` failure** → `meta.json` schema mismatch. Run `kfu validate <local-dir>` locally and fix the named field.
- **`security_scan` hard-block** → `PKG-INSTALL` (no `pip install` / `npm install` / etc. inside `scripts/`), `EXEC-ARBITRARY`, `OBFUSCATED-CODE`, and others. Declare runtime dependencies in `meta.json.requires.commands` instead. Remove or rewrite the offending code.
- **`SKILL.md` filename case** → Linux CI rejects lowercase `skill.md`. Commit `SKILL.md` (case-exact).
- **GitHub ID mismatch** → `author.github_id` must equal the numeric ID returned by `gh api users/<login>`. Re-run `kfu init` to refetch it automatically.
- **Multiple `submitted/` dirs touched** → split into one PR per skill (see "One skill per PR").

After fixing, push to the same branch — the open PR updates and CI re-runs automatically.

## Other verbs

```
kfu issue <author>/<slug>                              # open an improvement issue
kfu deprecate <id> --in-favor-of <new-id>              # mark as deprecated
kfu yank <id>@<version> --reason "specific reason"     # hard-block a compromised version
```

## The compounding loop

If the user is *improving* a skill someone else authored: same submission flow, treated as a new version. The original author of record stays (`author` is curator/maintainer-of-record, see ADR-002 for the credit model). `kfu issue` is the lighter-touch path for ideas the user cannot or will not implement themselves — every accepted improvement is a sharper skill the next agent inherits.
