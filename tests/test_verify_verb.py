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
    cache = home / ".cache/iknowkungfu"
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
    cache = home / ".cache/iknowkungfu"
    cache.mkdir(parents=True)
    (cache / "registry.json").write_text(json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z", "skills": [],
    }))
    from agent_skills.verbs.verify import run
    class Args:
        id = "noone/nope"; agent = "claude-code"; json = False; yes = False
    rc = run(Args())
    assert rc != 0


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


# ─── Friction #4 (v0.1.7 field test): verify resolves host w/o --agent ──────

def test_verify_without_agent_multihost(tmp_path, monkeypatch, capsys):
    """With multiple hosts detected and no `--agent`, verify must check where
    the skill is actually installed — not exit 1 with 'Multiple agent hosts
    detected'. Friction #4 from the v0.1.7 Hermes Agent field test."""
    info = setup_installed(tmp_path, monkeypatch)
    # A second detectable host with nothing installed — this is what previously
    # triggered the "pick one with --agent" exit-1 error.
    (info["home"] / ".hermes").mkdir()

    from agent_skills.verbs.verify import run

    class Args:
        id = "test-author/example"; agent = None; json = False; yes = False

    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 0, captured.out + captured.err
    assert "CLEAN" in captured.out.upper()
