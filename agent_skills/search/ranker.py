"""Search runner.

Combines the query DSL parser (search.query) with the FTS5 index
(search.index) to produce ranked, deterministic search results.

Determinism contract (see spec § 6.4):
- BM25 scoring is deterministic.
- Tie-breaks: (score ASC, semver tuple DESC, id ASC).
- Tokenizer is fixed in the index (unicode61 remove_diacritics 2).
- Result list is byte-identical given identical (registry_version, query).

V1 scope:
- All search-style terms (Term, Phrase, Prefix, FieldFilter on indexed columns)
  go through FTS5's MATCH clause and contribute to BM25 ranking.
- FieldFilters on UNINDEXED columns go through SQL WHERE.
- Version-range filters are applied as post-filters in Python (FTS5 / SQL
  can't compare semver strings reliably).
- Boolean structure: AND mixes FTS5 and SQL freely. OR works within FTS5
  or within SQL, but mixed-OR (one indexed branch + one unindexed branch)
  raises CompilerError — UNION support is deferred.
- NOT works on leaves and well-typed subexpressions.

See spec § 7 D1, D5.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_skills.search.query import (
    And,
    CompOp,
    Empty,
    FieldFilter,
    Node,
    Not,
    Or,
    Phrase,
    Prefix,
    Term,
    parse,
)


# Fields that live in FTS5-indexed columns. Use FTS5 column-query syntax for these.
# Maps DSL field name → FTS5 column name. `tag` is the documented DSL spelling
# (matching SPEC § 6.2) while the underlying FTS5 column is `tags` — keep both
# in sync if either is renamed.
_INDEXED_FIELDS: dict[str, str] = {
    "name": "name",
    "description": "description",
    "tag": "tags",
    "tags": "tags",
    "body": "body",
}

# Fields that go through SQL WHERE. Maps DSL field name → (column, kind).
# kind ∈ {'exact', 'prefix', 'pipe', 'version'}
_UNINDEXED_FIELDS: dict[str, tuple[str, str]] = {
    "id": ("id", "exact"),
    "category": ("category", "exact"),
    "agent": ("agent_compat", "pipe"),
    "license": ("license", "exact"),
    "author": ("author_login", "exact"),
    "version": ("version", "version"),
    "status": ("status", "exact"),
    "requires": ("requires", "pipe"),
    "platform": ("platforms", "pipe"),
}


class CompilerError(NotImplementedError):
    """Query shape not supported by the v1 compiler."""


# ─── Compiled-query representation ──────────────────────────────────────────

@dataclass(frozen=True)
class Compiled:
    """Result of compiling an AST node.

    `kind`:
      'empty'      — node contributes no filter
      'fts5'       — positive FTS5 MATCH only (in `fts5`)
      'fts5_anti'  — negative FTS5 only (in `fts5_anti`); applied via
                     `rowid NOT IN (SELECT rowid FROM skills WHERE skills MATCH ?)`.
                     Required because FTS5 'NOT' is a BINARY operator —
                     a bare `NOT X` is a SQLite syntax error.
      'sql'        — SQL WHERE only (in `sql`/`params`)
      'both'       — any combination of fts5 + fts5_anti + sql; combined with
                     AND in the final query.
    """
    kind: str
    fts5: str = ""
    fts5_anti: str = ""
    sql: str = ""
    params: tuple[Any, ...] = field(default_factory=tuple)
    version_filter: tuple[str, CompOp, str] | None = None
    # version_filter = (column_name, op, value) — applied in Python post-fetch


# ─── Helpers ────────────────────────────────────────────────────────────────

def _escape_fts5_term(term: str) -> str:
    """Escape a free-text term for an FTS5 MATCH clause.

    FTS5 supports double-quoting to escape special chars; inner double quotes
    are doubled. This produces a phrase-literal of one token, which behaves
    as a single search term."""
    return '"' + term.replace('"', '""') + '"'


def _escape_like(value: str) -> str:
    """Escape SQL LIKE metacharacters in a user-supplied value.

    Without this, `agent:%` silently matches every row (the `%` is treated
    as a wildcard in the LIKE pattern we synthesize). With ESCAPE '\\\\'
    set on the LIKE clause, the escaped chars become literals.
    """
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _semver_tuple(version: str) -> tuple[int, ...]:
    """Parse a semver-ish string into a comparable int tuple. Components beyond
    MAJOR.MINOR.PATCH (e.g. pre-release tags) are stripped — pre-release sort
    order is a v2 concern."""
    m = re.match(r"^(\d+)\.(\d+)(?:\.(\d+))?", version or "")
    if not m:
        return (0, 0, 0)
    return tuple(int(x or 0) for x in m.groups())


def _semver_sort_key(version: str) -> tuple[int, ...]:
    """Tuple for descending semver sort: negate components so ASC sort puts
    higher versions first."""
    return tuple(-c for c in _semver_tuple(version))


def _check_version(value: str, op: CompOp, target: str) -> bool:
    v = _semver_tuple(value)
    t = _semver_tuple(target)
    if op is CompOp.EQ:
        return v == t
    if op is CompOp.GTE:
        return v >= t
    if op is CompOp.LTE:
        return v <= t
    if op is CompOp.GT:
        return v > t
    if op is CompOp.LT:
        return v < t
    raise ValueError(f"unsupported comparison op {op!r}")


# ─── AST → Compiled translator ──────────────────────────────────────────────

def _compile(node: Node) -> Compiled:
    if isinstance(node, Empty):
        return Compiled(kind="empty")

    if isinstance(node, Term):
        return Compiled(kind="fts5", fts5=_escape_fts5_term(node.text))

    if isinstance(node, Phrase):
        # FTS5 phrase queries use double quotes naturally.
        return Compiled(kind="fts5", fts5=_escape_fts5_term(node.text))

    if isinstance(node, Prefix):
        # FTS5 prefix syntax: `term*` (no quotes around the prefix part).
        # Escape internal quotes by removing them — FTS5 doesn't support
        # quoted prefix queries.
        safe = re.sub(r'[^A-Za-z0-9_]', '', node.text)
        if not safe:
            raise CompilerError(
                f"Prefix {node.text!r} has no alphanumeric chars after escape"
            )
        return Compiled(kind="fts5", fts5=f"{safe}*")

    if isinstance(node, FieldFilter):
        return _compile_field(node)

    if isinstance(node, Not):
        return _compile_not(node)

    if isinstance(node, And):
        return _compile_and(node)

    if isinstance(node, Or):
        return _compile_or(node)

    raise CompilerError(f"unknown AST node type: {type(node).__name__}")


def _compile_field(node: FieldFilter) -> Compiled:
    if node.field in _INDEXED_FIELDS:
        column = _INDEXED_FIELDS[node.field]
        # FTS5 column-specific query: `column:value` (no quotes for token).
        # Quotes break column-prefix parsing in FTS5, so we use the bare value.
        # Hyphenated values get tokenized; this is documented behavior.
        if node.op is not CompOp.EQ:
            raise CompilerError(
                f"comparison operators are not supported on indexed field "
                f"{node.field!r}"
            )
        v = re.sub(r'[^A-Za-z0-9_]', ' ', node.value).strip()
        if not v:
            raise CompilerError(
                f"value {node.value!r} for field {node.field!r} reduces to empty after escaping"
            )
        # Use phrase form so multi-token values match as a phrase.
        v_quoted = '"' + v + '"'
        fragment = f"{column}:{v_quoted}"
        if node.prefix:
            # Prefix on indexed columns: use raw prefix (no quotes).
            safe = re.sub(r'[^A-Za-z0-9_]', '', node.value)
            if not safe:
                raise CompilerError(f"prefix {node.value!r} reduces to empty")
            fragment = f"{column}:{safe}*"
        return Compiled(kind="fts5", fts5=fragment)

    if node.field not in _UNINDEXED_FIELDS:
        raise CompilerError(f"unknown field: {node.field!r}")

    col, kind = _UNINDEXED_FIELDS[node.field]

    if kind == "version":
        if node.op is CompOp.EQ and not node.prefix:
            return Compiled(kind="sql", sql=f"{col} = ?", params=(node.value,))
        # Other ops applied as post-filter (semver-aware).
        return Compiled(
            kind="sql",
            sql="1=1",  # placeholder — real filtering happens in Python
            version_filter=(col, node.op, node.value),
        )

    if kind == "pipe":
        # Multi-value pipe-delimited column: `LIKE '%|value|%'`.
        # User-supplied `%` and `_` are escaped — without this, `agent:%`
        # would match every row (review finding #3).
        escaped = _escape_like(node.value)
        if node.prefix:
            return Compiled(
                kind="sql",
                sql=f"{col} LIKE ? ESCAPE '\\'",
                params=(f"%|{escaped}%",),
            )
        return Compiled(
            kind="sql",
            sql=f"{col} LIKE ? ESCAPE '\\'",
            params=(f"%|{escaped}|%",),
        )

    # 'exact' or 'prefix'
    if node.prefix:
        return Compiled(
            kind="sql",
            sql=f"{col} LIKE ? ESCAPE '\\'",
            params=(f"{_escape_like(node.value)}%",),
        )
    return Compiled(kind="sql", sql=f"{col} = ?", params=(node.value,))


def _compile_not(node: Not) -> Compiled:
    inner = _compile(node.inner)
    if inner.kind == "empty":
        return inner
    if inner.kind == "fts5":
        # FTS5 'NOT' is BINARY (<expr1> NOT <expr2>), so bare `NOT X` would
        # be a syntax error. Route negation through a separate `rowid NOT IN`
        # subquery, or combine into FTS5 binary NOT in _combine_compiled
        # when paired with a positive FTS5 expression.
        return Compiled(kind="fts5_anti", fts5_anti=inner.fts5)
    if inner.kind == "fts5_anti":
        # Double negation: NOT NOT X → X.
        return Compiled(kind="fts5", fts5=inner.fts5_anti)
    if inner.kind == "sql":
        return Compiled(
            kind="sql",
            sql=f"NOT ({inner.sql})",
            params=inner.params,
            version_filter=inner.version_filter,
        )
    raise CompilerError(
        "NOT of a mixed FTS5+SQL subexpression is not supported in v1"
    )


def _combine_fts5(a: str, b: str, op: str) -> str:
    if not a:
        return b
    if not b:
        return a
    return f"({a}) {op} ({b})"


def _combine_sql(a: str, b: str, op: str) -> str:
    if not a or a == "1=1":
        return b
    if not b or b == "1=1":
        return a
    return f"({a}) {op} ({b})"


def _compile_and(node: And) -> Compiled:
    left = _compile(node.left)
    right = _compile(node.right)
    return _combine_compiled(left, right, "AND")


def _compile_or(node: Or) -> Compiled:
    left = _compile(node.left)
    right = _compile(node.right)
    return _combine_compiled(left, right, "OR")


def _is_fts5_kind(kind: str) -> bool:
    """fts5 or fts5_anti — both live in the FTS5 'side' of the world."""
    return kind in {"fts5", "fts5_anti"}


def _is_sql_kind(kind: str) -> bool:
    return kind == "sql"


def _combine_compiled(left: Compiled, right: Compiled, op: str) -> Compiled:
    if left.kind == "empty":
        return right
    if right.kind == "empty":
        return left

    # OR cannot mix FTS5 and SQL branches in v1. With fts5_anti added, the
    # rule extends: OR involving an anti against an SQL or 'both' kind is
    # also rejected. OR of two antis IS supported (DeMorgan: NOT A OR NOT B
    # = NOT (A AND B)).
    if op == "OR":
        left_is_fts5 = _is_fts5_kind(left.kind)
        right_is_fts5 = _is_fts5_kind(right.kind)
        if (left_is_fts5 and right.kind == "sql") or (
            right_is_fts5 and left.kind == "sql"
        ):
            raise CompilerError(
                "OR across FTS5 (indexed) and SQL (unindexed) fields is not "
                "supported in v1. Split the query, or contact maintainers if "
                "you need UNION support."
            )
        if left.kind == "both" or right.kind == "both":
            raise CompilerError(
                "OR with a mixed FTS5+SQL subexpression is not supported in v1."
            )

    # Version filter combination: AND merges; OR with two distinct version
    # filters would require splitting the result set.
    new_vf = left.version_filter or right.version_filter
    if (
        left.version_filter
        and right.version_filter
        and (left.version_filter != right.version_filter)
        and op == "OR"
    ):
        raise CompilerError("OR of two distinct version-range filters not supported")

    # ── Pure FTS5 combinations ────────────────────────────────────────────
    if left.kind == "fts5" and right.kind == "fts5":
        return Compiled(kind="fts5", fts5=_combine_fts5(left.fts5, right.fts5, op))

    if op == "AND":
        # fts5 AND fts5_anti → collapse into FTS5 binary NOT: `(pos) NOT (anti)`
        if left.kind == "fts5" and right.kind == "fts5_anti":
            return Compiled(kind="fts5", fts5=f"({left.fts5}) NOT ({right.fts5_anti})")
        if right.kind == "fts5" and left.kind == "fts5_anti":
            return Compiled(kind="fts5", fts5=f"({right.fts5}) NOT ({left.fts5_anti})")
        # fts5_anti AND fts5_anti → DeMorgan: NOT A AND NOT B = NOT (A OR B)
        if left.kind == "fts5_anti" and right.kind == "fts5_anti":
            return Compiled(
                kind="fts5_anti",
                fts5_anti=f"({left.fts5_anti}) OR ({right.fts5_anti})",
            )
    elif op == "OR":
        # fts5_anti OR fts5_anti → DeMorgan: NOT A OR NOT B = NOT (A AND B)
        if left.kind == "fts5_anti" and right.kind == "fts5_anti":
            return Compiled(
                kind="fts5_anti",
                fts5_anti=f"({left.fts5_anti}) AND ({right.fts5_anti})",
            )
        # fts5 OR fts5_anti within FTS5 land: emit `pos OR (rowid NOT IN anti)` —
        # but rowid NOT IN can't live inside an FTS5 MATCH expression. Reject.
        if left.kind == "fts5_anti" or right.kind == "fts5_anti":
            raise CompilerError(
                "OR with a negated FTS5 subexpression is not supported in v1. "
                "Workaround: use AND with negation (`A -B`) or split the query."
            )

    # ── Pure SQL ──────────────────────────────────────────────────────────
    if left.kind == "sql" and right.kind == "sql":
        return Compiled(
            kind="sql",
            sql=_combine_sql(left.sql, right.sql, op),
            params=left.params + right.params,
            version_filter=new_vf,
        )

    # ── Mixed AND: FTS5 (pos and/or anti) + SQL → kind='both' ─────────────
    # Collect FTS5 positive + anti parts from each side.
    def _fts5_parts(c: Compiled) -> tuple[str, str]:
        return (c.fts5, c.fts5_anti)

    l_pos, l_anti = _fts5_parts(left)
    r_pos, r_anti = _fts5_parts(right)
    new_pos = _combine_fts5(l_pos, r_pos, "AND")
    new_anti = _combine_fts5(l_anti, r_anti, "OR")  # DeMorgan again
    # If we have both pos and anti, collapse into binary NOT.
    if new_pos and new_anti:
        new_pos = f"({new_pos}) NOT ({new_anti})"
        new_anti = ""

    sql_l = left.sql if left.kind in ("sql", "both") else ""
    sql_r = right.sql if right.kind in ("sql", "both") else ""
    new_sql = _combine_sql(sql_l, sql_r, "AND")

    return Compiled(
        kind="both",
        fts5=new_pos,
        fts5_anti=new_anti,
        sql=new_sql,
        params=left.params + right.params,
        version_filter=new_vf,
    )


# ─── Public API ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SearchResult:
    total: int
    offset: int
    limit: int
    registry_version: str
    results: tuple[dict[str, Any], ...]


_RESULT_COLUMNS = (
    "id",
    "name",
    "description",
    "tags",
    "category",
    "agent_compat",
    "license",
    "author_login",
    "author_id",
    "version",
    "status",
    "requires",
    "platforms",
)


def search(
    query: str,
    *,
    db_path: Path,
    limit: int = 20,
    offset: int = 0,
    include_deprecated: bool = False,
) -> SearchResult:
    """Execute a search query against the FTS5 index.

    Determinism: same (db file, query) → identical result list.

    Yank handling: yanks live in a separate ``yanks.json`` overlay (per
    SCHEMA.md § 7) that is not yet consulted here. When yank-overlay
    integration lands, a ``yanks_overlay`` parameter will be added rather
    than the previous ``include_yanked`` flag, which was dead code.
    """
    if limit < 1:
        raise ValueError("limit must be ≥ 1")
    if offset < 0:
        raise ValueError("offset must be ≥ 0")

    ast = parse(query)
    compiled = _compile(ast)

    # Build the SQL.
    select_cols = ", ".join(_RESULT_COLUMNS)
    base_where: list[str] = []
    base_params: list[Any] = []
    has_fts5 = compiled.kind in {"fts5", "both"} and bool(compiled.fts5)
    has_fts5_anti = bool(compiled.fts5_anti)
    has_sql = (
        compiled.kind in {"sql", "both"}
        and bool(compiled.sql)
        and compiled.sql != "1=1"
    )

    if has_fts5:
        base_where.append("skills MATCH ?")
        base_params.append(compiled.fts5)
    if has_fts5_anti:
        # FTS5 NOT is binary — a bare negation must be expressed as an
        # anti-subquery. Always applied via rowid: exclude rows whose rowid
        # matches the anti FTS5 expression.
        base_where.append(
            "rowid NOT IN (SELECT rowid FROM skills WHERE skills MATCH ?)"
        )
        base_params.append(compiled.fts5_anti)
    if has_sql:
        # Wrap the user clause in parens — preserves OR semantics when AND'd
        # with the deprecated/yanked filters below. Without this, SQL's
        # AND > OR precedence pulls the deprecated filter inside one OR branch.
        base_where.append(f"({compiled.sql})")
        base_params.extend(compiled.params)
    if not include_deprecated:
        base_where.append("status != 'deprecated'")

    where_clause = " AND ".join(base_where) if base_where else "1=1"
    order_clause = (
        "bm25(skills), version DESC, id ASC"
        if has_fts5
        else "version DESC, id ASC"
    )

    sql_query = (
        f"SELECT {select_cols}"
        + (", bm25(skills) AS score" if has_fts5 else "")
        + f" FROM skills WHERE {where_clause}"
        + f" ORDER BY {order_clause}"
    )

    # Note: `with sqlite3.connect()` only commits on exit, it does NOT close
    # the connection. On Windows that leaks a file lock and breaks subsequent
    # os.replace() rebuilds of the same db. Explicit close in finally is required.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.row_factory = sqlite3.Row
        rows = list(conn.execute(sql_query, base_params))
        registry_version_row = conn.execute(
            "SELECT value FROM skills_meta WHERE key = 'registry_generated_at'"
        ).fetchone()
    finally:
        conn.close()
    registry_version = registry_version_row[0] if registry_version_row else ""

    # Post-filter: version-range comparison.
    if compiled.version_filter is not None:
        col, op, target = compiled.version_filter
        rows = [r for r in rows if _check_version(r[col], op, target)]

    # Stable tie-break secondary sort: when scores tie, use semver DESC then id ASC.
    if has_fts5:
        rows.sort(key=lambda r: (r["score"], _semver_sort_key(r["version"]), r["id"]))
    else:
        rows.sort(key=lambda r: (_semver_sort_key(r["version"]), r["id"]))

    total = len(rows)
    window = rows[offset : offset + limit]

    def _row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
        d = {c: r[c] for c in _RESULT_COLUMNS}
        d["agent_compat"] = _split_pipe(r["agent_compat"])
        d["platforms"] = _split_pipe(r["platforms"])
        d["requires"] = _split_pipe(r["requires"])
        d["tags"] = r["tags"].split(" ") if r["tags"] else []
        if has_fts5:
            d["score"] = round(float(r["score"]), 4)
        return d

    return SearchResult(
        total=total,
        offset=offset,
        limit=limit,
        registry_version=registry_version,
        results=tuple(_row_to_dict(r) for r in window),
    )


def _split_pipe(s: str) -> list[str]:
    if not s:
        return []
    return [p for p in s.split("|") if p]
