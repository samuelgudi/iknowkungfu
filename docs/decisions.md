# Decisions

Architectural and product decisions for this project. Append-only — once locked, an ADR is not edited except for typos. Superseding a prior decision means adding a new ADR that explicitly supersedes the older one.

Format: each ADR is numbered, dated, and structured as Context → Decision → Consequences. Read in order; later ADRs assume earlier ones.

---

## ADR-001 — 2026-05-12 — Project rename: `agent-skills` → `I Know Kung Fu`

### Status

**Accepted**, lock applied.

### Context

The project was previously named `agent-skills` internally and `samuelgudi/agent-skills` on GitHub. Session-5 strategic discovery (see `docs/handoff/2026-05-12-execution-handoff-session5.md` and `…-session6.md`) surfaced three blocking realities:

1. **PyPI namespace `agent-skills` is taken** by `datalayer/agent-skills` (an unrelated Jupyter project). Cannot publish under that name.
2. **The 2026 AI/agent-skills naming bin is saturated.** Pre-rename research identified 15+ direct or near-direct competitors using `agent-skills*` / `skill-hub*` / `skill-mesh*` / `agent-skills-hub*` variants. Generic descriptive names cannot differentiate.
3. **The product's actual positioning** — a structured commons where AI agents are *citizens* (consumers, suppliers, AND maintainers of skills) — is not captured by any descriptive compound name.

The rename had to happen before public launch (Phase 2 of the session-6 plan).

### Decision

The project is renamed to **`I Know Kung Fu`** (Title Case for the brand; `iknowkungfu` lowercase, no separators, for technical artifacts).

| Surface | Form |
|---|---|
| Brand name (marketing, docs, README hero) | **I Know Kung Fu** |
| PyPI package | `iknowkungfu` |
| CLI command (alias) | `kfu` (defined in `[project.scripts]`) |
| GitHub repo | `samuelgudi/iknowkungfu` (renamed 2026-05-12) |
| Domains | `iknowkungfu.io`, `iknowkungfu.ai`, defensively `.com` / `.dev` |
| GitHub org (future) | `iknowkungfu` (reserve before public launch) |
| Python module on disk | **Stays `agent_skills/`** for now (internal rename is invasive and not required for the external brand to be consistent) |

The name references Neo's line in *The Matrix* (1999) after Tank uploads martial-arts training into his brain — "I know kung fu." It directly mirrors the user experience this product delivers: an AI agent acquires a skill it didn't previously have, then says (in effect) *"I know kung fu now."*

### Why this name beat the alternatives

After ~40 candidates probed across 4 expert-frameworks (Alexandra Watkins SMILE/SCRATCH, David Placek / Lexicon Diamond + sound symbolism, Igor's 4 naming types, structured competitive landscape analysis):

- **Functional names** (skill-library, agent-skill-hub, skillmesh, skillex, etc.) — 0 of 12 viable. All contested by existing competitors; all flagged Watkins "T-Tame" + "C-Copycat".
- **Evocative English words** (cairn, solera, mycelium, praxis, hearth, almanac, atrium, tarn, etc.) — 0 of 14 clean. All PyPI-squatted *and* most brand-contested.
- **Playful short nouns** (kiln, hatch, mint, roost, magpie, crane, owl, glean, croft, cask, lathe) — 0 of 10 clean. 100% PyPI-squatted as of May 2026.
- **Coined / invented names** (Evria, Aurika, Korva) — 3 of 8 mechanically clean; survived as backup options.
- **Cultural-reference / OpenClaw-register** — `I Know Kung Fu` survived clean.

The data convergence is documented in `docs/handoff/2026-05-12-naming-decision.md`. Short conclusion: in 2026, every common English word ≤6 letters in the AI/agent/skill conceptual space is either PyPI-squatted, brand-owned, or both. The only categories with available namespace are (a) coined invented names and (b) longer cultural-reference phrases.

`I Know Kung Fu` was chosen over the coined alternatives (Aurika, Korva, Evria) because:

1. **Maximum memorability** — passes Watkins SMILE on all 5 dimensions (Suggestive, Memorable, Imagery, Legs, Emotional).
2. **Perfect concept fit** — the Matrix scene is *literally* about instantaneous skill download, which is the user experience this registry delivers.
3. **Brand voice writes itself** — *"For your agents."* / *"Show me."* / `kfu install <skill>` ergonomics.
4. **Fits the audience's cultural register** — AI/dev tooling skews 35+ for serious adoption; the Matrix reference lands.
5. **No PyPI / domain / trademark collisions** at the time of decision (verified).

Accepted trade-offs:

- **CLI ergonomics**: `iknowkungfu` is too long for direct CLI use → mitigated via `kfu` short alias.
- **Generational skew**: under-30 devs may need to Google the reference. Acceptable — the actual buying motion for skill-registries skews to senior engineers.
- **WB nuisance-suit risk (low)**: the phrase itself is not trademarkable as a short dialogue snippet under US trademark law; Warner Bros owns *The Matrix* film copyright and the "THE MATRIX" trademark, but not individual dialogue lines. Mitigation: avoid all Matrix iconography (green falling code, agent sunglasses, Trinity/Morpheus likenesses), do not claim affiliation, optionally pay $300-500 for a USPTO clearance consult before public launch.
- **Aging**: every year the reference is one year older. Accepted — *Jekyll* (static site generator) names itself after an 1886 novel and has aged fine.

### Consequences

**Immediate (before public launch — Phase 2 of session-6 plan):**

1. **Register defensive domains now** to prevent squatter capture now that the name is committed: `iknowkungfu.io`, `iknowkungfu.ai`. Optionally `.com` and `.dev`.
2. **Reserve PyPI** by publishing a placeholder `0.0.0` of `iknowkungfu`. PyPI namespace was free at decision-time but is a race against squatters.
3. **Reserve GitHub org** `iknowkungfu` (or accept the user-namespace path `samuelgudi/iknowkungfu` long-term).
4. **Rename external surfaces** during session-6 Phase 1: `pyproject.toml` (`name`, `[project.scripts]`), README hero, `CONTRIBUTING.md`, `SCHEMA.md`, `docs/` references, `clients/skill_discovery/update.py` constants (`DEFAULT_REGISTRY_URL`, `DEFAULT_REGISTRY_REPO`), `agent_skills/__init__.py` docstring + `__version__`, any branded strings in `agent_skills/cli.py`, tests that hardcode `"agent-skills"` literals.
5. **Do NOT rename the Python module on disk** (`agent_skills/` → `iknowkungfu/`). The external brand can be `I Know Kung Fu` while the internal module name stays `agent_skills`. This is the pragmatic minimum-disruption approach; full module rename can happen later if it becomes worth the cost.
6. **CLI alias `kfu`** defined in `[project.scripts]`: `kfu = "agent_skills.cli:main"` (or whatever the existing entry point is).
7. **CHANGELOG.md** entry for v0.1.2 documents the rename.

**Brand-voice guidelines (for README + marketing):**

- Tagline candidates: *"For your agents."* / *"Show me."* / *"The skills your agents need. Instantly."*
- Avoid Matrix imagery, fonts, color schemes, or character references — keep the brand on the *phrase alone*.
- Acceptable: subtle, generic typographic references to the scene (white-on-black hero with the phrase as the headline). Avoid: green falling code, character names, scene recreations.

**Legal pre-flight (before public launch):**

- $300-500 USPTO clearance consult with a trademark lawyer to confirm clean filing in software classes 9 and 42.
- Optional: file USPTO application once `iknowkungfu.io` is live and product is shipping.

### Supersedes

None (first ADR).
