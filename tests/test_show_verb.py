"""Tests for the show verb."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent


def run_cli(*args, env_extra=None):
    env = None
    if env_extra:
        import os
        env = {**os.environ, **env_extra}
    return subprocess.run(
        [sys.executable, "-m", "agent_skills", *args],
        capture_output=True, text=True, env=env,
    )


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Redirect ~/.cache/iknowkungfu to a tmpdir, populate with a tiny registry."""
    home = tmp_path / "home"
    home.mkdir()
    cache = home / ".cache/iknowkungfu"
    cache.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: home)
    # Touch a fake .claude so detect_host doesn't fail
    (home / ".claude").mkdir()
    registry = {
        "schema_version": 2,
        "generated_at": "2026-05-11T00:00:00Z",
        "skills": [
            {
                "id": "test-author/example",
                "name": "example",
                "description": "Example skill for testing.",
                "version": "0.1.0",
                "status": "active",
                "author": {"name": "Test", "github_login": "test-author", "github_id": 1},
                "category": "meta",
                "tags": ["test"],
                "platforms": ["linux"],
                "agent_compat": ["claude-code"],
                "requires": {"env_vars": [], "commands": []},
                "license": "MIT",
                "install": {"claude-code": {"scope": "user"}},
                "has_scripts": False,
                "versions": {"0.1.0": {"sha": "a" * 40, "released": "2026-05-11T00:00:00Z"}},
                "source": {"path": "skills/test-author/example", "content_hash": "sha256:" + "0" * 64, "files": ["SKILL.md", "meta.json"]},
            }
        ],
    }
    (cache / "registry.json").write_text(json.dumps(registry))
    return cache


def test_show_prints_known_skill(cache_dir):
    """show <id> finds the skill and prints id, version, license, category."""
    # Invoke via the cli.run function directly to use the monkeypatched HOME
    from agent_skills.verbs.show import run
    class Args:
        id = "test-author/example"
        agent = "claude-code"
        json = False
        yes = False
    rc = run(Args())
    # We can't capture stdout here easily; check rc only. Format is verified by JSON test below.
    assert rc == 0


def test_show_json_emits_full_entry(cache_dir, capsys):
    from agent_skills.verbs.show import run
    class Args:
        id = "test-author/example"
        agent = "claude-code"
        json = True
        yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["id"] == "test-author/example"
    assert payload["version"] == "0.1.0"
    assert payload["license"] == "MIT"
    assert payload["category"] == "meta"
    assert "installed" in payload  # boolean install-status field


def test_show_unknown_id_returns_1(cache_dir, capsys):
    from agent_skills.verbs.show import run
    class Args:
        id = "noone/nope"
        agent = "claude-code"
        json = False
        yes = False
    rc = run(Args())
    captured = capsys.readouterr()
    assert rc == 1
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_show_no_cache_returns_1(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    from agent_skills.verbs.show import run
    class Args:
        id = "test-author/example"
        agent = "claude-code"
        json = False
        yes = False
    rc = run(Args())
    assert rc == 1


def test_show_renders_tags_with_hash_prefix(tmp_path, monkeypatch, capsys):
    """show's plaintext output uses #tag notation matching search verb.
    Finding 7 of the 2026-05-12 walkthrough — search and show used different
    tag formats, which is just visual inconsistency."""
    home = tmp_path / "home"; home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/iknowkungfu"; cache.mkdir(parents=True)
    import json as _json
    (cache / "registry.json").write_text(_json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "test/example", "name": "example", "description": "d",
            "version": "0.1.0", "status": "active",
            "author": {"name": "T", "github_login": "test", "github_id": 1},
            "category": "meta", "tags": ["alpha", "beta"],
            "platforms": ["linux"], "agent_compat": ["claude-code"],
            "license": "MIT", "install": {"claude-code": {"scope": "user"}},
            "has_scripts": False,
            "requires": {"env_vars": [], "commands": []},
            "versions": {"0.1.0": {"sha": "x" * 40, "released": "2026-05-11T00:00:00Z"}},
            "source": {"path": "skills/test/example", "content_hash": "sha256:0", "files": []},
        }],
    }))
    from agent_skills.verbs.show import run
    class Args:
        id = "test/example"; agent = "claude-code"; json = False; yes = False
    run(Args())
    out = capsys.readouterr().out
    assert "#alpha" in out and "#beta" in out
    # The old space-separated bare form should be gone
    assert "alpha beta" not in out


# ---------------------------------------------------------------------------
# Imported skills: curator/origin distinction in show output (ADR-002)
# ---------------------------------------------------------------------------

def test_show_renders_origin_for_imported_skill(tmp_path, monkeypatch, capsys):
    """An imported skill (one with an origin block) renders the curator/origin
    distinction: the header says 'curated by <curator>, originally by <origin
    author>', an Origin section shows repo/ref, and the JSON payload carries
    the origin block."""
    home = tmp_path / "home"; home.mkdir()
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    cache = home / ".cache/iknowkungfu"; cache.mkdir(parents=True)
    (cache / "registry.json").write_text(json.dumps({
        "schema_version": 2, "generated_at": "2026-05-11T00:00:00Z",
        "skills": [{
            "id": "curator/imported-example", "name": "imported-example",
            "description": "An imported skill.", "version": "0.1.0", "status": "active",
            "author": {"name": "The Curator", "github_login": "curator", "github_id": 1},
            "category": "dev", "tags": [],
            "platforms": ["linux"], "agent_compat": ["claude-code"],
            "license": "MIT", "install": {"claude-code": {"scope": "user"}},
            "has_scripts": False,
            "requires": {"env_vars": [], "commands": []},
            "versions": {"0.1.0": {"sha": "x" * 40, "released": "2026-05-11T00:00:00Z"}},
            "source": {"path": "skills/curator/imported-example",
                       "content_hash": "sha256:0", "files": []},
            "origin": {
                "author_name": "Original Dev",
                "author_url": "https://github.com/original-dev",
                "repo": "https://github.com/original-dev/src",
                "ref": "deadbeef",
                "imported_at": "2026-05-14T00:00:00Z",
            },
        }],
    }))
    from agent_skills.verbs.show import run

    class Args:
        id = "curator/imported-example"; agent = "claude-code"; json = False; yes = False
    run(Args())
    out = capsys.readouterr().out
    assert "curated by curator" in out
    assert "originally by Original Dev" in out
    assert "https://github.com/original-dev/src" in out
    assert "deadbeef" in out

    class ArgsJ:
        id = "curator/imported-example"; agent = "claude-code"; json = True; yes = False
    run(ArgsJ())
    payload = json.loads(capsys.readouterr().out)
    assert payload["origin"]["author_name"] == "Original Dev"
    assert payload["origin"]["repo"] == "https://github.com/original-dev/src"


def test_show_first_party_skill_has_no_origin(cache_dir, capsys):
    """A first-party skill (no origin block) must not render origin lines, and
    its JSON payload must not gain an origin key. The plain 'by <login>'
    header form is preserved."""
    from agent_skills.verbs.show import run

    class ArgsJ:
        id = "test-author/example"; agent = "claude-code"; json = True; yes = False
    run(ArgsJ())
    payload = json.loads(capsys.readouterr().out)
    assert "origin" not in payload

    class Args:
        id = "test-author/example"; agent = "claude-code"; json = False; yes = False
    run(Args())
    out = capsys.readouterr().out
    assert "originally by" not in out
    assert "curated by" not in out
    assert "by test-author" in out
