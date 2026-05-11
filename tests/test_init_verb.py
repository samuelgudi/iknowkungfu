"""Tests for the init verb."""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fake_gh_user():
    """Return values matching the fake_gh fixture response."""
    return ("test-author", 12345678)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_init_scaffolds_meta_from_skill_md(tmp_path, fake_gh, monkeypatch):
    skill = tmp_path / "homelab-docs"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: homelab-docs\ndescription: example\n---\n# H\n")
    # Inputs: id, version, status, license, category=3 (ops), tags, platforms, agents=1 (claude-code), commands, env_vars
    inputs = "\n".join(["", "", "", "", "3", "homelab,docs", "linux,windows", "1", "git,ssh", ""]) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(inputs))
    # Bypass subprocess/gh on Windows by patching _fetch_gh_user directly
    import agent_skills.verbs.init as init_mod
    monkeypatch.setattr(init_mod, "_fetch_gh_user", _fake_gh_user)

    from agent_skills.verbs.init import run
    class Args:
        target = str(skill)
        yes = False
    rc = run(Args())
    assert rc == 0, "init should succeed"
    meta_path = skill / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["id"] == "test-author/homelab-docs"
    assert meta["category"] == "ops"
    assert meta["author"]["github_login"] == "test-author"
    assert meta["author"]["github_id"] == 12345678
    assert "git" in meta["requires"]["commands"]
    assert "ssh" in meta["requires"]["commands"]
    assert meta["tags"] == ["homelab", "docs"]
    assert meta["platforms"] == ["linux", "windows"]
    assert meta["agent_compat"] == ["claude-code"]
    assert meta["license"] == "MIT"
    assert meta["version"] == "0.1.0"
    assert meta["status"] == "active"
    # Reserved fields initialized empty
    assert meta["composes"] == []
    assert meta["extends"] is None
    assert meta["supersedes"] == []
    assert meta["superseded_by"] is None


def test_init_renames_lowercase_skill_md(tmp_path, fake_gh, monkeypatch):
    skill = tmp_path / "test-skill"
    skill.mkdir()
    (skill / "skill.md").write_text("---\nname: test-skill\ndescription: lowercase\n---\n# Body\n")
    inputs = "\n".join(["", "", "", "", "7", "", "", "1", "", ""]) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(inputs))

    import agent_skills.verbs.init as init_mod
    monkeypatch.setattr(init_mod, "_fetch_gh_user", _fake_gh_user)

    from agent_skills.verbs.init import run
    class Args:
        target = str(skill)
        yes = False
    rc = run(Args())
    assert rc == 0
    assert (skill / "SKILL.md").exists()
    # On Windows (NTFS) the rename is case-insensitive; verify via os.listdir
    actual_names = os.listdir(skill)
    assert "SKILL.md" in actual_names
    assert "skill.md" not in actual_names


def test_init_fails_missing_skill_md(tmp_path, fake_gh, capsys):
    skill = tmp_path / "empty"
    skill.mkdir()
    from agent_skills.verbs.init import run
    class Args:
        target = str(skill)
        yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    assert "SKILL.md" in (captured.out + captured.err)


@pytest.mark.skipif(
    os.name == "nt",
    reason="NTFS is case-insensitive — cannot create distinct SKILL.md and skill.md simultaneously",
)
def test_init_fails_both_uppercase_and_lowercase_skill_md(tmp_path, fake_gh, capsys):
    skill = tmp_path / "conflicted"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: x\ndescription: x\n---\n")
    (skill / "skill.md").write_text("---\nname: x\ndescription: x\n---\n")
    from agent_skills.verbs.init import run
    class Args:
        target = str(skill)
        yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    assert "both" in (captured.out + captured.err).lower() or "conflict" in (captured.out + captured.err).lower()
