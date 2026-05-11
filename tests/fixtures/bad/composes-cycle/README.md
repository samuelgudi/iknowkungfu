# Bad fixture: composes-cycle

Violates rule: **composes cycle** — `a` composes `b`, and `b` composes `a`, forming a cycle.

Sub-fixtures:
- `a/` — `composes: ["test-author/comp-b"]`
- `b/` — `composes: ["test-author/comp-a"]`

Expected validation error: circular `composes` dependency detected.
