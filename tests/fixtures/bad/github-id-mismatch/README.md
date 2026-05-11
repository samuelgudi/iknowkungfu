# Bad fixture: github-id-mismatch

Violates rule: **github_id mismatch** — `author.github_id` is `99999999` in meta.json, but the `fake_gh` conftest fixture returns `{"id": 12345678, "login": "test-author"}` from `gh api`.

Tests using this fixture must activate `fake_gh` to simulate the GitHub API response.

Expected validation error: `author.github_id` does not match the GitHub API response for `author.github_login`.
