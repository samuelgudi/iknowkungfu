# agent-skills v0.1.1 — session 5 status (submit pipeline dogfooded + all 6 adapters shipped)

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Prior handoffs | session1-4 (read for backstory); session-5 dogfood doc: `docs/dogfood/2026-05-12-submit-pipeline-walkthrough.md` |
| Branch | `main` |
| Starting commit | `2f1a6ef` (post session-4 handoff) |
| Latest commit | `ac23b7a` — feat(adapters): add Pi and OpenClaw adapters |
| Remote | pushed (origin/main = ac23b7a) |
| Tests | 223 passing on Windows (was 158 at session-4 close); 1 skipped (Linux/macOS case-sensitive-fs test); CI green on Linux × macOS × Windows × Python 3.10–3.13 |
| Version | `0.1.1` (bump to `0.1.2` recommended before going public — see § Next session) |
| State | Submit pipeline now dogfood-hardened end-to-end. All 6 declared agents have working adapters. **No outstanding bugs.** |

---

## What landed in session 5

Three distinct efforts, in order:

### Effort 1 — submit pipeline dogfood walkthrough (3 blockers found + fixed)

The session-4 handoff flagged the contribution-flow as "the LAST untested pipeline path". This session ran it end-to-end on the live repo and found three blockers no fixture-based test had caught. Full details in `docs/dogfood/2026-05-12-submit-pipeline-walkthrough.md`.

**Pass A (rehearsal)** — fabricated throwaway skill, ran `init` + `submit`, opened PR #1, observed output, closed cleanly. **Pass B (real)** — picked `ask-gemini` as candidate, audited it, rejected as Samuel-coupled. Authored clean-room `samuelgudi/semver-bump-decider` instead (universal SemVer decision aid, no scripts, no Samuel coupling), ran `init` + `submit`, all 14 CI checks green, **squash-merged PR #2**, watched `on-merge.yml` promote → manifest regen → tag → push. **Round-trip** — `update` cache, `install --agent claude-code`, marker verified, `verify` returned `CLEAN`, `uninstall` clean.

**Three blockers landed inline (with regression tests):**

| Commit | Bug | Fix |
|---|---|---|
| `6cb7669` | `submit` never `git push`ed the contrib branch before `gh pr create` → always failed on fresh branch | Added `git push -u --force-with-lease origin <branch>`; test_repo fixture now wires a real bare origin; new `test_submit_pushes_branch_to_origin` |
| `eed2d09` | `on-merge.yml` regenerated manifest **before** committing the promotion → `versions[v].sha` was always `""` → install fell over with `git archive :<path>` | Split workflow into two commits (promotion then manifest); new `tests/test_on_merge_workflow.py` parses the YAML and asserts step ordering |
| `9bbb279` | Rollback guard string-compared `generated_at` across mixed TZ formats; manifest generator emitted local-TZ timestamps | Parse as `datetime` in update.py; `_to_utc_z` helper normalizes all manifest timestamps to UTC-Z; 4 new tests |

Plus one doc-only commit: `0f75759` (`docs/dogfood/...`).

### Effort 2 — Codex + OpenCode adapters (4-agent coverage)

Spec § 19 deferred: `agent_compat` advertised codex + opencode but only claude-code and hermes had adapters. Closed that gap in `318f4f2`.

| Adapter | Detect | User path | Frontmatter rewrite |
|---|---|---|---|
| `codex` | `~/.codex/` | `~/.agents/skills/<flat>/` | `name` → `<author>-<slug>` |
| `opencode` | `~/.config/opencode/` | `~/.config/opencode/skills/<flat>/` | `name` → `<author>-<slug>` (OpenCode enforces folder-name == frontmatter-name) |

Both use marker-hash verify (Hermes-style) since rewriting frontmatter makes disk-hash diverge from registry-hash by design.

`tests/test_detect.py` added: locks `ADAPTERS == set(init.AGENTS)` so future agent additions touch only two source-of-truth lists.

### Effort 3 — Pi + OpenClaw adapters (6-agent coverage)

Two more user-requested agents added in `ac23b7a`. Both are real, modern (2026) AI-coding CLIs with SKILL.md-folder conventions:

| Adapter | Detect | User path | Frontmatter rewrite |
|---|---|---|---|
| `pi` | `~/.pi/agent/` (or `PI_CODING_AGENT_DIR` env) | `~/.pi/agent/skills/<flat>/` | `name` → `<author>-<slug>` |
| `openclaw` | `~/.openclaw/` | `~/.openclaw/skills/<flat>/` | `name` → `<author>-<slug>` **plus inject `version`** (OpenClaw requires it in frontmatter) |

Schema updated: `AGENTS` in `init.py`, `scripts/schema.json` enum, `SCHEMA.md` text (both subset locations). All four target dirs and the OpenClaw version-injection were smoke-tested end-to-end on Samuel's Windows machine.

---

## Final adapter matrix

| Agent | Detect signal | User install path | Notes |
|---|---|---|---|
| `claude-code` | `~/.claude/` | `~/.claude/skills/<flat>/` | Raw copy, disk-hash verify |
| `hermes` | `~/.hermes/` | `~/.hermes/skills/<category>/<slug>/` | Full frontmatter synthesis |
| `codex` | `~/.codex/` | `~/.agents/skills/<flat>/` | `name` rewrite |
| `opencode` | `~/.config/opencode/` | `~/.config/opencode/skills/<flat>/` | `name` rewrite |
| `pi` | `~/.pi/agent/` | `~/.pi/agent/skills/<flat>/` | `name` rewrite |
| `openclaw` | `~/.openclaw/` | `~/.openclaw/skills/<flat>/` | `name` + `version` injection |

`<flat>` = `<author>-<slug>`. Project-scope paths are documented in each adapter's module docstring.

---

## Tests added this session

223 passing total (was 158). New test files:

- `tests/test_on_merge_workflow.py` (3 tests) — YAML-structural locks on the on-merge.yml ordering
- `tests/test_adapter_codex.py` (12 tests)
- `tests/test_adapter_opencode.py` (12 tests)
- `tests/test_detect.py` (8 tests) — host-detection contract + ADAPTERS-vs-AGENTS sync
- `tests/test_adapter_pi.py` (13 tests, including PI_CODING_AGENT_DIR env-var override)
- `tests/test_adapter_openclaw.py` (12 tests, including version-injection lock)

Plus updates to existing tests:

- `tests/test_submit.py` — `test_repo` fixture now wires a bare origin so submit tests exercise real `git push`; new `test_submit_pushes_branch_to_origin` (F1 lock)
- `tests/test_generate_manifest.py` — added `test_generated_at_is_utc_z` + `test_to_utc_z_normalizes_offsets` (F3b locks)
- `tests/test_update.py` — added two rollback-guard TZ-aware tests (F3 locks)

---

## Commits landed this session

```
ac23b7a feat(adapters): add Pi and OpenClaw adapters
318f4f2 feat(adapters): add Codex and OpenCode adapters
0f75759 docs: session-5 dogfood walkthrough — submit pipeline end-to-end
9bbb279 fix(timestamps): normalize manifest to UTC, parse rollback guard as datetime
eed2d09 fix(on-merge): commit promotion before regenerating manifest
3dacb4f chore: promote samuelgudi/semver-bump-decider v0.1.0 + regenerate manifest  (auto, on-merge.yml run for PR #2)
7fcc957 Submit samuelgudi/semver-bump-decider v0.1.0 (#2)                          (auto, squash-merge of dogfood PR)
6cb7669 fix(submit): push contrib branch before gh pr create
```

(Plus the auto-generated tag `v0.1.0-samuelgudi-semver-bump-decider`.)

---

## Architecture decisions still locked

All 18 § 4 spec decisions from session 4 hold. Two new conventions that the codebase now relies on:

- **Adapter–AGENTS sync**: `agent_skills.detect.ADAPTERS` must equal `set(agent_skills.verbs.init.AGENTS)`. Locked by `tests/test_detect.py::test_adapters_match_init_agents_list`. To add a new agent, update both lists + the schema enum.
- **Manifest timestamps are UTC-Z**: `scripts.generate_manifest._to_utc_z` normalizes every timestamp in the registry. Cross-platform manifest generation now produces byte-equal output regardless of generator TZ. Locked by `test_generated_at_is_utc_z` + `test_to_utc_z_normalizes_offsets`.

---

## What's NOT done / open follow-ups

None are v0-blocking now. Listed in order of recommended next-session priority:

1. **Version bump 0.1.1 → 0.1.2.** Three user-facing fixes landed (submit push, on-merge ordering, rollback guard) plus two new adapters. The bump signals to early adopters that the submit pipeline became real.
2. **Make repo public.** v0.1.1 satisfied the "functional v0" gate; the dogfood + adapter expansion in v0.1.2 makes it ready. README badges only resolve against public Actions URLs.
3. **PyPI publication.** `python -m build` + `twine upload`. `[project.scripts]` already exposes `agent-skills`. Reserve the name before squatters do.
4. **F4 — `init` command-detector false-positives on prose.** Same class as session-4 F8a env-var fix. Detected `npm`, `pip`, `go` from prose body of the dogfood skill. Tighten by requiring shell-syntax context (e.g. `npm install` not bare `npm`).
5. **F5 — `init` "no-commands / no-env-vars" sentinel.** Currently you have to type `,` to clear detected defaults. Add an explicit flag or a recognised sentinel.
6. **F6 — Node 20 deprecation warning** in `actions/checkout@v4` + `actions/setup-python@v5`. Track upstream pin updates; bump when Node 24-capable versions land.
7. **Hermes verify asymmetry.** Carry-over from session 4: store pre- and post-rewrite hashes in the marker so verify can do a real content check on hosts that rewrite frontmatter (which is now four of the six: hermes, codex, opencode, pi, openclaw — actually five).
8. **End-to-end contribution dogfood on Linux.** This session's dogfood ran on Windows. A second pass on Milo's WSL box would surface any platform-specific issues.
9. **Gemini CLI adapter.** The only remaining major coding agent with a SKILL.md-style folder convention. Defer until v0.2 or until a user asks.

---

## Environment

- Python: 3.13.3 in use; 3.10–3.13 supported (matrix CI green).
- `pip install -e .[dev]` was run after the session — entry point unchanged.
- `gh` CLI: authenticated as `samuelgudi` (active) and `vincenzodimarzo`.
- Repository: clean working tree, no uncommitted changes.
- Live skills published in the registry: 3 (`agent-skills-contribution`, `agent-skills-discovery`, `semver-bump-decider`).

---

## Prompt for the next session (paste verbatim if more work is needed)

> agent-skills is at HEAD `ac23b7a` on `main`. 223 tests passing, CI green on Linux × macOS × Windows × Python 3.10-3.13. The submit pipeline has been dogfooded end-to-end (3 blockers found + fixed in session 5); all 6 declared agents have working adapters (claude-code, hermes, codex, opencode, pi, openclaw).
>
> Before doing anything else, read these in order:
> 1. `docs/handoff/2026-05-12-execution-handoff-session5.md` — this file. Summarises session 5.
> 2. `docs/dogfood/2026-05-12-submit-pipeline-walkthrough.md` — the dogfood findings.
> 3. `docs/handoff/2026-05-12-execution-handoff-session4.md` — prior session backstory.
>
> Verify state:
> ```
> cd X:/Repos/agent-skills
> git log --oneline -8                       # HEAD should be ac23b7a
> python -m pytest tests/ -q --tb=no         # expect: 223 passed, 1 skipped
> gh run list --limit 1 --workflow=ci.yml    # expect: success
> ```
>
> Recommended next steps (Samuel will pick which):
> 1. **Version bump 0.1.1 → 0.1.2** + brief CHANGELOG entry citing the dogfood fixes and the 4 new adapters.
> 2. **Make repo public** — `gh repo edit --visibility public`. Update README CI badge URLs if needed.
> 3. **PyPI publication** — `python -m build && twine upload dist/*`.
> 4. **Hand the repo to Milo** for a Linux-side dogfood pass (this is the second-user / second-platform test — see § Next session in this file).
> 5. **Fix F4** (init command-detector prose false-positives) — same shape as F8a env-var fix.
> 6. **Gemini CLI adapter** if/when a user asks.

End of session-5 handoff.
