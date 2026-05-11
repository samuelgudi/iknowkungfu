import json
from pathlib import Path
import re

import pytest

from adapters.hermes import HermesAdapter
from adapters._base import compute_dir_content_hash


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def src_skill(tmp_path):
    src = tmp_path / "src/test-author/example"
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text("---\nname: example\ndescription: test skill\n---\n\n# Example\n\nBody text.\n")
    (src / "meta.json").write_text(json.dumps({
        "id": "test-author/example",
        "version": "0.3.0",
        "author": {"name": "Test", "github_login": "test", "github_id": 1},
        "category": "ops",
        "license": "MIT",
        "platforms": ["linux"],
        "tags": ["test", "fixture"],
        "requires": {"env_vars": ["MY_VAR"], "commands": ["git"]},
        "related_skills": ["test-author/other"],
    }))
    return src


def test_target_dir_uses_category(home):
    a = HermesAdapter()
    t = a.target_dir("test-author/example", category="ops")
    assert str(t).endswith("/.hermes/skills/ops/example") or str(t).endswith("\\.hermes\\skills\\ops\\example")


def test_install_synthesizes_full_frontmatter(home, src_skill):
    (home / ".hermes").mkdir()
    a = HermesAdapter()
    h = compute_dir_content_hash(src_skill)
    meta = json.loads((src_skill / "meta.json").read_text())
    result = a.install(src_skill, "test-author/example", "0.3.0", meta=meta, opts={"registry_hash": h, "source_url": "x", "tree_sha": "abc"})
    assert result.success
    target = home / ".hermes/skills/ops/example"
    installed_md = (target / "SKILL.md").read_text()

    # Synthesized fields appear in frontmatter
    assert "version: 0.3.0" in installed_md
    assert "license: MIT" in installed_md
    assert "platforms" in installed_md and "linux" in installed_md
    assert "prerequisites" in installed_md and "MY_VAR" in installed_md and "git" in installed_md
    assert "metadata" in installed_md and "hermes" in installed_md and "test" in installed_md
    # Body preserved
    assert "# Example" in installed_md
    assert "Body text." in installed_md
