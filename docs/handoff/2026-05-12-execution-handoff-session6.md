# agent-skills — session 6 plan (post strategic-reframe, pre-launch)

| Field | Value |
|---|---|
| Date written | 2026-05-12 (end of session 5) |
| Date of next session | TBD |
| Branch | `main` |
| HEAD | `3c913b4` — docs: session-5 handoff |
| Remote | pushed (origin/main = `3c913b4`) |
| Tests | 223 passing / 1 skipped; CI green on Linux × macOS × Windows × Python 3.10–3.13 |
| Version on disk | `0.1.1` (next session ships `0.1.2`) |
| Repo visibility | **PRIVATE** (next session makes it public) |
| PyPI status | **NOT YET PUBLISHED** (next session publishes — under a new name TBD) |
| Live skills in registry | 3 (`agent-skills-contribution`, `agent-skills-discovery`, `samuelgudi/semver-bump-decider`) |
| State | Functionally complete v0.1.1; strategic pivot identified; rename + public + PyPI pending; new feature pipeline planned |

> **Read this entire file before doing anything in session 6.** It contains a strategic reframe that was not visible in earlier handoffs and changes the product's positioning, the name, the next-feature roadmap, and the adapter-expansion priority list.

---

## Session 5 — what closed

Session 5 covered three distinct efforts plus a strategic discovery at the end:

1. **Submit-pipeline dogfood walkthrough** — 3 blockers found + fixed (`6cb7669`, `eed2d09`, `9bbb279`), 8 regression tests added. Full report: `docs/dogfood/2026-05-12-submit-pipeline-walkthrough.md`.
2. **Codex + OpenCode adapters** (`318f4f2`) — closed the spec § 19 gap. 24 tests added.
3. **Pi + OpenClaw adapters** (`ac23b7a`) — user-requested. 25 tests added.
4. **Strategic discovery** (this file) — found `agentskills.io`, the Anthropic-originated open standard our format already follows. Found `skyll` (assafelovic/skyll), a direct competitor in the same space.

Detailed session-5 close-out is in `docs/handoff/2026-05-12-execution-handoff-session5.md`. **That file does NOT include the strategic discovery** — this file does. Read both, but treat this as the canonical plan for session 6.

---

## The strategic discovery — what changed

### `agentskills.io` is the canonical spec

- Open standard **originated at Anthropic**, now community-maintained at `github.com/agentskills/agentskills`.
- **18,400 stars, 1,100 forks** on the spec repo. 42 open issues, 21 PRs in flight. Highly active.
- **~35 agent runtimes officially adopting it.** Full list at `agentskills.io`. Includes Claude Code, Claude, OpenAI Codex, Gemini CLI, Cursor, GitHub Copilot, VS Code, OpenCode, OpenHands, Goose (Block), Junie (JetBrains), Amp, Letta, Factory, Databricks, Snowflake, Roo Code, TRAE (ByteDance), Mistral Vibe, Spring AI, Pi, Workshop, Kiro, nanobot, fast-agent, Piebald, Agentman, Ona, Emdash, VT Code, Qodo, Laravel Boost, Command Code, Roo Code, Google AI Edge Gallery.
- **OpenClaw is NOT in the official adopter list.** Worth noting — Samuel's `openclaw` adapter targets a non-official runtime. Keep the adapter (Milo uses it; Samuel asked for it) but understand its position.

### Spec format

| Field | Required | Constraints |
|---|---|---|
| `name` | Yes | ≤64 chars, lowercase `a-z` + hyphens. No leading/trailing/consecutive hyphens. **Must match parent directory name.** |
| `description` | Yes | 1–1024 chars. WHEN + WHAT. |
| `license` | No | Short license name or filename. |
| `compatibility` | No | ≤500 chars. Environment requirements (intended product, sys packages, network access). |
| `metadata` | No | Free-form key-value map. Clients namespace under their own keys to avoid collision. |
| `allowed-tools` | No (experimental) | Space-separated pre-approved tools. |

Optional directories: `scripts/`, `references/`, `assets/`.

**Progressive disclosure model** (the spec's load semantics):
1. **Stage 1 — Metadata** (~100 tokens): only `name` + `description` loaded at startup for all skills.
2. **Stage 2 — Activation** (<5000 tokens recommended): full `SKILL.md` body loaded when a task matches.
3. **Stage 3 — Resources** (as needed): `scripts/`, `references/`, `assets/` files loaded on demand.

### Our spec-compatibility audit

| Spec field | Required | Our current handling |
|---|---|---|
| `name` | Yes | Present in SKILL.md frontmatter ✓. Adapters that rewrite (codex, opencode, pi, openclaw) flip it to `<author>-<slug>` so parent-dir-must-match-name holds — ✓ compliant. |
| `description` | Yes | Present ✓. |
| `license` | No | In `meta.json`, **not** in SKILL.md frontmatter. Spec allows either; we should mirror it into frontmatter too for tools that read only frontmatter. |
| `compatibility` | No | Not surfaced today. Should be addable. |
| `metadata` | No | We use `meta.json` as our extension format. Should ALSO expose under `metadata.<our-namespace>` in SKILL.md frontmatter for spec compliance. |
| `allowed-tools` | No | Not surfaced today. Optional. |

**We are spec-compatible today.** Cleanup work (license-in-frontmatter + metadata namespace bridge) is small and can ship in `0.1.2` or `0.2.0`.

### `skyll` (assafelovic/skyll) — the competitor

- PyPI: `skyll` v0.1.1 — owner `assafelovic` (Assaf Elovic, creator of GPT Researcher, ~17k stars on that project).
- GitHub: `github.com/assafelovic/skyll` — 227 stars, 24 forks. Created 31 Jan 2026, last pushed 2 Apr 2026. Active.
- Website: `skyll.app` with API at `api.skyll.app`.
- **Self-positioning**: "A tool for autonomous agents like OpenClaw to discover and learn skills autonomously."

**Skyll's product shape:**
- REST API + MCP server + Python client. Hosted at `api.skyll.app`, self-hostable.
- **Federated discovery** — aggregates skills from external GitHub repos (vercel-labs/ai-skills, skills.sh, community). The "skill" is the markdown file at the source repo; Skyll just indexes + caches metadata.
- **Pull-based, agent-initiated search** at runtime (`search("query")`, `get(source, skill_id)`).
- **Trust**: maintainer-gated PR review only. No content hashes, no signing, no version pinning, no yank/deprecate.
- **Mental model: search engine for skills** (Google for SKILL.md).

**Our product shape (current):**
- CLI + local registry repo + adapter system + dogfood-hardened submit pipeline.
- **Centralized curated registry** — skills live IN the registry repo, content-hashed, version-tagged.
- **Setup-time user-initiated install** with per-host adapter writing to the host's canonical skills directory.
- **Trust**: PR review + sanitize + security_scan + content-hash verification + immutable GitHub numeric ID author binding + yank/deprecate semantics.
- **Mental model: package manager for skills** (npm/pip for SKILL.md).

### Skyll's wedges (what they have, we don't)

1. **Runtime MCP discovery.** A running agent can mid-task query Skyll and pull a skill into context. Our model is install-before-run. **This is the gap Samuel wants to close in session 6.**
2. **Federated source aggregation.** If their network grows, every other skill source feeds them.
3. **Brand and traction.** Live website, 227 stars, polished docs, MCP integration already shipped.

### Our wedges (what we have, they don't)

1. **Install-into-host adapter system.** 6 hosts: claude-code, hermes, codex, opencode, pi, openclaw. Skyll returns markdown; we put files on disk where the agent runtime finds them. Spec's "parent dir == name" constraint enforced per host. They'd have to build 6 adapters from scratch.
2. **Versioning + reproducibility.** Semver pinning (`@0.1.0`), tagged immutable releases, content hashes per version. Required for any production deployment.
3. **Yank + deprecate semantics.** First-class. When (not if) a published skill has a CVE, we can recall it. They can't.
4. **GitHub-ID author immutability.** We pin to numeric `github_id` which survives username/repo renames and transfers. They pin to repo path which breaks on rename.
5. **Sanitize + security_scan pipeline.** Automated before merge. They have PR review only.
6. **Self-contained, no hosted dependency.** Just git + raw content fetch. They require `api.skyll.app` (or self-host FastAPI).

### Strategic verdict

These products **don't compete head-on; they compete on philosophy**:
- Skyll = Google for skills (search engine).
- Ours = npm for skills (package manager).

Different users want different things. Both can win in the same ecosystem. **The agentskills.io 18k-star adopter base is large enough for both.** Our move is not to copy Skyll's federated-search model but to add their MCP runtime-discovery capability **on top of our package-manager core** — best of both worlds.

---

## Pending decisions (must be resolved before session 6 ships)

### 1. Project name (BLOCKING for PyPI + public)

The current name `agent-skills` is taken on PyPI by `datalayer/agent-skills` (a real Jupyter-related project, not a squatter). Session 5 explored many alternatives. Open questions Samuel left unresolved:

- **`skyll`** — confirmed unavailable (taken by the competitor; also semantic conflict).
- **`skillery`** — PyPI free, but **brand-contested** (Nashville coworking space `theskillery.com` since 2011, plus Skillery LLC coaching platform, plus `skillery.co`, plus several training apps). We'd be one of several "Skillerys."
- **`skill-forge` / SkillForge** — PyPI free, GitHub free. CurseForge-style lineage gives instant legibility. Samuel rejected as "not unique enough."
- **`techne`** — PyPI free. Greek for "skill/craft". Unique. Samuel didn't pursue.
- **Registry-positioning candidates not yet probed**: `canon`, `almanac`, `atlas`, `trove`, `archive`, `corpus`, `annals`, `gazette`, `manifest`, `compendium`, `anvil`, `omnibus`, `cairn`, `gazetteer`.
- **Italian-flavored candidates**: `bottega` (Renaissance artisan's workshop — direct hit on the "master-apprentice agent skills" metaphor), `archivio`, `ateneo`.

**Session-6 action**: probe the registry-positioning slate + bottega for PyPI / GitHub / domain / brand conflicts. Pick one. Don't ship until decided.

### 2. Positioning angle (drives README + landing)

Two viable framings:

- **"The package manager for agent skills"** — directly contrasts Skyll's search-engine model. Honest, technical, attracts production-minded users. Recommended.
- **"The curated library for agent skills"** — Alexandria framing Samuel originally articulated. More poetic, less technical. Could combine with the above.

**Session-6 action**: write the README hero copy in one of these two framings. Decide before publishing.

### 3. Release plan order

Three viable orders:

- **A (recommended)**: Bump 0.1.2 → rename → make public → publish PyPI → announce. Lowest risk; everything lined up first.
- **B**: Bump 0.1.2 → make public → publish PyPI under old name → rename later. Squats the chosen name on PyPI but risks user confusion.
- **C**: Rename first, then 0.1.2 ship. Cleanest narrative but the rename is invasive.

Recommend A. Each step is small.

---

## Session-6 mission and concrete plan

Mission: **transition from "private dogfood-hardened prototype" to "public package on PyPI, positioned as the registry for the Anthropic open standard, with the first dynamic-discovery MCP integration shipped or near-shipped."**

### Phase 1 — Cleanup + rename + version bump (small, mechanical)

1. **Pick the project name.** Probe the registry-positioning slate + `bottega`. Confirm availability on PyPI + GitHub + key domains. Decide. Update memory.
2. **Rename across the codebase.**
   - `pyproject.toml`: `name`, `[project.scripts]` CLI binary.
   - `agent_skills/__init__.py`: docstring + `__version__`.
   - `README.md`, `CONTRIBUTING.md`, `SCHEMA.md`, `docs/` references.
   - `clients/skill_discovery/update.py`: `DEFAULT_REGISTRY_URL` + `DEFAULT_REGISTRY_REPO` constants.
   - `agent_skills/cli.py`: any branded strings.
   - Tests that hardcode `"agent-skills"` strings.
   - Optional: rename Python module `agent_skills/` → `<new_name>/` (invasive — recommend keeping module name `agent_skills` for now, only rebrand external surface).
3. **Bump version 0.1.1 → 0.1.2.**
   - `pyproject.toml` version.
   - Add `CHANGELOG.md` (does not exist yet) with entries for F1/F2/F3/F3b dogfood fixes + the 4 new adapters (codex, opencode, pi, openclaw).
4. **Spec-alignment improvements (cheap):**
   - Add `license` mirror in SKILL.md frontmatter at install time (codex/opencode/pi/openclaw adapters already rewrite — small extension).
   - Add `metadata.<our-namespace>` bridge in SKILL.md frontmatter so spec-only readers see our registry fields.
   - Add `compatibility` field surfacing where applicable.

### Phase 2 — Public + PyPI ship

5. **Make repo public**: `gh repo edit samuelgudi/<new-name> --visibility public` (or `samuelgudi/agent-skills` if not renaming the repo, just the package).
6. **PyPI publish**: `python -m build && twine upload dist/*`. Verify the install command works on a clean machine.
7. **README hero**: write the positioning copy (package-manager-for-agent-skills + Alexandria-curated-library combo). Include the explicit contrast with Skyll where useful.
8. **Verify CI badges resolve** against public Actions URLs.

### Phase 3 — Dynamic discovery MCP server (the new feature Samuel wants)

This is the post-launch sprint. Design + ship a thin MCP server that exposes the registry via the agentskills.io progressive-disclosure model.

**Design draft:**

```
MCP server name: <new-name>-mcp (e.g. canon-mcp, bottega-mcp)

Tools:
  list_skills(category?, tag?, agent_compat?, limit?)
    -> [{id, name, description, version, category, tags}]   # stage 1 metadata only

  search_skills(query, limit?)
    -> [{id, name, description, score, snippet}]            # stage 1 + relevance

  get_skill(id, version?)
    -> {id, version, name, description, body, files[]}     # stage 2 full SKILL.md

  get_skill_file(id, file_path, version?)
    -> file_bytes / text                                    # stage 3 on-demand resources

  install_skill(id, version?, agent?)
    -> {target_path, marker_path, install_log}              # OUR UNIQUE WEDGE
```

Stack: Python stdlib + the existing `clients/skill_discovery/` cache. Reuse the rollback-guard and adapter-detect code we already have.

Hosting: `mcp.<new-name>.app` (or self-hosted SSE/stdio per MCP spec). Don't require the hosted service to be up for the CLI to work.

Differentiation: `install_skill` is the headline. No competitor offers cross-host install via MCP today. An agent on Claude Code mid-task can call `install_skill("samuelgudi/some-skill", agent="claude-code")` and the adapter writes the skill into `~/.claude/skills/` so the agent can immediately use it.

### Phase 4 — Adapter expansion to claim the ecosystem

We currently cover 6 of ~35 official adopters. Priority order for next batch, by audience size + spec compliance:

1. **Gemini CLI** (Google) — `~/.gemini/extensions/` or similar. High-traffic.
2. **Cursor** — `.cursor/rules/*.mdc` shape may differ; verify their skills convention first.
3. **GitHub Copilot** — VS Code agent skills convention.
4. **OpenHands** — open-source, audience overlap with us.
5. **Goose** (Block) — open-source.
6. **Junie** (JetBrains) — IDE-bound but listed.
7. **Amp**, **Letta**, **Roo Code**, **Workshop**, **Kiro** — second batch.

Each adapter: detect signal + target path + frontmatter rewrite (if needed) + ~10 tests. Pattern is now well-trodden; ~100 LOC per adapter.

### Phase 5 — Positioning + outreach

9. **Submit a PR to `agentskills.io`** adding us to the Client Showcase (we're a registry, not a client, so confirm placement — possibly a "Registries" section if it exists, or a contribution to the Resources section).
10. **HN / Twitter / Reddit launch** — only after PyPI is live + repo is public + README is polished. Story arc: "I built a package manager for the Agent Skills open standard. Here's how it differs from Skyll."
11. **Reach out to Assaf (skyll author)** — friendly note, not adversarial. Two products, complementary niches; possible interop opportunity (Skyll could index our registry as one of its federated sources).

---

## Decisions to make at session 6 start

Before you write any code:

1. **Lock the project name.** Probe the slate (see § Pending decisions). Don't proceed until decided.
2. **Lock the positioning angle.** Package manager vs library vs combo. Drives README + announce copy.
3. **Lock the release order.** Recommend A (rename → 0.1.2 → public → PyPI). Don't skip steps to "ship faster" — there's no fire.

---

## Verification commands (run at session 6 start to confirm state)

```bash
cd X:/Repos/agent-skills
git log --oneline -10                       # HEAD should be 3c913b4 (session-5 handoff doc)
git status --short                          # should be empty
python -m pytest tests/ -q --tb=no          # expect: 223 passed, 1 skipped
gh run list --limit 1 --workflow=ci.yml     # expect: completed/success
gh repo view samuelgudi/agent-skills --json visibility | jq .visibility
                                             # expect: "PRIVATE" until phase 2
```

---

## Files to read at session 6 start (in order)

1. **This file** — `docs/handoff/2026-05-12-execution-handoff-session6.md`. Contains the strategic reframe + plan.
2. **`docs/handoff/2026-05-12-execution-handoff-session5.md`** — what session 5 closed with (pre-discovery).
3. **`docs/dogfood/2026-05-12-submit-pipeline-walkthrough.md`** — the dogfood findings + regression locks.
4. **`docs/handoff/2026-05-12-execution-handoff-session4.md`** — prior backstory.
5. **`SCHEMA.md`** — current schema. Compare against agentskills.io spec § "Frontmatter".
6. **`agentskills.io/specification`** (web) — re-read the spec page; it's the ground truth our format must align with.
7. **`github.com/agentskills/agentskills`** (web) — check for spec changes since 2026-05-12.

---

## Embedded next-session prompt (paste verbatim into a fresh Claude Code session at `X:/Repos/agent-skills`)

> agent-skills is at HEAD `3c913b4` on `main`. 223 tests passing on Windows; CI green Linux × macOS × Windows × Python 3.10–3.13. v0.1.1 is functionally complete + dogfood-hardened + ships 6 working adapters (claude-code, hermes, codex, opencode, pi, openclaw).
>
> **Read the session-6 plan before doing anything**: `docs/handoff/2026-05-12-execution-handoff-session6.md`. It contains a strategic reframe (agentskills.io is an Anthropic-blessed open standard with 18k stars and ~35 adopters; we are already spec-compatible; Skyll is a direct competitor with a different — federated-search — model) that wasn't visible in earlier handoffs. The plan defines three pending decisions (name, positioning, release order) that BLOCK any code work, then a phased implementation plan (rename + 0.1.2 → public + PyPI → MCP server for dynamic discovery → adapter expansion to the wider ecosystem → positioning + outreach).
>
> Also read, in order: `docs/handoff/2026-05-12-execution-handoff-session5.md` (session-5 close-out), `docs/dogfood/2026-05-12-submit-pipeline-walkthrough.md` (dogfood findings), `docs/handoff/2026-05-12-execution-handoff-session4.md` (prior backstory).
>
> Verify state:
> ```
> cd X:/Repos/agent-skills
> git log --oneline -10                       # HEAD should be 3c913b4
> python -m pytest tests/ -q --tb=no          # expect: 223 passed, 1 skipped
> gh run list --limit 1 --workflow=ci.yml     # expect: success
> ```
>
> **Stop conditions**: do not start renaming, publishing, or shipping any code until Samuel has confirmed (1) the project name, (2) the positioning angle, and (3) the release order. The plan recommends specific values for each but Samuel makes the call. If you find a contradiction between docs and code state, the code is authoritative; ask Samuel before silently aligning the docs.
>
> **The name decision is the gating one.** Probe these candidates on PyPI + GitHub + key domains before surfacing options: `canon`, `almanac`, `atlas`, `trove`, `archive`, `corpus`, `annals`, `gazette`, `manifest`, `compendium`, `anvil`, `omnibus`, `cairn`, `gazetteer`, `bottega`, `archivio`, `ateneo`. Surface a focused slate of 3-4 confirmed-available names with brand-conflict checks and let Samuel pick. Do not push more than one slate without asking what feels off.

---

## What's explicitly NOT in scope for session 6 (defer to session 7+)

- F4 (init command-detector prose false-positives) — same class as F8a env-var fix; ship in 0.1.3.
- F5 (init "no-detect" sentinel) — UX cleanup.
- Hermes verify asymmetry — long-standing carry-over from session 4.
- Signing infrastructure (`registry.json.sig`) — spec § 19.
- Linux dogfood pass via Milo — wait until public + PyPI so Milo runs `pip install <new-name>` like a real user would.
- Adapters beyond the next-batch list above.

---

## Open intelligence questions for Samuel to consider before session 6

1. **Is Milo's WSL Hermes setup ready to be a real first user**, or do we want one more in-house pass first?
2. **Will we apply to be listed on agentskills.io's client showcase**, or wait until we have more stars / community traction first?
3. **Should the MCP server share the project name** (e.g. `<name>-mcp`) or have its own product identity?
4. **Hosting story for the MCP server**: do we run `mcp.<name>.app` ourselves, or ship stdio-only and let users self-host?
5. **Relationship with skyll's Assaf**: cold reach out now, after ship, or never? Trade-off: he could index us as a source (free distribution); also early signaling that we exist puts us on his radar (potential learning, potential preemption).

End of session-6 plan handoff.
