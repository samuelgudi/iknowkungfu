"""Tests for the yank verb."""
import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_with_registry(tmp_path):
    """A fake registry repo with one skill having versions 0.1.0 + 0.2.0."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# test\n")
    registry = {
        "schema_version": 2,
        "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test-author/example",
            "name": "example", "description": "test",
            "version": "0.2.0", "status": "active",
            "author": {"name": "T", "github_login": "test-author", "github_id": 1},
            "category": "meta", "tags": [], "platforms": ["linux"],
            "agent_compat": ["claude-code"],
            "requires": {"env_vars": [], "commands": []},
            "license": "MIT",
            "install": {"claude-code": {"scope": "user"}},
            "has_scripts": False,
            "versions": {
                "0.1.0": {"sha": "a" * 40, "released": "2026-05-01T00:00:00Z"},
                "0.2.0": {"sha": "b" * 40, "released": "2026-05-11T00:00:00Z"},
            },
            "source": {"path": "skills/test-author/example", "content_hash": "sha256:" + "0" * 64, "files": ["SKILL.md", "meta.json"]},
        }],
    }
    (repo / "registry.json").write_text(json.dumps(registry, indent=2))
    (repo / "yanks.json").write_text(json.dumps({"yanks": []}, indent=2))
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_yank_appends_entry_and_branches(repo_with_registry, fake_gh):
    from agent_skills.verbs.yank import yank
    ok, info = yank(repo_with_registry, "test-author/example@0.1.0", "Compromised upstream dep")
    assert ok, f"error: {info}"
    yanks = json.loads((repo_with_registry / "yanks.json").read_text(encoding="utf-8"))
    assert len(yanks["yanks"]) == 1
    entry = yanks["yanks"][0]
    assert entry["id"] == "test-author/example"
    assert entry["version"] == "0.1.0"
    assert "Compromised" in entry["reason"]
    assert "yanked_at" in entry
    branches = subprocess.run(["git", "-C", str(repo_with_registry), "branch"], capture_output=True, text=True).stdout
    assert "yank/test-author-example-0.1.0" in branches


def test_yank_unknown_skill(repo_with_registry, fake_gh):
    from agent_skills.verbs.yank import yank
    ok, info = yank(repo_with_registry, "noone/nope@0.1.0", "test")
    assert not ok
    assert "not found" in (info or "")


def test_yank_unknown_version(repo_with_registry, fake_gh):
    from agent_skills.verbs.yank import yank
    ok, info = yank(repo_with_registry, "test-author/example@9.9.9", "test")
    assert not ok
    assert "9.9.9" in (info or "")
    assert "available" in (info or "").lower()


def test_yank_empty_reason(repo_with_registry, fake_gh):
    from agent_skills.verbs.yank import yank
    ok, info = yank(repo_with_registry, "test-author/example@0.1.0", "   ")
    assert not ok
    assert "reason" in (info or "").lower()


def test_yank_bad_spec_format(repo_with_registry, fake_gh):
    from agent_skills.verbs.yank import yank
    ok, info = yank(repo_with_registry, "test-author/example", "no version")
    assert not ok
    assert "spec" in (info or "").lower() or "version" in (info or "").lower()


def test_yank_duplicate_refused(repo_with_registry, fake_gh):
    from agent_skills.verbs.yank import yank
    ok, _ = yank(repo_with_registry, "test-author/example@0.1.0", "first reason")
    assert ok
    # Need to checkout main to avoid being stuck on the yank branch (which won't have the next entry)
    subprocess.run(["git", "-C", str(repo_with_registry), "checkout", "main"], check=True, capture_output=True)
    ok2, info2 = yank(repo_with_registry, "test-author/example@0.1.0", "second reason")
    assert not ok2
    assert "already" in (info2 or "").lower()
