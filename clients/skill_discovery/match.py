"""Keyword + filter scoring."""
from __future__ import annotations

import math
import re
from collections import Counter


STOPWORDS = {"a", "an", "the", "and", "or", "but", "with", "for", "from", "of", "to", "in", "on"}
TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall((text or "").lower()) if t not in STOPWORDS]


def jaccard_idf(query_tokens: set[str], target_tokens: list[str], idf: dict[str, float]) -> float:
    target_set = set(target_tokens)
    if not query_tokens or not target_set:
        return 0.0
    intersection_score = sum(idf.get(t, 1.0) for t in query_tokens & target_set)
    union_score = sum(idf.get(t, 1.0) for t in query_tokens | target_set) or 1.0
    return intersection_score / union_score


def build_idf(skills: list[dict]) -> dict[str, float]:
    N = max(1, len(skills))
    df = Counter()
    for s in skills:
        terms = set(
            tokenize(s["name"])
            + tokenize(s["description"])
            + sum((tokenize(t) for t in s.get("tags", [])), [])
        )
        for term in terms:
            df[term] += 1
    return {term: math.log(1 + N / max(1, freq)) for term, freq in df.items()}


def filter_yanked_latest(s: dict) -> bool:
    versions = s.get("versions", {})
    if not versions:
        return True
    return any(not v.get("yanked", False) for v in versions.values())


def score(query: str, skill: dict, idf: dict[str, float]) -> float:
    q = set(tokenize(query))
    n = jaccard_idf(q, tokenize(skill["name"]), idf)
    d = jaccard_idf(q, tokenize(skill["description"]), idf)
    t = jaccard_idf(q, [tok for tag in skill.get("tags", []) for tok in tokenize(tag)], idf)
    desc_len = len(skill["description"])
    length_factor = 1.0 if desc_len <= 500 else max(0.5, 500 / desc_len)
    return (0.45 * n + 0.40 * d + 0.15 * t) * length_factor


def _version_sort_key(version: str) -> tuple[int, ...]:
    """Return a tuple suitable for descending version sort (higher version = smaller key)."""
    parts = (version + ".0.0.0").split(".")[:3]
    return tuple(-int(x) for x in parts)


def rank(
    query: str,
    registry: dict,
    *,
    agent: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    platform: str | None = None,
    limit: int = 5,
    include_archived: bool = False,
) -> list[dict]:
    skills = registry["skills"]
    candidates = []
    for s in skills:
        if s.get("status") == "deprecated" and not include_archived:
            continue
        if not filter_yanked_latest(s):
            continue
        if agent and agent not in s.get("agent_compat", []):
            continue
        if category and s.get("category") != category:
            continue
        if tag and tag not in s.get("tags", []):
            continue
        if platform and platform not in s.get("platforms", []):
            continue
        candidates.append(s)
    idf = build_idf(skills)
    # Sort by: descending score, descending version (via negated-int tuple), then id ascending.
    # Bug fix: the plan's `-tuple(int(x) for x in ...)` raises TypeError because you cannot negate
    # a tuple. Fixed by using `_version_sort_key` which returns `tuple(-int(x) for x in ...)`,
    # a tuple of negative ints that sorts ascending (lowest = highest version), achieving
    # descending-version ordering without the unary-minus-on-tuple error.
    scored = sorted(
        candidates,
        key=lambda s: (
            -score(query, s, idf),
            _version_sort_key(s["version"]),
            s["id"],
        ),
    )
    out = []
    for s in scored[:limit]:
        out.append({**s, "score": round(score(query, s, idf), 3)})
    return out
