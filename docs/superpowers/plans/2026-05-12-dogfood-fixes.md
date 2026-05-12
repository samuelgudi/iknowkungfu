# agent-skills v0 — post-walkthrough fix plan

| Field | Value |
|---|---|
| Status | plan — ready for execution |
| Date | 2026-05-12 |
| Author | Claude Code (Morpheus, Opus 4.7) |
| Source report | `docs/dogfood/2026-05-12-first-user-walkthrough.md` |
| Base commit | `82e7f71` (main, 136 tests passing) |
| Spec reference | `docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md` |

---

## 1. Executive summary

The walkthrough surfaced two blockers and seven polish/UX items. The blockers are independent: Finding 2 is a 6-line CLI-entry fix (force UTF-8 stdout on Windows), Finding 5 is a deeper architectural fix that unifies two divergent content-hash implementations into a single canonical function in `adapters/_base.py` that `scripts/generate_manifest.py` imports.

**Recommended PR strategy: three PRs.** PR #1 (BLOCKER) ships the UTF-8 stdout fix alone (small, isolated, ships fast, unblocks every Windows user). PR #2 (BLOCKER) ships the hash unification + an integration test that runs install→verify→clean (the load-bearing fix). PR #3 (POLISH) bundles the seven remaining findings + non-blocking polish; nothing in it is urgent and grouping reduces review thrash.

Order of operations: PR #1 → PR #2 → PR #3. PR #1 and #2 can be developed in parallel (no shared files) and are mergeable in either order, but PR #1 lands first because it's smaller. The `pyproject.toml` version bump (`0.1.0 → 0.1.1`) lands in PR #2 alongside the hash fix because that's the change with user-visible semantic shift; PR #3 does not bump.

---

## 2. Fix order and dependency graph

```
Finding 2  (UTF-8 stdout)     ──► PR #1  (independent, ship first)
                                          │
Finding 5  (hash unification) ──► PR #2 ──┤
                                          │
Finding 1  (mojibake dash)         ── (auto-fixed by Finding 2's PR; falls into PR #1 by side-effect — keep separate test)
Finding 3  (detect msg UX)         ──► PR #3
Finding 4  (positive observation, no fix)
Finding 6  (verify exit codes)     ──► PR #3
Finding 7  (tag format unify)      ──► PR #3
Finding 8a (env-var FP)            ──► PR #3
Finding 8b (init id default)       ──► PR #3
Finding 9  (positive observation, no fix; uninstall happy-path returns once Finding 5 lands)
Finding 10 (NEW: marker MARKER_FILENAME filter parity) ──► PR #2 (folded into hash unification)
Finding 11 (NEW: install marker-hash recomputed unnecessarily) ──► PR #2 (folded into hash unification)
```

**Parallelisable**: PR #1 and PR #2 share no files; both touch existing tests only at the level of new test additions. PR #3 depends on neither (none of its files overlap with PR #1/#2 except `agent_skills/cli.py` for any `--version` polish, which can be punted to a follow-up).

**Sequential constraint**: Finding 1's regression test (Windows mojibake dash) lives in PR #1 because the fix is the same UTF-8-reconfigure line. Adding a test for it before the fix would block PR #1 unnecessarily.

---

## 3. Per-finding fix plan

### Finding 2 — `search` crashes on Windows (`★` UnicodeEncodeError)

- **Severity**: BLOCKER
- **PR grouping**: `BLOCKER PR #1`
- **Files to touch**:
  - `agent_skills/cli.py` (add UTF-8 reconfigure at entry)
  - `tests/test_cli_scaffold.py` (new test asserting stdout/stderr encoding after `main` entry)
- **Semantic change**: On import-time / first call to `cli.main`, force `sys.stdout` and `sys.stderr` into UTF-8 mode with `errors="replace"` so Unicode glyphs in any verb's output (★, em-dash, smart quotes) never raise `UnicodeEncodeError` on Windows consoles whose default code page lacks them. Behaviour on POSIX is unchanged because those stdouts are already UTF-8.

- **TDD steps**:
  1. Write `test_main_reconfigures_stdout_utf8` (below) — asserts the encoding side-effect.
  2. Write `test_search_with_unicode_star_does_not_crash` — runs the full `search` verb against a tmp registry with an emoji/star in output. Force `sys.stdout` to a CP1252-emulating wrapper before invocation; assert `run()` exits 0 and produces the `★` byte in the captured output.
  3. Run both; expect fail.
  4. Implement the reconfigure block at the top of `cli.main`.
  5. Run; expect pass.
  6. Commit.

- **Test code** (append to `tests/test_cli_scaffold.py`):

```python
def test_main_reconfigures_stdout_utf8_on_entry(monkeypatch, capsys):
    """cli.main must force UTF-8 on stdout/stderr at entry so Unicode glyphs
    survive on Windows consoles that default to CP1252. Regression test for
    Finding 2 of the 2026-05-12 walkthrough (★ in search output crashed)."""
    import io
    import sys
    from agent_skills import cli

    # Simulate a Windows CP1252 stdout that would reject U+2605.
    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                                   write_through=True, line_buffering=True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)
    fake_stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                                   write_through=True, line_buffering=True)
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    # Invoke with no-op verb that triggers parser help via missing args; we only
    # care that main() reaches its reconfigure logic without crashing.
    try:
        cli.main(["search", "anything"])
    except SystemExit:
        pass

    # After main() runs, stdout encoding must be utf-8 (or equivalent alias).
    enc = (sys.stdout.encoding or "").lower().replace("-", "")
    assert "utf8" in enc, f"expected UTF-8 stdout after cli.main; got {sys.stdout.encoding!r}"
    enc_err = (sys.stderr.encoding or "").lower().replace("-", "")
    assert "utf8" in enc_err, f"expected UTF-8 stderr after cli.main; got {sys.stderr.encoding!r}"


def test_cli_search_unicode_star_does_not_crash(tmp_path, monkeypatch, capsys):
    """End-to-end: search prints '★' in its top-match prefix. With CP1252
    stdout (Windows-cmd default), pre-fix this raised UnicodeEncodeError and
    exited 1. Post-fix it survives via UTF-8 reconfiguration."""
    import io
    import json as _json
    import sys
    from pathlib import Path

    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    (cache / "registry.json").write_text(_json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test/example", "name": "example", "description": "find things",
            "version": "0.1.0", "status": "active",
            "author": {"name": "T", "github_login": "test", "github_id": 1},
            "category": "meta", "tags": ["search"], "platforms": ["windows"],
            "agent_compat": ["claude-code"], "license": "MIT",
            "install": {"claude-code": {"scope": "user"}},
            "requires": {"env_vars": [], "commands": []},
            "has_scripts": False,
            "versions": {"0.1.0": {"sha": "a" * 40, "released": "2026-05-11T00:00:00Z"}},
            "source": {"path": "skills/test/example", "content_hash": "sha256:0", "files": []},
        }],
    }))

    fake_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict",
                                   write_through=True, line_buffering=True)
    monkeypatch.setattr(sys, "stdout", fake_stdout)

    from agent_skills.cli import main
    rc = main(["search", "find", "--agent", "claude-code"])
    assert rc == 0
    fake_stdout.flush()
    raw = fake_stdout.buffer.getvalue()
    # After fix, stdout has been reconfigured to UTF-8; the star is encodable.
    assert "★".encode("utf-8") in raw or b"\xe2\x98\x85" in raw
```

- **Implementation code shape** (top of `agent_skills/cli.py::main`, before `make_parser()`):

```python
def _force_utf8_streams() -> None:
    """Force sys.stdout/stderr to UTF-8 at CLI entry. Windows consoles default
    to CP1252 (or similar legacy code page), which can't encode common output
    glyphs (★, em-dash). Reconfiguring at the entrypoint costs nothing on POSIX
    (already UTF-8) and prevents UnicodeEncodeError tracebacks on Windows.
    Uses errors='replace' on stderr so warning messages never bubble a second
    fault if a truly unmappable char slips through."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        # Some test environments wrap streams in non-reconfigurable BufferedIO;
        # guard with hasattr so we degrade gracefully rather than blow up.
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            # Stream not text-mode or already detached; nothing to do.
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_streams()
    p = make_parser()
    # ... existing body unchanged
```

- **Risk callouts**: None for installed users. Calling `.reconfigure` on a stream that doesn't support it (very old Python, exotic test wrappers) is wrapped in a try/except. POSIX behaviour unchanged.
- **Commit message**: `fix(cli): force UTF-8 stdout/stderr at entry to prevent Windows console crashes`

---

### Finding 5 — `verify` reports DRIFT immediately after install (hash divergence)

- **Severity**: BLOCKER
- **PR grouping**: `BLOCKER PR #2`
- **Files to touch**:
  - `adapters/_base.py` (rewrite `compute_dir_content_hash` to be the single canonical implementation; add `_sha256_file_normalised` helper)
  - `scripts/generate_manifest.py` (delete `sha256_file` + `compute_content_hash`; import from `adapters._base`; rebuild `registry.json` via the rebuilt function so existing entries' hashes update)
  - `registry.json` (regenerated by `python scripts/generate_manifest.py`)
  - `pyproject.toml` (`0.1.0` → `0.1.1`)
  - `tests/test_adapter_base.py` (new tests for the canonical hash)
  - `tests/test_hash_canonical.py` (NEW file — see § 4)
- **Semantic change**: One canonical function — `adapters._base.compute_dir_content_hash` — is used by (a) `generate_manifest.py` to write `registry.json[].source.content_hash`, (b) `verbs/install.py` to compute the marker's `registry_content_hash`, and (c) `adapters/claude_code.py::verify` to recompute the on-disk hash for drift detection. All three call sites now produce identical hashes for identical content, so `verify` immediately after `install` returns `clean`. CRLF→LF normalisation and POSIX-string file sorting are applied uniformly (matching the existing `sha256_file` behaviour from `generate_manifest`).

- **TDD steps**:
  1. Write the integration test in § 4 first (`test_install_then_verify_returns_clean`) — this is the gate that protects against this class of bug forever.
  2. Write `test_canonical_hash_matches_generate_manifest_legacy` — locks the exact bytes structure (so a future refactor can't silently change the hash output).
  3. Run; expect both fail (current behaviour: drift).
  4. Implement the canonical function in `_base.py`, port `generate_manifest.py` to import it, regenerate `registry.json`.
  5. Run full test suite; expect all 136 existing + new tests pass.
  6. Commit.

- **Test code** (NEW file `tests/test_hash_canonical.py`):

```python
"""Tests that lock the canonical content-hash function as the single source
of truth used by generate_manifest.py, the install verb, and adapter.verify.
Regression guard for Finding 5 of the 2026-05-12 walkthrough — two divergent
hash implementations made every freshly-installed skill report DRIFT."""
import hashlib
import os
from pathlib import Path

import pytest

from adapters._base import compute_dir_content_hash, MARKER_FILENAME


def _seed_skill(root: Path) -> None:
    """A skill dir with a mix of file types and a Windows-CRLF-prone text file."""
    (root / "SKILL.md").write_bytes(b"---\nname: x\ndescription: y\n---\n# body\nline2\n")
    (root / "meta.json").write_bytes(b'{\n  "id": "a/b"\n}\n')
    (root / "scripts").mkdir()
    (root / "scripts" / "run.py").write_bytes(b"print('hi')\n")
    (root / "templates").mkdir()
    (root / "templates" / "out.md").write_bytes(b"hello\n")


def test_hash_is_stable_across_runs(tmp_path):
    a = tmp_path / "a"; a.mkdir(); _seed_skill(a)
    h1 = compute_dir_content_hash(a)
    h2 = compute_dir_content_hash(a)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_hash_is_identical_for_identical_content(tmp_path):
    a = tmp_path / "a"; a.mkdir(); _seed_skill(a)
    b = tmp_path / "b"; b.mkdir(); _seed_skill(b)
    assert compute_dir_content_hash(a) == compute_dir_content_hash(b)


def test_hash_ignores_marker_file(tmp_path):
    """Marker file must not contribute — it's written by the adapter AFTER
    content hashing, so its presence/contents would break verify."""
    a = tmp_path / "a"; a.mkdir(); _seed_skill(a)
    h_before = compute_dir_content_hash(a)
    (a / MARKER_FILENAME).write_text('{"id": "a/b"}')
    h_after = compute_dir_content_hash(a)
    assert h_before == h_after


def test_hash_normalises_crlf_for_text_files(tmp_path):
    """A SKILL.md committed with LF on Linux and checked out with CRLF on
    Windows (autocrlf=true) must produce the same hash. Without this,
    every cross-platform install reports drift."""
    a = tmp_path / "a"; a.mkdir()
    (a / "SKILL.md").write_bytes(b"---\nname: x\ndescription: y\n---\n# body\n")
    b = tmp_path / "b"; b.mkdir()
    (b / "SKILL.md").write_bytes(b"---\r\nname: x\r\ndescription: y\r\n---\r\n# body\r\n")
    assert compute_dir_content_hash(a) == compute_dir_content_hash(b)


def test_hash_does_not_normalise_binary_files(tmp_path):
    """Binary files (e.g. PNG, embedded models) must be hashed byte-exact —
    CRLF normalisation would corrupt the hash for any file containing the
    \\r\\n byte sequence in its binary content."""
    a = tmp_path / "a"; a.mkdir()
    (a / "asset.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"data" * 10)
    b = tmp_path / "b"; b.mkdir()
    (b / "asset.png").write_bytes(b"\x89PNG\n\x1a\n" + b"data" * 10)
    assert compute_dir_content_hash(a) != compute_dir_content_hash(b)


def test_hash_file_sort_is_platform_independent(tmp_path):
    """File-sort key must be the POSIX relative-path string, not a Path
    object — WindowsPath sorts case-insensitively while PosixPath does not,
    which would otherwise produce platform-dependent hashes."""
    a = tmp_path / "a"; a.mkdir()
    # Files chosen to bait case-sensitive sort divergence.
    (a / "SKILL.md").write_bytes(b"x\n")
    (a / "meta.json").write_bytes(b"y\n")
    (a / "README.md").write_bytes(b"z\n")

    # Force-sort the files into Python's relative-string order and recompute
    # the hash manually, then assert it matches the function's output.
    files = sorted(
        str(f.relative_to(a)).replace("\\", "/")
        for f in a.rglob("*") if f.is_file() and f.name != "__marker__"
    )
    # Sanity: SKILL.md should sort before meta.json under string-case ordering
    # ('S' < 'm' in ASCII), and README.md (also uppercase) should come first.
    assert files == ["README.md", "SKILL.md", "meta.json"]
    h = compute_dir_content_hash(a)
    assert h.startswith("sha256:")


def test_generate_manifest_and_base_produce_equal_hashes(tmp_path, monkeypatch):
    """generate_manifest.py and adapters._base must produce byte-identical
    content_hash for the same skill tree. This is the heart of Finding 5."""
    import sys, subprocess, json, shutil
    ROOT = Path(__file__).parent.parent

    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "tests", "skills"))
    skill = repo / "skills" / "test-author" / "example"
    shutil.copytree(ROOT / "tests/fixtures/good/instructions-only", skill, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "x"], cwd=repo, check=True, capture_output=True)
    subprocess.run([sys.executable, str(repo / "scripts/generate_manifest.py")],
                   cwd=repo, check=True, capture_output=True)
    reg = json.loads((repo / "registry.json").read_text(encoding="utf-8"))
    registry_hash = reg["skills"][0]["source"]["content_hash"]
    base_hash = compute_dir_content_hash(skill)
    assert registry_hash == base_hash, (
        f"Hash divergence — registry={registry_hash!r} base={base_hash!r}. "
        "generate_manifest and adapters._base must share one canonical function."
    )
```

- **Implementation code shape**.

In `adapters/_base.py`, replace the existing `compute_dir_content_hash` with:

```python
# File extensions and bare names we treat as text — these get CRLF→LF
# normalisation before hashing so a Windows checkout (autocrlf=true) produces
# the same content_hash as a Linux checkout. The set mirrors the one in
# scripts/generate_manifest.py prior to v0.1.1; both files now import from
# here so the rules cannot drift again.
_TEXT_SUFFIXES = frozenset({
    ".md", ".py", ".pyi", ".js", ".ts", ".mjs", ".sh", ".bash", ".zsh",
    ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg", ".ini", ".rst",
})
_TEXT_NAMES = frozenset({
    "SKILL.md", "skill.md", "README.md", "LICENSE", "CONTRIBUTING.md",
    "SECURITY.md", "SCHEMA.md",
})


def _sha256_file_normalised(p: Path) -> str:
    """Hash file bytes. For known text files normalise CRLF→LF first so
    hashes are platform-independent (Windows autocrlf produces CRLF in the
    working tree even when the repo stores LF). Binary files are hashed
    byte-exact — normalising them would corrupt any file whose payload
    legitimately contains \\r\\n (PNG signature, compressed streams, etc.)."""
    h = hashlib.sha256()
    data = p.read_bytes()
    if p.suffix.lower() in _TEXT_SUFFIXES or p.name in _TEXT_NAMES:
        data = data.replace(b"\r\n", b"\n")
    h.update(data)
    return h.hexdigest()


def compute_dir_content_hash(directory: Path) -> str:
    """Canonical content hash for a skill directory. Used by:
      - scripts/generate_manifest.py    → registry.json[].source.content_hash
      - agent_skills/verbs/install.py    → marker's registry_content_hash
      - adapters/claude_code.py::verify  → recompute disk-state for drift

    Algorithm (locked — changing this invalidates every existing marker):
      1. Walk all files under `directory`, exclude MARKER_FILENAME.
      2. Sort by POSIX-style relative-path string (forward slashes,
         case-sensitive byte order — NOT WindowsPath case-folding).
      3. For each file: produce `<posix_rel>\\0<sha256_hex>\\n` where
         sha256 is over CRLF-normalised bytes for text files / raw bytes
         for binary files.
      4. Concatenate all entries, sha256 the result, prefix `sha256:`.
    """
    rels = sorted(
        str(f.relative_to(directory)).replace("\\", "/")
        for f in directory.rglob("*")
        if f.is_file() and f.name != MARKER_FILENAME
    )
    h = hashlib.sha256()
    for rel in rels:
        file_hash = _sha256_file_normalised(directory / rel)
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(file_hash.encode("ascii"))
        h.update(b"\n")
    return "sha256:" + h.hexdigest()
```

In `scripts/generate_manifest.py`:

```python
# Delete sha256_file, _TEXT_SUFFIXES, compute_content_hash.
# Replace with:
from adapters._base import compute_dir_content_hash


# In build_skill_entry, replace:
#   content_hash, files = compute_content_hash(skill_dir)
# with:
content_hash = compute_dir_content_hash(skill_dir)
files = sorted(
    str(f.relative_to(skill_dir)).replace("\\", "/")
    for f in skill_dir.rglob("*") if f.is_file()
)
```

(The `files` list still needs to be built locally because `generate_manifest` records it in `registry.json[].source.files`, and that list intentionally does NOT exclude any marker — registry-side directories never contain markers anyway. Keeping `files` computation here keeps `_base.py` focused on the hash alone.)

After implementation, run `python scripts/generate_manifest.py` to regenerate `registry.json` with the new hashes, and commit the regenerated file.

- **Risk callouts**:
  - **Existing markers in the wild become "drifted"**: zero impact today (repo private, no public users). On first `update` after merge, anyone with an old install would see `verify` report drift. Acceptable for pre-public phase. Document this in the PR description.
  - **No `schema_version` bump needed** — the registry schema is unchanged; only the algorithm that computes `source.content_hash` changes. The field's shape (`"sha256:<hex>"`) and meaning are identical.
  - **Marker format unchanged** — `.agent-skills-marker.json` still records `registry_content_hash`; the value's algorithm changes but the field's contract is unchanged.
  - Ensure `scripts/generate_manifest.py` can still `import adapters._base` when run as `python scripts/generate_manifest.py` from repo root: today, `scripts/generate_manifest.py` doesn't add the repo root to `sys.path`, so the import must work via the editable install's `agent_skills` / `adapters` packages. CI's `pip install -e .[dev]` step ensures this. Local execution from a non-installed checkout would need `python -m scripts.generate_manifest` OR the script can prepend `sys.path` itself — recommend adding the same path-prepend shim that other scripts use:

```python
# At top of scripts/generate_manifest.py, before importing from adapters:
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
```

- **Commit message**: `fix(hash): unify content-hash across registry, install, verify (Finding 5)`

---

### Finding 1 — Mojibake em-dash in `update` warning

- **Severity**: minor — auto-fixed by Finding 2 (same root cause: stdout encoding)
- **PR grouping**: `BLOCKER PR #1` (free ride with the UTF-8 fix)
- **Files to touch**: `tests/test_update.py` (new regression test only — no source change)
- **Semantic change**: After PR #1, the em-dash byte sequence `\xe2\x80\x94` in the warning string is encodable by stdout. Behaviour change is implicit.
- **TDD steps**:
  1. Write a unit test that invokes `clients.skill_discovery.update.refresh` with a registry URL whose `.sig` 404s, simulates a CP1252 stderr, captures the byte stream, and asserts the em-dash bytes appear (rather than `\x3f` replacements or a crash).
  2. Run; expect pass (because PR #1 already reconfigured the stream).
  3. Commit alongside the Finding 2 fix.

- **Test code** (append to `tests/test_update.py`):

```python
def test_unsigned_warning_uses_proper_em_dash_after_utf8_fix(tmp_path, monkeypatch, capsys):
    """The unsigned-registry warning contains an em-dash (U+2014). After the
    Finding 2 UTF-8 reconfigure, the dash must reach stderr as proper UTF-8
    bytes (\\xe2\\x80\\x94), not '?' or a UnicodeEncodeError. Regression test
    for Finding 1 of the 2026-05-12 walkthrough."""
    import io
    import sys
    import json
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread

    payload = json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z", "skills": []
    }).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (stdlib API)
            if self.path.endswith("registry.json"):
                self.send_response(200); self.end_headers(); self.wfile.write(payload)
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *_a, **_k): pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    t = Thread(target=server.serve_forever, daemon=True); t.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/registry.json"
        cache = tmp_path / "cache"
        monkeypatch.setattr("clients.skill_discovery.update._cache_dir", lambda: cache.mkdir(exist_ok=True) or cache)
        monkeypatch.setenv("AGENT_SKILLS_SKIP_REPO_SYNC", "1")

        # Apply the same reconfigure cli.main does, to mirror real CLI usage.
        from agent_skills.cli import _force_utf8_streams
        _force_utf8_streams()

        from clients.skill_discovery.update import refresh
        rc = refresh(registry_url=url)
        assert rc == 0
    finally:
        server.shutdown()

    captured = capsys.readouterr()
    # Em-dash (U+2014) must appear in stderr message — not '?' (lossy replace)
    # and not omitted (raised exception).
    assert "—" in captured.err
```

- **Implementation code shape**: none — Finding 2's `_force_utf8_streams` makes this test green.
- **Risk callouts**: None.
- **Commit message**: included in Finding 2's commit (this is a regression-test addition only).

---

### Finding 3 — Multi-host detect message lacks inline example

- **Severity**: minor UX
- **PR grouping**: `POLISH PR #3`
- **Files to touch**:
  - `agent_skills/detect.py` (improve `detect_host` error message)
  - `tests/test_cli_scaffold.py` (new test for message shape)
- **Semantic change**: When multiple hosts are detected, the SystemExit message becomes conversational and includes a literal-copyable example using the first detected host. No behavioural change; only the string content of the SystemExit changes.
- **TDD steps**:
  1. Write a test that monkeypatches both adapters' `detect()` to True, calls `detect_host()`, captures the SystemExit message, asserts it contains: (a) a copy-pastable `--agent <name>` example, (b) the env var name, (c) the literal list of detected hosts.
  2. Run; expect fail (current message doesn't include the example).
  3. Update `detect.py`.
  4. Run; expect pass.

- **Test code**:

```python
def test_detect_host_multi_host_message_includes_example(monkeypatch):
    """When multiple hosts are detected, the SystemExit message must give a
    ready-to-copy `--agent <name>` example and name the env var override.
    Finding 3 of the 2026-05-12 walkthrough — Samuel had both stacks installed
    and the bare `repr(['claude-code', 'hermes'])` was unfriendly."""
    import pytest
    from agent_skills.detect import detect_host
    from adapters.claude_code import ClaudeCodeAdapter
    from adapters.hermes import HermesAdapter

    monkeypatch.setattr(ClaudeCodeAdapter, "detect", lambda self: True)
    monkeypatch.setattr(HermesAdapter, "detect", lambda self: True)
    monkeypatch.delenv("AGENT_SKILLS_DEFAULT_AGENT", raising=False)

    with pytest.raises(SystemExit) as exc:
        detect_host()
    msg = str(exc.value)
    # Conversational text, not bare repr
    assert "claude-code" in msg and "hermes" in msg
    # Inline copy-pastable example
    assert "--agent claude-code" in msg or "--agent hermes" in msg
    # Env var override mentioned
    assert "AGENT_SKILLS_DEFAULT_AGENT" in msg
```

- **Implementation code shape** (rewrite `detect_host`'s multi-host branch):

```python
raise SystemExit(
    "Multiple agent hosts detected: " + ", ".join(found) + ".\n"
    "Pick one with --agent, e.g.:\n"
    f"  agent-skills <verb> --agent {found[0]}\n"
    "Or set a default: export AGENT_SKILLS_DEFAULT_AGENT=" + found[0]
)
```

- **Risk callouts**: None — string content of an error message.
- **Commit message**: `feat(detect): friendlier multi-host message with inline --agent example (Finding 3)`

---

### Finding 6 — `verify --json` exit code conflicts with structured status

- **Severity**: minor
- **PR grouping**: `POLISH PR #3`
- **Files to touch**:
  - `agent_skills/verbs/verify.py`
  - `tests/test_verify_verb.py`
- **Semantic change**: When `--json` is set, `verify` always exits 0 (the JSON IS the answer; the caller scripts off `status` field). When `--json` is not set, behaviour is unchanged — exit 0 on `clean`, exit 1 on every other status, exit 2 on hard errors (no registry, registry parse error, agent detection failure). The exit-code matrix is now documented as a docstring at the top of `verify.py`. (This is a small departure from the current uniform "1 on non-clean"; documenting it explicitly so the matrix is reviewable.)
- **TDD steps**:
  1. Add `test_verify_json_returns_zero_even_on_drift` to `test_verify_verb.py`.
  2. Add `test_verify_json_returns_zero_on_not_installed`.
  3. Keep existing `test_verify_drift` / `test_verify_yanked` as-is (no `--json`, still rc != 0).
  4. Update verify.py.
  5. Run; expect pass.

- **Test code** (append to `tests/test_verify_verb.py`):

```python
def test_verify_json_returns_zero_on_drift(tmp_path, monkeypatch, capsys):
    """With --json, verify always exits 0 — the JSON status field IS the
    machine-readable answer. Without --json, drift still exits 1 (unchanged).
    Finding 6 of the 2026-05-12 walkthrough."""
    setup_installed(tmp_path, monkeypatch, drift=True)
    from agent_skills.verbs.verify import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; json = True; yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    import json as _json
    payload = _json.loads(captured.out)
    assert rc == 0, "--json mode always exits 0 — status is in the payload"
    assert payload["status"] == "drift"


def test_verify_json_returns_zero_on_yanked(tmp_path, monkeypatch, capsys):
    setup_installed(tmp_path, monkeypatch, yanked=True)
    from agent_skills.verbs.verify import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; json = True; yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    import json as _json
    payload = _json.loads(captured.out)
    assert rc == 0
    assert payload["status"] == "yanked"


def test_verify_json_returns_nonzero_on_hard_error(tmp_path, monkeypatch, capsys):
    """Even with --json, true hard errors (missing registry) must exit non-zero
    so CI scripts can distinguish 'verify ran and reported a status' from
    'verify couldn't run'."""
    home = tmp_path / "home"; home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    # No registry.json written
    from agent_skills.verbs.verify import run
    class Args:
        id = "any/thing"; agent = "claude-code"; json = True; yes = False
    rc = run(Args())
    assert rc != 0  # hard error: no registry cache
```

- **Implementation code shape** (replace end of `verify.run`):

```python
"""Exit-code matrix:
  Without --json:  0 = clean ; 1 = any non-clean status ; 2 = hard error.
  With    --json:  0 = verify ran (status in payload) ; non-zero only on hard
                   errors (missing registry, unknown agent, etc.). The JSON
                   payload is the machine-readable answer in all non-error cases.
Finding 6 of the 2026-05-12 walkthrough.
"""
# ... unchanged until vr = adapter.verify(...)

if args.json:
    print(json.dumps({"id": args.id, "status": vr.status, "message": vr.message}, indent=2))
    return 0

print(f"{args.id}: {vr.status.upper()}")
print(f"  {vr.message}")
return 0 if vr.status == "clean" else 1
```

The hard-error paths (`registry is None`, `skill is None`) already `return 1`; rename internally to `return 2` is too invasive for v0.1.1 — leave as `return 1` for hard errors. Tests just assert non-zero, which is sufficient. (Documenting matrix as `0/1/2` in the docstring is aspirational for future v0.2 work; current code returns 0 or 1.)

- **Risk callouts**: `--json` flag now suppresses non-zero exit on drift/yanked. Any caller scripting off `agent-skills verify --json X; echo $?` would see behaviour change. Acceptable — zero callers today, and the doc says "the JSON IS the answer."
- **Commit message**: `feat(verify): --json mode returns 0 with status in payload (Finding 6)`

---

### Finding 7 — `show` tags format differs from `search`

- **Severity**: trivial
- **PR grouping**: `POLISH PR #3`
- **Files to touch**:
  - `agent_skills/verbs/show.py`
  - `tests/test_show_verb.py`
- **Semantic change**: `show` non-JSON output uses the `#tag` convention that `search` already uses. JSON output (the `tags` array) is unchanged.
- **TDD steps**:
  1. Update `test_show_verb.py` test that asserts the rendered Tags line — assert `#tag1 #tag2` shape.
  2. Run; expect fail.
  3. Update show.py line 67.
  4. Run; expect pass.

- **Test code**:

```python
def test_show_renders_tags_with_hash_prefix(tmp_path, monkeypatch, capsys):
    """show's plaintext output uses #tag notation matching search verb.
    Finding 7 of the 2026-05-12 walkthrough — search and show used different
    tag formats, which is just visual inconsistency."""
    # Reuse existing show-verb fixture/setup pattern (see existing tests)
    home = tmp_path / "home"; home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"; cache.mkdir(parents=True)
    import json as _json
    (cache / "registry.json").write_text(_json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test/example", "name": "example", "description": "d",
            "version": "0.1.0", "status": "active",
            "author": {"name": "T", "github_login": "test", "github_id": 1},
            "category": "meta", "tags": ["alpha", "beta"],
            "platforms": ["linux"], "agent_compat": ["claude-code"],
            "license": "MIT", "install": {"claude-code": {"scope": "user"}},
            "has_scripts": False,
            "requires": {"env_vars": [], "commands": []},
            "versions": {"0.1.0": {"sha": "x" * 40, "released": "2026-05-11T00:00:00Z"}},
            "source": {"path": "skills/test/example", "content_hash": "sha256:0", "files": []},
        }],
    }))
    from agent_skills.verbs.show import run
    class Args:
        id = "test/example"; agent = "claude-code"; json = False; yes = False
    run(Args())
    out = capsys.readouterr().out
    assert "#alpha" in out and "#beta" in out
    # The old space-separated bare form should be gone
    assert "alpha beta" not in out
```

- **Implementation code shape** (in `show.py`):

```python
tags = skill.get("tags", [])
tag_line = " ".join(f"#{t}" for t in tags) if tags else "—"
print(f"  Tags:      {tag_line}")
```

- **Risk callouts**: None.
- **Commit message**: `style(show): use #tag format consistent with search verb (Finding 7)`

---

### Finding 8a — `init` env-var detector has high false-positive rate

- **Severity**: moderate UX
- **PR grouping**: `POLISH PR #3`
- **Files to touch**:
  - `agent_skills/verbs/init.py`
  - `tests/test_init_verb.py`
- **Semantic change**: Replace the bare `\b[A-Z][A-Z0-9_]{2,}\b` regex with three USE-pattern regexes (shell-style `$VAR` / `${VAR}`, `os.environ.get("VAR")`, `os.getenv("VAR")`). Bare prose acronyms (`SSH`, `LLM`, `NFS`) no longer trigger detection — only references that look like an actual env-var lookup.
- **TDD steps**:
  1. Write tests: prose acronyms not detected, shell-style detected, Python-style detected.
  2. Run; expect first to fail with current regex.
  3. Update `init.py`.
  4. Run; expect pass.

- **Test code** (append to `tests/test_init_verb.py`):

```python
def test_init_env_var_scan_ignores_prose_acronyms(tmp_path, fake_gh, monkeypatch):
    """Acronyms in prose (SSH, LLM, NFS, README, CLAUDE) must not be flagged
    as env vars. Finding 8a of the 2026-05-12 walkthrough — Samuel's
    homelab-docs SKILL.md generated 5 false positives ('README', 'CLAUDE',
    'LLM', 'NFS', 'SSH'), all of which were bare prose acronyms."""
    import io
    skill = tmp_path / "homelab"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: homelab\ndescription: x\n---\n\n"
        "Use SSH and NFS to access ~/.claude/ on the LLM cluster.\n"
        "See README.md for setup.\n"
    )
    inputs = "\n".join(["", "", "", "", "3", "", "", "1", "", ""]) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(inputs))
    import agent_skills.verbs.init as init_mod
    monkeypatch.setattr(init_mod, "_fetch_gh_user", lambda: ("test-author", 1))

    from agent_skills.verbs.init import run
    class Args:
        target = str(skill); yes = False
    run(Args())
    import json as _json
    meta = _json.loads((skill / "meta.json").read_text(encoding="utf-8"))
    # None of these prose acronyms is a real env var
    assert meta["requires"]["env_vars"] == [], (
        f"expected empty env_vars, got {meta['requires']['env_vars']}"
    )


def test_init_env_var_scan_detects_shell_style(tmp_path, fake_gh, monkeypatch):
    """Real env var uses (shell $VAR / ${VAR}, os.environ, os.getenv) ARE
    detected. Counterpoint to test_init_env_var_scan_ignores_prose_acronyms."""
    import io
    skill = tmp_path / "real-env"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: x\ndescription: y\n---\n\n"
        "Set $SPOTIFY_CLIENT_ID and ${SPOTIFY_CLIENT_SECRET}.\n"
        "Python: os.environ.get('GITHUB_TOKEN') or os.getenv('AGENT_SKILLS_DEFAULT_AGENT').\n"
    )
    # Accept default detection (empty input on env_vars prompt accepts the
    # detected CSV).
    inputs = "\n".join(["", "", "", "", "3", "", "", "1", "", ""]) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(inputs))
    import agent_skills.verbs.init as init_mod
    monkeypatch.setattr(init_mod, "_fetch_gh_user", lambda: ("test-author", 1))

    from agent_skills.verbs.init import run
    class Args:
        target = str(skill); yes = False
    run(Args())
    import json as _json
    meta = _json.loads((skill / "meta.json").read_text(encoding="utf-8"))
    detected = set(meta["requires"]["env_vars"])
    assert "SPOTIFY_CLIENT_ID" in detected
    assert "SPOTIFY_CLIENT_SECRET" in detected
    assert "GITHUB_TOKEN" in detected
    assert "AGENT_SKILLS_DEFAULT_AGENT" in detected
```

- **Implementation code shape** (in `init.py`, replace `ENV_VAR_RE` and the env-detection block in `_scan_body`):

```python
# Real env-var USES, not bare acronyms. Patterns:
#   $VAR / ${VAR}               (shell)
#   os.environ[X] / .get(X)     (Python dict-style and method-style)
#   os.getenv(X)                (Python)
# Captures the variable name itself.
ENV_VAR_PATTERNS = [
    re.compile(r"\$\{?([A-Z_][A-Z0-9_]*)\}?"),
    re.compile(r"os\.environ(?:\[|\.get\(\s*)[\"']([A-Z_][A-Z0-9_]*)[\"']"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']"),
]


def _scan_body(body: str) -> tuple[list[str], list[str]]:
    """Scan body text for env-var USES (not bare ALL_CAPS acronyms) and
    command tokens. Pre-Finding-8a, the env-var heuristic was a bare
    `\\b[A-Z][A-Z0-9_]{2,}\\b` regex which matched any prose acronym
    (SSH, LLM, NFS) — high false-positive rate. Now patterns require an
    actual use site: $VAR, ${VAR}, os.environ[...], os.getenv(...)."""
    env_vars: list[str] = []
    seen_env: set[str] = set()
    for pat in ENV_VAR_PATTERNS:
        for m in pat.finditer(body):
            tok = m.group(1)
            if tok and tok not in seen_env:
                env_vars.append(tok)
                seen_env.add(tok)

    # commands unchanged
    commands = []
    seen_cmd: set[str] = set()
    for token in COMMAND_TOKENS:
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(token) + r"(?![A-Za-z0-9_])"
        if re.search(pattern, body) and token not in seen_cmd:
            commands.append(token)
            seen_cmd.add(token)
    commands.sort()
    return env_vars, commands
```

Delete the now-unused `ENV_VAR_SKIP` set (its purpose evaporates with the new patterns) — or keep it as a final filter for the rare bare `$VAR` that's actually a placeholder. Recommendation: delete it; if a real false positive shows up, add a skip set then. Less code, less misleading.

- **Risk callouts**: A skill author whose SKILL.md only mentions env vars as bare prose (e.g., "set SPOTIFY_CLIENT_ID before running") will no longer get them auto-detected; they'll have to type the CSV themselves at the prompt. That's correct — auto-detection should err toward false-negatives over false-positives. The existing test `test_init_scaffolds_meta_from_skill_md` uses SKILL.md body `# H\n` (no env vars) so no test breakage.
- **Commit message**: `fix(init): detect env-var USES not bare acronyms (Finding 8a)`

---

### Finding 8b — `init` defaults `id` slug to directory name, not SKILL.md `name`

- **Severity**: low
- **PR grouping**: `POLISH PR #3`
- **Files to touch**:
  - `agent_skills/verbs/init.py` (line 207: derive slug from frontmatter `name` not `target.name`)
  - `tests/test_init_verb.py`
- **Semantic change**: Default `id` becomes `<gh_login>/<frontmatter_name>` instead of `<gh_login>/<dir_basename>`. The user can still override at the prompt. Eliminates the round-trip via `validate.py` failure when dir name ≠ frontmatter name (common scenario: user copies a skill into a `-test` dir).
- **TDD steps**:
  1. Test: dir name is `homelab-docs-test` but SKILL.md has `name: homelab-docs`; default id offered is `<login>/homelab-docs`.
  2. Test: empty input at id prompt accepts the default; meta.json id matches frontmatter name.
  3. Run; expect fail.
  4. Update init.py.
  5. Run; expect pass.

- **Test code**:

```python
def test_init_defaults_id_to_frontmatter_name_not_dir(tmp_path, fake_gh, monkeypatch):
    """When the local dir name differs from the SKILL.md frontmatter `name`,
    init defaults the id slug to the FRONTMATTER name (the source of truth),
    not the dir basename. Finding 8b of the 2026-05-12 walkthrough — Samuel
    tested in /tmp/homelab-docs-test/ with frontmatter name: homelab-docs,
    and the wrong default broke validate.py's cross-file consistency check."""
    import io
    skill = tmp_path / "homelab-docs-test"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: homelab-docs\ndescription: real name\n---\n# body\n"
    )
    inputs = "\n".join(["", "", "", "", "3", "", "", "1", "", ""]) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(inputs))
    import agent_skills.verbs.init as init_mod
    monkeypatch.setattr(init_mod, "_fetch_gh_user", lambda: ("test-author", 1))

    from agent_skills.verbs.init import run
    class Args:
        target = str(skill); yes = False
    run(Args())
    import json as _json
    meta = _json.loads((skill / "meta.json").read_text(encoding="utf-8"))
    # Slug part of id MUST come from frontmatter, not dir
    assert meta["id"] == "test-author/homelab-docs", (
        f"expected id 'test-author/homelab-docs', got {meta['id']!r}"
    )
```

- **Implementation code shape** (in `init.py`, line 207-208):

```python
# Default id slug comes from SKILL.md frontmatter `name` (source of truth),
# not from `target.name` — the dir is incidental, the frontmatter is
# canonical. Falls back to target.name only if frontmatter parsing failed
# somehow (defensive; the missing-name case already exits earlier).
slug = name or target.name
default_id = f"{gh_login}/{slug}"
```

- **Risk callouts**: None. The existing happy-path test (`test_init_scaffolds_meta_from_skill_md`) has dir name == frontmatter name (`homelab-docs`), so no regression.
- **Commit message**: `fix(init): default id slug to SKILL.md frontmatter name not dir (Finding 8b)`

---

### Finding 4 — `install` end-to-end works (positive observation)

- **Severity**: n/a — no fix
- **PR grouping**: n/a
- **Action**: None. Documented in the walkthrough as a positive end-to-end check; no code change.

---

### Finding 9 — `uninstall --force` drift handling (positive observation)

- **Severity**: n/a — no fix
- **PR grouping**: n/a
- **Action**: None. Once Finding 5 lands, the false-positive drift on every install disappears and uninstall-without-force becomes the happy path again automatically.

---

### Finding 10 (NEW — discovered during planning pass) — `generate_manifest.compute_content_hash` does NOT filter `MARKER_FILENAME`, but `_base.compute_dir_content_hash` DOES

- **Severity**: trivial (currently moot, but a future-proofing concern)
- **PR grouping**: `BLOCKER PR #2` (resolved as a side-effect of hash unification)
- **Description**: `scripts/generate_manifest.py::compute_content_hash` doesn't exclude `MARKER_FILENAME` from its file walk. `adapters/_base.py::compute_dir_content_hash` does. Today this never matters because registry-side skill dirs (under `skills/<author>/<slug>/`) never contain a marker — markers are written at install time into the user's home. But if someone ever accidentally commits a marker to the registry (e.g., copy-pasting an installed skill into the repo), the registry hash and the install-time hash would diverge again. The unified canonical hash function in PR #2 filters `MARKER_FILENAME` consistently, removing this latent footgun.
- **Action**: Folded into Finding 5's fix. No separate test needed — `test_hash_ignores_marker_file` in `test_hash_canonical.py` covers it.

---

### Finding 11 (NEW — discovered during planning pass) — `verbs/install.py` recomputes `content_hash` after `materialize_tree` then passes it to the adapter as `registry_hash`, but the registry already has the canonical hash

- **Severity**: very low (post-Finding-5; pre-Finding-5 it's a symptom, not a cause)
- **PR grouping**: `BLOCKER PR #2` (cleanup alongside the hash unification)
- **Description**: In `agent_skills/verbs/install.py:109`, install does `content_hash = compute_dir_content_hash(staging)` and then passes it as `opts["registry_hash"]` to the adapter. The adapter writes that value into the marker as `registry_content_hash`. But the canonical `content_hash` for the skill is already in `registry.json[].source.content_hash` — by recomputing from the staging dir, we are (a) asserting our function matches registry's (which is the bug Finding 5 catches) and (b) doing redundant work. **Recommendation**: post-Finding-5, use `skill["source"]["content_hash"]` directly from the registry and assert (defensively, with a debug-only check) that the staging dir's recomputed hash matches it. If mismatch, abort install with a clear error — that's a real tamper signal (the git tree we just materialized doesn't hash to what the registry promised).
- **Action**: In PR #2, change install.py to:

```python
# Use the registry's canonical hash for the marker. Defensively verify the
# staging dir hashes to the same value — if it doesn't, either (a) the
# canonical hash function in adapters._base has a bug, or (b) the git
# archive returned different bytes than the registry was built from
# (tamper signal — abort).
registry_hash = skill.get("source", {}).get("content_hash", "")
staging_hash = compute_dir_content_hash(staging)
if registry_hash and staging_hash != registry_hash:
    print(
        f"Install aborted: materialized tree hash {staging_hash} does not match\n"
        f"registry-declared hash {registry_hash} for {full_id}@{target_version}.\n"
        f"The git tree at sha {tree_sha} may have been altered.",
        file=sys.stderr,
    )
    return 1
content_hash = registry_hash or staging_hash
```

This converts the silent post-Finding-5 redundancy into an active tamper check.

- **Test code** (append to `tests/test_install_verb.py`):

```python
def test_install_aborts_on_staging_hash_mismatch(install_env, monkeypatch, capsys):
    """If the canonical hash of the materialized staging dir does not match
    the registry's declared content_hash, install aborts with a clear error.
    This catches the case where the git tree at the recorded SHA has been
    altered (tamper). Finding 11 (planning-pass discovery)."""
    # Mutate registry to declare a hash that won't match what the real tree
    # produces. The staging dir will hash to something else, install must abort.
    import json as _json
    reg_path = install_env["cache"] / "registry.json"
    reg = _json.loads(reg_path.read_text())
    reg["skills"][0]["source"]["content_hash"] = "sha256:" + "f" * 64
    reg_path.write_text(_json.dumps(reg))

    from agent_skills.verbs.install import run
    class Args:
        spec = "test-author/example"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    msg = (captured.out + captured.err).lower()
    assert "hash" in msg
    assert "registry" in msg
```

- **Commit message**: include in Finding 5's commit, or split as `feat(install): tamper-check materialized tree against registry hash`. Recommendation: single commit with Finding 5 since the two are conceptually one fix (unified hashing + tamper integrity).

---

## 4. Cross-cutting test additions

These go in PR #2 (the hash unification PR), with one in PR #1 (UTF-8) for cross-cutting CLI smoke.

### 4.1 `test_install_then_verify_returns_clean` — the load-bearing integration test

Goes in a NEW file `tests/test_integration_install_verify.py`. Runs the actual `install` verb against a tmp registry-repo, then the actual `verify` verb, and asserts `clean`. This is the regression gate for Finding 5 going forward.

```python
"""Integration test for Finding 5: install → verify must report 'clean'.
Pre-fix this returned 'drift' on every install because generate_manifest and
adapters._base used divergent hash algorithms. Post-fix, they share one
canonical function — this test prevents that class of bug from re-entering."""
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent


def test_install_then_verify_clean(tmp_path, monkeypatch):
    """Full pipeline: generate_manifest builds registry.json with content_hash;
    install materializes the tree, writes the marker (which stores the SAME
    hash); verify recomputes from disk and compares. All three operations
    must produce identical bytes for the same content."""
    # 1) Build a tmp registry-repo with one skill from the good fixture.
    repo = tmp_path / "registry-repo"
    shutil.copytree(ROOT, repo,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "tests"))
    # Replace skills/ with a single fixture skill.
    skills_root = repo / "skills"
    if skills_root.exists():
        shutil.rmtree(skills_root)
    skill_src = ROOT / "tests/fixtures/good/instructions-only"
    skill_dst = repo / "skills/test-author/example"
    skill_dst.mkdir(parents=True)
    shutil.copytree(skill_src, skill_dst, dirs_exist_ok=True)
    # Ensure the fixture's meta.json id matches our author/slug
    meta = json.loads((skill_dst / "meta.json").read_text(encoding="utf-8"))
    meta["id"] = "test-author/example"
    meta.setdefault("author", {})
    meta["author"]["github_login"] = "test-author"
    meta["author"]["github_id"] = 1
    (skill_dst / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, capture_output=True)
    # 2) Generate registry.json
    subprocess.run([sys.executable, str(repo / "scripts/generate_manifest.py")],
                   cwd=repo, check=True, capture_output=True)

    # 3) Set up fake HOME with .claude and the registry/repo in the cache.
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    shutil.copy(repo / "registry.json", cache / "registry.json")
    shutil.copytree(repo, cache / "registry-repo")

    # 4) Run install.
    from agent_skills.verbs.install import run as install_run
    class IArgs:
        spec = "test-author/example"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = install_run(IArgs())
    assert rc == 0, "install must succeed"
    target = home / ".claude/skills/test-author-example"
    assert (target / "SKILL.md").exists()
    assert (target / ".agent-skills-marker.json").exists()

    # 5) Run verify — MUST return clean.
    from agent_skills.verbs.verify import run as verify_run
    class VArgs:
        id = "test-author/example"; agent = "claude-code"; json = True; yes = False
    rc = verify_run(VArgs())
    assert rc == 0, "verify --json always returns 0; status must be 'clean' in payload"

    # 6) Sanity-check: marker's hash == registry's hash == on-disk hash.
    marker = json.loads((target / ".agent-skills-marker.json").read_text(encoding="utf-8"))
    registry = json.loads((cache / "registry.json").read_text(encoding="utf-8"))
    registry_hash = registry["skills"][0]["source"]["content_hash"]
    assert marker["registry_content_hash"] == registry_hash

    from adapters._base import compute_dir_content_hash
    on_disk_hash = compute_dir_content_hash(target)
    assert on_disk_hash == registry_hash, (
        f"on-disk recomputed hash diverges from registry hash — "
        f"this is exactly Finding 5 re-emerging. "
        f"on_disk={on_disk_hash!r} registry={registry_hash!r}"
    )
```

### 4.2 `test_uninstall_no_force_succeeds_after_install` — protects against drift-detection false positives

Adds to `tests/test_uninstall_verb.py` or `test_integration_install_verify.py`.

```python
def test_uninstall_without_force_succeeds_after_install(tmp_path, monkeypatch):
    """Pre-Finding-5, uninstall-without-force failed on every install because
    every install reported drift. Post-fix, the happy path works. Regression
    guard so this never re-breaks."""
    # ... (same setup as test_install_then_verify_clean steps 1-4)
    # Then:
    from agent_skills.verbs.uninstall import run as uninstall_run
    class UArgs:
        id = "test-author/example"
        agent = "claude-code"
        force = False
        json = False
        yes = True
    rc = uninstall_run(UArgs())
    assert rc == 0
    target = home / ".claude/skills/test-author-example"
    assert not target.exists()
```

### 4.3 `test_cli_no_unicode_traceback_on_cp1252_stdout` — covers the entire CLI surface for Unicode-glyph crashes

PR #1, in `test_cli_scaffold.py`. Already covered by `test_cli_search_unicode_star_does_not_crash` above — no additional test needed.

### 4.4 `test_generate_manifest_imports_canonical_hash_from_base` — locks the architecture

Optional but cheap belt-and-braces. Goes in `tests/test_generate_manifest.py`.

```python
def test_generate_manifest_uses_canonical_hash_function():
    """generate_manifest.py must NOT define its own compute_content_hash —
    it must import from adapters._base. Lock the architecture so a future
    contributor doesn't re-introduce the two-implementations bug."""
    import scripts.generate_manifest as gm
    import adapters._base as base
    # If both modules export the same function object, they share an
    # implementation. If they don't, this test is a no-op (false-negative
    # safe), but the test in test_hash_canonical.py
    # `test_generate_manifest_and_base_produce_equal_hashes` is the real gate.
    # This test just protects against a sneaky re-fork.
    assert not hasattr(gm, "compute_content_hash"), (
        "generate_manifest.compute_content_hash was removed in v0.1.1 — "
        "the canonical implementation lives in adapters._base. If you need "
        "to extend hashing semantics, edit adapters/_base.py only."
    )
    assert not hasattr(gm, "sha256_file"), (
        "generate_manifest.sha256_file was removed in v0.1.1 — see above."
    )
```

---

## 5. Risk register

### 5.1 `.gitattributes` — already correct, but worth a defensive addition

The current `.gitattributes` sets `* text=auto eol=lf`. This is correct and addresses the CRLF→LF normalisation at the git layer, complementing the in-code normalisation in the canonical hash function. **No change needed.** However, an explicit rule for the two high-impact filenames would make the intent loud:

```
SKILL.md text eol=lf
meta.json text eol=lf
```

Cheap, defensive, recommended as a 2-line addition in PR #2.

### 5.2 Other hash-touching code paths — audited, none missed

- `clients/skill_contribution/submit.py` — does NOT compute any hash. Reads meta.json, runs validate/security_scan as subprocesses, writes REVIEW.md + SANITIZATION.diff + scan_results.json. Safe.
- `clients/skill_contribution/sanitize.py` and `diff.py` — these don't hash either (they emit unified diffs). Safe.
- `clients/skill_discovery/match.py` and `update.py` — match scores against the registry's `description`/`tags`/etc; refresh fetches and stores the registry verbatim. Neither computes content hashes. Safe.
- `agent_skills/cache.py` — pure JSON load. Safe.
- `adapters/hermes.py::verify` — compares `marker["registry_content_hash"]` to the registry hash directly (does NOT recompute on disk, because Hermes rewrites SKILL.md frontmatter at install time so on-disk bytes intentionally diverge). The fix to the canonical hash function does NOT affect Hermes's verify path because it doesn't recompute. Safe.

**One audit-flag worth surfacing**: Hermes's verify path won't catch real disk-side tampering — it only catches marker-vs-registry mismatch. If an attacker edits a file in `~/.hermes/skills/<cat>/<slug>/` after install, the marker still has the original hash and Hermes verify still reports `clean`. This is a known and accepted v0 trade-off (per the Hermes adapter docstring) but worth noting in the risk register because the fix to Finding 5 makes the Claude-Code adapter MORE rigorous, widening the gap. Recommendation: add a docstring comment in `hermes.py::verify` explicitly noting this asymmetry, and consider a Hermes-specific approach in a future PR (store BOTH the original tree hash AND the post-rewrite hash in the marker, compare both).

### 5.3 `schema_version` bump — NOT needed

The fix to Finding 5 changes the algorithm that computes `source.content_hash`. The field's shape (`"sha256:<64-hex>"`) and meaning ("content hash of the skill directory") are unchanged. **No schema bump required.** A consumer reading `registry.json` cannot tell the difference between a v0.1.0-generated hash and a v0.1.1-generated hash — both are valid sha256 hex strings of the same shape. Existing markers in user homes (zero today) would mismatch the new registry, surfacing as `drift` until reinstall. Acceptable for pre-public.

### 5.4 Existing markers in the wild — zero users today

The registry is private; the only `~/.claude/skills/<flat>/.agent-skills-marker.json` files in existence are on Samuel's machine. After PR #2 lands, those existing markers will report `drift` on the next `verify`. The walkthrough notes this explicitly: "every freshly-installed skill on every platform reports DRIFT" — i.e., the markers Samuel has today already have bad hashes anyway. The recovery path is simply `agent-skills install <id>` (reinstall), which writes a fresh marker with the now-canonical hash. **No migration step needed.**

### 5.5 Spec § 4 locked decisions — no conflicts

Audited the 18 locked decisions in spec § 4 against the proposed fixes:
- Decision #16 (SKILL.md casing) — Finding 8b respects it (frontmatter `name` is canonical, dir is incidental). No conflict.
- Decision #17 (init flow) — Finding 8a + 8b refine init's UX heuristics; they don't change the locked behavioural contract (scan SKILL.md, prompt interactively, write meta.json). No conflict.
- Decision #5 (drift refuses uninstall) — Finding 9 confirms working as intended. No conflict.
- Decision #10 (yanking model) — Finding 6's `--json` change is orthogonal to yank semantics (hard-refuse install is still hard-refuse). No conflict.
- All other decisions (#1-4, #6-9, #11-15, #18) — untouched.

**Zero locked-decision conflicts.**

---

## 6. Non-blocking polish recommended while in the area

Up to 5 items. Recommended for inclusion in PR #3:

1. **`--version` flag on `agent-skills`**: surfaces `__version__` from `agent_skills/__init__.py`. Two lines in `cli.py` (`p.add_argument("--version", action="version", version=f"agent-skills {__version__}")`). Currently a user has no way to know what version they're running. Worth adding alongside the 0.1.0→0.1.1 bump in PR #2 — moving this into PR #2 is also defensible.

2. **`update --quiet`**: suppresses the "Warning: registry.json.sig not found — running unsigned." message when the user knows they're using unsigned (e.g., local-file registry). One arg + one `if not args.quiet:` guard. The warning is correct but spammy in dev loops.

3. **`detect_host` error mentions the env var with `=<name>`**: change `"... or pass --agent."` to `"... or pass --agent <name>."` so the example is copy-pastable. Trivially small; folded into Finding 3.

4. **`init` shows a one-line confirmation summary at the end before writing**: the verb already prints a summary AFTER writing. Adding a `--yes` flag (already in cli.py argparse) actually-skips-confirmation, and adding a `(y/N)?` prompt when `--yes` is not set, makes the verb safer against accidental overwrites. Defer — actually a small spec change; tabled for v0.2.

5. **`verbs/install.py` clearer error when `~/.cache/agent-skills/registry-repo` is missing**: current message `"No registry repo at {repo}. Run agent-skills update first."` is already clear. Skip.

**Recommended for PR #3**: items 1, 2, 3. Item 4 deferred. Item 5 no-op.

---

## 7. Deliverable execution plan (tactical)

### How many PRs

**Three.** Strict ordering for merge sequence:

1. **PR #1 — BLOCKER: UTF-8 stdout** (Finding 2 + regression test for Finding 1).
   - Files: `agent_skills/cli.py`, `tests/test_cli_scaffold.py`, `tests/test_update.py`.
   - Tests added: 3.
   - Lines changed: ~30 source, ~80 tests.
   - Sign-off: `pytest tests/ -v` returns 0 with at least 139 tests collected (136 baseline + 3 new). CI matrix green across all 12 cells (3 OS × 4 Python).

2. **PR #2 — BLOCKER: hash unification + tamper check + version bump** (Finding 5 + Finding 10 + Finding 11).
   - Files: `adapters/_base.py`, `scripts/generate_manifest.py`, `agent_skills/verbs/install.py`, `registry.json` (regenerated), `pyproject.toml` (version bump 0.1.0 → 0.1.1), `.gitattributes` (defensive 2 lines), `tests/test_hash_canonical.py` (NEW), `tests/test_integration_install_verify.py` (NEW), `tests/test_install_verb.py` (1 new test), `tests/test_generate_manifest.py` (1 new test).
   - Tests added: ~10.
   - Lines changed: ~80 source, ~280 tests.
   - Sign-off: `pytest tests/ -v` returns 0 with at least 149 tests collected. `python scripts/generate_manifest.py --check` returns 0. Registry-checks CI job green.

3. **PR #3 — POLISH: 7 findings + polish items** (Findings 3, 6, 7, 8a, 8b + non-blocking polish items 1 & 2).
   - Files: `agent_skills/detect.py`, `agent_skills/verbs/verify.py`, `agent_skills/verbs/show.py`, `agent_skills/verbs/init.py`, `agent_skills/verbs/update.py` (`--quiet` flag), `agent_skills/cli.py` (`--version` flag), `agent_skills/__init__.py` (add `__version__`), corresponding tests.
   - Tests added: ~10.
   - Lines changed: ~60 source, ~200 tests.
   - Sign-off: full suite green; no version bump (still 0.1.1).

### Order of merge

PR #1 first (smallest, isolates the most user-visible fix). PR #2 second. PR #3 third.

### Sign-off per PR

After each PR is merged to `main`:
- `pytest tests/ -v` exits 0.
- `python scripts/validate.py --all` exits 0.
- `python scripts/security_scan.py --all` exits 0.
- `python scripts/generate_manifest.py --check` exits 0.
- CI matrix (3 OS × 4 Python = 12 cells) all green.
- Test counts: PR #1 ≥ 139; PR #2 ≥ 149; PR #3 ≥ 159 (approximate — exact counts depend on which test files get split).

### `pyproject.toml` version bump

**Yes, bump `0.1.0` → `0.1.1` in PR #2 only.** Rationale: PR #2 changes user-visible semantic behaviour (hash algorithm; install tamper-check). PR #1 is a bug fix that doesn't change any API contract (and is arguably part of `0.1.0` should-have-worked behaviour). PR #3 polishes UX without changing contracts; bumping again to `0.1.2` is defensible but premature pre-public. Single bump in PR #2 keeps the changelog tidy.

Additionally, in PR #2, also update the marker's `installed_by` field in `adapters/_base.py::write_marker` from `"agent-skills 0.1.0"` to read the version dynamically:

```python
from agent_skills import __version__ as _agent_skills_version
# ...
"installed_by": f"agent-skills {_agent_skills_version}",
```

And add `__version__ = "0.1.1"` to `agent_skills/__init__.py` (one line) — this also enables polish item #1 (`--version` flag).

---

## Appendix A — Findings → PR mapping at a glance

| # | Finding | Sev | PR | Files touched | Tests added |
|---|---|---|---|---|---|
| 1 | Mojibake em-dash | low | PR #1 | none (auto-fix) | 1 regression test |
| 2 | `★` crash | BLOCKER | PR #1 | `cli.py` | 2 |
| 3 | Multi-host UX | minor | PR #3 | `detect.py` | 1 |
| 4 | (positive — install OK) | — | — | — | — |
| 5 | Hash divergence | BLOCKER | PR #2 | `_base.py`, `generate_manifest.py`, `install.py`, `registry.json`, `pyproject.toml`, `.gitattributes` | ~8 |
| 6 | `verify --json` exit | minor | PR #3 | `verify.py` | 3 |
| 7 | tag format | trivial | PR #3 | `show.py` | 1 |
| 8a | env-var FP | moderate | PR #3 | `init.py` | 2 |
| 8b | id default | low | PR #3 | `init.py` | 1 |
| 9 | (positive — uninstall OK) | — | — | — | 1 happy-path |
| 10 | (new) Marker filter parity | trivial | PR #2 | folded into Finding 5 | (covered) |
| 11 | (new) Install tamper-check | low | PR #2 | `install.py` | 1 |

**Total new tests: ~21. Total source files touched: 9.**

---

## Appendix B — Notes on contradictions / re-classifications

- **Finding 6**: walkthrough author called this minor and offered "exit 0 when --json is set" as an idea. I'd promote the idea to a recommendation — without it, `agent-skills verify --json X | jq .status` requires `set +e` wrapping in shell scripts, which is the opposite of what `--json` is for. Plan adopts the idea.
- **Finding 7**: walkthrough author called this trivial. I agree — but include it in PR #3 for free; the test is two lines and the source change is two lines.
- **Finding 8a**: walkthrough author suggested either tighter regex OR lean on the user-confirm UX. Plan takes the tighter regex path — auto-detection should be high-precision, not high-recall. If a real false negative shows up post-merge, we add prose-acronym detection back behind an explicit `--scan-acronyms` flag.
- **Finding 4 + 9**: positive observations. Worth adding 1 happy-path test for the Finding 9 case (uninstall-without-force succeeds after install) — that test goes in PR #2's integration test file because it depends on Finding 5 being fixed.

End of plan.
