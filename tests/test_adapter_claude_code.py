from pathlib import Path
import json
import shutil

import pytest

from adapters.claude_code import ClaudeCodeAdapter
from adapters._base import compute_dir_content_hash


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def src_skill(tmp_path):
    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: example\ndescription: test\n---\n# Example\n")
    (src / "meta.json").write_text(json.dumps({"id": "test-author/example", "version": "0.1.0"}))
    return src


def test_detect_false_when_no_claude(home):
    assert ClaudeCodeAdapter().detect() is False


def test_detect_true_when_claude_dir_exists(home):
    (home / ".claude").mkdir()
    assert ClaudeCodeAdapter().detect() is True


def test_install_writes_files_and_marker(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    result = adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    assert result.success
    target = home / ".claude/skills/test-author-example"
    assert (target / "SKILL.md").exists()
    assert (target / ".agent-skills-marker.json").exists()


def test_uninstall_removes_directory(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    target = home / ".claude/skills/test-author-example"
    assert target.exists()
    result = adapter.uninstall("test-author/example")
    assert result.success
    assert not target.exists()


def test_uninstall_refuses_without_marker(home, src_skill):
    (home / ".claude").mkdir()
    target = home / ".claude/skills/test-author-example"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("hand-authored")
    adapter = ClaudeCodeAdapter()
    result = adapter.uninstall("test-author/example")
    assert not result.success
    assert target.exists()


def test_verify_clean(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    result = adapter.verify("test-author/example", registry_hash=h, yanked=False, yank_reason=None)
    assert result.status == "clean"


def test_verify_drift_when_file_edited(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    target = home / ".claude/skills/test-author-example"
    (target / "SKILL.md").write_text("tampered")
    result = adapter.verify("test-author/example", registry_hash=h, yanked=False, yank_reason=None)
    assert result.status == "drift"


def test_verify_yanked_alert(home, src_skill):
    (home / ".claude").mkdir()
    adapter = ClaudeCodeAdapter()
    h = compute_dir_content_hash(src_skill)
    adapter.install(src_skill, "test-author/example", "0.1.0", meta={"category": "meta"}, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    result = adapter.verify("test-author/example", registry_hash=h, yanked=True, yank_reason="compromised dep")
    assert result.status == "yanked"
    assert "compromised dep" in result.message
