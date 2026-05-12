# agent-skills v0 — first-user walkthrough findings

| Field | Value |
|---|---|
| Date | 2026-05-12 |
| Tester | Claude Code (Opus 4.7), running on Windows 11 / Python 3.13.3 |
| HEAD at start | `03e54f7` |
| Environment | Real `~/.claude/skills/` populated with ~30 of Samuel's actual skills; `~/.hermes/skills/` also present (Hermes coexistence) |
| Approach | Use the published CLI as a fresh first-time user against the local repo via env vars. No code fixes until walkthrough is complete. |

---

## Setup

Pointed the CLI at the local repo without touching the GitHub origin (repo still private):

```
AGENT_SKILLS_REGISTRY_URL=file:///X:/Repos/agent-skills/registry.json
AGENT_SKILLS_REGISTRY_REPO=X:/Repos/agent-skills
```

The `file://` URL is handled by `urllib.request.urlopen` natively. Local-path repo URL is handled by `git clone` / `git fetch` against a local directory.

---

## Findings (in order encountered)

### Finding 1: `update` succeeded but issued a Mojibake-only warning about `.sig`

**Where**: `agent-skills update` (first run, fresh cache)

**Symptom**:
```
Warning: registry.json.sig not found � running unsigned.
```

The `—` em-dash (UTF-8 0xE2 0x80 0x94) prints as `�` on the Windows CP1252 console. Functionally harmless — the cache was populated, registry-repo cloned, install proceeded. Mojibake is the leading edge of Finding 2.

**Reproducer**: run `update` on Windows out of the box; observe the dash.

---

### Finding 2: `search` hard-crashes on Windows with `UnicodeEncodeError: '★'`

**Where**: `agent_skills/verbs/search.py:30` — the `★` star prefix on the top match.

**Symptom**:
```
UnicodeEncodeError: 'charmap' codec can't encode character '★' in position 3:
character maps to <undefined>
```

Python's default stdout encoding on Windows console is CP1252 (or whatever the active code page is). `★` is U+2605 which isn't in CP1252. The verb cannot complete; exit code 1; the user sees no results, only a traceback.

**Severity**: blocker for Windows first-time users. The default code path crashes.

**Root cause family**: same as Finding 1 (default stdout encoding). The `★` happens to be the literal that triggers the hard crash; the `—` in Finding 1 prints garbled but doesn't crash because `print` survives via `errors='replace'` semantics inherited from somewhere upstream.

**Workaround for the walkthrough**: set `PYTHONIOENCODING=utf-8` in env. Then the search runs cleanly and prints `★ 1` correctly. This is a runtime workaround; the real fix is to force UTF-8 stdout on Windows at CLI entry (e.g., `sys.stdout.reconfigure(encoding="utf-8")` in `cli.main`).

**Repro**:
```
agent-skills search agent skills --agent claude-code
```

**Sample output once `PYTHONIOENCODING=utf-8` is set**:
```
   ★ 1  samuelgudi/agent-skills-contribution     v0.1.0
       Submit a new agent-skill or update an existing one to the agent-skills registry. ...
       #agent-skills #contribution #submit #registry

     2  samuelgudi/agent-skills-discovery        v0.1.0
       Query the agent-skills registry for a skill that matches the current task. ...
       #agent-skills #discovery #search #registry
```

---

### Finding 3: detector message is clear but does not suggest the `--agent` flag inline

**Where**: `agent_skills/detect.py::detect_host` — multi-host case.

**Symptom**:
```
Multiple hosts detected (['claude-code', 'hermes']). Set AGENT_SKILLS_DEFAULT_AGENT or pass --agent.
```

This is correct and clear — but it's the FIRST thing a real new user sees if they have both stacks installed (Samuel does; many others will too). The message could be tightened: it currently lists hosts in `repr` form. A more conversational line plus a one-line example would shave 30 seconds of friction off the first command.

**Severity**: minor (UX polish, not a bug).

**Idea**: print the message AND, if stdout is a TTY, prepend a recommendation line like `Tip: agent-skills search ... --agent claude-code`.

---

### Finding 4: `install` works end-to-end + Claude Code auto-discovers the new skill

**Where**: `agent-skills install samuelgudi/agent-skills-discovery --agent claude-code --yes` (with `PYTHONIOENCODING=utf-8`).

**Observed**:
- `git archive` extracted the tree at SHA `38bc4c1...` into a tmp staging dir.
- `adapter.install` copied staging → `~/.claude/skills/samuelgudi-agent-skills-discovery/`.
- Marker JSON landed correctly with `id`, `version`, `installed_at`, `installed_by`, `registry_content_hash`, `source_url`, `tree_sha`.
- **The Claude Code harness picked up the new skill IMMEDIATELY** — it appeared in this session's available-skills list as `samuelgudi-agent-skills-discovery` without restarting. This is the end-to-end loop closing for real.

**Sub-observation**: Claude Code's loader uses the directory name as the displayed skill key. Since the ClaudeCodeAdapter uses flat `<author>-<slug>/` naming (Decision: avoid collisions in the flat namespace), the skill shows up as `samuelgudi-agent-skills-discovery` rather than `agent-skills-discovery`. Possibly a future polish (e.g., honour an `id` field in a skill-loader manifest) but not a v0 issue. Documented for awareness.

---

### Finding 5: 🔴 BLOCKER — `verify` reports DRIFT immediately after install

**Where**: `agent-skills verify samuelgudi/agent-skills-discovery --agent claude-code`

**Symptom**:
```
samuelgudi/agent-skills-discovery: DRIFT
  installed files differ from registry source hash for samuelgudi/agent-skills-discovery@0.1.0
```

**This is the most important finding of the walkthrough.** The drift-detection feature — the core integrity check that protects against post-install tampering — is broken because the **two hash functions in the codebase produce different outputs for identical files**:

| Function | Where | Used by |
|---|---|---|
| `generate_manifest.compute_content_hash` | `scripts/generate_manifest.py:36` | sets `registry.json[].source.content_hash` |
| `adapters._base.compute_dir_content_hash` | `adapters/_base.py:65` | install (computes marker hash), verify (compares disk hash) |

**Concrete divergence** for `samuelgudi/agent-skills-discovery`:
- Registry hash: `sha256:cde6ff0e81d6777547cd5e1f2b7425c085e0e4abcc237fa17a3629c53ed264d6`
- Marker hash:   `sha256:35677acaae1993213a48d0ea8c7fe29659ad432be50531fd51047b980eca745c`

These hash the same on-disk content but the algorithms differ:
1. **File-sort key**: generate_manifest sorts by POSIX-string; _base sorts Path objects (case-insensitive on Windows, case-sensitive on POSIX — same bug we fixed in generate_manifest but not propagated to _base).
2. **Separator placement**: generate_manifest does `\n.join(entries)`; _base does `entry + \n` for each. The trailing-byte structure differs.
3. **CRLF normalisation**: generate_manifest normalises CRLF→LF in `sha256_file`; _base does raw `read_bytes()`. Cross-platform installs will diverge.
4. **Marker filtering**: _base skips `MARKER_FILENAME`; generate_manifest doesn't filter (but registry-side dirs never contain markers, so moot one-way).

**Implication**: every freshly-installed skill on every platform reports DRIFT. The user can't tell a real tamper from a false alarm. The yanked-version check still works (boolean flag, not content), and the marker-content-check inside Hermes adapter still works (it compares marker.registry_content_hash to registry, not disk-content). But the Claude-Code adapter's recompute-disk-and-compare path is fully broken.

**Fix shape** (for later batch): extract ONE canonical content-hash function and have every call site use it. Likely home: `adapters/_base.py` since it's already shared; `generate_manifest.compute_content_hash` should import + call it. Tests should assert hash equality between fresh-install state and registry.

**Severity**: 🔴 v0-blocking. Drift detection is a load-bearing security feature.

---

### Finding 6: `verify` exit-1-on-drift makes `verify --json` unscriptable as "is it clean?"

Currently `verify` returns 1 for any non-clean status (drift / yanked / marker_outdated / not_installed). The `--json` output reports `{"status": "drift", ...}` which is structured, but the non-zero exit means a script can't differentiate "not installed" from "yanked" without parsing JSON before checking exit code. Minor.

Possibly desired: exit 0 always when `--json` is set (the JSON IS the answer), exit non-zero only on actual error (no registry, no agent, etc.). Or define an exit-code matrix per status.

---

### Finding 7: `show` works clean — `Installed: yes (claude-code)` correctly reported

No issues. Output is well-formatted and reflects install state.

One minor cosmetic: `Tags:` line uses space-separated bare strings (`agent-skills discovery search registry`) whereas `search` uses `#`-prefix style (`#agent-skills #discovery #search #registry`). Pick one convention and use it everywhere. Trivial.

---

### Finding 8: `init` works end-to-end against a real local skill — with two UX problems

**Setup**: copied `~/.claude/skills/homelab-docs/` (one of Samuel's real skills, lowercase `skill.md`, no meta.json) into `/tmp/homelab-docs-test/`. Ran `agent-skills init` with piped stdin to drive the prompts.

**Worked**:
- `skill.md` → `SKILL.md` rename + notice ("Renamed skill.md → SKILL.md")
- `gh api user` resolved the login + numeric id (`samuelgudi`, `124914565`) — Windows `gh.bat` shim issue from prior debugging is moot when the REAL `gh.exe` is on PATH
- Body scan detected commands correctly: `docker, git, ssh`
- Prompts presented all defaults; user could press enter or override
- Final meta.json is structurally valid (json.loads OK; all required fields present)

**Problem 8a — env-var detector has high false-positive rate**

Detected "env vars": `['README', 'CLAUDE', 'LLM', 'NFS', 'SSH']`.

None of these are real environment variable references. They are uppercase prose acronyms in the SKILL.md body:
- `README` — appears as part of `README.md`
- `CLAUDE` — appears in `~/.claude/` path mentions
- `LLM` — Large Language Model prose
- `NFS` — protocol name in prose
- `SSH` — protocol name in prose

Current regex (`init.py`): `\b[A-Z][A-Z0-9_]{2,}\b` with skip-list `{"URL", "API", "PR", "ID", "TODO", "FIXME"}`. The skip-list is too short for the actual frequency of ALL-CAPS prose acronyms in skill bodies.

**Better heuristic**: match only patterns that look like env-var USES, not bare acronyms:
- `\$\{?[A-Z][A-Z0-9_]+\}?` (shell `$VAR` / `${VAR}`)
- `os\.environ(?:\.get)?\(["']([A-Z][A-Z0-9_]+)["']\)`
- `os\.getenv\(["']([A-Z][A-Z0-9_]+)["']\)`

Or accept high-FP rate and lean harder on the user-confirms-each-suggested-item UX (init does prompt; my piped stdin accepted blindly).

**Problem 8b — `id` defaults to dir basename, not SKILL.md frontmatter `name`**

Test dir was `/tmp/homelab-docs-test/`; SKILL.md frontmatter had `name: homelab-docs`. Init defaulted id to `samuelgudi/homelab-docs-test` (taking the dir name).

This produced a meta.json that fails `validate.py`:
```
ERROR  frontmatter name 'homelab-docs' != meta.json id slug part 'homelab-docs-test'
```

The cross-file consistency check (Task 8) catches it, so it's not a security gap — but it's avoidable user friction. The fix is to default id slug to the SKILL.md frontmatter `name`, not the dir basename. The dir is incidental; the SKILL.md is source of truth.

**Severity 8a**: moderate (UX, but user-confirmable).
**Severity 8b**: low (validate catches it before submit can land, but causes a wasted-roundtrip).

---

## Summary of findings

| # | Finding | Severity | Area |
|---|---|---|---|
| 1 | Mojibake in `update` warning text on Windows | low | encoding |
| 2 | `search` hard-crashes on Windows console (`★`) | 🔴 blocker | encoding |
| 3 | Multi-host error message could include inline example | minor UX | detect |
| 4 | `install` end-to-end works + Claude Code auto-discovers (positive) | — | adapter |
| 5 | `verify` reports DRIFT immediately — two hash algorithms diverge | 🔴 blocker | hash |
| 6 | `verify --json` exit code conflicts with JSON-status-reporting | minor | verify |
| 7 | `show` cosmetic: tags format differs from `search` | trivial | UX |
| 8a | `init` env-var detector has high false-positive rate | moderate UX | init |
| 8b | `init` defaults id slug to dir basename, not SKILL.md `name` | low | init |

### Finding 9: `uninstall` flow handles drift correctly (positive)

Without `--force`: refused with "Drift detected: ... Refusing to uninstall a modified skill. Use --force to override." — correct behaviour per Decision-5/Task-18.

With `--force --yes`: removed the directory cleanly. `ls` confirms gone.

This is interesting in context of Finding 5: the drift-detection bug makes EVERY uninstall require `--force` today (false-positive drift on every install). Once the hash-unification fix lands, uninstall-without-force becomes the happy path again.

---

### What we did NOT test in this pass

- `submit` end-to-end — would open a real PR against `samuelgudi/agent-skills`; deferred until we're ready for that to happen
- `issue`, `deprecate`, `yank` verbs — same reason (all call `gh pr/issue create`)
- The Hermes adapter path on this machine — `~/.hermes/skills/` exists and detect found hermes, but I picked claude-code; can re-run for Hermes as a separate dogfood
- `update` against a real HTTPS URL once the repo is public

### Blocker fixes needed before any wider user onboarding

1. **Finding 2** — Force UTF-8 stdout/stderr on Windows at CLI entry. Without this, `search` doesn't work for any Windows user out of the box.
2. **Finding 5** — Unify the content-hash function. Extract one canonical implementation, have all three call sites (registry generate, install marker write, verify recompute) use it. Add an integration test that runs the full install → verify cycle and asserts `clean`.

Everything else is polish that can land in subsequent commits.

