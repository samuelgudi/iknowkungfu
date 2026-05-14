# I Know Kung Fu — session 8 execution handoff

| Field | Value |
|---|---|
| Date written | 2026-05-13 (end of session of 2026-05-13) |
| Date of next session | TBD |
| Branch | `main` |
| HEAD (last commit) | `26b7ce2` — *0.1.5: kfu --version + suppress first-pull unsigned-registry warning* |
| Remote | `samuelgudi/iknowkungfu` |
| Repo visibility | **PUBLIC** |
| Latest release | `v0.1.5` — tagged + GitHub release + on PyPI (`iknowkungfu==0.1.5`) |
| Test suite | **450 passing / 1 skipped** on Windows × Python 3.13. CI green on `26b7ce2` across Linux × macOS × Windows × Python 3.10-3.13 |
| Registry contents | **3 skills**: `samuelgudi/semver-bump-decider` (real, general-utility), `samuelgudi/iknowkungfu-contribution` + `samuelgudi/iknowkungfu-discovery` (meta-skills about iknowkungfu itself) |
| Field tests | Two passed — Hermes Agent on 0.1.3 (→ patched into 0.1.4) and on 0.1.4 (→ polished into 0.1.5, clean-pass verdict) |

> **Read this entire file before doing anything in session 8.** The product is shippable and twice field-tested. The single thing blocking a broad public launch is **catalog depth** — a registry whose `kfu search` returns one general-purpose skill converts poorly on cold channels (Reddit, general Discord servers), and those are one-shot first impressions. Session 8 is about fixing that.

---

## Strategic context — why session 8 exists

After the 0.1.5 ship, Samuel asked whether to start presenting the repo on subreddits / Discord servers now, or wait. The conclusion reached this session:

- **Don't do the broad subreddit/general-Discord blitz yet.** The catalog is too thin to convert cold traffic, and you only get one first impression per community.
- **The Hermes Agent's Discord is the right first audience** for a soft-launch — aligned users, first-class hermes adapter, "your agent learns a new skill" lands natively, and a thin catalog reads there as "early, come seed it" rather than "empty."
- **Before even the soft-launch**, thicken the catalog so the product can demonstrate its core value.

Samuel's proposal, accepted as the session-8 mission: assemble a curated set of genuinely useful skills and include them from the start. Split into two tracks because they have very different risk profiles.

---

## The plan

### Track 1 — First-party skill authoring (safe; the bulk of session 8)

Author **3-5 genuinely useful, generalizable skills** that Samuel owns outright. These are clean first-party registry entries — no provenance or licensing complications, they go straight through the normal flow.

**Candidate sources** (Samuel picks — these are starting points, not a mandate):
- Domain material Samuel already has skill-shaped: homelab documentation workflow, Caddy local-proxy setup patterns, Thalamus/PTC helper patterns, a deployment-runbook skill, a "session handoff" skill.
- **Hard filter — generalizability**: `CONTRIBUTING.md` § "Personal and private skills" explicitly says skills tightly scoped to one person's setup (specific paths, personal API keys, private services) degrade the registry's signal-to-noise. A skill that only works for Samuel must NOT be published, or must be genericized first. When in doubt, ask Samuel "would a stranger get value from this unchanged?"

**Per-skill authoring checklist** (all rules from `SCHEMA.md` + `CONTRIBUTING.md` — read both before starting):
1. `SKILL.md` — uppercase, case-exact filename. Frontmatter `name` (≤64 chars, lowercase + hyphens, must match parent dir) + `description` (complete sentence, WHEN-to-invoke not just WHAT).
2. `meta.json` — `kfu init <dir>` scaffolds it interactively. `author.github_id` must be the numeric ID (CLI fetches via `gh api`). `category` from the 8-value taxonomy. `agent_compat` — include at minimum `claude-code` and `hermes`; add `codex`/`opencode`/`pi`/`openclaw` only if actually verified.
3. `REVIEW.md` — `kfu submit` generates the template. Fill all six fields honestly. For any skill with a `scripts/` dir (`has_scripts: true`), real test evidence is **mandatory** — actual commands + actual output.
4. Validate locally: `python scripts/validate.py --all` must report `clean`.
5. Add to `skills/samuelgudi/<slug>/`, regenerate the manifest (`python scripts/generate_manifest.py`), confirm `--check` exits 0.
6. Each skill is its own commit. Push after each (or batch — Samuel's call, but push before session end).

**Target outcome**: registry goes from 1 real skill → **5-8 real skills**, all hermes-compatible, all passing validate + security scan.

### Track 2 — Third-party import path design (design only; do NOT import anything yet)

Importing "the best OSS skills out there" collides with locked design decisions. **This track is a design pass, not an implementation.**

**The collision** (must be resolved before any third-party skill enters the registry):
- iknowkungfu binds every skill to the contributor's **immutable GitHub numeric ID** at submit time (Decision #4, anti-impersonation by design). Re-hosting someone else's skill means either misattributing it to Samuel or needing the original author's ID.
- `SECURITY.md` makes the submitter reviewer-of-record. Bulk-importing means Samuel vouches for code he didn't write.
- Each source skill carries its own license — redistribution needs license compatibility + preservation.

**What the design pass must produce:**
1. A new ADR in `docs/decisions.md` defining an **import/curation provenance model** distinct from the normal submit flow. Sketch of the shape (refine in-session): an `imported` status or a `provenance.imported_from` block; original author credited in a **display-only, non-identity-binding** field; original license preserved and surfaced; clear marking so consumers see "imported, curated by samuelgudi" not "authored by samuelgudi."
2. Corresponding `SCHEMA.md` updates for the new fields.
3. A decision on whether imports even belong in v0 at all — **"keep the registry purely first-party for launch, defer imports entirely" is a perfectly clean call** and may be the right one. Don't force imports if the provenance model gets messy.

**Do not import any third-party skill until this ADR is written and Samuel has signed off on it.**

### Phase 3 — Hermes Discord soft-launch prep (only if Track 1 lands)

Once the catalog has ~5-8 real skills:
- Draft the Hermes Discord soft-launch post (positioning: "package manager for Agent Skills, hermes adapter is first-class, here's `kfu install`").
- Naming rule applies to the post and every public artifact: it is **"Hermes Agent"**, never Milo/MILO. See `feedback-hermes-agent-naming` in Claude memory.
- Do not post to general subreddits / unaligned Discords yet — that round waits until the catalog can carry the pitch.

---

## What is explicitly NOT in scope for session 8

- **The broad subreddit / general-Discord launch.** Catalog-gated. Not session 8.
- **Persistent default-agent UX** (Hermes Agent 0.1.4 field-test finding #3): multi-host environments need `--agent hermes` on every adapter call. `IKNOWKUNGFU_DEFAULT_AGENT` env var is the current escape hatch and the multi-host error message is already actionable. Nice-to-have, not launch-blocking. Pick up only if Track 1 finishes early.
- **Adapters beyond the current 6** (Gemini CLI, Cursor, GitHub Copilot, OpenHands, Goose): ~20 spec-listed agents still missing. Not launch-blocking.
- **Signing infrastructure** (spec § 19): not implemented. The 0.1.5 change means the unsigned-registry warning stays silent until signing rolls out.
- **`iknowkungfu-mcp` PATH note for `uv tool install`**: minor doc addition the Hermes Agent suggested (after `uv tool install`, `~/.local/bin` may need to be on the host process PATH). Trivial — fold into a Track 1 commit if convenient, otherwise skip.

---

## Verification commands at session start

```bash
cd X:/Repos/agent-skills
git log --oneline -5                        # HEAD should be 26b7ce2 (or further)
git status --short                          # expect clean
python -m pytest tests/ -q --tb=no          # expect: 450 passed, 1 skipped
python scripts/validate.py --all            # expect: all skills "clean"
python scripts/generate_manifest.py --check ; echo "exit=$?"   # expect exit=0
gh run list --limit 1 --workflow=ci.yml     # expect: success
kfu --version                               # expect: kfu 0.1.5 (or further)
python -c "import json; print(len(json.load(open('registry.json'))['skills']), 'skills')"  # currently 3
```

## Authoritative references — read before project work

1. `CHANGELOG.md` — newest source of truth per release.
2. `SCHEMA.md` — field-level reference for `meta.json` / `registry.json` / `yanks.json`, category taxonomy, slug grammar. **Read fully before authoring any skill.**
3. `CONTRIBUTING.md` — submission workflow, skill design guidelines, the personal-vs-generalizable filter, REVIEW.md template.
4. `SECURITY.md` — reviewer checklist, threat model. Relevant to Track 2.
5. `docs/decisions.md` — ADRs. Decision #4 (immutable GitHub-ID binding) is the one Track 2 collides with.
6. `docs/mcp-integration.md` — MCP wiring + authoritative per-adapter install paths.

Always treat code as ground truth and reconcile docs to it if they disagree.

## Open questions for Samuel (resolve at session start)

1. **Which skills for Track 1?** Bring 3-5 concrete candidates, or ask Claude to propose from your `~/.claude/skills/` directory + domain context — but you make the final generalizability call.
2. **Track 2: design now or defer entirely?** Writing the import-provenance ADR is worthwhile even if imports never happen in v0, because it clarifies the registry's identity. But "first-party only for launch" is a clean, defensible call. Decide before spending session time on it.
3. **Soft-launch timing**: tie the Hermes Discord post to one of their events, or post independently once the catalog is ready? (This session's read: don't wait for an event — post when the catalog is ready.)
