# Hermes Discord soft-launch post — DRAFT (v2, repositioned)

| Field | Value |
|---|---|
| Status | **DRAFT — not posted.** For Samuel's final read. |
| Target | Hermes Discord (aligned first audience) |
| Drafted | 2026-05-14 (session 9); **rewritten 2026-07-17 (session 11)** around the supply-chain positioning |
| Points at | `iknowkungfu` v0.1.9 (latest on PyPI; trust-model hardening release) |

Naming: the agent is **"Hermes Agent"**, never Milo/MILO — holds for this post and every public artifact.

---

## The post (~170 words)

**I Know Kung Fu — the verified supply chain for agent skills**

There are plenty of places to *find* skills for your agent. There's nowhere that guarantees *what you're installing* — and a skill is instructions your agent will execute. **I Know Kung Fu** is one reviewed registry where every skill is validated, security-scanned (including the SKILL.md body itself — prompt-injection patterns, hidden instructions, exfiltration attempts), content-hash verified at install, and hard-yanked if compromised.

The other half: agents don't just consume it — they contribute back through the same reviewed pipeline. That's not a roadmap slide: the newest skill in the registry, `hermes-tweet`, was submitted by an agent, cross-fork PR to promotion, fully gated. Agents of different users, improving one shared catalog, safely.

The **Hermes adapter is first-class**: `kfu install <author>/<skill>` drops into `~/.hermes/skills/`, and the `iknowkungfu-mcp` server lets the Hermes Agent search, install, and contribute mid-session.

```
uv tool install iknowkungfu     # or: pip install iknowkungfu
kfu update
kfu search <query>
kfu install <author>/<skill>
```

Ten reviewed skills today — small and dense on purpose. Every one you add or improve is one the next agent inherits, verified. → github.com/samuelgudi/iknowkungfu

---

## Notes for review

- **What changed vs v1**: lead is now the trust/verification story ("verified supply chain"), with the contribution loop as proof rather than promise — anchored on the real `hermes-tweet` external submission. "Compounds with use" demoted from headline to implication.
- **"Ten reviewed skills"** — updated count (was "seven"); still a count, not a name-drop. "Small and dense on purpose" turns the size into the pitch.
- **`hermes-tweet` name-drop**: deliberate — it's a Hermes-ecosystem skill, submitted by an agent, landing in the Hermes Discord. Triple-relevant. Drop the name if you'd rather not spotlight one contributor.
- **v0.1.9 not named in the post** — the hardening is *shown* (the scan list) rather than announced as a version. Add "fresh v0.1.9 on PyPI" if you want the recency signal.
- **Posting**: still a draft. Hermes Discord only — no general subreddits / unaligned Discords this round.
