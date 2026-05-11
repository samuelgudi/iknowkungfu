# agent-skills

Agent-agnostic registry for skill discovery and contribution.

**Status**: v0 — spec phase. No code yet.

The full design lives at [`docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md`](docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md).

## What this is

A registry where:

- **Agents** (Claude Code, Hermes, others) can search and install skills they don't have built-in for a given task.
- **Contributors** (humans, agents) can submit new skills via a sanitization + review pipeline.
- The registry is a single flat-file git repo — anyone can clone the whole thing.

## What it is not

- Not a Claude-Code-only or Hermes-only registry. Agent-agnostic by design.
- Not a plugin distribution system. Skills only in v0; plugins are a separate trust tier.
- Not auto-curated. Every merge is reviewed by a human in v0.

## Layout

See the spec. Top-level summary:

- `registry.json` — machine-readable manifest (generated; never hand-edited).
- `skills/` — approved skills, organized as `<author>/<slug>/`.
- `archive/` — deprecated skills with `superseded_by` pointers.
- `submitted/` — open contribution PRs.
- `scripts/` — registry tooling (`validate.py`, `security_scan.py`, `generate_manifest.py`).
- `clients/` — `skill-discovery/` and `skill-contribution/` reference clients.
- `adapters/` — per-agent install logic (`claude-code.py`, `hermes.py`).
- `tests/` — pytest suite covering scripts/clients/adapters.

## License

MIT. See `LICENSE`.
