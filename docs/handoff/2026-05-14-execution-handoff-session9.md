# I Know Kung Fu — session 9 execution handoff

| Field | Value |
|---|---|
| Date written | 2026-05-14 (end of session 8) |
| Date of next session | TBD |
| Branch | `main` |
| HEAD (last work commit) | `0e5a4bc` — *feat(origin): implement ADR-002 import/curation provenance model* (the handoff-doc commit follows it) |
| Remote | `samuelgudi/iknowkungfu` |
| Repo visibility | **PUBLIC** |
| Latest release | `v0.1.5` — on PyPI (`iknowkungfu==0.1.5`). **No release was cut in session 8** — see open question 2. |
| Test suite | **458 passing / 1 skipped** on Windows × Python 3.13. CI green on `0e5a4bc` across Linux × macOS × Windows × Python 3.10-3.13 |
| Registry contents | **9 skills**: 7 real general-purpose + 2 meta-skills. See "Registry state" below. |
| Field tests | Two passed (Hermes Agent on 0.1.3 → 0.1.4, and on 0.1.4 → 0.1.5). No new field test in session 8. |

> **Read this entire file before doing anything in session 9.** Session 8 closed out both tracks of the session-8 plan: the catalog is now thick (7 real skills, up from 1) and the third-party import tooling is designed *and* implemented. The product is shippable and the catalog can now carry a launch pitch. Session 9 is about the soft-launch — and a release decision.

---

## What session 8 accomplished

Session 8's mission was "thicken the catalog before any broad launch." Both tracks landed.

### Track 1 — first-party skill authoring (DONE)

Six new instructions-only, generalizable first-party skills were authored, validated, and pushed. Each passed the hard "would a stranger get value from this unchanged?" filter — Samuel's personal skills (homelab-docs, openmymind-*, etc.) were deliberately excluded as too setup-specific.

| Skill | Category | What it teaches |
|---|---|---|
| `samuelgudi/session-handoff` | ai | Handing off agent work across a context-window boundary |
| `samuelgudi/caddy-local-https` | ops | Caddy as a local reverse proxy with auto-HTTPS `.localhost` domains |
| `samuelgudi/keep-a-changelog` | dev | CHANGELOG discipline; pairs with `semver-bump-decider` |
| `samuelgudi/deployment-runbook` | ops | Writing a deploy runbook a stranger can follow under pressure |
| `samuelgudi/lessons-learned-log` | docs | Durable one-line capture of hard-won lessons |
| `samuelgudi/adversarial-test-design` | dev | Tests that actually catch regressions, not false-green tests |

Commits: 6 per-skill `feat(skills):` commits + 1 `chore(registry):` manifest regen. Registry went from 3 skills (1 real + 2 meta) to **9** (7 real + 2 meta).

### Track 2 — import/curation provenance model (DESIGNED + IMPLEMENTED)

The collision: re-hosting third-party skills breaks the immutable-GitHub-ID identity binding (Decision #4), because the `author` object does two jobs at once — identity/accountability *and* credit.

The resolution, captured in **ADR-002** (`docs/decisions.md`, Status: **Accepted**) and fully implemented:

- `author` is **unchanged structurally**, clarified to mean **curator / maintainer-of-record**. Decision #4, CI verification, reviewer-of-record chain — all intact.
- A new optional **`origin` block** in `meta.json` carries original authorship as **display-only, non-identity-binding credit**: `{author_name, author_url?, repo, ref, imported_at}`. Named `origin` (not `provenance` — that name was already taken by a derived field).
- **Presence of `origin` is the import marker** — there is no separate `imported` flag.
- The top-level `license` field carries the source license; there is no `origin.license` (an importer can't re-license, so it would only duplicate).
- `validate.py` permits `LICENSE`/`LICENSE.txt`/`NOTICE` in the root of a skill *that has an `origin` block*, and rejects them otherwise.
- `kfu show` renders imported skills as *"curated by `<curator>`, originally by `<origin author>`"* plus an Origin section. First-party output unchanged. `kfu search` was left untouched — it does not surface authorship.

Implementation touched: `scripts/schema.json`, `scripts/validate.py`, `scripts/generate_manifest.py`, `agent_skills/verbs/show.py`, `SCHEMA.md` (new § 9), the spec (`docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md`), `docs/decisions.md`. Tests: 1 good fixture (`tests/fixtures/good/imported`) + 3 bad fixtures + 8 new tests (TDD, red-first).

**Critical:** accepting ADR-002 authorised the *tooling*. **No third-party skill has been imported.** Each import remains a per-skill, human-reviewed decision, and the ADR's recommendation — defer actual importing past launch — still stands.

---

## Registry state (9 skills)

Real general-purpose (7): `adversarial-test-design`, `caddy-local-https`, `deployment-runbook`, `keep-a-changelog`, `lessons-learned-log`, `semver-bump-decider`, `session-handoff`.
Meta-skills about iknowkungfu itself (2): `iknowkungfu-contribution`, `iknowkungfu-discovery`.

---

## The plan for session 9

### Phase 3 — Hermes Discord soft-launch (primary focus; now unblocked)

Session 8's handoff gated this on Track 1 landing. It landed. The catalog can now carry the pitch.

- Draft the Hermes Discord soft-launch post. Positioning: *"package manager for Agent Skills, the hermes adapter is first-class, here's `kfu install`."* A thin-but-real catalog reads on the Hermes Discord as "early, come seed it" rather than "empty."
- **Naming rule — applies to the post and every public artifact**: the agent is **"Hermes Agent"**, never Milo/MILO. See `feedback-hermes-agent-naming` in Claude memory.
- Do NOT post to general subreddits / unaligned Discords yet — that round still waits. The Hermes Discord is the aligned first audience.
- Session-8's read, still valid: don't wait for a Hermes Discord event — post when ready.

### Release decision — see open question 2

Session 8 shipped real, user-visible changes (6 new skills, the `origin` schema/validator/CLI feature) on top of `v0.1.5` with **no version bump**. Decide whether session 9 cuts **`v0.1.6`** (version bump in `pyproject.toml` + `agent_skills/__init__.py` + `agent_skills/mcp/__init__.py` + the HTTP User-Agent in `clients/skill_discovery/update.py`, plus a `CHANGELOG.md` entry). The new `keep-a-changelog` skill is, fittingly, the reference for the CHANGELOG entry.

### Explicitly NOT in scope for session 9 (unless Samuel overrides)

- **Actually importing third-party skills.** The tooling is ready, but ADR-002 recommends deferring imports past launch. If Samuel does want to pilot, the ADR specifies starting with `obra/superpowers-skills` (MIT, archived/stable, genre-aligned) — one clean source to prove the `origin` model end-to-end.
- **The broad subreddit / general-Discord launch.** Still catalog-and-timing gated.
- **Persistent default-agent UX** (Hermes Agent 0.1.4 field-test finding #3): multi-host environments need `--agent hermes` on every adapter call; `IKNOWKUNGFU_DEFAULT_AGENT` is the current escape hatch. Nice-to-have, not launch-blocking.
- **`iknowkungfu-mcp` PATH note**: after `uv tool install`, `~/.local/bin` may need to be on the host PATH. Trivial doc addition — fold into a commit if convenient.
- **Adapters beyond the current 6** (Gemini CLI, Cursor, Copilot, etc.). Not launch-blocking.
- **Signing infrastructure** (spec § 19): not implemented; unsigned-registry warning stays silent until it rolls out.

---

## Verification commands at session start

```bash
cd X:/Repos/agent-skills
git log --oneline -5                        # HEAD: the session-9 handoff commit, on top of 0e5a4bc
git status --short                          # expect clean
python -m pytest tests/ -q --tb=no          # expect: 458 passed, 1 skipped
python scripts/validate.py --all            # expect: all 9 skills "clean"
python scripts/generate_manifest.py --check ; echo "exit=$?"   # expect exit=0
gh run list --limit 1 --workflow=ci.yml     # expect: success
python -c "import json; print(len(json.load(open('registry.json'))['skills']), 'skills')"  # expect 9
```

## Open questions for Samuel (resolve at session start)

1. **Soft-launch post — tone and scope.** Who drafts it, how long, does it link specific skills, does it include a `kfu install` walkthrough? Bring preferences or let Claude draft a first version for review.
2. **Cut `v0.1.6`?** Session 8's work is unreleased. Either cut 0.1.6 now (clean: ship the catalog + `origin` tooling as a release the soft-launch post can point at) or defer the bump. Recommendation: cut it — the soft-launch reads better pointing at a fresh release.
3. **Import pilot — now or defer?** ADR-002 says defer past launch. Confirm that holds, or greenlight a `obra/superpowers-skills` pilot to exercise the `origin` tooling on real content.

## Authoritative references — read before project work

1. `CHANGELOG.md` — newest source of truth per release.
2. `docs/decisions.md` — ADRs. **ADR-002** (Accepted) defines the import/curation provenance model.
3. `SCHEMA.md` — field-level reference. **§ 9** covers imported skills; the `origin` object is in § 3.
4. `CONTRIBUTING.md` — submission workflow, the personal-vs-generalizable filter.
5. `SECURITY.md` — reviewer checklist, threat model. Relevant if the import pilot goes ahead.
6. `docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md` — the spec; it carries the `origin` field too.

Always treat code as ground truth and reconcile docs to it if they disagree.

---

## Next session — copy-paste prompt

```
Session 9 on iknowkungfu (X:\Repos\agent-skills). Read
docs/handoff/2026-05-14-execution-handoff-session9.md in full first — it's
the plan and the source of truth.

Start by running the verification commands in the handoff to confirm clean
state (HEAD = the session-9 handoff commit on top of 0e5a4bc, 458 tests
passing, CI green). Then resolve the three open questions at the bottom of
the handoff with me before doing anything — especially the release decision
(cut v0.1.6?) and the soft-launch post scope.

Primary focus: Phase 3 — draft the Hermes Discord soft-launch post. The
catalog is now thick enough to carry the pitch (7 real general-purpose
skills). Positioning: "package manager for Agent Skills, hermes adapter is
first-class, here's kfu install." Do not post anywhere yet — this session
produces a draft for my review.

Naming rule, applies everywhere in this repo and any public artifact: the
agent is "Hermes Agent", never Milo/MILO.

Do NOT import any third-party skill — ADR-002 recommends deferring imports
past launch, and that holds unless I explicitly greenlight a pilot.
```
