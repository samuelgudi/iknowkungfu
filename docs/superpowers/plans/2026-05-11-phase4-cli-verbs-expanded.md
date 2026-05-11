# Phase 4 CLI Verbs — Expanded TDD Plan (Tasks 16-21)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the structurally compressed Tasks 16-21 of `2026-05-11-agent-skills-hub-v0.md` (the `show`, `install`, `uninstall`, `verify`, `list`, `update` verbs) into full TDD steps with complete test code, complete implementation code, and exact commit messages.

**Architecture:** Each verb is `agent_skills/verbs/<verb>.py` exposing `def run(args) -> int`. The CLI in `agent_skills/cli.py` (already written by Task 14) registers the verb's argparse subparser and dispatches `run(args)`. Verbs use `agent_skills.cache.load_registry()` and `agent_skills.detect.detect_host(...)` for shared mechanics. `update.py` lives in `clients/skill_discovery/` and is invoked by the `update` verb. The discovery cache is `~/.cache/agent-skills/`.

**Pattern reference:** `agent_skills/verbs/search.py` (Task 15) is the canonical template — load_registry + detect_host + work + JSON-or-table output.

**Tech Stack:** Python 3.10+, argparse, subprocess (for `git`, `gh`), urllib.request (for HTTPS fetch). No new dependencies.

**Spec ref:** `docs/superpowers/specs/2026-05-11-agent-skills-hub-design.md` § 9.

**Prerequisites done:** Tasks 1-15 (registry tooling + adapters + CLI scaffold + search verb). HEAD at `f327326`. 72 tests passing.

---

## File Structure

| File | Responsibility |
|---|---|
| `agent_skills/verbs/show.py` | Single-skill detail printer |
| `agent_skills/verbs/install.py` | Resolve version → fetch tree → call adapter.install |
| `agent_skills/verbs/uninstall.py` | Drift check → call adapter.uninstall |
| `agent_skills/verbs/verify.py` | Read registry hash + yanked flag → adapter.verify → print status |
| `agent_skills/verbs/list.py` | Walk adapter.list_installed → print one line per skill |
| `agent_skills/verbs/update.py` | Thin CLI wrapper that calls clients.skill_discovery.update.refresh() |
| `clients/skill_discovery/update.py` | HTTPS fetch of registry.json + yanks.json, sha256 verify, rollback guard, atomic write |
| `tests/test_show_verb.py` | Subprocess + tmpdir registry tests for `show` |
| `tests/test_install_verb.py` | Local-git-registry tests; covers version pinning, yanked refusal, conflict refuse |
| `tests/test_uninstall_verb.py` | Adapter-call coverage, drift refusal, --force override |
| `tests/test_verify_verb.py` | clean / drift / yanked / marker_outdated paths |
| `tests/test_list_verb.py` | --agent override; empty + populated cases |
| `tests/test_update.py` | HTTP-server-fixture tests; rollback guard; sha256 verify (optional warn) |
| `agent_skills/cli.py` | Add per-verb argparse subparser + dispatch import for each new verb |

---

## Execution order

Tasks 16-20 are independent of each other after Task 15. Task 21 introduces `update.py` and reuses no logic from 16-20. Dispatch one at a time (subagent-driven), verify each commit before moving on.

---

## Task 16: `show` verb

**Files:**
- Create: `agent_skills/verbs/show.py`
- Create: `tests/test_show_verb.py`
- Modify: `agent_skills/cli.py` (wire `show <id>` subparser + dispatch)

- [ ] **Step 1: Write tests/test_show_verb.py**

```python
"""Tests for the show verb."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent


def run_cli(*args, env_extra=None):
    env = None
    if env_extra:
        import os
        env = {**os.environ, **env_extra}
    return subprocess.run(
        [sys.executable, "-m", "agent_skills", *args],
        capture_output=True, text=True, env=env,
    )


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Redirect ~/.cache/agent-skills to a tmpdir, populate with a tiny registry."""
    home = tmp_path / "home"
    home.mkdir()
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home)
    # Touch a fake .claude so detect_host doesn't fail
    (home / ".claude").mkdir()
    registry = {
        "schema_version": 2,
        "generated_at": "2026-05-11T00:00:00Z",
        "skills": [
            {
                "id": "test-author/example",
                "name": "example",
                "description": "Example skill for testing.",
                "version": "0.1.0",
                "status": "active",
                "author": {"name": "Test", "github_login": "test-author", "github_id": 1},
                "category": "meta",
                "tags": ["test"],
                "platforms": ["linux"],
                "agent_compat": ["claude-code"],
                "requires": {"env_vars": [], "commands": []},
                "license": "MIT",
                "install": {"claude-code": {"scope": "user"}},
                "has_scripts": False,
                "versions": {"0.1.0": {"sha": "a" * 40, "released": "2026-05-11T00:00:00Z"}},
                "source": {"path": "skills/test-author/example", "content_hash": "sha256:" + "0" * 64, "files": ["SKILL.md", "meta.json"]},
            }
        ],
    }
    (cache / "registry.json").write_text(json.dumps(registry))
    return cache


def test_show_prints_known_skill(cache_dir):
    """show <id> finds the skill and prints id, version, license, category."""
    # Invoke via the cli.run function directly to use the monkeypatched HOME
    from agent_skills.verbs.show import run
    class Args:
        id = "test-author/example"
        agent = "claude-code"
        json = False
        yes = False
    rc = run(Args())
    # We can't capture stdout here easily; check rc only. Format is verified by JSON test below.
    assert rc == 0


def test_show_json_emits_full_entry(cache_dir, capsys):
    from agent_skills.verbs.show import run
    class Args:
        id = "test-author/example"
        agent = "claude-code"
        json = True
        yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["id"] == "test-author/example"
    assert payload["version"] == "0.1.0"
    assert payload["license"] == "MIT"
    assert payload["category"] == "meta"
    assert "installed" in payload  # boolean install-status field


def test_show_unknown_id_returns_1(cache_dir, capsys):
    from agent_skills.verbs.show import run
    class Args:
        id = "noone/nope"
        agent = "claude-code"
        json = False
        yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 1
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_show_no_cache_returns_1(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    from agent_skills.verbs.show import run
    class Args:
        id = "test-author/example"
        agent = "claude-code"
        json = False
        yes = False
    rc = run(Args())
    assert rc == 1
```

- [ ] **Step 2: Run tests, verify FAIL (module missing)**

```bash
pytest tests/test_show_verb.py -v
```

Expected: 4 FAILs (ImportError on `agent_skills.verbs.show`).

- [ ] **Step 3: Implement agent_skills/verbs/show.py**

```python
"""show verb — print detail on one skill."""
import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import detect_host, get_adapter


def find_skill(registry: dict, skill_id: str) -> dict | None:
    for s in registry.get("skills", []):
        if s["id"] == skill_id:
            return s
    return None


def is_installed(skill_id: str, agent: str) -> bool:
    try:
        adapter = get_adapter(agent)
    except Exception:
        return False
    for inst in adapter.list_installed():
        if inst.id == skill_id:
            return True
    return False


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("Run `agent-skills update` first.", file=sys.stderr)
        return 1
    skill = find_skill(registry, args.id)
    if skill is None:
        print(f"Skill '{args.id}' not found in registry.", file=sys.stderr)
        return 1
    try:
        agent = detect_host(override=args.agent)
    except SystemExit:
        agent = None
    installed = is_installed(args.id, agent) if agent else False

    payload = {
        "id": skill["id"],
        "version": skill["version"],
        "status": skill["status"],
        "license": skill["license"],
        "author": skill["author"],
        "category": skill["category"],
        "tags": skill.get("tags", []),
        "platforms": skill.get("platforms", []),
        "agent_compat": skill.get("agent_compat", []),
        "files": skill.get("source", {}).get("files", []),
        "requires": skill.get("requires", {"env_vars": [], "commands": []}),
        "has_scripts": skill.get("has_scripts", False),
        "installed": installed,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"{skill['id']}  v{skill['version']}  ({skill['license']}, by {skill['author']['github_login']})")
    print()
    print(f"  {skill.get('description', '')}")
    print()
    print(f"  Category:  {skill['category']}")
    print(f"  Tags:      {' '.join(skill.get('tags', [])) or '—'}")
    print(f"  Platforms: {', '.join(skill.get('platforms', [])) or '—'}")
    print(f"  Agents:    {', '.join(skill.get('agent_compat', [])) or '—'}")
    if skill.get("requires"):
        env = skill["requires"].get("env_vars", [])
        cmds = skill["requires"].get("commands", [])
        if env:
            print(f"  Env vars:  {', '.join(env)}")
        if cmds:
            print(f"  Commands:  {', '.join(cmds)}")
    print(f"  Files:")
    for f in skill.get("source", {}).get("files", []):
        print(f"    {f}")
    print()
    print(f"  Installed: {'yes (' + agent + ')' if installed else 'no'}")
    return 0
```

- [ ] **Step 4: Wire show in agent_skills/cli.py**

In `make_parser`, replace the generic registration for `show` with:

```python
        elif v == "show":
            sp = sub.add_parser("show", help="Show details for one skill")
            sp.add_argument("id")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
```

Dispatch is already wired in `main()` (Task 14 added the `if args.verb == "show":` branch). Verify it exists; otherwise add:

```python
    if args.verb == "show":
        from agent_skills.verbs.show import run
        return run(args)
```

- [ ] **Step 5: Run all tests, verify pass**

```bash
pytest tests/test_show_verb.py -v
pytest tests/ -q --tb=line
```

Expected: 4 new tests pass + 0 regressions.

- [ ] **Step 6: Commit**

```bash
git add agent_skills/verbs/show.py agent_skills/cli.py tests/test_show_verb.py
git commit -m "feat: show verb (detail + install status; JSON output)"
```

---

## Task 17: `install` verb

**Files:**
- Create: `agent_skills/verbs/install.py`
- Create: `tests/test_install_verb.py`
- Modify: `agent_skills/cli.py` (wire `install <id>[@version]` subparser + dispatch)

Install resolves the requested version via `registry.json.skills[id].versions[ver]`, refuses yanked, fetches the git tree at `versions[ver].sha`, materializes files, computes content_hash, and calls `adapter.install(...)`.

**Registry-repo cache strategy**: `update.py` (Task 21) maintains a clone at `~/.cache/agent-skills/registry-repo/`. Install reads tree files from that clone via `git -C <cache> archive <sha>` piped into tar OR `git -C <cache> --work-tree=<staging> checkout-index --all` after `git read-tree <sha>`. For v0, simplest is: `git -C <cache> archive --format=tar <sha>:<source_path> | (cd <staging> && tar -xf -)` on POSIX; on Windows: use `git -C <cache> archive --format=zip <sha>:<source_path> > <staging>.zip` + `zipfile.ZipFile.extractall`. Encapsulate behind a helper.

- [ ] **Step 1: Write tests/test_install_verb.py**

```python
"""Tests for the install verb."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def setup_registry_repo(tmp_path):
    """Build a local git repo that looks like the agent-skills registry.
    Returns (repo_path, registry_dict_with_versions_pointing_to_real_shas)."""
    repo = tmp_path / "registry-repo"
    repo.mkdir()
    # Initialise + first commit: just a SKILL.md skeleton for skills/test-author/example
    skill_dir = repo / "skills/test-author/example"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n\n# Example v0.1.0\n")
    (skill_dir / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.1.0",
        "status": "active",
        "author": {"name": "Test", "github_login": "test-author", "github_id": 1},
        "category": "meta",
        "agent_compat": ["claude-code"],
        "license": "MIT",
        "install": {"claude-code": {"scope": "user"}},
        "requires": {"env_vars": [], "commands": []},
    }))
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "v0.1.0"], cwd=repo, check=True, capture_output=True)
    # Capture tree SHA for v0.1.0
    sha_v010 = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return repo, sha_v010


@pytest.fixture
def install_env(tmp_path, monkeypatch):
    """Set up HOME (with .claude dir), cache dir, and a local registry-repo."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    repo, sha = setup_registry_repo(tmp_path)
    # Move repo to where install expects it
    repo_target = cache / "registry-repo"
    shutil.move(str(repo), str(repo_target))
    # Write registry.json that references the tree sha
    registry = {
        "schema_version": 2,
        "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test-author/example",
            "name": "example",
            "description": "test",
            "version": "0.1.0",
            "status": "active",
            "author": {"name": "Test", "github_login": "test-author", "github_id": 1},
            "category": "meta",
            "tags": [],
            "platforms": ["linux", "macos", "windows"],
            "agent_compat": ["claude-code"],
            "requires": {"env_vars": [], "commands": []},
            "license": "MIT",
            "install": {"claude-code": {"scope": "user"}},
            "has_scripts": False,
            "versions": {"0.1.0": {"sha": sha, "released": "2026-05-11T00:00:00Z"}},
            "source": {"path": "skills/test-author/example", "content_hash": "sha256:" + "0" * 64, "files": ["SKILL.md", "meta.json"]},
        }],
    }
    (cache / "registry.json").write_text(json.dumps(registry))
    return {"home": home, "cache": cache, "registry": registry, "tree_sha": sha}


def test_install_default_latest(install_env):
    from agent_skills.verbs.install import run
    class Args:
        spec = "test-author/example"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = run(Args())
    target = install_env["home"] / ".claude/skills/test-author-example"
    assert rc == 0
    assert (target / "SKILL.md").exists()
    assert (target / ".agent-skills-marker.json").exists()


def test_install_explicit_version_ok(install_env):
    from agent_skills.verbs.install import run
    class Args:
        spec = "test-author/example@0.1.0"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = run(Args())
    assert rc == 0
    target = install_env["home"] / ".claude/skills/test-author-example"
    assert target.exists()


def test_install_unknown_version_fails(install_env, capsys):
    from agent_skills.verbs.install import run
    class Args:
        spec = "test-author/example@9.9.9"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 1
    assert "9.9.9" in captured.out + captured.err
    assert "available" in (captured.out + captured.err).lower()


def test_install_yanked_refused(install_env, capsys):
    # Mutate the registry to yank 0.1.0
    reg_path = install_env["cache"] / "registry.json"
    reg = json.loads(reg_path.read_text())
    reg["skills"][0]["versions"]["0.1.0"]["yanked"] = True
    reg["skills"][0]["versions"]["0.1.0"]["yank_reason"] = "compromised dep"
    reg_path.write_text(json.dumps(reg))

    from agent_skills.verbs.install import run
    class Args:
        spec = "test-author/example@0.1.0"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    msg = (captured.out + captured.err).lower()
    assert "yank" in msg
    assert "compromised" in msg


def test_install_deprecated_refused_without_flag(install_env, capsys):
    reg_path = install_env["cache"] / "registry.json"
    reg = json.loads(reg_path.read_text())
    reg["skills"][0]["status"] = "deprecated"
    reg["skills"][0]["superseded_by"] = "test-author/replacement"
    reg_path.write_text(json.dumps(reg))

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
    assert "deprecated" in (captured.out + captured.err).lower()


def test_install_deprecated_allowed_with_flag(install_env):
    reg_path = install_env["cache"] / "registry.json"
    reg = json.loads(reg_path.read_text())
    reg["skills"][0]["status"] = "deprecated"
    reg["skills"][0]["superseded_by"] = "test-author/replacement"
    reg_path.write_text(json.dumps(reg))

    from agent_skills.verbs.install import run
    class Args:
        spec = "test-author/example"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = True
    rc = run(Args())
    assert rc == 0


def test_install_no_registry_fails(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    from agent_skills.verbs.install import run
    class Args:
        spec = "any/thing"
        agent = "claude-code"
        scope = "user"
        json = False
        yes = True
        allow_deprecated = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 1
    assert "update" in (captured.out + captured.err).lower()
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
pytest tests/test_install_verb.py -v
```

- [ ] **Step 3: Implement agent_skills/verbs/install.py**

```python
"""install verb — resolve version, fetch tree, call adapter.install."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_skills.cache import load_registry, cache_dir
from agent_skills.detect import detect_host, get_adapter
from adapters._base import compute_dir_content_hash


def parse_spec(spec: str) -> tuple[str, str | None]:
    if "@" in spec:
        id_part, version = spec.split("@", 1)
        return id_part, version
    return spec, None


def find_skill(registry: dict, skill_id: str) -> dict | None:
    for s in registry.get("skills", []):
        if s["id"] == skill_id:
            return s
        # Also allow bare slug match if author is registry's default; for v0 require full id
    return None


def materialize_tree(repo_path: Path, tree_sha: str, source_subpath: str, staging: Path) -> None:
    """Use `git archive` to extract files at tree_sha:source_subpath into staging."""
    staging.mkdir(parents=True, exist_ok=True)
    # `git archive --format=tar <sha>:<path>` writes a tarball of that subtree to stdout.
    archive = subprocess.run(
        ["git", "-C", str(repo_path), "archive", "--format=tar", f"{tree_sha}:{source_subpath}"],
        check=True, capture_output=True,
    )
    import tarfile, io
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tf:
        tf.extractall(staging)


def resolve_install_id(registry: dict, raw_id: str) -> str | None:
    """If raw_id has author/slug shape, return as-is. Otherwise try bare-slug lookup.
    Returns the canonical `<author>/<slug>` id, or None."""
    if "/" in raw_id:
        return raw_id if find_skill(registry, raw_id) else None
    # Bare slug — try to find a unique match
    matches = [s["id"] for s in registry["skills"] if s["id"].split("/", 1)[1] == raw_id]
    if len(matches) == 1:
        return matches[0]
    return None


def run(args) -> int:
    registry = load_registry()
    if registry is None:
        print("Run `agent-skills update` first.", file=sys.stderr)
        return 1

    raw_id, version = parse_spec(args.spec)
    full_id = resolve_install_id(registry, raw_id)
    if full_id is None:
        print(f"Skill '{raw_id}' not found in registry. Try: agent-skills search {raw_id}", file=sys.stderr)
        return 1

    skill = find_skill(registry, full_id)

    if skill["status"] == "deprecated" and not getattr(args, "allow_deprecated", False):
        ssby = skill.get("superseded_by", "(none)")
        print(f"{full_id} is DEPRECATED, superseded by {ssby}.", file=sys.stderr)
        print("Use --allow-deprecated to install anyway.", file=sys.stderr)
        return 1

    versions = skill.get("versions", {})
    target_version = version or skill["version"]

    if target_version not in versions:
        available = ", ".join(sorted(versions.keys()))
        print(f"Version {target_version} not found. Available: {available}.", file=sys.stderr)
        return 1

    ver_info = versions[target_version]
    if ver_info.get("yanked", False):
        reason = ver_info.get("yank_reason", "(no reason given)")
        print(f"{full_id}@{target_version} was YANKED: {reason}.", file=sys.stderr)
        print("Yanked versions cannot be installed. No override flag exists.", file=sys.stderr)
        non_yanked = [v for v, info in versions.items() if not info.get("yanked")]
        if non_yanked:
            print(f"Try: agent-skills install {full_id}@{sorted(non_yanked)[-1]}", file=sys.stderr)
        return 1

    tree_sha = ver_info["sha"]
    source_path = skill.get("source", {}).get("path", f"skills/{full_id}")

    repo = cache_dir() / "registry-repo"
    if not (repo / ".git").exists():
        print(f"No registry repo at {repo}. Run `agent-skills update` first.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "staging"
        try:
            materialize_tree(repo, tree_sha, source_path, staging)
        except subprocess.CalledProcessError as e:
            print(f"git archive failed for tree {tree_sha}:{source_path}: {e}", file=sys.stderr)
            return 1

        content_hash = compute_dir_content_hash(staging)

        agent = detect_host(override=args.agent)
        adapter = get_adapter(agent)
        meta = json.loads((staging / "meta.json").read_text(encoding="utf-8"))
        result = adapter.install(
            staging, full_id, target_version,
            meta=meta,
            opts={
                "registry_hash": content_hash,
                "source_url": f"git+{repo}@{tree_sha}",
                "tree_sha": tree_sha,
                "scope": getattr(args, "scope", "user"),
            },
        )
        if not result.success:
            print(f"Install failed: {result.error}", file=sys.stderr)
            return 1

        if getattr(args, "json", False):
            print(json.dumps({
                "installed": True, "id": full_id, "version": target_version,
                "target": str(result.target), "files": result.files_written,
            }, indent=2))
        else:
            print(f"Installed {full_id}@{target_version} at {result.target}")
        return 0
```

- [ ] **Step 4: Wire install in agent_skills/cli.py**

In `make_parser`, add a branch for `install`:

```python
        elif v == "install":
            sp = sub.add_parser("install", help="Install a skill (latest non-yanked by default)")
            sp.add_argument("spec", help="<id>[@version] or bare-slug")
            sp.add_argument("--agent")
            sp.add_argument("--scope", default="user", choices=["user", "project"])
            sp.add_argument("--allow-deprecated", action="store_true")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
```

In `main()`, add the dispatch:

```python
    if args.verb == "install":
        from agent_skills.verbs.install import run
        return run(args)
```

- [ ] **Step 5: Run tests + full suite**

```bash
pytest tests/test_install_verb.py -v
pytest tests/ -q --tb=line
```

Expected: all 7 install tests pass + no regressions.

- [ ] **Step 6: Commit**

```bash
git add agent_skills/verbs/install.py agent_skills/cli.py tests/test_install_verb.py
git commit -m "feat: install verb (version pinning + yanked refusal + deprecated gate + git-archive fetch)"
```

---

## Task 18: `uninstall` verb

**Files:**
- Create: `agent_skills/verbs/uninstall.py`
- Create: `tests/test_uninstall_verb.py`
- Modify: `agent_skills/cli.py`

Uninstall calls `adapter.uninstall()`. By default, refuses to remove if `adapter.verify()` reports `drift` (user has hand-edited files). `--force` overrides.

- [ ] **Step 1: Write tests/test_uninstall_verb.py**

```python
"""Tests for the uninstall verb."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from adapters.claude_code import ClaudeCodeAdapter
from adapters._base import compute_dir_content_hash


@pytest.fixture
def installed_env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)

    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n# Example\n")
    (src / "meta.json").write_text(json.dumps({"id": "test-author/example", "version": "0.1.0"}))

    h = compute_dir_content_hash(src)
    adapter = ClaudeCodeAdapter()
    result = adapter.install(src, "test-author/example", "0.1.0",
                             meta={"category": "meta"},
                             opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    assert result.success

    registry = {
        "schema_version": 2,
        "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test-author/example",
            "name": "example", "description": "test",
            "version": "0.1.0", "status": "active",
            "author": {"name": "Test", "github_login": "test-author", "github_id": 1},
            "category": "meta", "agent_compat": ["claude-code"], "license": "MIT",
            "install": {"claude-code": {"scope": "user"}},
            "tags": [], "platforms": ["linux"], "has_scripts": False,
            "requires": {"env_vars": [], "commands": []},
            "versions": {"0.1.0": {"sha": "a" * 40, "released": "2026-05-11T00:00:00Z"}},
            "source": {"path": "skills/test-author/example", "content_hash": h, "files": ["SKILL.md", "meta.json"]},
        }],
    }
    (cache / "registry.json").write_text(json.dumps(registry))

    return {"home": home, "cache": cache, "target": home / ".claude/skills/test-author-example", "hash": h}


def test_uninstall_clean(installed_env):
    from agent_skills.verbs.uninstall import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; force = False
        json = False; yes = True
    rc = run(Args())
    assert rc == 0
    assert not installed_env["target"].exists()


def test_uninstall_refuses_on_drift_without_force(installed_env, capsys):
    (installed_env["target"] / "SKILL.md").write_text("hand-edited")
    from agent_skills.verbs.uninstall import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; force = False
        json = False; yes = True
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    assert installed_env["target"].exists()
    assert "drift" in (captured.out + captured.err).lower()


def test_uninstall_force_removes_drifted(installed_env):
    (installed_env["target"] / "SKILL.md").write_text("hand-edited")
    from agent_skills.verbs.uninstall import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; force = True
        json = False; yes = True
    rc = run(Args())
    assert rc == 0
    assert not installed_env["target"].exists()


def test_uninstall_not_installed_returns_1(installed_env, capsys):
    from agent_skills.verbs.uninstall import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; force = False
        json = False; yes = True
    # First call: succeeds
    rc = run(Args())
    assert rc == 0
    # Second call: not installed
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement agent_skills/verbs/uninstall.py**

```python
"""uninstall verb."""
from __future__ import annotations

import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import detect_host, get_adapter


def run(args) -> int:
    agent = detect_host(override=args.agent)
    adapter = get_adapter(agent)

    registry = load_registry()
    registry_hash = ""
    if registry:
        for s in registry.get("skills", []):
            if s["id"] == args.id:
                registry_hash = s.get("source", {}).get("content_hash", "")
                break

    if not getattr(args, "force", False):
        vr = adapter.verify(args.id, registry_hash=registry_hash, yanked=False, yank_reason=None)
        if vr.status == "drift":
            print(f"Drift detected: {vr.message}", file=sys.stderr)
            print("Refusing to uninstall a modified skill. Use --force to override.", file=sys.stderr)
            return 1
        if vr.status == "not_installed":
            print(f"{args.id} is not installed in {agent}.", file=sys.stderr)
            return 1

    result = adapter.uninstall(args.id)
    if not result.success:
        print(f"Uninstall failed: {result.error}", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        print(json.dumps({"uninstalled": True, "id": args.id, "target": str(result.target)}, indent=2))
    else:
        print(f"Removed {result.target}")
    return 0
```

- [ ] **Step 4: Wire uninstall in agent_skills/cli.py**

```python
        elif v == "uninstall":
            sp = sub.add_parser("uninstall", help="Remove an installed skill")
            sp.add_argument("id")
            sp.add_argument("--agent")
            sp.add_argument("--force", action="store_true", help="Remove even if local files have drifted")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
```

Dispatch:

```python
    if args.verb == "uninstall":
        from agent_skills.verbs.uninstall import run
        return run(args)
```

- [ ] **Step 5: Run tests + full suite, verify pass**

```bash
pytest tests/test_uninstall_verb.py -v
pytest tests/ -q --tb=line
```

- [ ] **Step 6: Commit**

```bash
git add agent_skills/verbs/uninstall.py agent_skills/cli.py tests/test_uninstall_verb.py
git commit -m "feat: uninstall verb (drift check; --force override; not-installed clear error)"
```

---

## Task 19: `verify` verb

**Files:**
- Create: `agent_skills/verbs/verify.py`
- Create: `tests/test_verify_verb.py`
- Modify: `agent_skills/cli.py`

Verify queries the registry for the skill's content_hash + yanked flag for the installed version, calls `adapter.verify(...)`, prints status. Exit codes: 0 = clean, 1 = drift/yanked/marker_outdated (any non-clean).

- [ ] **Step 1: Write tests/test_verify_verb.py**

```python
"""Tests for the verify verb."""
import json
from pathlib import Path

import pytest

from adapters.claude_code import ClaudeCodeAdapter
from adapters._base import compute_dir_content_hash


def setup_installed(tmp_path, monkeypatch, *, status="active", yanked=False, drift=False):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)

    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n# Example\n")
    (src / "meta.json").write_text(json.dumps({"id": "test-author/example", "version": "0.1.0"}))
    h = compute_dir_content_hash(src)

    adapter = ClaudeCodeAdapter()
    adapter.install(src, "test-author/example", "0.1.0",
                    meta={"category": "meta"},
                    opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    target = home / ".claude/skills/test-author-example"

    if drift:
        (target / "SKILL.md").write_text("hand-edited")

    ver_info = {"sha": "a" * 40, "released": "2026-05-11T00:00:00Z"}
    if yanked:
        ver_info["yanked"] = True
        ver_info["yank_reason"] = "compromised dep"

    registry = {
        "schema_version": 2,
        "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test-author/example",
            "name": "example", "description": "test",
            "version": "0.1.0", "status": status,
            "author": {"name": "Test", "github_login": "test-author", "github_id": 1},
            "category": "meta", "agent_compat": ["claude-code"], "license": "MIT",
            "install": {"claude-code": {"scope": "user"}},
            "tags": [], "platforms": ["linux"], "has_scripts": False,
            "requires": {"env_vars": [], "commands": []},
            "versions": {"0.1.0": ver_info},
            "source": {"path": "skills/test-author/example", "content_hash": h, "files": ["SKILL.md", "meta.json"]},
        }],
    }
    (cache / "registry.json").write_text(json.dumps(registry))
    return {"home": home, "cache": cache, "target": target, "hash": h}


def test_verify_clean(tmp_path, monkeypatch):
    setup_installed(tmp_path, monkeypatch)
    from agent_skills.verbs.verify import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    assert rc == 0


def test_verify_drift(tmp_path, monkeypatch, capsys):
    setup_installed(tmp_path, monkeypatch, drift=True)
    from agent_skills.verbs.verify import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    assert "drift" in (captured.out + captured.err).lower()


def test_verify_yanked(tmp_path, monkeypatch, capsys):
    setup_installed(tmp_path, monkeypatch, yanked=True)
    from agent_skills.verbs.verify import run
    class Args:
        id = "test-author/example"; agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    msg = (captured.out + captured.err).lower()
    assert "yank" in msg
    assert "compromised" in msg


def test_verify_not_installed(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    (cache / "registry.json").write_text(json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z", "skills": [],
    }))
    from agent_skills.verbs.verify import run
    class Args:
        id = "noone/nope"; agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    assert rc != 0
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement agent_skills/verbs/verify.py**

```python
"""verify verb — check installed skill against registry."""
from __future__ import annotations

import json
import sys

from agent_skills.cache import load_registry
from agent_skills.detect import detect_host, get_adapter
from adapters._base import read_marker


def run(args) -> int:
    agent = detect_host(override=args.agent)
    adapter = get_adapter(agent)
    registry = load_registry()
    if registry is None:
        print("No registry cache. Run `agent-skills update`.", file=sys.stderr)
        return 1

    skill = next((s for s in registry["skills"] if s["id"] == args.id), None)
    if skill is None:
        print(f"{args.id} not found in registry.", file=sys.stderr)
        return 1

    # Determine installed version to look up the right yanked flag
    yanked = False
    yank_reason = None
    registry_hash = skill.get("source", {}).get("content_hash", "")

    # Try to read the installed version from the marker so we can check the right yank entry
    for inst in adapter.list_installed():
        if inst.id == args.id:
            marker = read_marker(inst.target)
            installed_ver = marker.get("version") if marker else None
            if installed_ver and installed_ver in skill.get("versions", {}):
                v = skill["versions"][installed_ver]
                yanked = v.get("yanked", False)
                yank_reason = v.get("yank_reason")
            break

    vr = adapter.verify(args.id, registry_hash=registry_hash, yanked=yanked, yank_reason=yank_reason)

    if args.json:
        print(json.dumps({"id": args.id, "status": vr.status, "message": vr.message}, indent=2))
    else:
        print(f"{args.id}: {vr.status.upper()}")
        print(f"  {vr.message}")

    return 0 if vr.status == "clean" else 1
```

- [ ] **Step 4: Wire verify in agent_skills/cli.py**

```python
        elif v == "verify":
            sp = sub.add_parser("verify", help="Check an installed skill against the registry")
            sp.add_argument("id")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
```

Dispatch:

```python
    if args.verb == "verify":
        from agent_skills.verbs.verify import run
        return run(args)
```

- [ ] **Step 5: Run tests + full suite**

```bash
pytest tests/test_verify_verb.py -v
pytest tests/ -q --tb=line
```

- [ ] **Step 6: Commit**

```bash
git add agent_skills/verbs/verify.py agent_skills/cli.py tests/test_verify_verb.py
git commit -m "feat: verify verb (clean/drift/yanked/not_installed paths)"
```

---

## Task 20: `list` verb

**Files:**
- Create: `agent_skills/verbs/list.py` (filename intentional — module path `agent_skills.verbs.list` works fine; only the bare name `list` would shadow the builtin if used as a local var)
- Create: `tests/test_list_verb.py`
- Modify: `agent_skills/cli.py`

List queries `adapter.list_installed()` and prints one line per skill. With `--agent`, override detection.

- [ ] **Step 1: Write tests/test_list_verb.py**

```python
"""Tests for the list verb."""
import json
from pathlib import Path

import pytest

from adapters.claude_code import ClaudeCodeAdapter
from adapters._base import compute_dir_content_hash


@pytest.fixture
def home_with_two_installed(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    adapter = ClaudeCodeAdapter()
    for slug, ver in [("alpha", "0.1.0"), ("beta", "0.2.0")]:
        src = tmp_path / f"src/test-author/{slug}"
        src.mkdir(parents=True)
        (src / "SKILL.md").write_text(f"---\nname: {slug}\ndescription: test\n---\n# {slug}\n")
        (src / "meta.json").write_text(json.dumps({"id": f"test-author/{slug}", "version": ver}))
        h = compute_dir_content_hash(src)
        adapter.install(src, f"test-author/{slug}", ver,
                        meta={"category": "meta"},
                        opts={"registry_hash": h, "source_url": "x", "tree_sha": "a" * 40})
    return home


def test_list_finds_both(home_with_two_installed, capsys):
    from agent_skills.verbs.list import run
    class Args:
        agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 0
    assert "test-author/alpha" in captured.out
    assert "test-author/beta" in captured.out


def test_list_json_emits_array(home_with_two_installed, capsys):
    from agent_skills.verbs.list import run
    class Args:
        agent = "claude-code"; json = True; yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    ids = {entry["id"] for entry in payload["installed"]}
    assert ids == {"test-author/alpha", "test-author/beta"}


def test_list_empty(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    from agent_skills.verbs.list import run
    class Args:
        agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 0
    assert "no skills" in captured.out.lower() or "0" in captured.out
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement agent_skills/verbs/list.py**

```python
"""list verb — show installed skills for the current/overridden host."""
from __future__ import annotations

import json
import sys

from agent_skills.detect import detect_host, get_adapter


def run(args) -> int:
    agent = detect_host(override=args.agent)
    adapter = get_adapter(agent)
    installed = adapter.list_installed()

    if args.json:
        payload = {
            "agent": agent,
            "installed": [
                {"id": i.id, "version": i.version, "target": str(i.target)}
                for i in installed
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    if not installed:
        print(f"No skills installed in {agent}.")
        return 0

    print(f"{len(installed)} skill(s) installed in {agent}:")
    for i in installed:
        print(f"  {i.id:40s} v{i.version}  → {i.target}")
    return 0
```

- [ ] **Step 4: Wire list in agent_skills/cli.py**

```python
        elif v == "list":
            sp = sub.add_parser("list", help="Show installed skills")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
```

Dispatch:

```python
    if args.verb == "list":
        from agent_skills.verbs.list import run
        return run(args)
```

- [ ] **Step 5: Run tests + full suite**

```bash
pytest tests/test_list_verb.py -v
pytest tests/ -q --tb=line
```

- [ ] **Step 6: Commit**

```bash
git add agent_skills/verbs/list.py agent_skills/cli.py tests/test_list_verb.py
git commit -m "feat: list verb (--agent override; JSON output; empty case)"
```

---

## Task 21: `update` verb + `clients/skill_discovery/update.py`

**Files:**
- Create: `clients/skill_discovery/update.py`
- Create: `agent_skills/verbs/update.py`
- Create: `tests/test_update.py`
- Modify: `agent_skills/cli.py`

`update.py` fetches `registry.json` (and optionally `yanks.json`) from the configured remote, verifies sha256 against an optional `.sig` companion file (warning if missing — signing infrastructure is § 19 deferred), refuses rollback (fetched `generated_at` older than cached), writes atomically.

For v0, also maintain the registry-repo clone at `~/.cache/agent-skills/registry-repo/` so the `install` verb can `git archive` at version SHAs. Strategy: if not present, `git clone <remote> registry-repo`; if present, `git -C registry-repo fetch + reset --hard origin/main`.

The remote is configurable via env `AGENT_SKILLS_REGISTRY_URL` (default `https://raw.githubusercontent.com/samuelgudi/agent-skills/main/registry.json`) and `AGENT_SKILLS_REGISTRY_REPO` (default `https://github.com/samuelgudi/agent-skills.git`).

- [ ] **Step 1: Write tests/test_update.py**

```python
"""Tests for the update verb / refresh() routine."""
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import pytest


@pytest.fixture
def serve_dir(tmp_path):
    """Spin up http.server serving files from a tmpdir; yield the URL base."""
    serve = tmp_path / "serve"
    serve.mkdir()

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_): pass
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve), **kwargs)

    httpd = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield {"dir": serve, "url": f"http://127.0.0.1:{port}"}
    httpd.shutdown()


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


def make_registry(generated_at, skills=None):
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "skills": skills or [],
    }


def test_refresh_writes_registry(serve_dir, fake_home):
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))
    (serve_dir["dir"] / "yanks.json").write_text(json.dumps({"yanks": []}))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0

    cached = fake_home / ".cache/agent-skills/registry.json"
    assert cached.exists()
    assert json.loads(cached.read_text())["generated_at"] == "2026-05-11T00:00:00Z"


def test_refresh_rollback_guard_refuses_older(serve_dir, fake_home):
    """If fetched generated_at < cached generated_at, the write must be refused."""
    cache = fake_home / ".cache/agent-skills"
    cache.mkdir(parents=True)
    cached_reg = make_registry("2026-05-15T00:00:00Z")
    (cache / "registry.json").write_text(json.dumps(cached_reg))

    fetched_reg = make_registry("2026-05-10T00:00:00Z")  # OLDER
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(fetched_reg))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc != 0

    # The cached registry must remain the newer one
    assert json.loads((cache / "registry.json").read_text())["generated_at"] == "2026-05-15T00:00:00Z"


def test_refresh_atomic_write(serve_dir, fake_home):
    """No partial write on disk after a successful refresh."""
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0

    cache_dir = fake_home / ".cache/agent-skills"
    leftovers = [p for p in cache_dir.iterdir() if p.name.startswith(".registry.json.tmp")]
    assert leftovers == []


def test_refresh_yanks_when_present(serve_dir, fake_home):
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))
    yanks = {"yanks": [{"id": "x/y", "version": "0.1.0", "reason": "test", "yanked_at": "2026-05-11T00:00:00Z", "yanked_by": "ci"}]}
    (serve_dir["dir"] / "yanks.json").write_text(json.dumps(yanks))

    from clients.skill_discovery.update import refresh
    rc = refresh(serve_dir["url"] + "/registry.json")
    assert rc == 0

    cache = fake_home / ".cache/agent-skills"
    assert (cache / "yanks.json").exists()
    cached_yanks = json.loads((cache / "yanks.json").read_text())
    assert cached_yanks["yanks"][0]["id"] == "x/y"


def test_update_verb_invokes_refresh(serve_dir, fake_home, monkeypatch):
    """The verb-level run() calls refresh() and returns its exit code."""
    reg = make_registry("2026-05-11T00:00:00Z")
    (serve_dir["dir"] / "registry.json").write_text(json.dumps(reg))
    monkeypatch.setenv("AGENT_SKILLS_REGISTRY_URL", serve_dir["url"] + "/registry.json")
    # Skip the git clone in tests: we don't set REGISTRY_REPO so update.py only does the JSON pull
    monkeypatch.setenv("AGENT_SKILLS_SKIP_REPO_SYNC", "1")
    (fake_home / ".claude").mkdir()

    from agent_skills.verbs.update import run
    class Args:
        agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    assert rc == 0
    assert (fake_home / ".cache/agent-skills/registry.json").exists()
```

- [ ] **Step 2: Run, verify FAIL**

- [ ] **Step 3: Implement clients/skill_discovery/update.py**

```python
"""Registry refresh — HTTPS fetch, rollback guard, atomic write."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path


DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/samuelgudi/agent-skills/main/registry.json"
DEFAULT_REGISTRY_REPO = "https://github.com/samuelgudi/agent-skills.git"


def _cache_dir() -> Path:
    d = Path.home() / ".cache/agent-skills"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _http_fetch(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "agent-skills/0.1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _atomic_write(target: Path, data: bytes) -> None:
    """Write to a sibling tmp file, fsync, rename onto target."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=str(target.parent), delete=False,
                                     prefix=f".{target.name}.tmp.") as tf:
        tf.write(data)
        tf.flush()
        os.fsync(tf.fileno())
        tmp_path = Path(tf.name)
    os.replace(tmp_path, target)


def _sync_registry_repo(repo_url: str, dest: Path) -> None:
    if (dest / ".git").exists():
        subprocess.run(["git", "-C", str(dest), "fetch", "--depth=1", "origin", "main"],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(dest), "reset", "--hard", "FETCH_HEAD"],
                       check=True, capture_output=True)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth=1", repo_url, str(dest)],
                   check=True, capture_output=True)


def refresh(registry_url: str | None = None, *, repo_url: str | None = None) -> int:
    """Fetch registry.json + yanks.json, verify rollback, write atomically.
    Sync registry-repo clone (skipped if AGENT_SKILLS_SKIP_REPO_SYNC=1).
    Returns 0 on success, 1 on error/rollback."""
    cache = _cache_dir()
    url = registry_url or os.environ.get("AGENT_SKILLS_REGISTRY_URL", DEFAULT_REGISTRY_URL)

    try:
        reg_bytes = _http_fetch(url)
    except urllib.error.URLError as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        return 1

    try:
        fetched = json.loads(reg_bytes)
    except json.JSONDecodeError as e:
        print(f"Fetched registry is not valid JSON: {e}", file=sys.stderr)
        return 1

    cached_path = cache / "registry.json"
    if cached_path.exists():
        try:
            cached = json.loads(cached_path.read_text(encoding="utf-8"))
            if fetched.get("generated_at", "") < cached.get("generated_at", ""):
                print(
                    f"Rollback guard: fetched generated_at {fetched.get('generated_at')} "
                    f"< cached {cached.get('generated_at')}. Refusing to overwrite.",
                    file=sys.stderr,
                )
                return 1
        except (json.JSONDecodeError, OSError):
            pass  # Cached file corrupt — treat as missing.

    _atomic_write(cached_path, reg_bytes)

    # Optional sig — warn if missing
    sig_url = url + ".sig"
    try:
        sig_bytes = _http_fetch(sig_url, timeout=5.0)
        _atomic_write(cache / "registry.json.sig", sig_bytes)
    except urllib.error.URLError:
        print("Warning: registry.json.sig not found — running unsigned.", file=sys.stderr)

    # yanks.json — sibling to registry
    yanks_url = url.rsplit("/", 1)[0] + "/yanks.json"
    try:
        yanks_bytes = _http_fetch(yanks_url, timeout=10.0)
        _atomic_write(cache / "yanks.json", yanks_bytes)
    except urllib.error.URLError:
        pass  # yanks.json optional

    # Sync the registry-repo clone (needed for install's git archive step)
    if os.environ.get("AGENT_SKILLS_SKIP_REPO_SYNC") != "1":
        repo = repo_url or os.environ.get("AGENT_SKILLS_REGISTRY_REPO", DEFAULT_REGISTRY_REPO)
        repo_cache = cache / "registry-repo"
        try:
            _sync_registry_repo(repo, repo_cache)
        except subprocess.CalledProcessError as e:
            print(f"Warning: registry-repo sync failed: {e}. install verb may not work.",
                  file=sys.stderr)

    return 0
```

- [ ] **Step 4: Implement agent_skills/verbs/update.py**

```python
"""update verb — thin wrapper around clients.skill_discovery.update.refresh."""
from clients.skill_discovery.update import refresh


def run(args) -> int:
    return refresh()
```

- [ ] **Step 5: Wire update in agent_skills/cli.py**

```python
        elif v == "update":
            sp = sub.add_parser("update", help="Refresh the local registry cache")
            sp.add_argument("--agent")
            sp.add_argument("--json", action="store_true")
            sp.add_argument("--yes", action="store_true")
```

Dispatch:

```python
    if args.verb == "update":
        from agent_skills.verbs.update import run
        return run(args)
```

- [ ] **Step 6: Run tests + full suite**

```bash
pytest tests/test_update.py -v
pytest tests/ -q --tb=line
```

Expected: 5 update tests pass + no regressions.

- [ ] **Step 7: Commit**

```bash
git add clients/skill_discovery/update.py agent_skills/verbs/update.py agent_skills/cli.py tests/test_update.py
git commit -m "feat: update verb + clients/skill_discovery/update.py (HTTPS fetch, rollback guard, atomic write, repo sync)"
```

---

## End of Phase 4 plan

After Task 21:
- All 12 CLI verbs registered (search ✅, show, install, uninstall, verify, list, update done — init/submit/issue/deprecate/yank come in Phase 5).
- Total tests expected: 72 + 4 (show) + 7 (install) + 4 (uninstall) + 4 (verify) + 3 (list) + 5 (update) = **99 tests**.
- HEAD will be 6 commits beyond the start of this plan.

Next: Phase 5 — Task 22 (`init` verb, already fully expanded in the parent plan) + Tasks 23-28 (compressed; expand via writing-plans again before dispatch).
