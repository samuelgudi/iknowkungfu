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

---

## ADR-002 — 2026-05-14 — Import/curation provenance model for third-party skills

### Status

**Accepted**, lock applied (2026-05-14). The design pass was accepted; the implementation step described under Consequences (schema, validator, manifest, and rendering support for the `origin` model) is authorised. Note: accepting this ADR authorises the *tooling* for imports — it does **not** authorise importing any specific third-party skill. Each import remains a per-skill, human-reviewed decision, and the v0 recommendation (defer actual importing past launch) stands.

### Context

The registry's launch catalog is first-party only. To grow catalog depth, a recurring proposal is to re-host genuinely useful skills that already exist in the open-source ecosystem. Doing so collides with three locked properties of the current design:

1. **Immutable GitHub-ID identity binding (Decision #4 / spec "Skill identity", Gemini M2).** Every skill's `id` is `<author>/<slug>`, and `meta.json.author.github_id` is the contributor's immutable GitHub numeric user ID, recorded at first PR and re-verified by CI on every subsequent PR. This is the anti-impersonation anchor. Re-hosting someone else's skill under this model means either (a) misattributing authorship to the importer, or (b) needing the original author's GitHub ID — which the importer cannot legitimately claim.
2. **Submitter is reviewer-of-record (`SECURITY.md`).** The reviewer checklist makes whoever submits a skill accountable for it: they fill `REVIEW.md`, their claims are cross-checked against the code, and for `has_scripts: true` skills they must provide real test evidence. Bulk-importing means the importer vouches, in full, for code they did not write.
3. **Per-skill licensing.** Each source skill carries its own license. Redistribution requires license compatibility, attribution, and — for some licenses — preservation of a NOTICE.

Research into the ecosystem (session 8) established the licensing reality that shapes this decision:

- **License lives at the individual-skill level, not the repo level.** `anthropics/skills` has no repo-level `LICENSE`; every skill folder ships its own `LICENSE.txt`. ~13 of its skills are Apache-2.0; the four document skills (`docx`, `pdf`, `pptx`, `xlsx`) are explicitly "source-available, not open source" and carry a "demonstration purposes only" disclaimer. Importing is therefore **always a per-skill license check, never a bulk operation.**
- The cleanest candidate sources are MIT-licensed and genre-aligned: `obra/superpowers` (MIT, active) and `obra/superpowers-skills` (MIT, archived — frozen and stable).
- "Awesome-list" repos (`VoltAgent/awesome-agent-skills`, `ComposioHQ/awesome-claude-skills`, `hesreallyhim/awesome-claude-code`) are *indices of links*, not content sources. They are discovery maps; the import source is always the underlying content repo, with its own license.
- Raw "index every public skill on GitHub" is already a crowded lane (`claude-plugins.dev`, `skills.sh`). The registry's differentiator (per ADR-001: agents as citizens; human curation; security review; hermes-first) is **curated re-hosting with review and provenance** — not raw indexing.

The root cause of the collision: the `author` object does two jobs at once — **identity/accountability** (the immutable, CI-verified, reviewer-of-record binding) and **credit/authorship**. For first-party skills these are the same person, so the schema collapses them. For an imported skill they are different people, and the schema cannot currently express that.

### Decision

Resolve the collision by **separating the two jobs** the `author` object conflates. Do not weaken Decision #4 — stop overloading it.

**1. `author` is clarified to mean curator / maintainer-of-record.** No structural change. `author` remains `{name, github_login, github_id}`, remains immutable, remains CI-verified against `gh api`, remains the reviewer-of-record. For an imported skill, `author` is the iknowkungfu citizen who curated, reviewed, and is accountable for the entry — not the original author. The anti-impersonation guarantee is fully intact; the field is simply named correctly. (`SECURITY.md` already describes this field as an accountability anchor, never as "authorship".)

**2. A new optional `origin` block carries original authorship as display-only credit.** Author-supplied in `meta.json`, present only on imported skills. The name `origin` is deliberate — `provenance` is already taken by a *derived* field (`{submitted_pr, merged_at, reviewed_by}`, set by `generate_manifest.py`); `origin` is *author-supplied* and must not be confused with it. Proposed shape (to be finalised in the implementation step):

```json
"origin": {
  "author_name": "Jesse Vincent",
  "author_url": "https://github.com/obra",
  "repo": "https://github.com/obra/superpowers-skills",
  "ref": "<commit SHA imported from>",
  "license": "MIT",
  "imported_at": "2026-05-14T00:00:00Z"
}
```

`origin.author_name` / `origin.author_url` are **display-only, NOT `gh api`-verified, NOT identity-binding** — they are a citation, not an account. They confer no registry identity and so cannot be used to impersonate. `origin.ref` pins the exact source commit for auditability and re-sync.

**3. An `imported` marker so the registry renders honestly.** A skill with an `origin` block is an imported skill. Whether this is an explicit `imported: true` field in `meta.json` or derived from the presence of `origin` is an implementation detail; the requirement is that `kfu search` and `kfu show` display it as *"curated by `<curator>` · originally by `<origin.author_name>` · `<license>`"* — **never** as *"by `<curator>`"*.

**4. The existing `license` field carries the source license faithfully.** For an Apache-2.0 import, the source `LICENSE`/`NOTICE` is bundled into the skill directory and the attribution requirements are satisfied by that plus the `origin` block. (Implementation note: `validate.py`'s `ALLOWED_ROOT_FILES` is currently `{SKILL.md, meta.json, README.md}` and would reject a bundled `LICENSE`/`NOTICE` as extraneous — the implementation step must allow these for imported skills.)

**5. v0 recommendation: design the model now, defer actual importing past launch.** Reasons: the highest-value source (`anthropics/skills`) is a per-skill licensing minefield, not a quick win; `SECURITY.md` makes the importer reviewer-of-record, so every imported skill-with-scripts needs line-by-line review plus real test evidence — a real per-skill cost, not a bulk operation; the launch needs *enough good skills*, and session-8 Track 1 already delivered seven. A first-party-only v0 with a designed-but-dormant import path is a stronger story than a catalog padded with hastily-imported third-party skills.

**6. When importing does begin, pilot with `obra/superpowers-skills`.** A single MIT source, archived (stable, will not drift), genre-aligned. Prove the `origin` model end-to-end on one clean repo before touching the mixed-license `anthropics/skills` set.

**7. The generalizability filter does not relax for imports.** `CONTRIBUTING.md`'s personal-vs-generalizable filter ("would a stranger get value from this unchanged?") applies to imported skills exactly as to first-party ones. Many community and vendor skills are domain- or vendor-specific and must be filtered out regardless of license.

### Consequences

**Accepting this ADR unblocks an implementation step** (not part of this design pass), which must — per `SCHEMA.md`'s own rule — update the field-level reference and the spec together:

1. `SCHEMA.md` — add the `origin` block field definitions and the `imported` marker; clarify `author` semantics as curator/maintainer-of-record.
2. `docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md` — mirror the schema change (SCHEMA.md and the spec move together).
3. `scripts/validate.py` — validate the `origin` block when present (shape, SPDX `license`, URL fields); add `LICENSE`/`NOTICE` to `ALLOWED_ROOT_FILES` for imported skills; optionally assert `origin` ⇔ `imported` consistency.
4. `scripts/schema.json` — add the `origin` object schema.
5. `scripts/generate_manifest.py` — pass `origin` through to `registry.json`; keep it distinct from the derived `provenance` field.
6. `kfu search` / `kfu show` rendering — surface the curator/origin distinction as specified in Decision #3.

**Properties of the chosen model:**

- **Zero weakening of Decision #4.** The identity binding, CI verification, and reviewer-of-record chain are untouched. The derived `provenance.reviewed_by` already records the curator correctly.
- **Purely additive.** `origin` is optional; existing first-party skills are unaffected and omit it. No `schema_version` bump is required for an additive optional field.
- **Honest to consumers.** The registry shows the truth: curated by one party, authored by another, under the original license.
- **License-correct by construction.** MIT and Apache-2.0 both permit redistribution with attribution and license preservation; the `origin` block plus the preserved `license` field plus bundled NOTICE *is* that attribution.
- **Portable.** The curator/origin split mirrors how package registries already separate `author` from `maintainers` (npm, crates.io) and should be expressible in the `agentskills.io` open standard, so imported skills stay portable.

**Explicitly NOT decided here:** whether imports ever happen in v0 (recommendation is defer, but the call is the maintainer's); the exact `imported`-marker mechanism (explicit field vs derived); ownership-transfer flows (an imported skill's original author later claiming a real registry account); and bulk/automated import tooling (out of scope — imports are per-skill, human-reviewed).

### Supersedes

None.
