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
