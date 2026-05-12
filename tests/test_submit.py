"""Tests for submit pipeline. Uses fake_gh fixture + a real git repo in tmp_path."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def test_repo(tmp_path):
    """Copy the agent-skills repo (minus .git) into tmp_path; git init; wire up a bare
    origin so submit can actually push (mirrors the real contribution flow)."""
    repo = tmp_path / "registry-repo"
    shutil.copytree(REPO_ROOT, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", ".pytest_cache"))
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    # Bare origin so `git push` inside submit_skill has somewhere to go.
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", str(origin)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(origin)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "main"], check=True, capture_output=True)
    return repo


@pytest.fixture
def clean_skill(tmp_path):
    """A skill dir that passes validate + has nothing to sanitize."""
    src = tmp_path / "submitted-skill"
    src.mkdir()
    (src / "SKILL.md").write_text(
        "---\nname: example\ndescription: clean test fixture skill.\n---\n\n# Example\n\nBody.\n"
    )
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.1.0",
        "status": "active",
        "author": {"name": "Test Author", "github_login": "test-author", "github_id": 1},
        "category": "meta",
        "tags": ["test"],
        "platforms": ["linux"],
        "agent_compat": ["claude-code"],
        "requires": {"env_vars": [], "commands": []},
        "license": "MIT",
        "install": {"claude-code": {"scope": "user"}},
        "composes": [],
        "extends": None,
        "supersedes": [],
        "superseded_by": None,
    }))
    return src


def test_submit_creates_branch_and_files(test_repo, clean_skill, fake_gh):
    from clients.skill_contribution.submit import submit_skill
    result = submit_skill(clean_skill, test_repo, yes=True)
    assert result.success, f"error={result.error}"
    submitted = test_repo / "submitted" / "test-author-example"
    assert (submitted / "test-author/example/SKILL.md").exists()
    assert (submitted / "REVIEW.md").exists()
    assert (submitted / "SANITIZATION.diff").exists()
    assert (submitted / "scan_results.json").exists()
    # Branch should exist
    branches = subprocess.run(
        ["git", "-C", str(test_repo), "branch"], capture_output=True, text=True
    ).stdout
    assert "contrib/test-author-example" in branches
    # gh shim should have been called — result.success True proves it (shim returns exit 0)
    # The log redirect may silently fail on Windows when %* contains newlines/special chars,
    # so we verify via result.pr_url instead of the log file.
    assert result.pr_url is not None
    # If the log was written (Unix or simple invocations), also check it
    if fake_gh["log"].exists():
        log = fake_gh["log"].read_text(encoding="utf-8")
        assert "pr create" in log


def test_submit_aborts_when_validate_fails(test_repo, tmp_path, fake_gh):
    """Use a fixture missing license to fail validate."""
    src = tmp_path / "bad-skill"
    src.mkdir()
    (src / "SKILL.md").write_text("---\nname: bad\ndescription: invalid.\n---\n\n# bad\n")
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/bad",
        "version": "0.1.0",
        "status": "active",
        "author": {"name": "T", "github_login": "test-author", "github_id": 1},
        "category": "meta",
        "agent_compat": ["claude-code"],
        # NO license — validate should fail
        "install": {"claude-code": {}},
    }))
    from clients.skill_contribution.submit import submit_skill
    result = submit_skill(src, test_repo, yes=True)
    assert not result.success
    assert "validate" in (result.error or "").lower() or "license" in (result.error or "").lower()


def test_submit_aborts_when_meta_missing(test_repo, tmp_path, fake_gh):
    src = tmp_path / "no-meta"
    src.mkdir()
    (src / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n# x\n")
    from clients.skill_contribution.submit import submit_skill
    result = submit_skill(src, test_repo, yes=True)
    assert not result.success
    assert "meta.json" in (result.error or "")


def test_submit_renames_lowercase_skill_md(test_repo, tmp_path, fake_gh):
    src = tmp_path / "lowercase-skill"
    src.mkdir()
    (src / "skill.md").write_text(
        "---\nname: lower\ndescription: test.\n---\n# x\n"
    )
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/lower",
        "version": "0.1.0",
        "status": "active",
        "author": {"name": "T", "github_login": "test-author", "github_id": 1},
        "category": "meta",
        "agent_compat": ["claude-code"],
        "license": "MIT",
        "install": {"claude-code": {}},
        "requires": {"env_vars": [], "commands": []},
    }))
    from clients.skill_contribution.submit import submit_skill
    result = submit_skill(src, test_repo, yes=True)
    assert result.success, f"error={result.error}"
    # On case-insensitive filesystems (Windows), Path.exists() treats both casings as the same.
    # Use os.listdir to check the actual on-disk filename casing.
    import os as _os
    disk_names = _os.listdir(src)
    assert "SKILL.md" in disk_names, f"SKILL.md not in {disk_names}"
    assert "skill.md" not in disk_names, f"skill.md still in {disk_names} (rename did not change case)"


def test_submit_review_md_template_populated(test_repo, clean_skill, fake_gh):
    from clients.skill_contribution.submit import submit_skill
    result = submit_skill(clean_skill, test_repo, yes=True)
    assert result.success
    review = (test_repo / "submitted/test-author-example/REVIEW.md").read_text(encoding="utf-8")
    assert "test-author/example" in review
    assert "0.1.0" in review


def test_submit_pushes_branch_to_origin(test_repo, clean_skill, fake_gh):
    """Regression lock: submit must push the contrib branch to origin before calling
    `gh pr create`. Without the push, `gh pr create` aborts with
    'you must first push the current branch to a remote' on real (non-shimmed) gh."""
    from clients.skill_contribution.submit import submit_skill
    result = submit_skill(clean_skill, test_repo, yes=True)
    assert result.success, f"error={result.error}"
    # The bare origin lives alongside the working repo in tmp_path (see fixture).
    origin = test_repo.parent / "origin.git"
    branches = subprocess.run(
        ["git", "-C", str(origin), "branch"], capture_output=True, text=True, check=True
    ).stdout
    assert "contrib/test-author-example" in branches, (
        f"contrib branch not pushed to origin. origin branches:\n{branches}"
    )
