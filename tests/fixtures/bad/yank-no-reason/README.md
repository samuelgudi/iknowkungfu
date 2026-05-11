# Bad fixture: yank-no-reason

Violates rule: **yank reason required** — a `yanks.json` entry for this skill has `"reason": ""` (empty string).

This fixture contains only a stub `meta.json` + `SKILL.md`. The violation is exercised at test setup by injecting the following `yanks.json` entry:

```json
{
  "id": "test-author/yank-no-reason-skill",
  "version": "0.1.0",
  "yanked_at": "2026-05-11T00:00:00Z",
  "yanked_by": "test-author",
  "reason": ""
}
```

Expected validation error: `reason` field in yanks.json entry must be a non-empty string.
