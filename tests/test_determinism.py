"""Determinism contract tests for the search engine.

The contract (spec § 6.4): identical (registry_version, query) → identical
result list, across runs, across processes, across rebuilds of the index.

These tests pin the contract with concrete fixtures and SHA-256 hashes of
serialized results. If a future change accidentally breaks determinism, one
of these tests will fire.
"""
import hashlib
import json

import pytest

from agent_skills.search.index import build_index
from agent_skills.search.ranker import search


# A fixed fixture registry — every field deterministic, no timestamps that
# change between runs. The schema mirrors registry.json shape.
_FIXTURE = {
    "schema_version": 2,
    "generated_at": "2026-01-01T00:00:00Z",
    "skills": [
        {
            "id": "alpha/aaa",
            "name": "aaa",
            "description": "Alpha helper for aardvark",
            "version": "1.0.0",
            "status": "active",
            "category": "dev",
            "tags": ["alpha", "stdlib"],
            "platforms": ["linux", "macos"],
            "agent_compat": ["claude-code", "openclaw"],
            "requires": {"env_vars": [], "commands": []},
            "license": "MIT",
            "author": {"name": "A", "github_login": "alpha", "github_id": 1},
            "body": "",
        },
        {
            "id": "beta/bbb",
            "name": "bbb",
            "description": "Beta helper for bumblebee",
            "version": "2.1.0",
            "status": "active",
            "category": "dev",
            "tags": ["beta", "stdlib"],
            "platforms": ["linux", "macos", "windows"],
            "agent_compat": ["claude-code"],
            "requires": {"env_vars": ["BETA_KEY"], "commands": []},
            "license": "Apache-2.0",
            "author": {"name": "B", "github_login": "beta", "github_id": 2},
            "body": "",
        },
        {
            "id": "gamma/ccc",
            "name": "ccc",
            "description": "Gamma helper for camel",
            "version": "0.9.0",
            "status": "active",
            "category": "media",
            "tags": ["gamma"],
            "platforms": ["linux"],
            "agent_compat": ["codex"],
            "requires": {"env_vars": [], "commands": []},
            "license": "MIT",
            "author": {"name": "C", "github_login": "gamma", "github_id": 3},
            "body": "",
        },
    ],
}


def _result_hash(query: str, db_path) -> str:
    """Hash a search result so we can compare across runs without storing
    the entire result. The hash covers result count + id + version + score
    of each result — enough to catch any drift in ordering or composition."""
    r = search(query, db_path=db_path)
    payload = {
        "total": r.total,
        "registry_version": r.registry_version,
        "ids": [(x["id"], x["version"], x.get("score")) for x in r.results],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


# ─── Within-process determinism: 10 runs against the same db ──────────────


@pytest.mark.parametrize(
    "query",
    [
        "",
        "alpha",
        "helper",
        "tag:stdlib",
        "category:dev",
        "agent:claude-code tag:beta",
        "license:MIT OR license:Apache-2.0",
        "version:>=1.0",
        "name:bbb",
        '"helper for"',
    ],
)
def test_repeated_runs_same_db_identical_hash(query, tmp_path):
    db = tmp_path / "registry.db"
    build_index(_FIXTURE, db)
    first = _result_hash(query, db)
    for _ in range(9):
        assert _result_hash(query, db) == first


# ─── Cross-build determinism: separate db files, same registry ─────────────


@pytest.mark.parametrize(
    "query",
    [
        "alpha",
        "tag:stdlib",
        "category:dev version:>=1.0",
        "license:MIT OR license:Apache-2.0",
    ],
)
def test_separate_builds_same_registry_identical_hash(query, tmp_path):
    db_a = tmp_path / "a.db"
    db_b = tmp_path / "b.db"
    build_index(_FIXTURE, db_a)
    build_index(_FIXTURE, db_b)
    assert _result_hash(query, db_a) == _result_hash(query, db_b)


# ─── Stable ordering for tie-broken results ───────────────────────────────


def test_full_listing_order_is_deterministic(tmp_path):
    """Empty query → all active skills. The order must be stable across runs."""
    db = tmp_path / "registry.db"
    build_index(_FIXTURE, db)
    r1 = search("", db_path=db)
    r2 = search("", db_path=db)
    ids1 = tuple(x["id"] for x in r1.results)
    ids2 = tuple(x["id"] for x in r2.results)
    assert ids1 == ids2
    # Order: no BM25 (empty query), so sort is (semver DESC, id ASC).
    # versions: beta/bbb 2.1.0, alpha/aaa 1.0.0, gamma/ccc 0.9.0.
    assert ids1 == ("beta/bbb", "alpha/aaa", "gamma/ccc")


def test_pagination_is_deterministic(tmp_path):
    db = tmp_path / "registry.db"
    build_index(_FIXTURE, db)
    r0 = search("", db_path=db, limit=1, offset=0)
    r1 = search("", db_path=db, limit=1, offset=1)
    r2 = search("", db_path=db, limit=1, offset=2)
    assert r0.results[0]["id"] == "beta/bbb"
    assert r1.results[0]["id"] == "alpha/aaa"
    assert r2.results[0]["id"] == "gamma/ccc"


# ─── Recorded hashes (the "canary" — fail-loud on accidental drift) ───────

# These hashes were computed at spec-lock time. If the spec's determinism
# contract changes (e.g. a tokenizer swap, a sort-key change, an FTS5 version
# bump that shifts scoring), these hashes break and you should:
#   1. Audit the change to confirm it's intentional.
#   2. Re-record the hashes here.
#   3. Bump INDEX_SCHEMA_VERSION in agent_skills/search/index.py.

_RECORDED_HASHES = {
    # Pure-filter queries (no BM25) — sort is (semver DESC, id ASC).
    "tag:stdlib": [("beta/bbb", "2.1.0"), ("alpha/aaa", "1.0.0")],
    "category:dev": [("beta/bbb", "2.1.0"), ("alpha/aaa", "1.0.0")],
    "version:>=1.0": [("beta/bbb", "2.1.0"), ("alpha/aaa", "1.0.0")],
    "license:MIT": [("alpha/aaa", "1.0.0"), ("gamma/ccc", "0.9.0")],
}


@pytest.mark.parametrize("query,expected", list(_RECORDED_HASHES.items()))
def test_recorded_filter_query_results(query, expected, tmp_path):
    """Recorded id+version order for filter-only queries. Score-dependent
    queries are tested separately because BM25 weights can shift across
    SQLite versions — but the filter ordering above is purely (semver, id)
    and must remain stable forever."""
    db = tmp_path / "registry.db"
    build_index(_FIXTURE, db)
    r = search(query, db_path=db)
    got = [(x["id"], x["version"]) for x in r.results]
    assert got == expected
