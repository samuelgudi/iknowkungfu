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
