# agent-skills v0 — session 3 status (Tasks 1-22 done)

| Field | Value |
|---|---|
| Date | 2026-05-11 (session 3) |
| Previous handoffs | `2026-05-11-execution-handoff.md` (session 1) + `2026-05-11-execution-handoff-session2.md` (session 2) — read both for backstory |
| Branch | `main` |
| Latest commit | `b83c1b3` — feat: init verb scaffolds meta.json interactively from SKILL.md (W1) |
| Remote | pushed (origin/main = b83c1b3) |
| Tests | 102 passing on Windows (1 skipped, Linux/macOS-only); 103/103 on Linux/macOS |
| Tasks complete | 1-22 of 33 (~67%) |
| Next task | **Task 23: `sanitize.py`** — STRUCTURALLY COMPRESSED, needs writing-plans expansion |

---

## What landed in session 3 (this session)

Phase 4 — Tasks 16-21 — closed all consumer-side CLI verbs:
- `783937a` Task 16: `show` verb (4 tests)
- `604d92f` Task 17: `install` verb (7 tests; version pinning, yanked refusal, deprecated gate, git-archive fetch)
- `2206cf0` Task 18: `uninstall` verb (4 tests; drift check + `--force`)
- `68fda26` Task 19: `verify` verb (4 tests; clean/drift/yanked/not_installed)
- `5daead3` Task 20: `list` verb (3 tests; --agent override + JSON)
- `a501011` Task 21: `update` verb + `clients/skill_discovery/update.py` (5 tests; HTTPS fetch + rollback guard + atomic write + repo sync)

Phase 5 opened — Task 22:
- `b83c1b3` Task 22: `init` verb (3 passing + 1 Windows-skipped; meta.json scaffolding from SKILL.md via interactive prompts + `gh api user`)

Plus expanded plan:
- `77645e1` docs: Phase 4 expanded plan (`docs/superpowers/plans/2026-05-11-phase4-cli-verbs-expanded.md`, 1609 lines, full TDD detail for Tasks 16-21)

CLI verb count: **7 of 12** registered AND backed by `run()` implementations (search/show/install/uninstall/verify/list/update + init). Remaining: submit (Task 25), issue (Task 26), deprecate (Task 27), yank (Task 28).

---

## Decisions made this session (additive to session-2 list)

10. **Task 17 install — `tarfile.extractall()` deprecation warning**: Python 3.14 will require a `filter` argument; Python 3.13 emits a `DeprecationWarning`. The plan code is correct for 3.13. If/when we migrate to 3.14, pass `filter='data'` to the extractall call in `materialize_tree`. Tracked as "3 warnings" in pytest output — harmless on supported Python.

11. **Task 22 init — Windows fake-gh shim limitation**: The conftest's `fake_gh` fixture creates a `gh.bat` shim and prepends its dir to PATH. On Windows, the real `gh.exe` installed in `C:\Program Files\GitHub CLI\` resolves first via PATHEXT, ignoring PATH ordering for `.exe`-vs-`.bat`. Workaround: tests monkeypatch `agent_skills.verbs.init._fetch_gh_user` directly to bypass subprocess invocation. This is a real mock of an SUT helper — not ideal, but pragmatic. In Linux/macOS CI, the conftest's `gh` (no extension) shim works because there's no `.exe` to lose to. Future improvement: have the conftest detect Windows and either use a `.cmd` shim that subprocess can be coerced to call, or simply skip subprocess-based gh tests on Windows.

12. **Task 22 init — `gh api user` (singular)**: The plan said "call `gh auth status` + `gh api users/<login>`" (two calls). For v0 simplicity, the implementation uses the single `gh api user` endpoint which returns both `login` and `id` in one shot. Same outcome, half the subprocess overhead.

13. **Task 22 init — case-sensitive filename detection on Windows**: `Path.exists()` is case-insensitive on NTFS, so `(skill/"SKILL.md").exists()` is True even if only `skill.md` is on disk. Code uses `os.listdir()` and exact-name match for the SKILL.md vs skill.md detection. The "both files exist" test is skipped on NTFS (physically impossible).

14. **Tasks 16-21 dispatched via expanded sub-plan**: rather than inline expansion of compressed bullets, ran `superpowers:writing-plans` to produce `docs/superpowers/plans/2026-05-11-phase4-cli-verbs-expanded.md` (1609 lines). This is the recommended pattern per the session-1 handoff. Tasks 23-28 should be handled the same way.

---

## What comes next — Tasks 23-28 (compressed; need expansion)

The parent plan's bullets for the contribution-flow verbs:

**Task 23: `clients/skill_contribution/sanitize.py`**
- Detect: home paths (`/home/user/`, `C:\Users\name\`), API key shapes (GitHub PAT `ghp_*`, OpenAI `sk-*`, Anthropic `sk-ant-*`, AWS `AKIA*`), LAN IPs (192.168.*, 10.*), prompt injection in SKILL.md body.
- Interactive: per-detection accept/skip/cancel prompts.
- Apply: writes a sanitized copy of the skill dir to a target location, replacing accepted patterns with placeholders.
- Records sanitization actions for Task 24's diff.
- File: `clients/skill_contribution/sanitize.py` + `clients/skill_contribution/sanitize_rules.py` (data file).
- Test: `tests/test_sanitize.py`.

**Task 24: `clients/skill_contribution/diff.py`**
- Reads pre-sanitization snapshot + post-sanitization output, emits unified diff.
- Includes only files that changed.
- File: `clients/skill_contribution/diff.py`.
- Test: `tests/test_diff.py`.

**Task 25: `clients/skill_contribution/submit.py` + `agent_skills/verbs/submit.py`**
- 5-step pipeline:
  - Step 0: SKILL.md filename normalize + meta.json check (offers init if missing).
  - Step 1: validate.py on the skill dir.
  - Step 2: sanitize.py (interactive).
  - Step 3: security_scan.py (record findings).
  - Step 4: REVIEW.md template population + user edit.
  - Step 5: git branch + commit + `gh pr create`.
- Tests use `fake_gh` to record `gh pr create` invocations.
- Files: `clients/skill_contribution/submit.py` + `agent_skills/verbs/submit.py` + `clients/skill_contribution/templates/review.md` + `pr-body.md`.

**Task 26: `agent_skills/verbs/issue.py` (Path B contribution)**
- Interactive wizard: type, title, context, proposed change, will-implement-self.
- Calls `gh issue create --title ... --body ...`.

**Task 27: `agent_skills/verbs/deprecate.py`**
- Sets `meta.json.status: "deprecated"` + `superseded_by`; moves dir from `skills/` to `archive/`; commits + opens PR.

**Task 28: `agent_skills/verbs/yank.py` (Decision #10, M3 from Gemini)**
- Appends entry to `yanks.json`; opens PR titled `Yank <id>@<version>`.
- Validates: target version exists in versions map; reason non-empty.
- Hard refuse already enforced by Task 17 install — no `--allow-yanked` flag exists.

### Recommended approach for Tasks 23-28

Run `superpowers:writing-plans` again to produce `docs/superpowers/plans/2026-05-11-phase5-contribution-flow-expanded.md` with full TDD steps for each task. The Phase 4 expanded plan file is the model.

**Order**: 23 → 24 (depends on 23) → 25 (depends on 23+24+validate+security_scan, which all exist) → 26, 27, 28 (independent, can dispatch in any order, ideally serial to avoid git conflicts).

---

## Then Tasks 29-33 — Phase 6 (CI) + Phase 7 (Hardening)

- **Task 29**: `.github/workflows/ci.yml` — pytest matrix + `validate --all` + `security_scan --all` + manifest drift check (`generate_manifest.py --check`) + GitHub-ID verification for new authors on contribution PRs.
- **Task 30**: `.github/workflows/on-merge.yml` — moves `submitted/pr-NN/` → `skills/`/`archive/`; runs `generate_manifest.py`; tags release.
- **Task 31**: seed 2 canonical skills under `skills/samuelgudi/` (`agent-skills-discovery` + `agent-skills-contribution`), regenerate manifest, commit.
- **Task 32**: README polish for v0 ship (badges, install, quickstart).
- **Task 33**: final pass on SECURITY.md + CONTRIBUTING.md (yank procedure walkthrough, REVIEW.md template explanation, common rejection reasons).

Tasks 29-30 are short — direct YAML authoring with `actions/checkout@v4` etc. Tasks 31-33 are docs/seeding work.

---

## Environment state

- Python 3.13.3 + pytest 9.0.2 — running clean on Windows.
- `pip install -e .[dev]` last run in session 1; no re-install needed unless `packages.find.include` changes again.
- `gh` CLI authenticated as samuelgudi (Active) + vincenzodimarzo (secondary).
- Repository: clean working tree; all commits pushed to origin/main.

---

## First action for next session

1. Read both prior handoffs (`2026-05-11-execution-handoff.md` + `-session2.md` + this file).
2. Verify `git log --oneline -3` shows `b83c1b3` at HEAD.
3. Verify `python -m pytest tests/ -q` returns ~102 passed.
4. Run `superpowers:writing-plans` against Tasks 23-28 bullets to produce `docs/superpowers/plans/2026-05-11-phase5-contribution-flow-expanded.md`.
5. Dispatch Task 23 (`sanitize.py`) via subagent-driven-development.

End of session-3 handoff.
