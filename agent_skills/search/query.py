"""Query DSL parser.

Grammar (precedence low → high):
    expr     := or_expr
    or_expr  := and_expr ('OR' and_expr)*
    and_expr := unary (('AND' | <implicit>) unary)*
    unary    := 'NOT' unary | '-' unary | atom
    atom     := phrase | field_filter | prefix | word | '(' expr ')'

Examples (see SPEC § 6.3):
    rust serialization
    tag:rust agent:claude-code
    "binary data parsing" -status:deprecated
    name:format* version:>=1.0
    (tag:rust OR tag:go) agent:claude-code
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union


class CompOp(str, Enum):
    """Comparison operator for field filters (version ranges, etc.)."""
    EQ = "eq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"


@dataclass(frozen=True)
class Empty:
    """Empty query (whitespace / no terms)."""

    def __repr__(self) -> str:
        return "Empty()"


@dataclass(frozen=True)
class Term:
    """Free-text word matched against name/description/body."""
    text: str

    def __repr__(self) -> str:
        return f"Term({self.text!r})"


@dataclass(frozen=True)
class Phrase:
    """Exact phrase match (quoted in source)."""
    text: str

    def __repr__(self) -> str:
        return f"Phrase({self.text!r})"


@dataclass(frozen=True)
class Prefix:
    """Prefix match in free-text fields (e.g. `rust*`)."""
    text: str  # without the trailing '*'

    def __repr__(self) -> str:
        return f"Prefix({self.text!r})"


@dataclass(frozen=True)
class FieldFilter:
    """field:value filter. `prefix=True` for `field:value*`."""
    field: str
    value: str
    op: CompOp = CompOp.EQ
    prefix: bool = False

    def __repr__(self) -> str:
        op = "" if self.op is CompOp.EQ else f", op={self.op.value!r}"
        pfx = ", prefix=True" if self.prefix else ""
        return f"FieldFilter({self.field!r}, {self.value!r}{op}{pfx})"


@dataclass(frozen=True)
class Not:
    inner: "Node"

    def __repr__(self) -> str:
        return f"Not({self.inner!r})"


@dataclass(frozen=True)
class And:
    left: "Node"
    right: "Node"

    def __repr__(self) -> str:
        return f"And({self.left!r}, {self.right!r})"


@dataclass(frozen=True)
class Or:
    left: "Node"
    right: "Node"

    def __repr__(self) -> str:
        return f"Or({self.left!r}, {self.right!r})"


Node = Union[Empty, Term, Phrase, Prefix, FieldFilter, Not, And, Or]


class ParseError(ValueError):
    """Raised when the query string cannot be parsed."""


# ─── Tokenizer ──────────────────────────────────────────────────────────────

_KEYWORDS = {"AND", "OR", "NOT"}
_COMP_OPS = (
    (">=", CompOp.GTE),
    ("<=", CompOp.LTE),
    (">", CompOp.GT),
    ("<", CompOp.LT),
)


@dataclass(frozen=True)
class _Token:
    kind: str  # WORD, PHRASE, FIELD, LPAREN, RPAREN, MINUS, AND, OR, NOT, EOF
    value: object  # str for most; tuple for FIELD: (field, value, op, prefix)
    pos: int  # start position in source (for error messages)


def _tokenize(query: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    n = len(query)
    while i < n:
        c = query[i]
        if c.isspace():
            i += 1
            continue
        if c == '"':
            # Phrase — read until closing quote
            j = i + 1
            while j < n and query[j] != '"':
                j += 1
            if j >= n:
                raise ParseError(f"Unclosed quote at position {i}")
            tokens.append(_Token("PHRASE", query[i + 1 : j], i))
            i = j + 1
            continue
        if c == "(":
            tokens.append(_Token("LPAREN", "(", i))
            i += 1
            continue
        if c == ")":
            tokens.append(_Token("RPAREN", ")", i))
            i += 1
            continue
        if c == "-":
            # We reach this branch only at a token boundary (whitespace was just
            # consumed, or i == 0). So '-' here is always the negation prefix.
            # Hyphens INSIDE words (e.g. 'claude-code') are read by the word
            # loop below and never reach this check.
            tokens.append(_Token("MINUS", "-", i))
            i += 1
            continue
        # Read word — anything not whitespace, not paren, not quote
        start = i
        while i < n and not query[i].isspace() and query[i] not in '"()':
            i += 1
        word = query[start:i]
        # Boolean keyword (uppercase only, exact match)
        if word in _KEYWORDS:
            tokens.append(_Token(word, word, start))
            continue
        # Field filter: any ':' makes this a field expression.
        if ":" in word:
            field, _, raw_value = word.partition(":")
            if not field:
                raise ParseError(f"Empty field name at position {start}")
            value = raw_value
            op = CompOp.EQ
            for op_str, op_enum in _COMP_OPS:
                if value.startswith(op_str):
                    op = op_enum
                    value = value[len(op_str) :]
                    break
            if not value:
                raise ParseError(
                    f"Empty value for field {field!r} at position {start}"
                )
            is_prefix = value.endswith("*") and len(value) > 1
            if is_prefix:
                value = value[:-1]
            tokens.append(
                _Token("FIELD", (field, value, op, is_prefix), start)
            )
            continue
        # Bare word — check prefix marker
        is_prefix = word.endswith("*") and len(word) > 1
        if is_prefix:
            tokens.append(_Token("PREFIX", word[:-1], start))
        else:
            tokens.append(_Token("WORD", word, start))
    tokens.append(_Token("EOF", None, n))
    return tokens


# ─── Parser ─────────────────────────────────────────────────────────────────

class _Parser:
    def __init__(self, tokens: list[_Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> _Token:
        return self.tokens[self.pos]

    def _advance(self) -> _Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def _expect(self, kind: str) -> _Token:
        t = self._peek()
        if t.kind != kind:
            raise ParseError(
                f"Expected {kind} at position {t.pos}, got {t.kind} ({t.value!r})"
            )
        return self._advance()

    def parse(self) -> Node:
        if self._peek().kind == "EOF":
            return Empty()
        node = self._or_expr()
        if self._peek().kind != "EOF":
            t = self._peek()
            raise ParseError(
                f"Unexpected {t.kind} ({t.value!r}) at position {t.pos}"
            )
        return node

    def _or_expr(self) -> Node:
        node = self._and_expr()
        while self._peek().kind == "OR":
            self._advance()
            right = self._and_expr()
            node = Or(node, right)
        return node

    def _and_expr(self) -> Node:
        node = self._unary()
        while True:
            t = self._peek()
            if t.kind == "AND":
                self._advance()
                node = And(node, self._unary())
            elif t.kind in {"EOF", "RPAREN", "OR"}:
                break
            else:
                # Implicit AND between adjacent terms
                node = And(node, self._unary())
        return node

    def _unary(self) -> Node:
        t = self._peek()
        if t.kind in {"NOT", "MINUS"}:
            self._advance()
            inner = self._unary()
            return Not(inner)
        return self._atom()

    def _atom(self) -> Node:
        t = self._advance()
        if t.kind == "WORD":
            assert isinstance(t.value, str)
            return Term(t.value)
        if t.kind == "PHRASE":
            assert isinstance(t.value, str)
            return Phrase(t.value)
        if t.kind == "PREFIX":
            assert isinstance(t.value, str)
            return Prefix(t.value)
        if t.kind == "FIELD":
            assert isinstance(t.value, tuple)
            field, value, op, prefix = t.value
            return FieldFilter(field, value, op, prefix)
        if t.kind == "LPAREN":
            inner = self._or_expr()
            self._expect("RPAREN")
            return inner
        raise ParseError(
            f"Unexpected {t.kind} ({t.value!r}) at position {t.pos}"
        )


def parse(query: str) -> Node:
    """Parse a query string into an AST. Empty input → Empty().

    Raises ParseError on malformed input.
    """
    if not isinstance(query, str):
        raise TypeError(f"query must be str, got {type(query).__name__}")
    tokens = _tokenize(query)
    return _Parser(tokens).parse()
