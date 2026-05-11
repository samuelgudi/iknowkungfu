"""Tests for the deprecate verb."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def repo_with_skill(tmp_path):
    """A fake registry repo with one active skill under skills/."""
    repo = tmp_path / "repo"
    repo.mkdir()
    # Minimal scripts/ + registry pieces — only need git to work
    (repo / "README.md").write_text("# test\n")
    skill = repo / "skills/test-author/example"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: example\ndescription: test.\n---\n\n# x\n")
    (skill / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.1.0",
        "status": "active",
        "author": {"name": "T", "github_login": "test-author", "github_id": 1},
        "category": "meta",
        "agent_compat": ["claude-code"],
        "license": "MIT",
        "install": {"claude-code": {}},
        "superseded_by": None,
    }, indent=2))
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_deprecate_moves_and_marks(repo_with_skill, fake_gh):
    from agent_skills.verbs.deprecate import deprecate
    ok, info = deprecate(repo_with_skill, "test-author/example", "test-author/replacement")
    assert ok, f"error: {info}"
    # Skill moved
    assert not (repo_with_skill / "skills/test-author/example").exists()
    assert (repo_with_skill / "archive/test-author/example").exists()
    # meta.json updated
    meta = json.loads((repo_with_skill / "archive/test-author/example/meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "deprecated"
    assert meta["superseded_by"] == "test-author/replacement"
    # Branch exists
    branches = subprocess.run(["git", "-C", str(repo_with_skill), "branch"], capture_output=True, text=True).stdout
    assert "deprecate/test-author-example" in branches


def test_deprecate_unknown_skill_fails(repo_with_skill, fake_gh):
    from agent_skills.verbs.deprecate import deprecate
    ok, info = deprecate(repo_with_skill, "noone/nope", "x/y")
    assert not ok
    assert "not found" in (info or "")


def test_deprecate_rejects_bad_id_format(repo_with_skill, fake_gh):
    from agent_skills.verbs.deprecate import deprecate
    ok, info = deprecate(repo_with_skill, "bare-slug", "test-author/replacement")
    assert not ok
    assert "invalid" in (info or "").lower()
