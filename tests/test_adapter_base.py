import json
from pathlib import Path

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
