# Bad fixture: slug-path-traversal

Violates rule: **slug grammar** — `id` contains a path-traversal sequence (`"test-author/../etc"`).

Expected validation error: slug must match `^[a-z][a-z0-9-]{0,38}[a-z0-9]$`.
