import json
from pathlib import Path

import pytest

from adapters._base import write_marker, read_marker, MARKER_FILENAME


def test_write_and_read_marker(tmp_path):
    target = tmp_path / "skill"
    target.mkdir()
    write_marker(target, skill_id="a/b", version="0.1.0", content_hash="sha256:abc", source_url="x", tree_sha="def")
    m = read_marker(target)
    assert m["id"] == "a/b"
    assert m["version"] == "0.1.0"
    assert m["registry_content_hash"] == "sha256:abc"
    assert (target / MARKER_FILENAME).exists()


# ---------------------------------------------------------------------------
# split_skill_id — path-traversal guard
# ---------------------------------------------------------------------------

def test_split_skill_id_valid():
    from adapters._base import split_skill_id
    assert split_skill_id("samuelgudi/session-handoff") == ("samuelgudi", "session-handoff")


@pytest.mark.parametrize("bad_id", [
    "author/../../../../tmp/evil",
    "../escape/slug",
    "author/slug/extra",
    "Author/Slug",
    r"author\slug",
    "author/.hidden",
    "author/",
    "/slug",
    "",
    "author/slug..",
    "a//b",
])
def test_split_skill_id_rejects_traversal_and_bad_grammar(bad_id):
    from adapters._base import split_skill_id
    with pytest.raises(ValueError):
        split_skill_id(bad_id)


def test_checked_uninstall_refuses_marker_id_mismatch(tmp_path):
    from adapters._base import checked_uninstall, write_marker
    victim = tmp_path / "other-skill"
    victim.mkdir()
    (victim / "SKILL.md").write_text("# x\n", encoding="utf-8")
    write_marker(victim, skill_id="someone/other-skill", version="1.0.0",
                 content_hash="", source_url="", tree_sha="")
    result = checked_uninstall(victim, "attacker/requested-skill")
    assert not result.success
    assert "refusing" in result.error
    assert victim.exists()  # nothing was deleted


def test_checked_uninstall_removes_matching_marker(tmp_path):
    from adapters._base import checked_uninstall, write_marker
    target = tmp_path / "mine"
    target.mkdir()
    (target / "SKILL.md").write_text("# x\n", encoding="utf-8")
    write_marker(target, skill_id="me/mine", version="1.0.0",
                 content_hash="", source_url="", tree_sha="")
    result = checked_uninstall(target, "me/mine")
    assert result.success
    assert not target.exists()


# ---------------------------------------------------------------------------
# atomic_install — interruption safety
# ---------------------------------------------------------------------------

def test_atomic_install_swap_preserves_old_on_failure(tmp_path, monkeypatch):
    """If the move-into-place step dies, the previous install must be restored."""
    import shutil as _shutil
    from adapters._base import atomic_install
    src = tmp_path / "src"
    src.mkdir()
    (src / "SKILL.md").write_text("new\n", encoding="utf-8")
    target = tmp_path / "installed"
    target.mkdir()
    (target / "SKILL.md").write_text("old\n", encoding="utf-8")

    real_move = _shutil.move
    def exploding_move(a, b):
        if str(b) == str(target) and a.endswith("staged"):
            raise OSError("simulated interruption")
        return real_move(a, b)
    monkeypatch.setattr(_shutil, "move", exploding_move)

    with pytest.raises(OSError):
        atomic_install(src, target)
    assert target.exists()
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "old\n"


def test_atomic_install_reinstall_replaces_content(tmp_path):
    from adapters._base import atomic_install
    src = tmp_path / "src"
    src.mkdir()
    (src / "SKILL.md").write_text("new\n", encoding="utf-8")
    target = tmp_path / "installed"
    target.mkdir()
    (target / "SKILL.md").write_text("old\n", encoding="utf-8")
    (target / "stale.txt").write_text("x\n", encoding="utf-8")
    files = atomic_install(src, target)
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "new\n"
    assert not (target / "stale.txt").exists()
    assert files == ["SKILL.md"]
