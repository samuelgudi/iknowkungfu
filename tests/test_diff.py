"""Tests for diff.py."""
from pathlib import Path

import pytest

from clients.skill_contribution.diff import generate_diff, write_diff


def make_tree(root: Path, files: dict) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def test_diff_empty_when_identical(tmp_path):
    pre = tmp_path / "pre"
    post = tmp_path / "post"
    pre.mkdir(); post.mkdir()
    make_tree(pre, {"SKILL.md": "same\n", "scripts/k.py": "x = 1\n"})
    make_tree(post, {"SKILL.md": "same\n", "scripts/k.py": "x = 1\n"})
    out = generate_diff(pre, post)
    assert out.strip() == ""


def test_diff_shows_modified_file(tmp_path):
    pre = tmp_path / "pre"
    post = tmp_path / "post"
    pre.mkdir(); post.mkdir()
    make_tree(pre, {"SKILL.md": "secret_value\n"})
    make_tree(post, {"SKILL.md": "<PLACEHOLDER>\n"})
    out = generate_diff(pre, post)
    assert "--- a/SKILL.md" in out
    assert "+++ b/SKILL.md" in out
    assert "-secret_value" in out
    assert "+<PLACEHOLDER>" in out


def test_diff_omits_unchanged_files(tmp_path):
    pre = tmp_path / "pre"
    post = tmp_path / "post"
    pre.mkdir(); post.mkdir()
    make_tree(pre, {"SKILL.md": "secret\n", "README.md": "unchanged\n"})
    make_tree(post, {"SKILL.md": "<X>\n", "README.md": "unchanged\n"})
    out = generate_diff(pre, post)
    assert "SKILL.md" in out
    assert "README.md" not in out


def test_diff_shows_added_file(tmp_path):
    pre = tmp_path / "pre"
    post = tmp_path / "post"
    pre.mkdir(); post.mkdir()
    make_tree(pre, {"SKILL.md": "x\n"})
    make_tree(post, {"SKILL.md": "x\n", "scripts/new.py": "added\n"})
    out = generate_diff(pre, post)
    assert "scripts/new.py" in out
    assert "+added" in out


def test_diff_shows_removed_file(tmp_path):
    pre = tmp_path / "pre"
    post = tmp_path / "post"
    pre.mkdir(); post.mkdir()
    make_tree(pre, {"SKILL.md": "x\n", "scripts/gone.py": "remove me\n"})
    make_tree(post, {"SKILL.md": "x\n"})
    out = generate_diff(pre, post)
    assert "scripts/gone.py" in out
    assert "-remove me" in out


def test_write_diff_creates_file(tmp_path):
    pre = tmp_path / "pre"; post = tmp_path / "post"
    pre.mkdir(); post.mkdir()
    make_tree(pre, {"SKILL.md": "a\n"})
    make_tree(post, {"SKILL.md": "b\n"})
    out_path = tmp_path / "out/SANITIZATION.diff"
    write_diff(pre, post, out_path)
    assert out_path.exists()
    assert "SKILL.md" in out_path.read_text(encoding="utf-8")
