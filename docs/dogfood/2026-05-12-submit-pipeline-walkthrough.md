# agent-skills submit-pipeline dogfood walkthrough (session 5)

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Prior walkthrough | `2026-05-12-first-user-walkthrough.md` (covered install/verify/uninstall — registry-consumer side) |
| Scope | End-to-end contribution flow: author skill → `init` → `submit` → PR → CI → merge → on-merge promotion → registry update → install → verify → uninstall |
| Branch | `main` |
| Starting commit | `2f1a6ef` (post session-4 handoff) |
| Ending commit | `9bbb279` |
| Tests | 166 passing (was 158); 1 skipped (Linux/macOS-only) |
| State | Submit pipeline now operational end-to-end. Three blockers found and fixed during the walkthrough. |

This is the dogfood pass the session-4 handoff flagged as the **last untested pipeline path**. It found 3 blockers that fixture-based unit tests had missed, 1 high-severity timestamp bug, and 4 low-severity papercuts.

---

## What was done

1. **Pass A (rehearsal)** — fabricated a throwaway skill, ran the full `init` + `submit` flow against the live `samuelgudi/agent-skills` repo, opened PR #1, inspected output, closed without merging, cleaned up.
2. **`ask-gemini` audit** — reviewed Samuel's existing `~/.claude/skills/ask-gemini/SKILL.md` as Pass B candidate, found it too coupled to Samuel's setup to publish (Samuel references in prose, hardcoded `X:\` path, stale cutoff date). Switched candidates.
3. **Pass B (real submission)** — authored a clean-room skill `samuelgudi/semver-bump-decider` (universal SemVer decision aid, no scripts, no env vars, no Samuel coupling), ran `init` + `submit`, opened PR #2, all 14 CI checks green, **squash-merged**, watched `on-merge.yml` promote `submitted/` → `skills/samuelgudi/semver-bump-decider/`, regenerate manifest, tag `v0.1.0-samuelgudi-semver-bump-decider`, push.
4. **Round-trip** — `update` cache, `install --agent claude-code samuelgudi/semver-bump-decider`, observed `.agent-skills-marker.json` written with the canonical content hash + tree SHA, `verify` returned `CLEAN`, `uninstall` removed the directory.

End state of the registry: 3 skills published (`agent-skills-contribution`, `agent-skills-discovery`, `semver-bump-decider`).

---

## Findings

### F1 (BLOCKER, fixed) — `submit` did not push the contrib branch before `gh pr create`

Commit `6cb7669`.

`clients/skill_contribution/submit.py` called `git commit` then `gh pr create` with no `git push` in between. On a fresh branch, `gh pr create` aborts non-interactively with `"you must first push the current branch to a remote, or use the --head flag"`. The fixture-based submit tests use a shim `fake_gh` that always succeeds — it never required a real remote, so the bug passed all 5 tests.

**Fix**: insert `git push -u --force-with-lease origin <branch>` between commit and gh.
**Regression test**: `tests/test_submit.py::test_submit_pushes_branch_to_origin`. Modified `test_repo` fixture to wire a bare origin, so the existing happy-path test now exercises a real push.

### F2 (BLOCKER, fixed) — `on-merge.yml` regenerated manifest before committing the promotion

Commit `eed2d09`.

`on-merge.yml` did: `mv submitted/<flat>/<author>/<slug>/ skills/<author>/<slug>/`, `git add -A`, **regen manifest**, **then** `git commit`. At regen time the new file path had no git history, so `scripts/generate_manifest.py`'s `git log -- skills/<author>/<slug>/meta.json` returned empty, the fallback path also returned empty (because `git log --format=%T -- <uncommitted-file>` is empty), and `versions[v].sha` was written as the empty string.

Downstream: `agent_skills/verbs/install.py` does `git archive --format=tar <tree_sha>:<source_path>`. With `tree_sha = ""`, the command becomes `git archive :skills/...`, which git rejects with status 128 (`fatal: ambiguous argument`). Install was broken for **every** newly-promoted skill.

**Fix**: split the workflow into two commits — commit the promotion first, regen manifest (which now finds the just-made commit), commit the manifest. Tag still points to the promotion commit.

**Regression test**: `tests/test_on_merge_workflow.py::test_commit_promotion_precedes_manifest_regen` parses on-merge.yml and asserts the step ordering. Plus `test_promotion_step_does_not_commit` blocks a future refactor that re-combines them.

**Data fix**: regenerated `registry.json` locally so `samuelgudi/semver-bump-decider@0.1.0` got the correct `sha` (the v0.1.1 ship of this skill was published with `sha=""` in the original on-merge run; the manual regen fixed the published manifest).

### F3 (HIGH, fixed) — rollback guard did string-compare on `generated_at` across mixed TZ formats

Commit `9bbb279`.

`clients/skill_discovery/update.py` line 77 compared `generated_at` as raw strings: `if fetched.get("generated_at") < cached.get("generated_at")`. ISO 8601 strings with different timezone offsets cannot be string-compared meaningfully:

- Cached: `2026-05-12T10:43:59+02:00` (CEST — produced by my Windows-based manual regen of the on-merge artifact)
- Fetched: `2026-05-12T08:44:15Z` (UTC — produced by GHA in the on-merge run for the next commit)

In absolute UTC time, fetched is 16 seconds **newer**. But by ASCII sort, `"10:..."` > `"08:..."`, so the guard mis-classified fetched as older and refused to overwrite the cache. Install was therefore blocked from picking up the F2 manifest fix.

**Fix**: parse both sides as timezone-aware `datetime` and compare. Fails open (no-op) when either side is missing or malformed, matching prior leniency for corrupt cached files.

**Regression tests**: `tests/test_update.py::test_refresh_rollback_guard_handles_mixed_tz_formats` (the exact case from the dogfood — fetched IS newer in UTC) + `test_refresh_rollback_guard_blocks_older_across_tz` (opposite direction).

### F3b (related, fixed) — manifest timestamps depended on the generator's local timezone

Same commit `9bbb279`.

`scripts/generate_manifest.py` used `git log --format=%cI` which respects the local timezone. Manifests generated on GHA (Ubuntu/UTC) end with `Z`; manifests generated on a CEST dev box end with `+02:00`. Same commit timestamp, different formatting — non-deterministic across platforms, and a primary trigger for F3.

**Fix**: add `scripts.generate_manifest._to_utc_z` helper. Wrap `generated_at`, `versions[v].released`, and `provenance.merged_at`. All manifest timestamps now end with `Z` regardless of where the generator runs.

**Regression tests**: `test_generated_at_is_utc_z` (integration) + `test_to_utc_z_normalizes_offsets` (unit, including pass-through behavior for unrecognized values).

### F4 (LOW, deferred to v0.1.2) — `init` command-detector false-positives on prose

The command-detector in `agent_skills/verbs/init.py` uses word-boundary regex against `COMMAND_TOKENS = {ssh, git, curl, ..., npm, pip, go, ...}`. Any prose mention of these tokens in SKILL.md body fires:

- Throwaway skill mentioned `git pr create flow` in body → detected `git`.
- `semver-bump-decider` mentioned `npm, Cargo, pip-resolvers` as ecosystem examples in the 0.x section → detected `npm`, `pip` (`Cargo` survived because tokens are lowercase-only).

Same class as F8a from session 4 (env-var detector false-positives on prose acronyms). Acceptable for v0.1.1 ship but should be tightened by requiring shell-syntax context (e.g. detect only `npm install`, `npm run`, `npm ci`, not bare `npm`).

### F5 (LOW, workaround documented) — no clean way to say "no commands / no env vars" when init has detected some

In `init`, an empty answer at the `requires.commands (CSV)` prompt accepts the detected default. There is no `none` sentinel and no `--no-detect` flag.

**Workaround**: type a literal `,` at the prompt. The parser does `[c.strip() for c in raw.split(",") if c.strip()]` which produces `[]` for input `","`. Discovered by reading `init.py`.

Suggested improvement: add an explicit `--no-detect-commands` / `--no-detect-env-vars` CLI flag, or accept `-` or `none` as an explicit clear sentinel.

### F6 (LOW, defer) — Node.js 20 deprecation warning in workflows

GHA emits `"Node.js 20 actions are deprecated. ... Once Node.js 24 becomes the default, you can temporarily opt out by setting ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION=true. ... Node.js 20 will be removed from the runner on September 16th, 2026."`

`actions/checkout@v4` and `actions/setup-python@v5` still run on Node 20. Watch for newer pinned versions and bump.

### F7 (LOW, not a bug) — install requires `--agent` on hosts where multiple agent types are detected

`agent-skills install samuelgudi/semver-bump-decider` on Samuel's machine (which has both `~/.claude/` and a Hermes hint) emits:

```
Multiple agent hosts detected: claude-code, hermes.
Pick one with --agent, e.g.: agent-skills <verb> --agent claude-code
```

This is the intended behaviour from session 2 (the `AGENT_SKILLS_DEFAULT_AGENT` env var was added for this exact case). Worth documenting in CONTRIBUTING.md / README.md so first users don't think it's a bug.

---

## Tests added (regression locks)

All run as part of the standard `python -m pytest tests/`. Total now 166 passing (was 158 at session 4 close).

- `tests/test_submit.py::test_submit_pushes_branch_to_origin` — F1 lock.
- `tests/test_on_merge_workflow.py::test_commit_promotion_precedes_manifest_regen` — F2 lock (step ordering).
- `tests/test_on_merge_workflow.py::test_promotion_step_does_not_commit` — F2 lock (refactor police).
- `tests/test_on_merge_workflow.py::test_workflow_loads_as_yaml` — F2 lock (YAML well-formedness).
- `tests/test_update.py::test_refresh_rollback_guard_handles_mixed_tz_formats` — F3 lock (the exact dogfood case).
- `tests/test_update.py::test_refresh_rollback_guard_blocks_older_across_tz` — F3 lock (opposite direction).
- `tests/test_generate_manifest.py::test_generated_at_is_utc_z` — F3b lock (integration).
- `tests/test_generate_manifest.py::test_to_utc_z_normalizes_offsets` — F3b lock (unit).
- Modified `tests/test_submit.py::test_repo` fixture to wire a real bare origin so the entire submit test class now exercises real `git push`.

---

## Commits landed this session

| Commit | Scope |
|---|---|
| `6cb7669` | fix(submit): push contrib branch before gh pr create |
| `7fcc957` | Submit samuelgudi/semver-bump-decider v0.1.0 (#2) — the dogfood skill itself |
| `3dacb4f` | chore: promote samuelgudi/semver-bump-decider v0.1.0 + regenerate manifest (auto, on-merge.yml, pre-fix-F2) |
| `eed2d09` | fix(on-merge): commit promotion before regenerating manifest |
| `9bbb279` | fix(timestamps): normalize manifest to UTC, parse rollback guard as datetime |

---

## What's NOT done

1. **F4 (init command false-positives)** — same class as session-4 F8a env-var fix; deferred to v0.1.2.
2. **F5 (init: no-detect sentinel)** — UX papercut; workaround documented above.
3. **F6 (Node 20 deprecation)** — track upstream pin updates.
4. **Hermes verify asymmetry** — still open per session-4 handoff.
5. **PyPI publication** — still open. Next concrete step now that v0.1.1 is dogfood-hardened.
6. **Make repo public** — still open. v0.1.1 satisfies the "functional v0" gate; the submit pipeline is now confirmed working end-to-end.
7. **Adapter expansion** (Codex / OpenClaw) — out of scope for this session.

---

## Recommended next session

> agent-skills v0.1.1 is dogfood-hardened end-to-end (author → submit → CI → merge → on-merge → install → verify). HEAD `9bbb279`, 166 tests passing, CI green.
>
> The submit pipeline is no longer untested — three blockers were found and fixed in this session. Worth bumping to **v0.1.2** before going public, because the submit-flow fixes are user-facing.
>
> Concrete next steps:
> 1. **Version bump 0.1.1 → 0.1.2.** Add a brief CHANGELOG entry citing F1/F2/F3/F3b and the dogfood walkthrough doc.
> 2. **Address F4** (init command-detector false-positives on prose) — requires shell-syntax context like the F8a env-var fix.
> 3. **PyPI publication** — `python -m build` + `twine upload`. Reserve the name.
> 4. **Make repo public.** CI badges in README only work once public.
> 5. **Hermes/Codex/OpenClaw adapters** — declared in `agent_compat` but only `claude-code` and `hermes` have adapters today. Build out when target audience widens.

End of session-5 dogfood walkthrough.
