---
name: agent-skills-discovery
description: Query the I Know Kung Fu registry for a skill that matches the current task. Use ONLY when explicitly asked to search for a skill. Do not invoke reflexively for every task.
---

# I Know Kung Fu — discovery

Use this skill when the user has explicitly asked you to find or search the I Know Kung Fu registry for an existing skill that would help with the current task.

## When to use

- The user says: "is there a skill for X?", "find me a skill that does Y", "search the registry for Z".
- Before reaching for a third-party tool that may already be packaged as a skill.

## When NOT to use

- For every task automatically. Reflexive invocation pollutes session context and slows responses.
- For tasks where the user has not asked about skills at all.

## How to use

Run the discovery client via the CLI:

```
kfu search <query terms>
```

Pass `--agent claude-code` (or `hermes`, `codex`, etc.) to filter compatible skills. Pass `--json` for a structured response. The output ranks candidates by name/description/tag overlap with the query, with deterministic tie-breaking.

The back-compat `agent-skills` alias resolves to the same entry point, so existing scripts continue to work; new automation should prefer `kfu`.

## Limits

- BM25 ranking via SQLite FTS5; past ~30 candidates ranking quality degrades. Mitigated by category + tag filters and the 10-tag-per-skill cap.
- The registry is cached at `~/.cache/agent-skills/registry.json` (path kept for back-compat with existing installs); run `kfu update` to refresh.
