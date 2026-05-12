"""Tests for the search runner (agent_skills.search.ranker).

Covers: query DSL → SQL+FTS5 translation, BM25 ranking, deterministic
tie-breaking, version-range post-filtering, deprecated/yanked toggles,
mixed-OR rejection, edge cases.
"""
import pytest

from agent_skills.search.index import build_index
from agent_skills.search.ranker import CompilerError, search


def _skill(
    id, name=None, description="", tags=None, agent_compat=None,
    category="dev", license="MIT", version="1.0.0", status="active",
    requires=None, platforms=None, author=None,
):
    return {
        "id": id,
        "name": name or id.split("/")[-1],
        "description": description,
        "version": version,
        "status": status,
        "category": category,
        "tags": tags or [],
        "platforms": platforms if platforms is not None else ["linux", "macos", "windows"],
        "agent_compat": agent_compat or ["claude-code"],
        "requires": requires or {"env_vars": [], "commands": []},
        "license": license,
        "author": author or {"name": "Test", "github_login": "tester", "github_id": 1},
        "body": "",
    }


@pytest.fixture
def registry():
    return {
        "schema_version": 2,
        "generated_at": "2026-05-12T08:51:19Z",
        "skills": [
            _skill(
                "samuelgudi/rust-serde",
                description="Helpers for Rust serde serialization",
                tags=["rust", "serialization"],
                agent_compat=["claude-code", "openclaw"],
                category="dev",
                version="1.2.0",
            ),
            _skill(
                "samuelgudi/rust-tokio",
                description="Async runtime helpers for Rust tokio",
                tags=["rust", "async", "tokio"],
                agent_compat=["claude-code"],
                category="dev",
                version="0.9.0",
            ),
            _skill(
                "samuelgudi/whisper",
                description="Transcribe audio with Whisper",
                tags=["audio", "ai"],
                agent_compat=["claude-code", "hermes"],
                category="ai",
                requires={"env_vars": ["OPENAI_API_KEY"], "commands": ["ffmpeg"]},
                version="2.0.0",
                license="Apache-2.0",
            ),
            _skill(
                "samuelgudi/markdown",
                description="Deprecated markdown helper",
                tags=["markdown", "docs"],
                agent_compat=["claude-code"],
                category="docs",
                status="deprecated",
                version="1.5.0",
            ),
            _skill(
                "other/go-helpers",
                description="Go utility helpers",
                tags=["go", "stdlib"],
                agent_compat=["codex"],
                category="dev",
                version="3.1.0",
                author={"name": "Other", "github_login": "otheruser", "github_id": 2},
            ),
        ],
    }


@pytest.fixture
def db(registry, tmp_path):
    p = tmp_path / "registry.db"
    build_index(registry, p)
    return p


# ─── Empty / trivial queries ───────────────────────────────────────────────

def test_empty_query_returns_all_active(db):
    r = search("", db_path=db)
    ids = [x["id"] for x in r.results]
    assert "samuelgudi/markdown" not in ids  # deprecated by default
    assert r.total == 4


def test_empty_query_with_include_deprecated(db):
    r = search("", db_path=db, include_deprecated=True)
    assert r.total == 5


def test_whitespace_only_returns_all_active(db):
    r = search("   ", db_path=db)
    assert r.total == 4


# ─── Free-text matches ─────────────────────────────────────────────────────

def test_single_term_matches_description(db):
    r = search("serialization", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/rust-serde"]


def test_phrase_match(db):
    r = search('"Async runtime"', db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/rust-tokio"]


def test_phrase_not_matching(db):
    r = search('"random words that do not appear"', db_path=db)
    assert r.total == 0


def test_implicit_and_narrows_results(db):
    r_either = search("rust", db_path=db)
    assert len(r_either.results) >= 2
    r_both = search("rust async", db_path=db)
    # Both terms must appear
    assert [x["id"] for x in r_both.results] == ["samuelgudi/rust-tokio"]


# ─── Field filters (indexed columns) ───────────────────────────────────────

def test_tag_filter_uses_fts5_column_query(db):
    r = search("tag:tokio", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/rust-tokio"]


def test_name_filter(db):
    r = search("name:whisper", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/whisper"]


def test_name_prefix(db):
    r = search("name:rust*", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"samuelgudi/rust-serde", "samuelgudi/rust-tokio"}


# ─── Field filters (unindexed columns) ─────────────────────────────────────

def test_agent_filter(db):
    r = search("agent:hermes", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/whisper"]


def test_category_filter(db):
    r = search("category:dev", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"samuelgudi/rust-serde", "samuelgudi/rust-tokio", "other/go-helpers"}


def test_license_filter(db):
    r = search("license:Apache-2.0", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/whisper"]


def test_author_filter(db):
    r = search("author:otheruser", db_path=db)
    assert [x["id"] for x in r.results] == ["other/go-helpers"]


def test_status_filter_finds_deprecated(db):
    r = search("status:deprecated", db_path=db, include_deprecated=True)
    assert [x["id"] for x in r.results] == ["samuelgudi/markdown"]


def test_requires_env_var_filter(db):
    r = search("requires:env_var:OPENAI_API_KEY", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/whisper"]


def test_platform_filter(db):
    r = search("platform:linux", db_path=db)
    # All have linux
    assert r.total == 4


# ─── Version-range filters ─────────────────────────────────────────────────

def test_version_eq(db):
    r = search("version:1.2.0", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/rust-serde"]


def test_version_gte(db):
    r = search("version:>=2.0", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"samuelgudi/whisper", "other/go-helpers"}


def test_version_lte(db):
    r = search("version:<=1.0", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"samuelgudi/rust-tokio"}


def test_version_lt(db):
    r = search("version:<1.0", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"samuelgudi/rust-tokio"}


def test_version_gt(db):
    r = search("version:>2.0", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"other/go-helpers"}


# ─── Boolean combinators ──────────────────────────────────────────────────

def test_and_combines_filters(db):
    r = search("tag:rust agent:openclaw", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/rust-serde"]


def test_explicit_and(db):
    r = search("tag:rust AND tag:tokio", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/rust-tokio"]


def test_or_within_fts5(db):
    r = search("tag:tokio OR tag:serialization", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"samuelgudi/rust-serde", "samuelgudi/rust-tokio"}


def test_or_within_sql(db):
    r = search("license:MIT OR license:Apache-2.0", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {
        "samuelgudi/rust-serde",
        "samuelgudi/rust-tokio",
        "samuelgudi/whisper",
        "other/go-helpers",
    }


def test_or_across_fts5_and_sql_raises(db):
    with pytest.raises(CompilerError, match="OR across FTS5"):
        search("tag:rust OR license:MIT", db_path=db)


def test_not_on_field_filter(db):
    r = search("tag:rust -agent:openclaw", db_path=db)
    assert [x["id"] for x in r.results] == ["samuelgudi/rust-tokio"]


# ─── FTS5-side negation regression tests (fix for review finding #1) ───────


def test_bare_negation_of_free_text(db):
    """Bare `-rust` previously crashed with SQL syntax error because FTS5
    'NOT' is binary, not unary. Now routed through `rowid NOT IN`."""
    r = search("-rust", db_path=db)
    ids = {x["id"] for x in r.results}
    # Should return everything that doesn't match 'rust' freely.
    assert "samuelgudi/whisper" in ids
    assert "other/go-helpers" in ids
    assert "samuelgudi/rust-serde" not in ids
    assert "samuelgudi/rust-tokio" not in ids


def test_bare_negation_of_indexed_field(db):
    """`-tag:rust` — same crash class as bare -term."""
    r = search("-tag:rust", db_path=db)
    ids = {x["id"] for x in r.results}
    assert "samuelgudi/whisper" in ids
    assert "other/go-helpers" in ids
    assert "samuelgudi/rust-serde" not in ids


def test_pos_and_anti_collapse_into_fts5_binary_not(db):
    """`name:foo -name:bar` should collapse into FTS5's binary NOT (one MATCH
    expression), not produce two separate clauses."""
    r = search("description:Helpers -description:Async", db_path=db)
    ids = {x["id"] for x in r.results}
    # rust-serde has "Helpers" in description but not "Async"
    # rust-tokio has "Async" in description, should be excluded
    assert "samuelgudi/rust-serde" in ids
    assert "samuelgudi/rust-tokio" not in ids


def test_double_negation_of_fts5_term(db):
    """NOT NOT X → X (collapsed at compile time, not via runtime NOT IN)."""
    r = search("NOT NOT rust", db_path=db)
    ids = {x["id"] for x in r.results}
    assert "samuelgudi/rust-serde" in ids
    assert "samuelgudi/rust-tokio" in ids


def test_two_antis_combine_via_demorgan(db):
    """`-rust -tokio` → exclude rows matching EITHER (DeMorgan combination)."""
    r = search("-rust -tokio", db_path=db)
    ids = {x["id"] for x in r.results}
    # Skills with 'rust' OR 'tokio' as free-text terms get excluded.
    assert "samuelgudi/rust-serde" not in ids
    assert "samuelgudi/rust-tokio" not in ids
    # Skills with neither should remain.
    assert "samuelgudi/whisper" in ids


def test_sql_filter_and_fts5_anti_mixed(db):
    """category:dev -rust → SQL filter AND fts5 anti, combined into 'both'."""
    r = search("category:dev -rust", db_path=db)
    ids = {x["id"] for x in r.results}
    # In category:dev: rust-serde, rust-tokio, go-helpers.
    # Exclude rows matching 'rust' → only go-helpers should remain.
    assert ids == {"other/go-helpers"}


def test_or_with_fts5_anti_is_rejected(db):
    """OR with a negated FTS5 branch can't be expressed cleanly in v1 — reject."""
    with pytest.raises(CompilerError):
        search("rust OR -tokio", db_path=db)


# ─── LIKE-wildcard escaping (fix for review finding #3) ───────────────────


def test_user_percent_in_pipe_filter_is_literal(db):
    """`agent:%` previously matched every row because user `%` acted as a
    SQL LIKE wildcard. With ESCAPE clauses applied, `agent:%` is a literal
    string that no skill has → 0 matches."""
    r = search("agent:%", db_path=db)
    assert r.total == 0


def test_user_underscore_in_pipe_filter_is_literal(db):
    """`agent:rust_` should not match `agent:rust-serde` via SQL underscore
    wildcard (which would match any single char)."""
    r = search("agent:claude_code", db_path=db)
    # 'claude_code' is not a literal value of agent_compat for any skill in
    # the fixture (they use 'claude-code'), so 0 matches.
    assert r.total == 0


def test_user_percent_in_exact_filter_is_literal(db):
    r = search("license:M%", db_path=db)
    # No skill has license literally 'M%'.
    assert r.total == 0


# ─── Hyphenated-tag false-positive — current behavior documented ──────────


def test_hyphenated_tag_false_positive_documented(db, tmp_path):
    """Review finding #6: phrase-match via FTS5 on the tags column produces
    false positives when a skill has the constituent tokens as ADJACENT
    separate tags. The legitimate match still works; only the edge case
    misbehaves. A proper fix needs a schema change (separate pipe-delimited
    tags_filter column) which is deferred.

    This test captures CURRENT behavior so we notice when (or if) it changes.
    """
    from agent_skills.search.index import build_index

    reg = {
        "schema_version": 2,
        "generated_at": "2026-01-01T00:00:00Z",
        "skills": [
            _skill(
                "real/match",
                description="x",
                tags=["rust", "claude-code"],
                agent_compat=["claude-code"],
            ),
            _skill(
                "false/positive",
                description="y",
                tags=["claude", "code"],
                agent_compat=["claude-code"],
            ),
            _skill(
                "no/match",
                description="z",
                tags=["python"],
                agent_compat=["claude-code"],
            ),
        ],
    }
    db2 = tmp_path / "hyphen.db"
    build_index(reg, db2)
    r = search("tag:claude-code", db_path=db2)
    ids = {x["id"] for x in r.results}
    # The legitimate match works:
    assert "real/match" in ids
    # ⚠ KNOWN ISSUE: the false-positive also matches in v1 — see finding #6.
    # If a future commit fixes this, change `in` to `not in` and remove this note.
    assert "false/positive" in ids
    # Unrelated skill correctly excluded:
    assert "no/match" not in ids


def test_combined_real_world_query(db):
    # rust-serde has tag:rust but NOT tag:async; rust-tokio has both.
    r = search("rust tag:async", db_path=db)
    ids = {x["id"] for x in r.results}
    assert ids == {"samuelgudi/rust-tokio"}


# ─── Determinism contract ─────────────────────────────────────────────────

def test_determinism_same_query_same_results(db):
    a = search("rust tag:async", db_path=db)
    b = search("rust tag:async", db_path=db)
    assert a == b
    assert tuple(x["id"] for x in a.results) == tuple(x["id"] for x in b.results)


def test_determinism_score_is_stable(db):
    a = search("rust", db_path=db)
    b = search("rust", db_path=db)
    assert [x["score"] for x in a.results] == [x["score"] for x in b.results]


def test_determinism_tie_break_by_id_when_scores_match(db):
    # No FTS5 query → no BM25 score; tie-break is (semver DESC, id ASC).
    # claude-code agent: whisper 2.0.0, rust-serde 1.2.0, rust-tokio 0.9.0.
    r = search("agent:claude-code", db_path=db)
    ids = [x["id"] for x in r.results]
    assert ids == [
        "samuelgudi/whisper",
        "samuelgudi/rust-serde",
        "samuelgudi/rust-tokio",
    ]


# ─── Pagination ───────────────────────────────────────────────────────────

def test_limit_caps_result_count(db):
    r = search("", db_path=db, limit=2)
    assert len(r.results) == 2
    assert r.total == 4


def test_offset_skips_results(db):
    r1 = search("", db_path=db, limit=10, offset=0)
    r2 = search("", db_path=db, limit=10, offset=2)
    assert r1.results[2:] == r2.results


def test_limit_zero_raises():
    with pytest.raises(ValueError):
        search("", db_path="ignored", limit=0)


def test_negative_offset_raises():
    with pytest.raises(ValueError):
        search("", db_path="ignored", offset=-1)


# ─── Result shape ──────────────────────────────────────────────────────────

def test_result_contains_expected_fields(db):
    r = search("rust", db_path=db, limit=1)
    item = r.results[0]
    for key in [
        "id", "name", "description", "tags", "category", "agent_compat",
        "license", "version", "status", "requires", "platforms", "score",
    ]:
        assert key in item, f"missing key {key}"


def test_multi_value_fields_returned_as_lists(db):
    r = search("name:whisper", db_path=db, limit=1)
    item = r.results[0]
    assert isinstance(item["tags"], list)
    assert isinstance(item["agent_compat"], list)
    assert isinstance(item["platforms"], list)
    assert isinstance(item["requires"], list)
    assert "claude-code" in item["agent_compat"]
    assert "env_var:OPENAI_API_KEY" in item["requires"]


def test_registry_version_in_result(db):
    r = search("", db_path=db)
    assert r.registry_version == "2026-05-12T08:51:19Z"


# ─── Bite-tests ────────────────────────────────────────────────────────────

def test_special_chars_in_query_handled(db):
    # SQL injection attempt: should match literally, not break.
    r = search('"\'; DROP TABLE skills; --"', db_path=db)
    assert r.total == 0


def test_unknown_field_raises_compiler_error(db):
    with pytest.raises(CompilerError, match="unknown field"):
        search("nope:value", db_path=db)


def test_deprecated_excluded_by_default(db):
    r = search("tag:markdown", db_path=db)
    assert r.total == 0  # markdown skill is deprecated


def test_deprecated_visible_with_flag(db):
    r = search("tag:markdown", db_path=db, include_deprecated=True)
    assert [x["id"] for x in r.results] == ["samuelgudi/markdown"]
