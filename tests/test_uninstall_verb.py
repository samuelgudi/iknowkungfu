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
    cache = home / ".cache/iknowkungfu"
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
