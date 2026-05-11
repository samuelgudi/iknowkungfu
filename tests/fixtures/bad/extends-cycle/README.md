# Bad fixture: extends-cycle

Violates rule: **extends cycle** — `a` extends `b`, and `b` extends `a`, forming a cycle.

Sub-fixtures:
- `a/` — `extends: "test-author/ext-b"`
- `b/` — `extends: "test-author/ext-a"`

Expected validation error: circular `extends` dependency detected.
