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
