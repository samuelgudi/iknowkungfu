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


def test_init_fails_both_uppercase_and_lowercase_skill_md(tmp_path, fake_gh, capsys):
    """Both SKILL.md and skill.md present is a hard fail. Only meaningful on
    case-sensitive filesystems (default Linux). NTFS and default APFS/HFS+ are
    case-insensitive, so the two writes collapse to one file — we detect that
    at runtime and skip rather than guess via os.name (macOS isn't NT but is
    also case-insensitive by default)."""
    skill = tmp_path / "conflicted"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: x\ndescription: x\n---\n")
    (skill / "skill.md").write_text("---\nname: x\ndescription: x\n---\n")
    if len(os.listdir(skill)) < 2:
        pytest.skip("case-insensitive filesystem — cannot stage both SKILL.md and skill.md")
    from agent_skills.verbs.init import run
    class Args:
        target = str(skill)
        yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc != 0
    assert "both" in (captured.out + captured.err).lower() or "conflict" in (captured.out + captured.err).lower()


def test_init_env_var_scan_ignores_prose_acronyms(tmp_path, fake_gh, monkeypatch):
    """Acronyms in prose (SSH, LLM, NFS, README, CLAUDE) must not be flagged
    as env vars. Finding 8a of the 2026-05-12 walkthrough — Samuel's
    homelab-docs SKILL.md generated 5 false positives ('README', 'CLAUDE',
    'LLM', 'NFS', 'SSH'), all of which were bare prose acronyms."""
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
    meta = json.loads((skill / "meta.json").read_text(encoding="utf-8"))
    # None of these prose acronyms is a real env var
    assert meta["requires"]["env_vars"] == [], (
        f"expected empty env_vars, got {meta['requires']['env_vars']}"
    )


def test_init_env_var_scan_detects_shell_style(tmp_path, fake_gh, monkeypatch):
    """Real env var uses (shell $VAR / ${VAR}, os.environ, os.getenv) ARE
    detected. Counterpoint to test_init_env_var_scan_ignores_prose_acronyms."""
    skill = tmp_path / "real-env"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: x\ndescription: y\n---\n\n"
        "Set $SPOTIFY_CLIENT_ID and ${SPOTIFY_CLIENT_SECRET}.\n"
        "Python: os.environ.get('GITHUB_TOKEN') or os.getenv('IKNOWKUNGFU_DEFAULT_AGENT').\n"
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
    meta = json.loads((skill / "meta.json").read_text(encoding="utf-8"))
    detected = set(meta["requires"]["env_vars"])
    assert "SPOTIFY_CLIENT_ID" in detected
    assert "SPOTIFY_CLIENT_SECRET" in detected
    assert "GITHUB_TOKEN" in detected
    assert "IKNOWKUNGFU_DEFAULT_AGENT" in detected


def test_init_defaults_id_to_frontmatter_name_not_dir(tmp_path, fake_gh, monkeypatch):
    """When the local dir name differs from the SKILL.md frontmatter `name`,
    init defaults the id slug to the FRONTMATTER name (the source of truth),
    not the dir basename. Finding 8b of the 2026-05-12 walkthrough — Samuel
    tested in /tmp/homelab-docs-test/ with frontmatter name: homelab-docs,
    and the wrong default broke validate.py's cross-file consistency check."""
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
    meta = json.loads((skill / "meta.json").read_text(encoding="utf-8"))
    # Slug part of id MUST come from frontmatter, not dir
    assert meta["id"] == "test-author/homelab-docs", (
        f"expected id 'test-author/homelab-docs', got {meta['id']!r}"
    )
