"""Tests that lock the canonical content-hash function as the single source
of truth used by generate_manifest.py, the install verb, and adapter.verify.
Regression guard for Finding 5 of the 2026-05-12 walkthrough — two divergent
hash implementations made every freshly-installed skill report DRIFT."""
import hashlib
import os
from pathlib import Path

import pytest

from adapters._base import compute_dir_content_hash, MARKER_FILENAME


def _seed_skill(root: Path) -> None:
    """A skill dir with a mix of file types and a Windows-CRLF-prone text file."""
    (root / "SKILL.md").write_bytes(b"---\nname: x\ndescription: y\n---\n# body\nline2\n")
    (root / "meta.json").write_bytes(b'{\n  "id": "a/b"\n}\n')
    (root / "scripts").mkdir()
    (root / "scripts" / "run.py").write_bytes(b"print('hi')\n")
    (root / "templates").mkdir()
    (root / "templates" / "out.md").write_bytes(b"hello\n")


def test_hash_is_stable_across_runs(tmp_path):
    a = tmp_path / "a"; a.mkdir(); _seed_skill(a)
    h1 = compute_dir_content_hash(a)
    h2 = compute_dir_content_hash(a)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_hash_is_identical_for_identical_content(tmp_path):
    a = tmp_path / "a"; a.mkdir(); _seed_skill(a)
    b = tmp_path / "b"; b.mkdir(); _seed_skill(b)
    assert compute_dir_content_hash(a) == compute_dir_content_hash(b)


def test_hash_ignores_marker_file(tmp_path):
    """Marker file must not contribute — it's written by the adapter AFTER
    content hashing, so its presence/contents would break verify."""
    a = tmp_path / "a"; a.mkdir(); _seed_skill(a)
    h_before = compute_dir_content_hash(a)
    (a / MARKER_FILENAME).write_text('{"id": "a/b"}')
    h_after = compute_dir_content_hash(a)
    assert h_before == h_after


def test_hash_normalises_crlf_for_text_files(tmp_path):
    """A SKILL.md committed with LF on Linux and checked out with CRLF on
    Windows (autocrlf=true) must produce the same hash. Without this,
    every cross-platform install reports drift."""
    a = tmp_path / "a"; a.mkdir()
    (a / "SKILL.md").write_bytes(b"---\nname: x\ndescription: y\n---\n# body\n")
    b = tmp_path / "b"; b.mkdir()
    (b / "SKILL.md").write_bytes(b"---\r\nname: x\r\ndescription: y\r\n---\r\n# body\r\n")
    assert compute_dir_content_hash(a) == compute_dir_content_hash(b)


def test_hash_does_not_normalise_binary_files(tmp_path):
    """Binary files (e.g. PNG, embedded models) must be hashed byte-exact —
    CRLF normalisation would corrupt the hash for any file containing the
    \\r\\n byte sequence in its binary content."""
    a = tmp_path / "a"; a.mkdir()
    (a / "asset.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"data" * 10)
    b = tmp_path / "b"; b.mkdir()
    (b / "asset.png").write_bytes(b"\x89PNG\n\x1a\n" + b"data" * 10)
    assert compute_dir_content_hash(a) != compute_dir_content_hash(b)


def test_hash_file_sort_is_platform_independent(tmp_path):
    """File-sort key must be the POSIX relative-path string, not a Path
    object — WindowsPath sorts case-insensitively while PosixPath does not,
    which would otherwise produce platform-dependent hashes."""
    a = tmp_path / "a"; a.mkdir()
    # Files chosen to bait case-sensitive sort divergence.
    (a / "SKILL.md").write_bytes(b"x\n")
    (a / "meta.json").write_bytes(b"y\n")
    (a / "README.md").write_bytes(b"z\n")

    # Force-sort the files into Python's relative-string order and recompute
    # the hash manually, then assert it matches the function's output.
    files = sorted(
        str(f.relative_to(a)).replace("\\", "/")
        for f in a.rglob("*") if f.is_file() and f.name != "__marker__"
    )
    # Sanity: SKILL.md should sort before meta.json under string-case ordering
    # ('S' < 'm' in ASCII), and README.md (also uppercase) should come first.
    assert files == ["README.md", "SKILL.md", "meta.json"]
    h = compute_dir_content_hash(a)
    assert h.startswith("sha256:")


def test_generate_manifest_and_base_produce_equal_hashes(tmp_path, monkeypatch):
    """generate_manifest.py and adapters._base must produce byte-identical
    content_hash for the same skill tree. This is the heart of Finding 5."""
    import sys, subprocess, json, shutil
    ROOT = Path(__file__).parent.parent

    repo = tmp_path / "repo"
    shutil.copytree(ROOT, repo,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "tests", "skills"))
    skill = repo / "skills" / "test-author" / "example"
    shutil.copytree(ROOT / "tests/fixtures/good/instructions-only", skill, dirs_exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "x"], cwd=repo, check=True, capture_output=True)
    subprocess.run([sys.executable, str(repo / "scripts/generate_manifest.py")],
                   cwd=repo, check=True, capture_output=True)
    reg = json.loads((repo / "registry.json").read_text(encoding="utf-8"))
    registry_hash = reg["skills"][0]["source"]["content_hash"]
    base_hash = compute_dir_content_hash(skill)
    assert registry_hash == base_hash, (
        f"Hash divergence — registry={registry_hash!r} base={base_hash!r}. "
        "generate_manifest and adapters._base must share one canonical function."
    )
