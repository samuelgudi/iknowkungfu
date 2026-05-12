"""Tests for the query DSL parser (agent_skills.search.query).

Covers every shape from the spec § 6.3 plus adversarial inputs that try to break
the parser (empty queries, unclosed quotes, weird whitespace, bare operators,
deeply-nested groupings, unicode, very long inputs).
"""
import pytest

from agent_skills.search.query import (
    And,
    CompOp,
    Empty,
    FieldFilter,
    Not,
    Or,
    ParseError,
    Phrase,
    Prefix,
    Term,
    parse,
)


# ─── Happy-path: single terms ───────────────────────────────────────────────

def test_empty_string_returns_empty():
    assert parse("") == Empty()


def test_whitespace_only_returns_empty():
    assert parse("   \t\n  ") == Empty()


def test_single_word():
    assert parse("rust") == Term("rust")


def test_single_phrase():
    assert parse('"binary data parsing"') == Phrase("binary data parsing")


def test_phrase_with_inner_punctuation():
    assert parse('"hello, world!"') == Phrase("hello, world!")


def test_empty_phrase_allowed():
    # Empty phrase is permitted by the tokenizer; downstream layers can decide.
    assert parse('""') == Phrase("")


def test_prefix():
    assert parse("rust*") == Prefix("rust")


def test_bare_star_is_word_not_prefix():
    # A lone '*' would be Prefix('') which is meaningless — require ≥1 char.
    assert parse("*") == Term("*")


# ─── Field filters ──────────────────────────────────────────────────────────

def test_field_filter_basic():
    assert parse("tag:rust") == FieldFilter("tag", "rust")


def test_field_filter_hyphenated_value():
    # 'claude-code' has a hyphen inside; must not be parsed as negation.
    assert parse("agent:claude-code") == FieldFilter("agent", "claude-code")


def test_field_filter_with_prefix():
    assert parse("name:format*") == FieldFilter("name", "format", prefix=True)


def test_field_filter_op_gte():
    assert parse("version:>=1.0") == FieldFilter("version", "1.0", op=CompOp.GTE)


def test_field_filter_op_lte():
    assert parse("version:<=2.0") == FieldFilter("version", "2.0", op=CompOp.LTE)


def test_field_filter_op_gt():
    assert parse("version:>1.0") == FieldFilter("version", "1.0", op=CompOp.GT)


def test_field_filter_op_lt():
    assert parse("version:<2.0") == FieldFilter("version", "2.0", op=CompOp.LT)


def test_field_filter_op_eq_explicit():
    assert parse("version:1.2.0") == FieldFilter("version", "1.2.0", op=CompOp.EQ)


def test_field_filter_with_colon_value():
    # 'requires:env_var:OPENAI_API_KEY' — the parser sees field='requires',
    # value='env_var:OPENAI_API_KEY' (only first colon is the separator).
    assert parse("requires:env_var:OPENAI_API_KEY") == FieldFilter(
        "requires", "env_var:OPENAI_API_KEY"
    )


# ─── Boolean operators ──────────────────────────────────────────────────────

def test_implicit_and_between_words():
    assert parse("rust serde") == And(Term("rust"), Term("serde"))


def test_implicit_and_chains_left_associative():
    # 'a b c' → And(And(a, b), c)
    assert parse("a b c") == And(And(Term("a"), Term("b")), Term("c"))


def test_explicit_and():
    assert parse("rust AND serde") == And(Term("rust"), Term("serde"))


def test_or():
    assert parse("rust OR go") == Or(Term("rust"), Term("go"))


def test_or_has_lower_precedence_than_and():
    # 'a b OR c' should parse as (a AND b) OR c, not a AND (b OR c).
    assert parse("a b OR c") == Or(And(Term("a"), Term("b")), Term("c"))


def test_explicit_and_or_mixed():
    assert parse("a AND b OR c") == Or(And(Term("a"), Term("b")), Term("c"))


def test_not_keyword():
    assert parse("NOT deprecated") == Not(Term("deprecated"))


def test_minus_as_negation():
    assert parse("-deprecated") == Not(Term("deprecated"))


def test_minus_in_middle_of_phrase_is_implicit_and():
    # 'rust -deprecated' → AND(rust, NOT deprecated)
    assert parse("rust -deprecated") == And(Term("rust"), Not(Term("deprecated")))


def test_double_negation():
    assert parse("NOT NOT x") == Not(Not(Term("x")))


def test_negation_of_field_filter():
    assert parse("-status:deprecated") == Not(
        FieldFilter("status", "deprecated")
    )


# ─── Grouping ───────────────────────────────────────────────────────────────

def test_grouping():
    assert parse("(rust OR go)") == Or(Term("rust"), Term("go"))


def test_grouping_changes_precedence():
    # '(a OR b) AND c' should differ from 'a OR (b AND c)'.
    grouped = parse("(rust OR go) agent:claude-code")
    assert grouped == And(
        Or(Term("rust"), Term("go")),
        FieldFilter("agent", "claude-code"),
    )


def test_nested_grouping():
    assert parse("((rust))") == Term("rust")


def test_grouping_with_negation():
    # '-(a OR b)' should negate the whole group.
    assert parse("-(rust OR go)") == Not(Or(Term("rust"), Term("go")))


# ─── Real-world worked examples (from spec § 6.3) ──────────────────────────

def test_spec_example_rust_serialization():
    got = parse("rust serialization tag:rust agent:claude-code")
    expected = And(
        And(
            And(Term("rust"), Term("serialization")),
            FieldFilter("tag", "rust"),
        ),
        FieldFilter("agent", "claude-code"),
    )
    assert got == expected


def test_spec_example_phrase_exclude_deprecated():
    got = parse('"binary data parsing" -status:deprecated')
    expected = And(
        Phrase("binary data parsing"),
        Not(FieldFilter("status", "deprecated")),
    )
    assert got == expected


def test_spec_example_or_with_agent_filter():
    got = parse("(tag:rust OR tag:go) agent:claude-code")
    expected = And(
        Or(FieldFilter("tag", "rust"), FieldFilter("tag", "go")),
        FieldFilter("agent", "claude-code"),
    )
    assert got == expected


def test_spec_example_not_requires_env_var():
    got = parse("NOT requires:env_var:*")
    expected = Not(
        FieldFilter("requires", "env_var:", prefix=True)
    )
    assert got == expected


def test_spec_example_author_license():
    got = parse("author:samuelgudi license:MIT")
    expected = And(
        FieldFilter("author", "samuelgudi"),
        FieldFilter("license", "MIT"),
    )
    assert got == expected


# ─── Adversarial / bite-test cases ──────────────────────────────────────────

def test_unclosed_quote_raises():
    with pytest.raises(ParseError, match="Unclosed quote"):
        parse('"unclosed')


def test_unclosed_quote_with_more_content():
    with pytest.raises(ParseError, match="Unclosed quote"):
        parse('rust "unclosed phrase serde')


def test_unmatched_close_paren_raises():
    with pytest.raises(ParseError):
        parse("a)")


def test_unmatched_open_paren_raises():
    with pytest.raises(ParseError):
        parse("(a")


def test_bare_and_raises():
    with pytest.raises(ParseError):
        parse("AND")


def test_bare_or_raises():
    with pytest.raises(ParseError):
        parse("OR")


def test_trailing_or_raises():
    with pytest.raises(ParseError):
        parse("rust OR")


def test_double_and_raises():
    with pytest.raises(ParseError):
        parse("a AND AND b")


def test_empty_field_name_raises():
    with pytest.raises(ParseError, match="Empty field name"):
        parse(":value")


def test_empty_field_value_raises():
    with pytest.raises(ParseError, match="Empty value"):
        parse("tag:")


def test_field_only_op_marker_raises():
    # 'version:>=' has no value after the operator.
    with pytest.raises(ParseError, match="Empty value"):
        parse("version:>=")


def test_unicode_in_word():
    # Unicode is preserved; downstream tokenizer (unicode61 in FTS5) will fold.
    assert parse("café") == Term("café")


def test_unicode_in_phrase():
    assert parse('"naïve approach"') == Phrase("naïve approach")


def test_non_string_input_raises_type_error():
    with pytest.raises(TypeError):
        parse(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse(42)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse(["rust"])  # type: ignore[arg-type]


def test_lots_of_whitespace_between_terms():
    assert parse("rust    \t  serde") == And(Term("rust"), Term("serde"))


def test_leading_trailing_whitespace_stripped():
    assert parse("  rust  ") == Term("rust")


def test_case_sensitive_keywords():
    # 'and' (lowercase) is a term, not the AND operator.
    assert parse("a and b") == And(And(Term("a"), Term("and")), Term("b"))


def test_minus_in_middle_of_word_is_not_negation():
    # 'claude-code' is one word, not 'claude' minus 'code'.
    assert parse("claude-code") == Term("claude-code")


def test_minus_after_word_is_part_of_next_word():
    # Edge case: 'foo -bar' → foo AND NOT bar; but 'foo-bar' → one word.
    # The disambiguation is whitespace.
    assert parse("foo-bar") == Term("foo-bar")
    assert parse("foo -bar") == And(Term("foo"), Not(Term("bar")))


def test_minus_at_start_of_phrase():
    assert parse('-"exact phrase"') == Not(Phrase("exact phrase"))


def test_long_query_does_not_crash():
    # Sanity check: don't blow up on a deeply-implicit-AND query.
    query = " ".join(f"word{i}" for i in range(50))
    result = parse(query)
    # Left-associative AND chain — verify by counting And nodes.
    count = 0
    node = result
    while isinstance(node, And):
        count += 1
        node = node.left
    assert count == 49  # 50 words → 49 AND combinations


def test_deeply_nested_parens():
    # 'rust' wrapped in 20 paren pairs should parse to Term('rust').
    q = "(" * 20 + "rust" + ")" * 20
    assert parse(q) == Term("rust")


def test_or_in_negation_group():
    # NOT(a OR b) should distribute correctly at parse time (kept as-is in AST).
    assert parse("NOT (a OR b)") == Not(Or(Term("a"), Term("b")))


def test_field_value_with_dots():
    # Semver values commonly contain dots; must remain intact.
    assert parse("version:1.2.3-rc.4") == FieldFilter(
        "version", "1.2.3-rc.4"
    )


def test_field_value_with_slash():
    # Author IDs may include slashes (e.g. org/user format).
    assert parse("id:samuelgudi/rust-serde") == FieldFilter(
        "id", "samuelgudi/rust-serde"
    )


def test_repr_round_trip_stable():
    # Sanity: repr is deterministic for testing.
    node = parse("rust tag:rust agent:claude-code")
    assert repr(node) == repr(node)


# ─── Determinism contract ──────────────────────────────────────────────────

def test_parse_is_deterministic():
    # Same input → same AST, including across repeated parses.
    q = '(tag:rust OR tag:go) agent:claude-code "exact phrase" -status:deprecated'
    a = parse(q)
    b = parse(q)
    assert a == b
    assert repr(a) == repr(b)
