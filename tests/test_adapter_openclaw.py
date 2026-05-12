"""Tests for the OpenClaw adapter."""
import json
from pathlib import Path

import pytest
import yaml

from adapters.openclaw import OpenClawAdapter
from adapters._base import compute_dir_content_hash, MARKER_FILENAME


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def src_skill(tmp_path):
    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    # NOTE: source SKILL.md does NOT have `version` in frontmatter — that is the
    # OpenClaw-specific field the adapter must inject at install time.
    (src / "SKILL.md").write_text(
        "---\nname: example\ndescription: Use this fixture skill in openclaw adapter tests.\n---\n\n# Example\n\nBody.\n"
    )
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.3.0",
        "author": {"name": "Test", "github_login": "test", "github_id": 1},
        "category": "dev",
        "license": "MIT",
        "agent_compat": ["openclaw"],
        "requires": {"env_vars": [], "commands": []},
    }))
    return src


def test_detect_finds_openclaw_dir(home):
    a = OpenClawAdapter()
    assert a.detect() is False
    (home / ".openclaw").mkdir()
    assert a.detect() is True


def test_target_dir_user_scope(home):
    a = OpenClawAdapter()
    t = a.target_dir("test-author/example", category="dev")
    rel = str(t.relative_to(home)).replace("\\", "/")
    assert rel == ".openclaw/skills/test-author-example"


def test_target_dir_project_scope_under_workspace(home, monkeypatch, tmp_path):
    """OpenClaw's workspace path is <workspace>/skills/, NOT <workspace>/.openclaw/skills/."""
    proj = tmp_path / "proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    a = OpenClawAdapter()
    t = a.target_dir("test-author/example", category="dev", scope="project")
    rel = str(t.relative_to(proj)).replace("\\", "/")
    assert rel == "skills/test-author-example"


def test_install_injects_version_into_frontmatter(home, src_skill):
    """OpenClaw requires `version` in SKILL.md frontmatter. The source skill
    does NOT have it (version lives in meta.json) — the adapter must inject
    it during install or OpenClaw will reject the skill at load."""
    (home / ".openclaw").mkdir()
    a = OpenClawAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    res = a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
                    opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    assert res.success, res.error
    target = home / ".openclaw/skills/test-author-example"
    fm = yaml.safe_load((target / "SKILL.md").read_text().split("---\n", 2)[1])
    assert fm["name"] == "test-author-example"
    assert fm["version"] == "0.3.0", "OpenClaw requires version in frontmatter"
    assert "fixture skill" in fm["description"]


def test_install_writes_marker(home, src_skill):
    (home / ".openclaw").mkdir()
    a = OpenClawAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    marker = json.loads((home / ".openclaw/skills/test-author-example" / MARKER_FILENAME).read_text())
    assert marker["id"] == "test-author/example"
    assert marker["registry_content_hash"] == h


def test_install_refuses_unmanaged(home, src_skill):
    (home / ".openclaw").mkdir()
    target = home / ".openclaw/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: pre\ndescription: u\nversion: 0.0.1\n---\n")
    a = OpenClawAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    res = a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={})
    assert not res.success
    assert "refuse to overwrite" in res.error


def test_uninstall_removes(home, src_skill):
    (home / ".openclaw").mkdir()
    a = OpenClawAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": "x"})
    res = a.uninstall("test-author/example")
    assert res.success
    assert not (home / ".openclaw/skills/test-author-example").exists()


def test_uninstall_refuses_unmanaged(home):
    (home / ".openclaw").mkdir()
    target = home / ".openclaw/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: x\ndescription: y\nversion: 0.0.1\n---\n")
    res = OpenClawAdapter().uninstall("test-author/example")
    assert not res.success
    assert "no marker" in res.error


def test_list_installed(home, src_skill):
    (home / ".openclaw").mkdir()
    a = OpenClawAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": "x"})
    user_authored = home / ".openclaw/skills/manual"
    user_authored.mkdir(parents=True)
    (user_authored / "SKILL.md").write_text("---\nname: manual\ndescription: y\nversion: 0.0.1\n---\n")
    assert [i.id for i in a.list_installed()] == ["test-author/example"]


def test_verify_clean(home, src_skill):
    (home / ".openclaw").mkdir()
    a = OpenClawAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash=h, yanked=False, yank_reason=None)
    assert res.status == "clean"


def test_verify_marker_outdated_on_hash_mismatch(home, src_skill):
    (home / ".openclaw").mkdir()
    a = OpenClawAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash="sha256:deadbeef", yanked=False, yank_reason=None)
    assert res.status == "marker_outdated"


def test_verify_yanked_takes_precedence(home, src_skill):
    (home / ".openclaw").mkdir()
    a = OpenClawAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash=h, yanked=True, yank_reason="cve")
    assert res.status == "yanked"
    assert "cve" in res.message
