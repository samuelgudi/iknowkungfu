"""Tests for the FTS5 index builder (agent_skills.search.index).

Covers: schema correctness, multi-value field encoding, atomic rebuild,
determinism (same registry → same query results), staleness detection,
tokenizer config (diacritics folded), and adversarial inputs.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from agent_skills.search.index import (
    INDEX_SCHEMA_VERSION,
    _pipe,
    _requires_encoded,
    _tags_indexed,
    build_index,
    get_index_meta,
    is_stale,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────

def _skill(
    id: str,
    name: str = "",
    description: str = "",
    tags=None,
    agent_compat=None,
    category: str = "dev",
    license: str = "MIT",
    version: str = "0.1.0",
    status: str = "active",
    requires=None,
    platforms=None,
    author=None,
    body: str = "",
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
        "body": body,
    }


@pytest.fixture
def simple_registry():
    return {
        "schema_version": 2,
        "generated_at": "2026-05-12T08:51:19Z",
        "skills": [
            _skill(
                "samuelgudi/rust-serde",
                description="Helpers for Rust serde serialization",
                tags=["rust", "serialization", "async"],
                agent_compat=["claude-code", "openclaw"],
                category="dev",
            ),
            _skill(
                "samuelgudi/whisper-transcribe",
                description="Transcribe audio with Whisper",
                tags=["audio", "transcription", "ai"],
                agent_compat=["claude-code", "hermes"],
                category="ai",
                requires={"env_vars": ["OPENAI_API_KEY"], "commands": ["ffmpeg"]},
            ),
            _skill(
                "samuelgudi/markdown-deprecated",
                description="A deprecated Markdown helper",
                tags=["markdown", "deprecated"],
                agent_compat=["claude-code"],
                category="docs",
                status="deprecated",
            ),
        ],
    }


@pytest.fixture
def empty_registry():
    return {"schema_version": 2, "generated_at": "2026-05-12T00:00:00Z", "skills": []}


# ─── Helper assertions ──────────────────────────────────────────────────────

class _ROConnection:
    """Read-only sqlite3 wrapper that ALWAYS closes on __exit__.

    Plain `with sqlite3.connect()` only commits on exit; it does NOT close.
    On Windows that leaks a file lock that breaks subsequent rebuilds. Mirrors
    the prod-side fix in agent_skills/search/{ranker,index}.py.
    """

    def __init__(self, db_path: Path):
        self._conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    def __enter__(self) -> sqlite3.Connection:
        return self._conn

    def __exit__(self, exc_type, exc, tb) -> None:
        self._conn.close()


def _connect_ro(db_path: Path) -> _ROConnection:
    return _ROConnection(db_path)


# ─── Encoding helpers (pure functions) ──────────────────────────────────────

def test_pipe_empty_list_returns_empty_string():
    assert _pipe([]) == ""


def test_pipe_single_value():
    assert _pipe(["rust"]) == "|rust|"


def test_pipe_multiple_values():
    assert _pipe(["claude-code", "openclaw", "codex"]) == "|claude-code|openclaw|codex|"


def test_tags_indexed_space_separated():
    assert _tags_indexed(["rust", "serialization"]) == "rust serialization"


def test_tags_indexed_empty():
    assert _tags_indexed([]) == ""


def test_requires_encoded_mixed():
    out = _requires_encoded({"env_vars": ["KEY_A", "KEY_B"], "commands": ["ffmpeg"]})
    assert out == "|env_var:KEY_A|env_var:KEY_B|command:ffmpeg|"


def test_requires_encoded_empty():
    assert _requires_encoded(None) == ""
    assert _requires_encoded({}) == ""
    assert _requires_encoded({"env_vars": [], "commands": []}) == ""


# ─── build_index — basic correctness ──────────────────────────────────────

def test_build_index_creates_db_file(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    assert db.exists()
    assert db.stat().st_size > 0


def test_build_index_inserts_all_skills(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        (count,) = c.execute("SELECT COUNT(*) FROM skills").fetchone()
    assert count == 3


def test_build_index_indexed_field_is_searchable_via_fts5(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        rows = c.execute(
            "SELECT id FROM skills WHERE skills MATCH 'rust'"
        ).fetchall()
    ids = [r[0] for r in rows]
    assert "samuelgudi/rust-serde" in ids
    # 'rust' is only in rust-serde, not in others
    assert len(ids) == 1


def test_build_index_tags_searchable_via_column_query(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        rows = c.execute(
            "SELECT id FROM skills WHERE skills MATCH 'tags:audio'"
        ).fetchall()
    assert [r[0] for r in rows] == ["samuelgudi/whisper-transcribe"]


def test_build_index_unindexed_field_present_via_select(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        row = c.execute(
            "SELECT id, category, license, agent_compat, status FROM skills "
            "WHERE id = ?",
            ("samuelgudi/whisper-transcribe",),
        ).fetchone()
    assert row[0] == "samuelgudi/whisper-transcribe"
    assert row[1] == "ai"
    assert row[2] == "MIT"
    assert row[3] == "|claude-code|hermes|"
    assert row[4] == "active"


def test_build_index_requires_encoded_correctly(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        row = c.execute(
            "SELECT requires FROM skills WHERE id = ?",
            ("samuelgudi/whisper-transcribe",),
        ).fetchone()
    assert row[0] == "|env_var:OPENAI_API_KEY|command:ffmpeg|"


def test_build_index_empty_requires_is_empty_string(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        row = c.execute(
            "SELECT requires FROM skills WHERE id = ?",
            ("samuelgudi/rust-serde",),
        ).fetchone()
    assert row[0] == ""


def test_build_index_platforms_pipe_delimited(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        row = c.execute(
            "SELECT platforms FROM skills WHERE id = ?",
            ("samuelgudi/rust-serde",),
        ).fetchone()
    assert row[0] == "|linux|macos|windows|"


def test_build_index_author_split_into_login_and_id(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        row = c.execute(
            "SELECT author_login, author_id FROM skills WHERE id = ?",
            ("samuelgudi/rust-serde",),
        ).fetchone()
    assert row[0] == "tester"
    assert row[1] == "1"


# ─── build_index — atomic rebuild ──────────────────────────────────────────

def test_build_index_replaces_existing_atomically(simple_registry, empty_registry, tmp_path):
    db = tmp_path / "registry.db"
    # First build with 3 skills, then rebuild with 0.
    build_index(simple_registry, db)
    build_index(empty_registry, db)
    with _connect_ro(db) as c:
        (count,) = c.execute("SELECT COUNT(*) FROM skills").fetchone()
    assert count == 0


def test_build_index_no_leftover_tmp_file_after_success(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    leftovers = [
        p for p in tmp_path.iterdir() if p.name.startswith(".") and p.suffix == ".db"
    ]
    assert leftovers == []


def test_build_index_creates_parent_directories(simple_registry, tmp_path):
    db = tmp_path / "nested" / "deep" / "registry.db"
    build_index(simple_registry, db)
    assert db.exists()


# ─── build_index — determinism contract ────────────────────────────────────

def test_build_index_query_results_are_deterministic(simple_registry, tmp_path):
    """Building the same registry twice → identical query results in the
    same order. (Byte-identical file is harder to guarantee with SQLite,
    so this is the practical determinism contract.)"""
    db1 = tmp_path / "a.db"
    db2 = tmp_path / "b.db"
    build_index(simple_registry, db1)
    build_index(simple_registry, db2)
    with _connect_ro(db1) as c1, _connect_ro(db2) as c2:
        r1 = c1.execute(
            "SELECT id, rank FROM skills WHERE skills MATCH 'rust' ORDER BY rank"
        ).fetchall()
        r2 = c2.execute(
            "SELECT id, rank FROM skills WHERE skills MATCH 'rust' ORDER BY rank"
        ).fetchall()
    assert r1 == r2


def test_build_index_insert_order_is_id_sorted(simple_registry, tmp_path):
    """Rows inserted in lexicographic id order — verify via rowid ASC."""
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    with _connect_ro(db) as c:
        rows = c.execute("SELECT id FROM skills ORDER BY rowid ASC").fetchall()
    ids = [r[0] for r in rows]
    assert ids == sorted(ids)


# ─── build_index — tokenizer config ────────────────────────────────────────

def test_build_index_tokenizer_folds_diacritics(tmp_path):
    """unicode61 remove_diacritics 2 should fold 'é' → 'e' so queries match."""
    reg = {
        "schema_version": 2,
        "generated_at": "2026-05-12T00:00:00Z",
        "skills": [_skill("a/cafe", description="Naïve café notes")],
    }
    db = tmp_path / "registry.db"
    build_index(reg, db)
    with _connect_ro(db) as c:
        # Query without diacritics should match content with diacritics.
        rows = c.execute(
            "SELECT id FROM skills WHERE skills MATCH 'cafe'"
        ).fetchall()
    assert rows == [("a/cafe",)]


# ─── build_index — edge cases ──────────────────────────────────────────────

def test_build_index_empty_registry(empty_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(empty_registry, db)
    assert db.exists()
    with _connect_ro(db) as c:
        (count,) = c.execute("SELECT COUNT(*) FROM skills").fetchone()
    assert count == 0


def test_build_index_skill_missing_optional_fields(tmp_path):
    """Skill with only the required `id` should still index (other fields → empty)."""
    reg = {
        "schema_version": 2,
        "generated_at": "2026-05-12T00:00:00Z",
        "skills": [{"id": "minimal/skill"}],
    }
    db = tmp_path / "registry.db"
    build_index(reg, db)
    with _connect_ro(db) as c:
        row = c.execute(
            "SELECT id, name, description, tags, category, license, "
            "agent_compat, requires, platforms FROM skills"
        ).fetchone()
    assert row == ("minimal/skill", "", "", "", "", "", "", "", "")


def test_build_index_raises_on_registry_without_skills_key(tmp_path):
    db = tmp_path / "registry.db"
    with pytest.raises(ValueError, match="skills"):
        build_index({"schema_version": 2}, db)


def test_build_index_handles_special_chars_in_fields(tmp_path):
    reg = {
        "schema_version": 2,
        "generated_at": "2026-05-12T00:00:00Z",
        "skills": [
            _skill(
                "a/special",
                description='SQL "injection" \'test\' and \\backslash',
                tags=["test'tag", 'tag"with"quote'],
            )
        ],
    }
    db = tmp_path / "registry.db"
    build_index(reg, db)
    with _connect_ro(db) as c:
        row = c.execute("SELECT description FROM skills").fetchone()
    assert "injection" in row[0]


# ─── Meta & staleness ──────────────────────────────────────────────────────

def test_get_index_meta_returns_expected_keys(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    meta = get_index_meta(db)
    assert meta["registry_generated_at"] == "2026-05-12T08:51:19Z"
    assert meta["registry_schema_version"] == "2"
    assert meta["index_schema_version"] == str(INDEX_SCHEMA_VERSION)
    assert meta["row_count"] == "3"
    assert meta["tokenizer"] == "unicode61 remove_diacritics 2"


def test_get_index_meta_missing_file_returns_empty(tmp_path):
    assert get_index_meta(tmp_path / "nope.db") == {}


def test_get_index_meta_corrupt_db_returns_empty(tmp_path):
    db = tmp_path / "garbage.db"
    db.write_bytes(b"not a sqlite database")
    assert get_index_meta(db) == {}


def test_is_stale_missing_file(tmp_path):
    assert is_stale(tmp_path / "nope.db", "2026-05-12T00:00:00Z") is True


def test_is_stale_matching_version(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    assert is_stale(db, "2026-05-12T08:51:19Z") is False


def test_is_stale_different_version(simple_registry, tmp_path):
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    assert is_stale(db, "2026-05-13T00:00:00Z") is True


def test_is_stale_corrupt_db(tmp_path):
    db = tmp_path / "garbage.db"
    db.write_bytes(b"not a sqlite database")
    assert is_stale(db, "anything") is True


def test_is_stale_when_index_schema_version_changes(simple_registry, tmp_path, monkeypatch):
    """If we ever bump INDEX_SCHEMA_VERSION, existing indexes are stale."""
    db = tmp_path / "registry.db"
    build_index(simple_registry, db)
    # Simulate: a future version of the code expects schema_version=2.
    import agent_skills.search.index as idx
    monkeypatch.setattr(idx, "INDEX_SCHEMA_VERSION", idx.INDEX_SCHEMA_VERSION + 99)
    assert idx.is_stale(db, "2026-05-12T08:51:19Z") is True


# ─── Integration with the real registry.json (smoke) ───────────────────────

def test_build_index_works_with_real_registry_json(tmp_path):
    """Smoke test against the actual registry.json shipped in the repo."""
    real = Path(__file__).parent.parent / "registry.json"
    if not real.exists():
        pytest.skip("registry.json not present")
    with real.open() as f:
        registry = json.load(f)
    db = tmp_path / "registry.db"
    build_index(registry, db)
    with _connect_ro(db) as c:
        (count,) = c.execute("SELECT COUNT(*) FROM skills").fetchone()
    assert count == len(registry["skills"])
