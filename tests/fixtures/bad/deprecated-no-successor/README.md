# Bad fixture: deprecated-no-successor

Violates rule: **deprecation requires successor** — `status` is `"deprecated"` but `superseded_by` is `null`.

Expected validation error: deprecated skills must set `superseded_by` to a non-null skill ID.
