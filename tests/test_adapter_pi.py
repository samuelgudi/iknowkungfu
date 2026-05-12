"""Tests for the Pi coding agent adapter."""
import json
from pathlib import Path

import pytest
import yaml

from adapters.pi import PiAdapter, _pi_config_home
from adapters._base import compute_dir_content_hash, MARKER_FILENAME


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
    return tmp_path


@pytest.fixture
def src_skill(tmp_path):
    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text(
        "---\nname: example\ndescription: Use this fixture skill in pi adapter tests.\n---\n\n# Example\n\nBody.\n"
    )
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.3.0",
        "author": {"name": "Test", "github_login": "test", "github_id": 1},
        "category": "dev",
        "license": "MIT",
        "agent_compat": ["pi"],
        "requires": {"env_vars": [], "commands": []},
    }))
    return src


def test_detect_finds_default_config_dir(home):
    a = PiAdapter()
    assert a.detect() is False
    (home / ".pi/agent").mkdir(parents=True)
    assert a.detect() is True


def test_detect_honours_pi_coding_agent_dir_env(monkeypatch, tmp_path):
    # Point HOME elsewhere so the default ~/.pi/agent does NOT exist.
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    custom = tmp_path / "custom-pi-home"
    custom.mkdir()
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(custom))
    a = PiAdapter()
    assert a.detect() is True
    assert _pi_config_home() == custom


def test_target_dir_user_scope(home):
    a = PiAdapter()
    t = a.target_dir("test-author/example", category="dev")
    rel = str(t.relative_to(home)).replace("\\", "/")
    assert rel == ".pi/agent/skills/test-author-example"


def test_target_dir_project_scope(home, monkeypatch, tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    monkeypatch.chdir(proj)
    a = PiAdapter()
    t = a.target_dir("test-author/example", category="dev", scope="project")
    rel = str(t.relative_to(proj)).replace("\\", "/")
    assert rel == ".pi/skills/test-author-example"


def test_install_rewrites_name_to_flat_slug(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    a = PiAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    result = a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
                       opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    assert result.success, result.error
    target = home / ".pi/agent/skills/test-author-example"
    fm = yaml.safe_load((target / "SKILL.md").read_text().split("---\n", 2)[1])
    assert fm["name"] == "test-author-example"
    assert "fixture skill" in fm["description"]


def test_install_writes_marker(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    a = PiAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    marker = json.loads((home / ".pi/agent/skills/test-author-example" / MARKER_FILENAME).read_text())
    assert marker["id"] == "test-author/example"
    assert marker["registry_content_hash"] == h


def test_install_refuses_unmanaged(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    target = home / ".pi/agent/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: pre\ndescription: u\n---\n")
    a = PiAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    res = a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={})
    assert not res.success
    assert "refuse to overwrite" in res.error


def test_uninstall_removes(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    a = PiAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": "x"})
    res = a.uninstall("test-author/example")
    assert res.success
    assert not (home / ".pi/agent/skills/test-author-example").exists()


def test_uninstall_refuses_unmanaged(home):
    (home / ".pi/agent").mkdir(parents=True)
    target = home / ".pi/agent/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: x\ndescription: y\n---\n")
    res = PiAdapter().uninstall("test-author/example")
    assert not res.success
    assert "no marker" in res.error


def test_list_installed(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    a = PiAdapter()
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": "x"})
    user_authored = home / ".pi/agent/skills/manual"
    user_authored.mkdir(parents=True)
    (user_authored / "SKILL.md").write_text("---\nname: manual\ndescription: y\n---\n")
    assert [i.id for i in a.list_installed()] == ["test-author/example"]


def test_verify_clean(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    a = PiAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash=h, yanked=False, yank_reason=None)
    assert res.status == "clean"


def test_verify_marker_outdated_on_hash_mismatch(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    a = PiAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash="sha256:deadbeef", yanked=False, yank_reason=None)
    assert res.status == "marker_outdated"


def test_verify_yanked_takes_precedence(home, src_skill):
    (home / ".pi/agent").mkdir(parents=True)
    a = PiAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    a.install(src_skill, "test-author/example", "0.3.0", meta=meta,
              opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    res = a.verify("test-author/example", registry_hash=h, yanked=True, yank_reason="cve")
    assert res.status == "yanked"
    assert "cve" in res.message
