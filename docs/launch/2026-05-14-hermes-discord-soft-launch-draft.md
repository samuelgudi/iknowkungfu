# Hermes Discord soft-launch post — DRAFT

| Field | Value |
|---|---|
| Status | **DRAFT — not posted.** For Samuel's review. |
| Target | Hermes Discord (aligned first audience) |
| Drafted | 2026-05-14 (session 9) |
| Points at | `iknowkungfu` v0.1.6 (fresh on PyPI) |

Naming: the agent is **"Hermes Agent"**, never Milo/MILO — holds for this post and every public artifact.

---

## The post (~150 words)

**I Know Kung Fu — a package manager for Agent Skills**

Every agent ecosystem reinvents its own scattered skill library. **I Know Kung Fu** is one content-hash-anchored registry instead: contributors publish once, any agent installs through a thin per-host adapter. Skills are plain Markdown + JSON — no proprietary formats, no runtime deps.

The **Hermes adapter is first-class**. `kfu install <author>/<skill>` drops a skill straight into `~/.hermes/skills/`, and the `iknowkungfu-mcp` server lets the Hermes Agent search and install skills mid-session without leaving the loop.

```
uv tool install iknowkungfu     # or: pip install iknowkungfu
kfu update
kfu search <query>
kfu install <author>/<skill>
```

The registry is young — seven real, general-purpose skills today. That is the pitch: it is early, and it is the right moment to seed it. Browse, install, contribute → github.com/samuelgudi/iknowkungfu

---

## Notes for review

- **Length/tone**: short & punchy per the session-9 decision; keeps the focus on the tool, names no individual skills.
- **"seven real, general-purpose skills"** — a count, not a name-drop. Signals "thin-but-real, come seed it" rather than "empty". Drop the number if you would rather not anchor on it.
- **MCP wiring** is mentioned but not spelled out — the README's `~/.hermes/config.yaml` block is one click away in the repo. Add it inline if you want the post fully self-contained.
- **Not included**: `kfu submit` contributor flow (kept the post to the consumer path), the determinism/verify story, ADR-002 import tooling (internal, not a user pitch yet).
- **Posting**: still a draft. Hermes Discord only — no general subreddits / unaligned Discords this round.
