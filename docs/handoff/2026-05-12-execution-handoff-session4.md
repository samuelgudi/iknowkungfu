# agent-skills v0.1.1 — session 4 status (functionally complete + hardened)

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Previous handoffs | `2026-05-11-execution-handoff.md` (s1) + `-session2.md` (s2) + `-session3.md` (s3) — read for backstory |
| Branch | `main` |
| Latest commit | `047719d` — fix(install): pass filter='data' to tarfile.extractall on Python 3.12+ |
| Remote | pushed (origin/main = 047719d) |
| Tests | 158 passing on Windows; 1 skipped (Linux/macOS-only case-sensitive-fs test); CI green on Linux × macOS × Windows × Python 3.10/3.11/3.12/3.13 |
| Version | `0.1.1` (bumped from `0.1.0` in PR #2 of the dogfood fixes) |
| State | v0.1.1 functionally complete + dogfood-hardened. **No outstanding bugs.** |

---

## What landed in session 4

Session 4 covered: real first-user walkthrough → fix plan → execution → verification.

### Dogfood walkthrough (commit `82e7f71`)
First-user pass against the published CLI, on Windows, against the local repo via env vars. Surfaced **9 findings** documented in `docs/dogfood/2026-05-12-first-user-walkthrough.md`. 2 were blockers (UTF-8 console crash; hash mismatch causing false-positive drift on every install).

### Fix plan (commit `6ef5dcd`)
Opus subagent read the walkthrough + relevant source, produced `docs/superpowers/plans/2026-05-12-dogfood-fixes.md` (~1300 lines). Added 2 new findings discovered during planning:
- **F10**: `generate_manifest.compute_content_hash` didn't filter `MARKER_FILENAME` (latent footgun).
- **F11**: `install.py` recomputed staging hash instead of using the registry hash as canonical + asserting staging matches (tamper-check missing).

Total: 11 findings. Plan organized into 3 sequential PRs.

### Three PRs executed (sonnet subagent + my review):

| PR | Commit | Scope |
|---|---|---|
| #1 | `81c4c4c` | UTF-8 stdout/stderr at CLI entry (`_force_utf8_streams` in `cli.py`). Fixes F1 + F2. |
| #2 | `df568f7` | Hash unification — single canonical `compute_dir_content_hash` in `adapters/_base.py`, imported by `scripts/generate_manifest.py`. Install asserts staging hash == registry hash (tamper-check). Version bump `0.1.0` → `0.1.1`. `.gitattributes` defensive rules for SKILL.md + meta.json. **NEW**: `tests/test_integration_install_verify.py` runs the full install→verify cycle on real FS + real registry and asserts `clean` — the regression test that would have caught F5. **NEW**: `tests/test_hash_canonical.py` locks the architecture (CRLF normalization for text only; binary untouched; platform-independent file sort; marker excluded; both call sites produce equal hashes). |
| #3 | `a62cd92` | Polish bundle: F3 (detect message with inline `--agent` example), F6 (`verify --json` exit 0 + status in payload), F7 (`show` uses `#tag` format), F8a (init env-var detector requires real use-sites: `$VAR` / `os.environ` / `os.getenv` — no more prose-acronym FPs), F8b (init defaults id slug to SKILL.md frontmatter `name`, not dir basename). |

### Post-PR tarfile fix (commit `047719d`)
`agent_skills/verbs/install.py` passed `tarfile.extractall(staging)` without `filter`, which emits a `DeprecationWarning` on Python 3.12/3.13 and will fail-or-change-defaults in 3.14. Fixed: `filter='data'` on 3.12+; sys.version_info gate for 3.10/3.11 (kwarg doesn't exist there). Test fixture in `test_install_verb.py` mirrored the same fix (it uses the same extract pattern to compute the registry-side hash during fixture setup). Full suite now passes with `-W error::DeprecationWarning`.

---

## Architecture state (locked decisions still hold)

All 18 § 4 locked decisions from the spec remain untouched. No schema bump needed for v0.1.1.

- Content hash: single canonical impl in `adapters/_base.compute_dir_content_hash` (CRLF→LF normalization for text; binary raw; POSIX-string sort; marker file excluded). Three call sites: registry generation, install marker, verify recompute. All converge.
- Drift detection: real and verified end-to-end via `test_install_then_verify_clean`.
- Yank semantics: hard refuse, no override flag (Decision #10) — unchanged.
- Deprecate semantics: soft, requires `--allow-deprecated` (Decision #9) — unchanged.
- GitHub-ID binding: immutable numeric `author.github_id` (Decision #4) — unchanged.

---

## What's NOT done / open follow-ups

These are in the spec's § 19 deferred list. None are v0-blocking.

1. **Repo public** — Samuel set "private until v0 functional"; v0.1.1 is functionally complete + CI-green. Make public when ready.
2. **PyPI publication** — `pipx install agent-skills` requires PyPI upload. Spec § 19. Trivial to do (twine + the existing pyproject) but skipped until repo is public.
3. **Hermes verify asymmetry** — Claude-Code's `verify` recomputes disk hash; Hermes's only compares marker-vs-registry (because Hermes rewrites SKILL.md frontmatter at install). Future improvement: store both pre- and post-rewrite hashes in Hermes markers. Documented in `docs/superpowers/plans/2026-05-12-dogfood-fixes.md` § 5.2.
4. **Reflexive skill-discovery invocation guard** — spec § 19. Wait for false-positive rate data before tightening.
5. **Hard-block override mechanism** — spec § 19. First legit need triggers design.
6. **Signing infrastructure** (`registry.json.sig` + key distribution) — spec § 19. v0 emits "running unsigned" warning at update.
7. **Real-world end-to-end submit test** — submit verb is tested against fixtures, but a true contribution-flow walkthrough (run `init` + `submit` against `~/.claude/skills/homelab-docs/`, watch a PR get created against the real repo, merge it, observe the seed-skills regen) has NOT been done. Worth doing as the next dogfood pass.

---

## Tests written this session (regression locks)

These tests would have caught every blocker discovered during the dogfood walkthrough. Any future regression to the same class would fail one of these:

- `tests/test_integration_install_verify.py::test_install_then_verify_clean` — full install→verify cycle, asserts `clean`. Catches F5 class.
- `tests/test_integration_install_verify.py::test_uninstall_without_force_succeeds_after_install` — confirms F9 happy-path holds post-fix.
- `tests/test_hash_canonical.py::test_generate_manifest_and_base_produce_equal_hashes` — architecture lock: both call sites converge.
- `tests/test_hash_canonical.py::test_hash_ignores_marker_file` — F10 lock.
- `tests/test_generate_manifest.py::test_generate_manifest_uses_canonical_hash_function` — sneaky-refork lock (asserts `gm.compute_content_hash` and `gm.sha256_file` don't exist; refactor police).
- `tests/test_cli_scaffold.py::test_*utf8*` — F2 lock.
- `tests/test_init_verb.py::test_init_env_var_scan_ignores_prose_acronyms` + `_detects_shell_style` — F8a both directions.
- `tests/test_init_verb.py::test_init_defaults_id_to_frontmatter_name_not_dir` — F8b lock.

---

## Environment

- Python: 3.13.3 in use; 3.10–3.13 supported (matrix CI green).
- `pip install -e .[dev]` was run after `0.1.0` bump; still valid for `0.1.1` (entry point unchanged).
- `gh` CLI: authenticated as `samuelgudi` (active) and `vincenzodimarzo`.
- Repository: clean working tree, no uncommitted changes.

---

## Prompt for the next session (paste verbatim if more work is needed)

> agent-skills v0.1.1 is functionally complete and dogfood-hardened. HEAD `047719d`, 158 tests passing, CI green on Linux × macOS × Windows × Python 3.10-3.13.
>
> Before doing anything else, read these in order:
> 1. `docs/handoff/2026-05-12-execution-handoff-session4.md` — this file. Includes what's done, what's open, the test-regression-lock matrix.
> 2. `docs/handoff/2026-05-12-execution-handoff-session3.md` — prior session state.
> 3. `docs/dogfood/2026-05-12-first-user-walkthrough.md` — first-user findings.
> 4. `docs/superpowers/plans/2026-05-12-dogfood-fixes.md` — fix plan that landed in PRs #1-3 of session 4.
>
> Verify state:
> ```
> cd X:/Repos/agent-skills
> git log --oneline -5            # HEAD should be 047719d
> python -m pytest tests/ -q --tb=no    # expect: 158 passed, 1 skipped
> gh run list --limit 1 --workflow=ci.yml    # expect: success
> ```
>
> Next concrete steps (Samuel will pick which):
> 1. **End-to-end contribution dogfood** — pick a real local skill (e.g. `~/.claude/skills/homelab-docs/`), copy to a working dir to avoid mutating Samuel's actual install, then run `agent-skills init` + `agent-skills submit` against the real `samuelgudi/agent-skills` repo. Watch the PR get created. Optionally merge it (the on-merge workflow will promote `submitted/` → `skills/`, regen manifest, tag a release). This is the LAST untested pipeline path.
> 2. **Make repo public** — repo has been private "until v0 functional". v0.1.1 satisfies that gate. Update README badges if needed (they reference public Actions URLs which only work when public). Confirm CI still passes after going public.
> 3. **PyPI publication** — `python -m build` + `twine upload`. The `pyproject.toml` is already set up. `[project.scripts]` exposes `agent-skills`. Reserve the name early to prevent squatting.
> 4. **Hermes verify enhancement** — store both pre- and post-frontmatter-rewrite hashes in Hermes markers so verify can do a real content check. See `docs/superpowers/plans/2026-05-12-dogfood-fixes.md` § 5.2.
> 5. **Hermes/Codex/OpenClaw adapter expansion** — agent_compat declares them but only `claude-code` and `hermes` have adapters. Add the others when those agent stacks become target audiences.
>
> Stop conditions: same as prior handoffs. If you find a contradiction between docs and code state, the code is authoritative; ask Samuel before silently aligning the docs.

End of session-4 handoff.
