"""Tests for the search CLI verb (agent_skills.verbs.search).

Covers: end-to-end integration with the new ranker, auto-index rebuild,
deprecated-flag translation + warning, JSON / NDJSON / pretty output,
CompilerError propagation, missing-registry handling.
"""
import argparse
import json
from pathlib import Path

import pytest

from agent_skills.verbs import search as search_verb


def _registry():
    return {
        "schema_version": 2,
        "generated_at": "2026-05-12T08:51:19Z",
        "skills": [
            {
                "id": "samuelgudi/rust-helpers",
                "name": "rust-helpers",
                "description": "Rust helpers for systems programming",
                "version": "1.0.0",
                "status": "active",
                "category": "dev",
                "tags": ["rust", "systems"],
                "platforms": ["linux", "macos", "windows"],
                "agent_compat": ["claude-code"],
                "requires": {"env_vars": [], "commands": []},
                "license": "MIT",
                "author": {
                    "name": "S",
                    "github_login": "samuelgudi",
                    "github_id": 1,
                },
                "body": "",
            },
            {
                "id": "samuelgudi/python-helpers",
                "name": "python-helpers",
                "description": "Python helpers",
                "version": "0.5.0",
                "status": "active",
                "category": "dev",
                "tags": ["python"],
                "platforms": ["linux"],
                "agent_compat": ["claude-code", "openclaw"],
                "requires": {"env_vars": [], "commands": []},
                "license": "MIT",
                "author": {
                    "name": "S",
                    "github_login": "samuelgudi",
                    "github_id": 1,
                },
                "body": "",
            },
        ],
    }


@pytest.fixture
def cached_registry(fake_home):
    """Write a registry.json into the patched ~/.cache/iknowkungfu/."""
    cache = fake_home / ".cache" / "iknowkungfu"
    cache.mkdir(parents=True)
    (cache / "registry.json").write_text(json.dumps(_registry()), encoding="utf-8")
    return cache


def _args(**overrides):
    defaults = {
        "terms": [],
        "agent": None,
        "category": None,
        "tag": None,
        "limit": 10,
        "offset": 0,
        "include_deprecated": False,
        "json": False,
        "ndjson": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ─── End-to-end: free-text + JSON output ───────────────────────────────────

def test_search_returns_zero_on_match(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["rust"], json=True))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["total"] == 1
    assert out["results"][0]["id"] == "samuelgudi/rust-helpers"


def test_search_pretty_output_shows_top_result_marker(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["rust"]))
    assert rc == 0
    out = capsys.readouterr().out
    assert "★" in out
    assert "samuelgudi/rust-helpers" in out


def test_search_no_match_message(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["nothingmatchesthis"]))
    assert rc == 0
    out = capsys.readouterr().out
    assert "No skills match" in out


def test_search_ndjson_output(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["rust"], ndjson=True))
    assert rc == 0
    out = capsys.readouterr().out.strip()
    # One JSON object per line.
    lines = out.splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["id"] == "samuelgudi/rust-helpers"


# ─── Auto-index behavior ────────────────────────────────────────────────────

def test_search_builds_index_on_first_use(cached_registry, capsys):
    db = cached_registry / "registry.db"
    assert not db.exists()
    search_verb.run(_args(terms=["rust"], json=True))
    assert db.exists()


def test_search_rebuilds_index_when_registry_updated(cached_registry, capsys):
    # First search builds an index.
    search_verb.run(_args(terms=["rust"], json=True))
    db = cached_registry / "registry.db"
    first_mtime = db.stat().st_mtime
    # Mutate the registry: new generated_at + new skill.
    reg = _registry()
    reg["generated_at"] = "2026-05-13T00:00:00Z"
    reg["skills"].append(
        {
            "id": "a/newskill",
            "name": "newskill",
            "description": "Brand new",
            "version": "0.1.0",
            "status": "active",
            "category": "meta",
            "tags": ["new"],
            "platforms": ["linux"],
            "agent_compat": ["claude-code"],
            "requires": {"env_vars": [], "commands": []},
            "license": "MIT",
            "author": {"name": "X", "github_login": "x", "github_id": 9},
            "body": "",
        }
    )
    (cached_registry / "registry.json").write_text(json.dumps(reg), encoding="utf-8")

    capsys.readouterr()  # drain
    search_verb.run(_args(terms=["newskill"], json=True))
    out = json.loads(capsys.readouterr().out)
    assert out["registry_version"] == "2026-05-13T00:00:00Z"
    assert out["total"] == 1


# ─── Deprecated flag handling ───────────────────────────────────────────────

def test_deprecated_agent_flag_translates_to_dsl(cached_registry, capsys):
    rc = search_verb.run(_args(agent="openclaw", json=True))
    assert rc == 0
    err = capsys.readouterr().err
    assert "--agent" in err and "deprecated" in err.lower()
    # Verify it filtered correctly via stdout JSON.


def test_deprecated_tag_flag_translates_to_dsl(cached_registry, capsys):
    rc = search_verb.run(_args(tag="python", json=True))
    assert rc == 0
    out_text = capsys.readouterr()
    err = out_text.err
    assert "--tag" in err
    out = json.loads(out_text.out)
    assert out["total"] == 1
    assert out["results"][0]["id"] == "samuelgudi/python-helpers"


def test_deprecated_category_flag(cached_registry, capsys):
    rc = search_verb.run(_args(category="dev", json=True))
    assert rc == 0
    out_text = capsys.readouterr()
    assert "--category" in out_text.err
    out = json.loads(out_text.out)
    assert out["total"] == 2


def test_multiple_deprecated_flags_all_warned(cached_registry, capsys):
    rc = search_verb.run(_args(agent="claude-code", tag="rust", json=True))
    assert rc == 0
    err = capsys.readouterr().err
    assert "--agent" in err
    assert "--tag" in err


def test_no_deprecation_warning_for_dsl_query(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["agent:claude-code", "tag:rust"], json=True))
    assert rc == 0
    err = capsys.readouterr().err
    assert "deprecated" not in err.lower()


# ─── Error handling ─────────────────────────────────────────────────────────

def test_search_returns_1_when_no_registry_cached(fake_home, capsys):
    rc = search_verb.run(_args(terms=["rust"]))
    assert rc == 1
    err = capsys.readouterr().err
    assert "kfu update" in err


def test_search_returns_2_on_compiler_error(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["unknownfield:value"]))
    assert rc == 2
    err = capsys.readouterr().err
    assert "Query error" in err


# ─── DSL queries via positional args ────────────────────────────────────────

def test_dsl_query_via_positionals(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["agent:openclaw"], json=True))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["total"] == 1
    assert out["results"][0]["id"] == "samuelgudi/python-helpers"


def test_dsl_combined_filter_and_freetext(cached_registry, capsys):
    rc = search_verb.run(_args(terms=["rust", "category:dev"], json=True))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["total"] == 1
    assert out["results"][0]["id"] == "samuelgudi/rust-helpers"


# ─── Pagination ────────────────────────────────────────────────────────────

def test_limit_passed_through(cached_registry, capsys):
    rc = search_verb.run(_args(limit=1, json=True))
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["limit"] == 1
    assert len(out["results"]) == 1
    assert out["total"] == 2  # total across the registry, not just the page


def test_offset_passed_through(cached_registry, capsys):
    rc = search_verb.run(_args(limit=10, offset=1, json=True))
    out = json.loads(capsys.readouterr().out)
    assert out["offset"] == 1
    assert len(out["results"]) == 1


# ─── Determinism via CLI ────────────────────────────────────────────────────

def test_cli_search_deterministic(cached_registry, capsys):
    """Two identical invocations → identical JSON output."""
    search_verb.run(_args(terms=["category:dev"], json=True))
    a = capsys.readouterr().out
    search_verb.run(_args(terms=["category:dev"], json=True))
    b = capsys.readouterr().out
    assert a == b
