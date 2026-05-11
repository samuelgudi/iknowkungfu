# Bad fixture: same-slug-collision

Violates rule: **slug collision** — two skills from different authors share the same slug `colliding-slug`.

Sub-fixtures:
- `author-x/` — `id: "author-x/colliding-slug"`
- `author-y/` — `id: "author-y/colliding-slug"`

Expected validation error: slug `colliding-slug` is already registered by a different author.
