# Bad fixture: deprecated-cycle

Violates rule: **deprecation cycle** — `a` is superseded by `b`, and `b` is superseded by `a`, forming a cycle.

Sub-fixtures:
- `a/` — `superseded_by: "test-author/cycle-b"`
- `b/` — `superseded_by: "test-author/cycle-a"`

Expected validation error: circular `superseded_by` chain detected.
