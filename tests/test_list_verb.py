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


def test_list_all_empty_consolidated(tmp_path, monkeypatch, capsys):
    """When no detected host has any installed skill, `kfu list` prints one
    consolidated line — not a repeated 'No skills installed' block per host.
    Friction #6 from the v0.1.7 Hermes Agent field test."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    (home / ".hermes").mkdir()  # two hosts detected, both empty
    monkeypatch.setattr(Path, "home", lambda: home)
    from agent_skills.verbs.list import run

    class Args:
        agent = None; json = False; yes = False

    rc = run(Args())
    out = capsys.readouterr().out
    assert rc == 0
    # One consolidated line — not one "No skills installed" block per host.
    assert out.lower().count("no skills installed") == 1
    assert "claude-code" in out and "hermes" in out
