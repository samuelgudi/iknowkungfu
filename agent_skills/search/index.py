"""FTS5 index builder.

Builds a SQLite FTS5 index from registry.json. Schema is deterministic — same
input registry → same query results across machines and Python versions. Build
is atomic via temp-write + rename.

See docs/superpowers/specs/2026-05-12-mcp-and-search-design.md § 4, § 7 D1.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

# Schema version of THIS module's output. Bump when the table layout changes
# in a way that requires a rebuild on existing installations.
INDEX_SCHEMA_VERSION = 1

# Fixed tokenizer config. Determinism contract: do not change without bumping
# INDEX_SCHEMA_VERSION.
_TOKENIZER = "unicode61 remove_diacritics 2"


_DDL = f"""
CREATE VIRTUAL TABLE skills USING fts5(
    name,
    description,
    tags,
    body,
    id UNINDEXED,
    category UNINDEXED,
    agent_compat UNINDEXED,
    license UNINDEXED,
    author_login UNINDEXED,
    author_id UNINDEXED,
    version UNINDEXED,
    status UNINDEXED,
    requires UNINDEXED,
    platforms UNINDEXED,
    tokenize='{_TOKENIZER}'
);

CREATE TABLE skills_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


# ─── Encoding helpers (multi-value fields) ──────────────────────────────────

def _pipe(values: list[str]) -> str:
    """Encode a list of exact-match values as pipe-delimited string with
    leading/trailing pipes. Enables reliable LIKE '%|value|%' filters in B3."""
    if not values:
        return ""
    return "|" + "|".join(values) + "|"


def _tags_indexed(tags: list[str]) -> str:
    """Encode tags for the FTS5-indexed `tags` column: space-separated so each
    tag is a separate token. Tags are lowercase per SCHEMA.md."""
    return " ".join(tags)


def _requires_encoded(requires: dict[str, list[str]] | None) -> str:
    """Encode `requires` as pipe-delimited tagged values:
        env_vars=['A','B'], commands=['c'] → '|env_var:A|env_var:B|command:c|'
    This shape is what the query DSL `requires:env_var:A` matches against."""
    if not requires:
        return ""
    parts: list[str] = []
    for ev in requires.get("env_vars") or []:
        parts.append(f"env_var:{ev}")
    for cmd in requires.get("commands") or []:
        parts.append(f"command:{cmd}")
    return _pipe(parts)


def _skill_row(skill: dict[str, Any]) -> tuple[Any, ...]:
    """Project a registry skill entry onto the FTS5 row tuple, with stable
    column order matching _DDL. Missing optional fields → empty strings."""
    author = skill.get("author") or {}
    return (
        # FTS5-indexed columns
        skill.get("name", ""),
        skill.get("description", ""),
        _tags_indexed(skill.get("tags") or []),
        skill.get("body", ""),
        # UNINDEXED filter columns
        skill["id"],  # required by schema
        skill.get("category", ""),
        _pipe(skill.get("agent_compat") or []),
        skill.get("license", ""),
        author.get("github_login", ""),
        str(author.get("github_id", "")),
        skill.get("version", ""),
        skill.get("status", ""),
        _requires_encoded(skill.get("requires")),
        _pipe(skill.get("platforms") or []),
    )


# ─── Build + staleness ──────────────────────────────────────────────────────

def build_index(registry: dict[str, Any], db_path: Path) -> None:
    """Build a fresh FTS5 index at `db_path` from a registry dict.

    Writes to a sibling temp file then atomically renames onto `db_path`. The
    existing index (if any) is replaced as a single filesystem operation.

    The insert order is deterministic: rows are inserted in `id` lexicographic
    ASC order. FTS5 BM25 scoring does not depend on insert order, but this
    keeps the index byte-shape stable across rebuilds where possible.
    """
    if "skills" not in registry:
        raise ValueError("registry must contain a 'skills' key")
    generated_at = registry.get("generated_at", "")
    schema_version_src = registry.get("schema_version", "")

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Build into a sibling temp file, then atomic rename.
    with tempfile.NamedTemporaryFile(
        dir=str(db_path.parent),
        delete=False,
        prefix=f".{db_path.name}.tmp.",
        suffix=".db",
    ) as tf:
        tmp_path = Path(tf.name)
    # Close the file descriptor before SQLite opens the path.

    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(tmp_path))
        conn.executescript(_DDL)
        skills = sorted(registry["skills"], key=lambda s: s["id"])
        conn.executemany(
            """
            INSERT INTO skills (
                name, description, tags, body,
                id, category, agent_compat, license,
                author_login, author_id, version, status,
                requires, platforms
            ) VALUES (?, ?, ?, ?,  ?, ?, ?, ?,  ?, ?, ?, ?,  ?, ?)
            """,
            (_skill_row(s) for s in skills),
        )
        meta_rows = [
            ("registry_generated_at", str(generated_at)),
            ("registry_schema_version", str(schema_version_src)),
            ("index_schema_version", str(INDEX_SCHEMA_VERSION)),
            ("row_count", str(len(skills))),
            ("tokenizer", _TOKENIZER),
        ]
        conn.executemany(
            "INSERT INTO skills_meta (key, value) VALUES (?, ?)", meta_rows
        )
        conn.commit()
        # Best-effort: optimize the FTS5 index for query performance. Failure
        # is tolerable (the index is still correct).
        try:
            conn.execute("INSERT INTO skills(skills) VALUES('optimize')")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    finally:
        if conn is not None:
            conn.close()

    # SQLite already fsynced on commit. os.replace is atomic on the same
    # volume across platforms (Windows, POSIX). The manual post-close fsync
    # we'd add here is platform-fragile (Windows rejects fsync on a path-
    # opened RO descriptor with EBADF) and SQLite's durability is sufficient.
    os.replace(str(tmp_path), str(db_path))


def get_index_meta(db_path: Path) -> dict[str, str]:
    """Return the skills_meta table as a dict. Empty dict if file missing or
    not a valid index.

    Explicit close (not `with`) — sqlite3's context manager only commits on
    exit, it does NOT close the connection. On Windows that leaks a file
    lock and breaks subsequent rebuilds.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return {}
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.execute("SELECT key, value FROM skills_meta")
        return dict(cur.fetchall())
    except sqlite3.DatabaseError:
        return {}
    finally:
        if conn is not None:
            conn.close()


def is_stale(db_path: Path, registry_generated_at: str) -> bool:
    """True if the index is missing, corrupt, or built from a different
    registry version than `registry_generated_at`.

    Strategy: comparison is exact-string on the `generated_at` ISO timestamp.
    Since registry.json's `generated_at` is the commit timestamp (per
    SCHEMA.md § 2), exact equality is the right notion of "same version" —
    no parsing or timezone math required.
    """
    meta = get_index_meta(db_path)
    if not meta:
        return True
    if meta.get("index_schema_version") != str(INDEX_SCHEMA_VERSION):
        return True
    return meta.get("registry_generated_at") != registry_generated_at
