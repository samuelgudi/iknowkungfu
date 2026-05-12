"""Tests for the Codex adapter."""
import json
from pathlib import Path

import pytest
import yaml

from adapters.codex import CodexAdapter
from adapters._base import compute_dir_content_hash, MARKER_FILENAME


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def src_skill(tmp_path):
    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text(
        "---\n"
        "name: example\n"
        "description: Use this skill when running the Codex adapter test fixture.\n"
        "---\n\n# Example\n\nBody text.\n"
    )
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.3.0",
        "author": {"name": "Test", "github_login": "test", "github_id": 1},
        "category": "dev",
        "license": "MIT",
        "platforms": ["linux"],
        "tags": ["test", "fixture"],
        "requires": {"env_vars": [], "commands": []},
    }))
    return src


def test_detect_finds_codex_config_dir(home):
    a = CodexAdapter()
    assert a.detect() is False
    (home / ".codex").mkdir()
    assert a.detect() is True


def test_target_dir_user_scope_under_agents_skills(home):
    a = CodexAdapter()
    t = a.target_dir("test-author/example", category="dev")
    # Canonical: ~/.agents/skills/<author>-<slug>
    rel = str(t.relative_to(home)).replace("\\", "/")
    assert rel == ".agents/skills/test-author-example"


def test_target_dir_project_scope_under_cwd(home, monkeypatch, tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    a = CodexAdapter()
    t = a.target_dir("test-author/example", category="dev", scope="project")
    rel = str(t.relative_to(proj)).replace("\\", "/")
    assert rel == ".agents/skills/test-author-example"


def test_install_rewrites_name_field_to_flat_slug(home, src_skill):
    (home / ".codex").mkdir()
    a = CodexAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    result = a.install(
        src_skill, "test-author/example", "0.3.0",
        meta=meta,
        opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"},
    )
    assert result.success, result.error
    target = home / ".agents/skills/test-author-example"
    assert target.exists()
    # SKILL.md frontmatter's `name` has been rewritten to the flat slug.
    installed = (target / "SKILL.md").read_text()
    fm_text = installed.split("---\n", 2)[1]
    fm = yaml.safe_load(fm_text)
    assert fm["name"] == "test-author-example"
    # Description preserved verbatim.
    assert fm["description"] == "Use this skill when running the Codex adapter test fixture."
    # Body preserved.
    assert "# Example" in installed and "Body text." in installed


def test_install_writes_marker(home, src_skill):
    (home / ".codex").mkdir()
    a = CodexAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    marker_path = home / ".agents/skills/test-author-example" / MARKER_FILENAME
    marker = json.loads(marker_path.read_text())
    assert marker["id"] == "test-author/example"
    assert marker["version"] == "0.3.0"
    assert marker["registry_content_hash"] == h


def test_install_refuses_to_overwrite_unmanaged_dir(home, src_skill):
    (home / ".codex").mkdir()
    target = home / ".agents/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: pre-existing\ndescription: user\n---\n")
    a = CodexAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    result = a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={})
    assert not result.success
    assert "refuse to overwrite" in result.error


def test_uninstall_removes_managed_skill(home, src_skill):
    (home / ".codex").mkdir()
    a = CodexAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": "x"})
    res = a.uninstall("test-author/example")
    assert res.success
    assert not (home / ".agents/skills/test-author-example").exists()


def test_uninstall_refuses_unmanaged(home):
    (home / ".codex").mkdir()
    target = home / ".agents/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: foo\ndescription: bar\n---\n")
    a = CodexAdapter()
    res = a.uninstall("test-author/example")
    assert not res.success
    assert "no marker" in res.error


def test_list_installed_only_returns_marker_dirs(home, src_skill):
    (home / ".codex").mkdir()
    a = CodexAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": "x"})
    # User-authored skill (no marker) must NOT appear in the list.
    user_authored = home / ".agents/skills/manual"
    user_authored.mkdir(parents=True)
    (user_authored / "SKILL.md").write_text("---\nname: manual\ndescription: hand-written\n---\n")
    installed = a.list_installed()
    ids = [i.id for i in installed]
    assert ids == ["test-author/example"]


def test_verify_uses_marker_hash_not_disk_hash(home, src_skill):
    """Codex rewrites SKILL.md, so disk hash != registry hash. verify must
    compare marker's recorded registry_content_hash, not a fresh disk hash."""
    (home / ".codex").mkdir()
    a = CodexAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash=h, yanked=False, yank_reason=None)
    assert res.status == "clean", res.message


def test_verify_marker_outdated_when_registry_hash_changes(home, src_skill):
    (home / ".codex").mkdir()
    a = CodexAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash="sha256:deadbeef", yanked=False, yank_reason=None)
    assert res.status == "marker_outdated"


def test_verify_yanked_takes_precedence(home, src_skill):
    (home / ".codex").mkdir()
    a = CodexAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash=h, yanked=True, yank_reason="security")
    assert res.status == "yanked"
    assert "security" in res.message
