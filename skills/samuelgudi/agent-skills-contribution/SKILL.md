---
name: agent-skills-contribution
description: Submit a new skill or update an existing one in the I Know Kung Fu registry. Use when the user wants to publish a skill, propose a deprecation, or yank a compromised version.
---

# I Know Kung Fu — contribution

Use this skill when the user wants to contribute to the I Know Kung Fu registry — submitting a new skill, updating an existing one, opening an improvement issue, deprecating a skill, or yanking a compromised version.

## When to use

- The user says: "I want to publish this skill", "submit my skill", "open a PR to the registry".
- The user wants to deprecate or yank an existing registry entry.

## How to use

The contribution flow is interactive. The CLI offers these verbs:

```
kfu init <local-dir>       # scaffold meta.json from an existing SKILL.md
kfu submit <local-dir>     # 5-step pipeline: validate → sanitize → scan → REVIEW.md → PR
kfu issue <id>             # open an improvement issue
kfu deprecate <id> --in-favor-of <new-id>
kfu yank <id>@<version> --reason "..."
```

The back-compat `agent-skills` alias resolves to the same entry point, so existing scripts continue to work; new automation should prefer `kfu`.

## Required by the registry

- Every contribution PR must include: a populated `REVIEW.md`, a `SANITIZATION.diff`, and a clean `scan_results.json` (no hard-blocks). The submit verb produces all three.
- For `has_scripts: true` skills: `REVIEW.md` must include real command output (not "would print X").

## Limits

- Yanked versions cannot be installed. There is no `--allow-yanked` flag.
- Deprecated skills require `--allow-deprecated` at install time.
