# I Know Kung Fu — session 11 execution handoff

| Field | Value |
|---|---|
| Date written | 2026-07-17 (end of session 11 — the "resumption" session after a 2-month pause) |
| Branch | `main` |
| HEAD (last work commit) | `985ea5c` — *release: v0.1.9 — trust-model hardening* (this handoff commit follows it) |
| Latest release | **v0.1.9** — on PyPI, GitHub release tagged, CI green |
| Test suite | **494 passing / 1 skipped** (27 new regression tests this session) |
| Registry contents | **10 skills**: 8 real (incl. the **first external contribution**, `kriptoburak/hermes-tweet`) + 2 meta-skills (at 0.2.0) |
| Open external PRs | **#6** `theheavenlyd3mon/token-compression` — changes requested (see below), waiting on contributor |

> **Read this entire file before doing anything in session 12.** Session 11 closed the entire security backlog, merged the first external skill, and produced a strategic repositioning decision framework. Session 12 is about the repositioning + launch sequence.

---

## What session 11 accomplished

### 1. External PR queue unblocked (it had been rotting since May/June)

- **PR #3 `kriptoburak/hermes-tweet` — MERGED and promoted.** Validated + scanned locally with main's own pipeline (clean), squash-merged, on-merge promotion ran end-to-end (promote → manifest regen → tag → push). **The cross-fork → CI → promotion path is now battle-tested** — it was the "not yet exercised at scale" caveat in AGENTS.md. Registry is at 10 skills.
- **PR #6 `theheavenlyd3mon/token-compression` — changes requested** (comment posted in Samuel's voice): missing `SANITIZATION.diff` + `scan_results.json` next to REVIEW.md, and a dangling reference to `references/iknowkungfu-submission-workflow.md` to drop. Skill content itself reviewed as good; **merge same-day when the contributor pushes**.
- **Operational gotcha discovered:** GitHub silently holds Actions runs for first-time-contributor forks until the maintainer clicks **"Approve and run"** in the PR UI. There is no API path. This is why both PRs showed zero checks for months. Watch for it on every new external PR.
- **Notable:** both external submissions were **agent-mediated** (PR #3 branch `codex/submit-hermes-tweet-skill` = a Codex agent ran the pipeline; PR #6 authored by "Senna / Hermes Agent"). Two agents, two different users, two different runtimes, spontaneously walked the contribution loop. This is load-bearing evidence for the positioning (see § Strategy).

### 2. Security hardening — v0.1.9 released (PyPI + tag + GitHub release)

Five findings from an internal review of the trust model, all closed with regression tests:

1. `security_scan.py` now scans **SKILL.md / all skill markdown** (the file loaded verbatim into agent context was previously unscanned). Five new rules in `rules.yaml`: `MD-EXFIL-INSTRUCTION`, `MD-PROMPT-OVERRIDE`, `MD-HIDDEN-COMMENT`, `MD-INVISIBLE-UNICODE` (blocks), `MD-B64-PAYLOAD` (warn); `SH-CURL-PIPE` extended to markdown. Zero false positives across the 10 registry skills.
2. CI (`ci.yml`) now runs `validate.py` + a **fresh** `security_scan.py` against `submitted/` — no longer trusts the submitter-provided `scan_results.json` alone. `on-merge.yml` gates promotion on the same checks + id-grammar enforcement.
3. Path traversal closed: `adapters/_base.py::split_skill_id` validates ids against the registry grammar before any path construction (all six adapters); `checked_uninstall` cross-checks the marker's id everywhere before `rmtree`.
4. `atomic_install` uses a move-aside swap — no more delete-then-move window that could destroy a working install on interruption.
5. `generate_manifest.py` refuses malformed directory names (id grammar enforced at manifest time too).

Plus: latent Windows bug fixed (`rules.yaml` read as cp1252 → scanner crash; stdout reconfigured to UTF-8). Retroactive CHANGELOG record added for the meta-skills 0.2.0 bump.

### 3. Market research (July 2026) + strategic decision

Landscape: category exploded (Anthropic official marketplace pre-configured in Claude Code; Microsoft APM cross-runtime; Vercel Skills.sh; Skilldex on arXiv = near-identical feature set incl. contribute-back on paper; SkillsMP-type aggregators at millions of scraped SKILL.md files). iknowkungfu traction: effectively pre-launch (1 star, ~33 dl/week).

**Positioning thesis (recommended, pending Samuel's final call):** drop "compounding skill library" as the headline (now category-common rhetoric) and lead with the **combination** nobody else has:

> *The verified supply chain for agent skills — the only registry where agents improve each other's skills, safely.*

Two legs, both now demonstrably true: (a) **trust chain** — content-hash verify, hard-refused yanks, CI re-validation + markdown scanning, gated promotion, provenance (ADR-002); (b) **cross-user agent contribution loop** — proven by real external agents this session. Open marketplaces can't afford (b) without (a); platform owners won't do runtime-neutral. Honest gap: the *improvement* branch of the loop (external agent bumps an existing skill's version) is implemented but not yet exercised by an outsider — closing that is Step 2 of the plan below.

---

## The plan (agreed with Samuel, 2026-07-17)

Sequenced to arrive at launch with the "loop + trust" story **demonstrated**, not claimed:

1. **Keep the loop closed (continuous, top priority).** Merge PR #6 same-day when updated (remember "Approve and run"). Never again let an external PR sit >48h — review throughput *is* the product.
2. **Trigger the first improvement iteration.** After #6 merges, invite both agent-contributors to walk the missing branch: use an existing registry skill, find a flaw, submit a **new version** via `kfu submit`. First complete compounding iteration by external agents = the launch case study.
3. **Repositioning pass (1 session, before the post).** Rewrite README + launch post around the supply-chain thesis. The draft post is stale anyway ("seven real skills" → now 10, first external contribution, v0.1.9 hardening).
4. **Soft-launch post (Samuel's action).** Hermes Discord first, after step 3. Don't block on step 2 — the launch feeds it.
5. **Signing + lockfile → v0.2.0** (spec § 19). The piece that turns "curated" into "provable". After launch, not before.
6. **Import pilot `obra/superpowers-skills`** (ADR-002) — after the post, with Samuel's explicit greenlight, single-source.

Parallel low-cost: check presence/compat where agents already look (agentskills.io standard; possibly a Claude Code plugin-marketplace manifest).

### Explicitly NOT in scope unless Samuel overrides

- Bulk imports; broad subreddit/general-Discord launch (Hermes Discord first); adapters beyond the current 6; persistent default-agent UX (unchanged nice-to-have).

---

## Verification commands at session start

```bash
cd X:/Repos/iknowkungfu
git log --oneline -5                       # HEAD: session-11 handoff commit on top of 985ea5c
python -m pytest tests/ -q --tb=no         # expect: 494 passed, 1 skipped
python scripts/validate.py --all           # expect: all 10 skills clean
python scripts/generate_manifest.py --check ; echo "exit=$?"   # expect 0
gh pr list -R samuelgudi/iknowkungfu       # check whether #6 was updated
gh run list --limit 2                      # expect CI + On-merge green
```

## Open questions for Samuel at session-12 start

1. ~~Final call on the repositioning~~ — **DECIDED and EXECUTED same session** (Samuel confirmed 2026-07-17): README lead, AGENTS.md intro, PyPI description, and the soft-launch post (v2) now lead with "the verified supply chain for agent skills"; commit `f0e679f`. Plan step 3 is done — the sequence now starts at step 4 (Samuel posts).
2. Has the contributor updated **PR #6**? If yes → review + merge + step 2 invitation.
3. **Soft-launch post**: rewritten and ready in `docs/launch/` — awaiting only Samuel's final read and posting to the Hermes Discord.

Naming rule, applies everywhere: the agent is "Hermes Agent", never Milo/MILO. Always treat code as ground truth and reconcile docs to it if they disagree.
